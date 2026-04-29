from __future__ import annotations

import math
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import numpy as np

from .config import PortableRAGConfig, load_portable_config
from .retrievers import BM25Retriever, CharNgramTfidfRetriever, TfidfRetriever, rrf_fuse
from .schemas import AnswerPack, EvidenceUnit, RetrievalHit, stable_id
from .semantic import SemanticReranker
from .structure import build_or_load_structured_units
from .text import normalize_text, split_sentences, tokenize


@dataclass
class ScoredEvidence:
    hit: RetrievalHit
    score: float
    coverage: float
    novelty_text: str


@dataclass
class ScoredSpan:
    text: str
    hit: RetrievalHit
    score: float
    coverage: float
    matched_terms: set[str]


class PortableRAGV4:
    """Training-free, rule-free portable RAG.

    v4 intentionally avoids question-type branches and hand-written domain
    rules. It uses corpus statistics only: source-level retrieval, unit-level
    retrieval, pseudo relevance feedback, IDF-weighted evidence scoring, and
    MMR span selection.
    """

    def __init__(self, config: PortableRAGConfig):
        self.config = config
        dense_config = (config.raw.get("indexes") or {}).get("dense") or {}
        self.semantic = SemanticReranker.try_create() if dense_config.get("enabled", False) else None
        self.documents, self.units = build_or_load_structured_units(
            config.data_dir,
            cache_path=config.index_dir / "portable_structured_units_v2.jsonl",
        )
        self.units_by_source = self.group_units_by_source(self.units)
        self.context_units = self.build_context_units(window_size=5, stride=2)
        self.context_units_by_source = self.group_units_by_source(self.context_units)
        self.context_index_by_id = {unit.unit_id: idx for idx, unit in enumerate(self.context_units)}
        self.source_units = self.build_source_units()
        self.idf = self.build_idf(self.units)
        self._last_semantic_question = ""
        self._last_semantic_scores: np.ndarray | None = None
        self._last_reader_candidates: List[RetrievalHit] = []

        self.unit_bm25 = BM25Retriever(self.units)
        self.unit_tfidf = TfidfRetriever(self.units)
        self.unit_char_tfidf = CharNgramTfidfRetriever(self.units)
        self.context_bm25 = BM25Retriever(self.context_units)
        self.context_tfidf = TfidfRetriever(self.context_units)
        self.source_bm25 = BM25Retriever(self.source_units)
        self.source_tfidf = TfidfRetriever(self.source_units)
        self.semantic_context_embeddings = self.load_or_build_semantic_context_index()

    @classmethod
    def from_config(cls, path: str | None = None) -> "PortableRAGV4":
        return cls(load_portable_config(path))

    def answer(self, question: str, top_k: int | None = None) -> AnswerPack:
        hits, trace = self.retrieve(question, top_k=top_k)
        confidence = float(trace["retrieval_confidence"])
        anchor_support = float(trace.get("anchor_support", 0.0))
        if not hits or confidence < self.answer_threshold(question) or anchor_support < self.anchor_threshold(question):
            return AnswerPack(
                question=question,
                answer="知识库证据不足，暂时不能给出确定答案。",
                status="insufficient_evidence",
                confidence=confidence,
                hits=hits,
                citations=[],
                trace={
                    **trace,
                    "anchor_threshold": self.anchor_threshold(question),
                    "abstain_reason": "low_statistical_support",
                },
            )

        spans, citations, answer_trace, answer_hits = self.compose_answer(question, hits)
        trace.update(answer_trace)
        if not spans:
            return AnswerPack(
                question=question,
                answer="知识库证据不足，暂时不能给出确定答案。",
                status="insufficient_evidence",
                confidence=confidence,
                hits=hits,
                citations=[],
                trace={**trace, "abstain_reason": "no_supported_span"},
            )
        final_hits = self.final_answer_hits(answer_hits, hits, top_k or self.config.top_k)

        return AnswerPack(
            question=question,
            answer="根据知识库，" + "；".join(spans),
            status="answered",
            confidence=confidence,
            hits=final_hits,
            citations=citations,
            trace=trace,
        )

    def retrieve(self, question: str, top_k: int | None = None) -> tuple[List[RetrievalHit], Dict]:
        top_k = top_k or self.config.top_k
        candidate_k = max(top_k * 8, self.config.candidate_k * 2)
        source_k = min(10, max(4, top_k))
        queries = self.build_queries(question)

        source_lists = []
        for query in queries[:2]:
            source_lists.append(self.source_bm25.search(query, source_k))
            source_lists.append(self.source_tfidf.search(query, source_k))
        semantic_source_hits: List[RetrievalHit] = []
        source_hits = rrf_fuse(source_lists, top_k=source_k, rrf_k=self.config.rrf_k, max_chunks_per_source=source_k)
        source_scores = {hit.evidence.source: 1.0 / (rank + 1) for rank, hit in enumerate(source_hits)}

        unit_lists = []
        for query in queries:
            unit_lists.append(self.unit_bm25.search(query, candidate_k))
            unit_lists.append(self.unit_tfidf.search(query, candidate_k))
            unit_lists.append(self.context_bm25.search(query, candidate_k))
            unit_lists.append(self.context_tfidf.search(query, candidate_k))
        semantic_context_hits = self.semantic_context_hits(question, top_k=max(candidate_k * 4, 256))
        if semantic_context_hits:
            unit_lists.append(semantic_context_hits)
        first_pass = rrf_fuse(unit_lists, top_k=candidate_k, rrf_k=self.config.rrf_k, max_chunks_per_source=candidate_k)

        feedback_terms: List[str] = []
        first_pass_anchor_support = self.anchor_support(question, first_pass[:top_k])
        used_feedback = False
        if used_feedback:
            feedback_query = " ".join([question] + feedback_terms)
            unit_lists.append(self.unit_bm25.search(feedback_query, candidate_k))
            unit_lists.append(self.unit_tfidf.search(feedback_query, candidate_k))
            unit_lists.append(self.context_bm25.search(feedback_query, candidate_k))
            unit_lists.append(self.context_tfidf.search(feedback_query, candidate_k))
        else:
            feedback_terms = []

        lexical_confidence = self.statistical_confidence(question, first_pass[:top_k])
        used_char = lexical_confidence < max(0.42, self.config.low_confidence + 0.18)
        if used_char:
            for query in queries[:2]:
                unit_lists.append(self.unit_char_tfidf.search(query, max(top_k * 4, self.config.candidate_k)))

        source_pool = self.source_constrained_hits(question, source_hits, per_source=max(30, top_k * 5))
        if source_pool:
            unit_lists.append(source_pool)

        fused = rrf_fuse(unit_lists, top_k=candidate_k, rrf_k=self.config.rrf_k, max_chunks_per_source=candidate_k)
        scored = self.score_evidence(question, fused, source_scores)
        hits = self.mmr_evidence(scored, top_k)
        self._last_reader_candidates = dedupe_hits(
            list(hits)
            + semantic_context_hits[: max(top_k * 4, 32)]
            + [item.hit for item in scored[: max(top_k * 4, 32)]]
        )
        confidence = self.statistical_confidence(question, hits)
        selected_anchor_support = self.anchor_support(question, hits)
        candidate_anchor_support = self.anchor_support(
            question,
            [item.hit for item in scored[: max(top_k * 3, 16)]],
        )
        trace = {
            "pipeline": "portable_rag_v4_training_free_rule_free",
            "document_count": len(self.documents),
            "evidence_unit_count": len(self.units),
            "context_unit_count": len(self.context_units),
            "candidate_k": candidate_k,
            "source_k": source_k,
            "queries": queries,
            "anchor_terms": self.anchor_terms(question),
            "semantic_source_count": len(semantic_source_hits),
            "feedback_terms": feedback_terms,
            "used_feedback": used_feedback,
            "used_char_retrieval": used_char,
            "semantic_enabled": self.semantic is not None,
            "semantic_model": "" if self.semantic is None else str(self.semantic.model_path),
            "semantic_context_index": self.semantic_context_embeddings is not None,
            "semantic_context_count": 0 if self.semantic_context_embeddings is None else int(self.semantic_context_embeddings.shape[0]),
            "lexical_confidence": lexical_confidence,
            "anchor_support": max(selected_anchor_support, candidate_anchor_support),
            "selected_anchor_support": selected_anchor_support,
            "candidate_anchor_support": candidate_anchor_support,
            "retrieval_confidence": confidence,
            "answer_threshold": self.answer_threshold(question),
        }
        return hits, trace

    def build_queries(self, question: str) -> List[str]:
        terms = self.query_terms(question)
        queries = [normalize_text(question)]
        if terms:
            queries.append(" ".join(terms[:8]))
        if len(terms) >= 4:
            queries.append(" ".join(terms[:4]))
            queries.append(" ".join(terms[-4:]))
        return [query for query in dict.fromkeys(queries) if query]

    def query_terms(self, text: str) -> List[str]:
        terms = tokenize(text)
        terms.sort(key=lambda term: self.idf_value(term), reverse=True)
        return terms

    def feedback_terms(self, question: str, hits: Sequence[RetrievalHit], limit: int) -> List[str]:
        if limit <= 0:
            return []
        question_terms = set(tokenize(question))
        anchor_terms = self.anchor_terms(question)
        counts: Counter[str] = Counter()
        doc_counts: Counter[str] = Counter()
        for hit in hits:
            coverage = weighted_coverage(question_terms, block_text(hit.evidence), self.idf)
            anchor_coverage = self.weighted_term_coverage(anchor_terms, evidence_text(hit.evidence))
            if coverage < 0.32 or anchor_coverage < 0.35:
                continue
            seen_terms = set()
            for term in tokenize(block_text(hit.evidence)):
                if term in question_terms:
                    continue
                score = (coverage * 0.55 + anchor_coverage * 0.45) * self.idf_value(term)
                counts[term] += score
                seen_terms.add(term)
            doc_counts.update(seen_terms)
        supported_terms = {
            term: score
            for term, score in counts.items()
            if doc_counts[term] >= 2 and 2 <= len(normalize_compact(term)) <= 10
        }
        return [term for term, _ in Counter(supported_terms).most_common(limit)]

    def source_constrained_hits(
        self,
        question: str,
        source_hits: Sequence[RetrievalHit],
        per_source: int,
    ) -> List[RetrievalHit]:
        output: List[RetrievalHit] = []
        for source_rank, source_hit in enumerate(source_hits, start=1):
            units = self.context_units_by_source.get(source_hit.evidence.source) or self.units_by_source.get(
                source_hit.evidence.source, []
            )
            scored = []
            for unit in units:
                score = self.raw_evidence_score(question, unit, source_bonus=1.0 / (source_rank + 1))
                if score > 0:
                    scored.append((score, unit))
            scored.sort(key=lambda item: item[0], reverse=True)
            for rank, (score, unit) in enumerate(scored[:per_source], start=1):
                output.append(
                    RetrievalHit(
                        evidence=unit,
                        score=score,
                        rank=rank,
                        retriever="source_constrained",
                        signals={"source_rank": source_rank},
                    )
                )
        return output

    def semantic_context_hits(self, question: str, top_k: int) -> List[RetrievalHit]:
        if self.semantic is None or self.semantic_context_embeddings is None or len(self.context_units) == 0:
            return []
        try:
            query_vec = self.semantic.embed_query(question)
        except Exception:
            return []
        scores = np.matmul(self.semantic_context_embeddings, query_vec)
        self._last_semantic_question = question
        self._last_semantic_scores = scores
        if scores.size == 0:
            return []
        top_k = min(top_k, scores.size)
        top_indices = np.argpartition(-scores, top_k - 1)[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]
        output = []
        for rank, idx in enumerate(top_indices, start=1):
            score = float(scores[idx])
            if score <= 0:
                continue
            output.append(
                RetrievalHit(
                    evidence=self.context_units[int(idx)],
                    score=score,
                    rank=rank,
                    retriever="semantic_context",
                    signals={"semantic_context": round(score, 6), "v4_semantic": round(score, 6)},
                )
            )
        return output

    def semantic_source_hits(self, question: str, top_k: int) -> List[RetrievalHit]:
        if self.semantic is None:
            return []
        texts = [evidence_text(unit)[:1200] for unit in self.source_units]
        try:
            scores = self.semantic.score(question, texts)
        except Exception:
            return []
        ranked = sorted(zip(scores, self.source_units), key=lambda item: item[0], reverse=True)
        output = []
        for rank, (score, unit) in enumerate(ranked[:top_k], start=1):
            if score <= 0:
                continue
            output.append(
                RetrievalHit(
                    evidence=unit,
                    score=float(score),
                    rank=rank,
                    retriever="semantic_source",
                    signals={"semantic_source": round(float(score), 6)},
                )
            )
        return output

    def semantic_rescore_units(
        self,
        question: str,
        scored_units: Sequence[tuple[float, EvidenceUnit]],
        source_rank: int,
    ) -> List[tuple[float, EvidenceUnit]]:
        if self.semantic is None or not scored_units:
            return list(scored_units)
        texts = [evidence_text(unit)[:900] for _, unit in scored_units]
        try:
            semantic_scores = self.semantic.score(question, texts)
        except Exception:
            return list(scored_units)
        output = []
        for (lexical_score, unit), semantic_score in zip(scored_units, semantic_scores):
            score = self.raw_evidence_score(
                question,
                unit,
                source_bonus=1.0 / (source_rank + 1),
                semantic_score=max(0.0, semantic_score),
            )
            output.append((score, unit))
        output.sort(key=lambda item: item[0], reverse=True)
        return output

    def score_evidence(
        self,
        question: str,
        hits: Sequence[RetrievalHit],
        source_scores: Dict[str, float],
    ) -> List[ScoredEvidence]:
        output = []
        seen = set()
        hit_list = list(hits)
        semantic_scores = self.semantic_scores(question, hit_list)
        for hit in hit_list:
            if hit.evidence.unit_id in seen:
                continue
            seen.add(hit.evidence.unit_id)
            source_bonus = source_scores.get(hit.evidence.source, 0.0)
            semantic_score = semantic_scores.get(hit.evidence.unit_id, 0.0)
            score = self.raw_evidence_score(question, hit.evidence, source_bonus=source_bonus, semantic_score=semantic_score)
            coverage = weighted_coverage(self.query_terms(question), evidence_text(hit.evidence), self.idf)
            if score <= 0:
                continue
            output.append(
                ScoredEvidence(
                    hit=RetrievalHit(
                        evidence=hit.evidence,
                        score=hit.score,
                        rank=hit.rank,
                        retriever=f"{hit.retriever}+v4_score",
                        signals={
                            **hit.signals,
                            "v4_score": round(score, 6),
                            "v4_coverage": round(coverage, 6),
                            "v4_semantic": round(semantic_score, 6),
                        },
                    ),
                    score=score,
                    coverage=coverage,
                    novelty_text=evidence_text(hit.evidence),
                )
            )
        output.sort(key=lambda item: (item.score, item.coverage), reverse=True)
        return output

    def raw_evidence_score(
        self,
        question: str,
        unit: EvidenceUnit,
        source_bonus: float,
        semantic_score: float = 0.0,
    ) -> float:
        query_terms = self.query_terms(question)
        anchors = self.anchor_terms(question)
        text = evidence_text(unit)
        body = block_text(unit)
        coverage = weighted_coverage(query_terms, text, self.idf)
        anchor_coverage = self.weighted_term_coverage(anchors, text)
        title_coverage = weighted_coverage(query_terms, evidence_title_text(unit), self.idf)
        proximity = proximity_score(query_terms, body)
        char_overlap = char_overlap_score(question, text)
        length = length_prior(body)
        return (
            coverage * 2.2
            + anchor_coverage * 1.75
            + title_coverage * 0.65
            + proximity * 0.65
            + char_overlap * 0.95
            + max(0.0, semantic_score) * 2.2
            + information_density(body) * 0.65
            + length * 0.30
            + source_bonus * 0.40
        )

    def mmr_evidence(self, scored: Sequence[ScoredEvidence], top_k: int) -> List[RetrievalHit]:
        if not scored:
            return []
        selected: List[ScoredEvidence] = []
        pool = list(scored[: max(top_k * 8, 40)])
        max_score = max(item.score for item in pool) or 1.0
        while pool and len(selected) < top_k:
            best_idx = 0
            best_value = -math.inf
            for idx, item in enumerate(pool):
                relevance = item.score / max_score
                redundancy = max((char_jaccard(item.novelty_text, prev.novelty_text) for prev in selected), default=0.0)
                value = 0.78 * relevance - 0.22 * redundancy
                if value > best_value:
                    best_idx = idx
                    best_value = value
            selected.append(pool.pop(best_idx))
        return [
            RetrievalHit(
                evidence=item.hit.evidence,
                score=item.hit.score,
                rank=rank,
                retriever=f"{item.hit.retriever}+v4_mmr",
                signals={**item.hit.signals, "v4_mmr_score": round(item.score, 6)},
            )
            for rank, item in enumerate(selected, start=1)
        ]

    def statistical_confidence(self, question: str, hits: Sequence[RetrievalHit]) -> float:
        if not hits:
            return 0.0
        terms = self.query_terms(question)
        top = weighted_coverage(terms, evidence_text(hits[0].evidence), self.idf)
        context = weighted_coverage(terms, " ".join(evidence_text(hit.evidence) for hit in hits[:5]), self.idf)
        anchors = self.anchor_support(question, hits)
        support = sum(1 for hit in hits[:8] if weighted_coverage(terms, evidence_text(hit.evidence), self.idf) >= 0.28)
        agreement = min(1.0, support / 4.0)
        semantic = max((float(hit.signals.get("v4_semantic", 0.0)) for hit in hits[:5]), default=0.0)
        return round(min(1.0, top * 0.28 + context * 0.28 + anchors * 0.22 + agreement * 0.07 + semantic * 0.15), 6)

    def answer_threshold(self, question: str) -> float:
        term_count = len(self.query_terms(question))
        base = max(0.34, self.config.low_confidence)
        if term_count >= 6:
            return base + 0.03
        if term_count <= 2:
            return base + 0.05
        return base

    def anchor_terms(self, question: str) -> List[str]:
        terms = self.query_terms(question)
        if not terms:
            return []
        known_terms = [term for term in terms if term in self.idf]
        unknown_terms = [term for term in terms if term not in self.idf and len(normalize_compact(term)) >= 2]
        anchor_count = min(4, max(2, math.ceil(len(terms) * 0.45)))
        anchors = unknown_terms[:2] + known_terms[:anchor_count]
        return list(dict.fromkeys(anchors)) or terms[:anchor_count]

    def anchor_support(self, question: str, hits: Sequence[RetrievalHit]) -> float:
        anchors = self.anchor_terms(question)
        if not anchors or not hits:
            return 0.0
        evidence = " ".join(evidence_text(hit.evidence) for hit in hits[:5])
        support = self.weighted_term_coverage(anchors, evidence)
        char_support = char_overlap_score(" ".join(anchors), evidence)
        return round(min(1.0, support * 0.82 + char_support * 0.18), 6)

    def anchor_threshold(self, question: str) -> float:
        anchors = self.anchor_terms(question)
        if len(anchors) <= 2:
            return 0.45
        return 0.42

    def weighted_term_coverage(self, terms: Iterable[str], text: str) -> float:
        unique_terms = list(dict.fromkeys(term for term in terms if term))
        if not unique_terms:
            return 0.0
        haystack = normalize_compact(text)
        total = sum(self.idf_value(term) for term in unique_terms)
        if total <= 0:
            return 0.0
        matched = 0.0
        for term in unique_terms:
            if normalize_compact(term) in haystack:
                matched += self.idf_value(term)
        return matched / total

    def semantic_scores(self, question: str, hits: Sequence[RetrievalHit]) -> Dict[str, float]:
        if self.semantic is None or not hits:
            return {}
        if self._last_semantic_question == question and self._last_semantic_scores is not None:
            output = {}
            for hit in hits:
                idx = self.context_index_by_id.get(hit.evidence.unit_id)
                if idx is not None:
                    output[hit.evidence.unit_id] = max(0.0, float(self._last_semantic_scores[idx]))
            return output
        limited = list(hits[: max(96, self.config.candidate_k * 3)])
        texts = [evidence_text(hit.evidence)[:900] for hit in limited]
        try:
            scores = self.semantic.score(question, texts)
        except Exception:
            return {}
        return {hit.evidence.unit_id: max(0.0, score) for hit, score in zip(limited, scores)}

    def load_or_build_semantic_context_index(self) -> np.ndarray | None:
        if self.semantic is None:
            return None
        self.config.index_dir.mkdir(parents=True, exist_ok=True)
        model_key = stable_id("semantic-model", str(self.semantic.model_path))
        ids_path = self.config.index_dir / f"portable_v4_semantic_context_ids_{model_key}.json"
        npy_path = self.config.index_dir / f"portable_v4_semantic_context_{model_key}.npy"
        current_ids = [unit.unit_id for unit in self.context_units]
        if ids_path.exists() and npy_path.exists():
            try:
                cached_ids = json.loads(ids_path.read_text(encoding="utf-8"))
                embeddings = np.load(npy_path)
                if cached_ids == current_ids and embeddings.shape[0] == len(current_ids):
                    return np.asarray(embeddings, dtype=np.float32)
            except Exception:
                pass
        texts = [evidence_text(unit)[:900] for unit in self.context_units]
        try:
            embeddings = self.semantic.embed(texts, batch_size=48)
        except Exception:
            return None
        np.save(npy_path, embeddings)
        ids_path.write_text(json.dumps(current_ids, ensure_ascii=False), encoding="utf-8")
        return np.asarray(embeddings, dtype=np.float32)

    def compose_answer(self, question: str, hits: Sequence[RetrievalHit]) -> tuple[List[str], List[Dict], Dict, List[RetrievalHit]]:
        seed_hits = self.reader_seed_hits(hits)
        focused_hits, focus_trace = self.focus_hits_by_source(question, seed_hits)
        expanded_hits, expansion_trace = self.expand_focus_neighbors(question, focused_hits)
        spans = self.score_spans(question, expanded_hits)
        selected = self.coverage_spans(
            question,
            spans,
            max_parts=5,
            max_chars=max(1400, self.config.max_context_chars // 3),
        )
        citations = self.build_citations(selected)
        answer_hits = [span.hit for span in selected]
        return [span.text for span in selected], citations, {
            **focus_trace,
            **expansion_trace,
            "answer_span_count": len(spans),
            "selected_span_count": len(selected),
            "top_span_score": round(spans[0].score, 6) if spans else 0.0,
            "answer_seed_hit_count": len(seed_hits),
        }, answer_hits

    def reader_seed_hits(self, hits: Sequence[RetrievalHit]) -> List[RetrievalHit]:
        candidates = list(hits)
        candidates.extend(self._last_reader_candidates)
        return dedupe_hits(candidates)

    def final_answer_hits(
        self,
        answer_hits: Sequence[RetrievalHit],
        retrieval_hits: Sequence[RetrievalHit],
        limit: int,
    ) -> List[RetrievalHit]:
        merged = dedupe_hits(list(answer_hits) + list(retrieval_hits))
        output = []
        for rank, hit in enumerate(merged[:limit], start=1):
            output.append(
                RetrievalHit(
                    evidence=hit.evidence,
                    score=hit.score,
                    rank=rank,
                    retriever=hit.retriever,
                    signals=hit.signals,
                )
            )
        return output

    def focus_hits_by_source(self, question: str, hits: Sequence[RetrievalHit]) -> tuple[List[RetrievalHit], Dict]:
        if not hits:
            return [], {"answer_focus_source": "", "answer_focus_hit_count": 0}
        query_terms = self.query_terms(question)
        anchors = self.anchor_terms(question)
        source_scores: Dict[str, float] = defaultdict(float)
        for hit in hits:
            semantic = float(hit.signals.get("v4_semantic", 0.0))
            evidence = evidence_text(hit.evidence)
            evidence_score = float(hit.signals.get("v4_mmr_score", hit.signals.get("v4_score", hit.score)))
            coverage = weighted_coverage(query_terms, evidence, self.idf)
            anchor_coverage = self.weighted_term_coverage(anchors, evidence)
            rank_discount = 1.0 / math.log2(hit.rank + 2)
            source_scores[hit.evidence.source] += (
                evidence_score * 0.18 + coverage * 1.15 + anchor_coverage * 0.90 + semantic * 0.35
            ) * rank_discount
        ranked_sources = sorted(source_scores.items(), key=lambda item: item[1], reverse=True)
        best_source, best_score = ranked_sources[0]
        selected_sources = {best_source}
        for source, score in ranked_sources[1:3]:
            if best_score > 0 and score / best_score >= 0.72:
                selected_sources.add(source)
        focused = [hit for hit in hits if hit.evidence.source in selected_sources]
        if len(focused) < 2 and len(hits) >= 2:
            focused = list(hits[: min(5, len(hits))])
            best_source = "mixed"
        return focused, {
            "answer_focus_source": best_source,
            "answer_focus_score": round(best_score, 6),
            "answer_focus_sources": [source for source, _ in ranked_sources[:3]],
            "answer_focus_hit_count": len(focused),
        }

    def expand_focus_neighbors(
        self,
        question: str,
        hits: Sequence[RetrievalHit],
    ) -> tuple[List[RetrievalHit], Dict]:
        if not hits:
            return [], {"answer_expanded_hit_count": 0, "answer_neighbor_hit_count": 0}
        output: Dict[str, RetrievalHit] = {hit.evidence.unit_id: hit for hit in hits}
        neighbor_candidates: List[tuple[float, int, EvidenceUnit, RetrievalHit]] = []
        for hit in hits:
            hit_range = unit_line_range(hit.evidence)
            if hit_range is None:
                continue
            contexts = self.context_units_by_source.get(hit.evidence.source, [])
            for unit in contexts:
                if unit.unit_id in output:
                    continue
                distance = line_range_distance(hit_range, unit_line_range(unit))
                if distance is None:
                    continue
                if distance > 8:
                    continue
                score = self.raw_evidence_score(question, unit, source_bonus=1.0 / (hit.rank + 1))
                if score <= 0:
                    continue
                neighbor_candidates.append((score, distance, unit, hit))
        neighbor_candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        neighbor_limit = max(16, len(hits) * 4)
        added = 0
        for rank_offset, (score, distance, unit, parent_hit) in enumerate(neighbor_candidates[:neighbor_limit], start=1):
            if unit.unit_id in output:
                continue
            output[unit.unit_id] = RetrievalHit(
                evidence=unit,
                score=score,
                rank=parent_hit.rank + rank_offset / 1000,
                retriever=f"{parent_hit.retriever}+source_neighbor",
                signals={
                    **parent_hit.signals,
                    "neighbor_distance": distance,
                    "neighbor_score": round(score, 6),
                },
            )
            added += 1
        expanded = sorted(output.values(), key=lambda hit: (hit.evidence.source, source_position_key(hit.evidence), hit.rank))
        return expanded, {
            "answer_expanded_hit_count": len(expanded),
            "answer_neighbor_hit_count": added,
        }

    def score_spans(self, question: str, hits: Sequence[RetrievalHit]) -> List[ScoredSpan]:
        output: List[ScoredSpan] = []
        query_terms = self.query_terms(question)
        anchors = self.anchor_terms(question)
        for hit in hits:
            for span in candidate_spans(block_text(hit.evidence)):
                coverage = weighted_coverage(query_terms, span, self.idf)
                if coverage <= 0:
                    continue
                anchor_coverage = self.weighted_term_coverage(anchors, span)
                semantic = float(hit.signals.get("v4_semantic", 0.0))
                score = (
                    coverage * 3.0
                    + anchor_coverage * 1.15
                    + proximity_score(query_terms, span) * 0.9
                    + length_prior(span) * 0.45
                    + semantic * 0.8
                    + information_density(span) * 0.75
                    + 1.0 / (hit.rank + 2)
                )
                output.append(
                    ScoredSpan(
                        text=dedupe_repeated_sentences(span),
                        hit=hit,
                        score=score,
                        coverage=coverage,
                        matched_terms=matched_terms(query_terms, span),
                    )
                )
        return self.semantic_rerank_spans(question, output)

    def semantic_rerank_spans(self, question: str, spans: Sequence[ScoredSpan]) -> List[ScoredSpan]:
        output = sorted(spans, key=lambda item: (item.score, item.coverage), reverse=True)
        if self.semantic is None or not output:
            return output
        rerank_limit = min(128, len(output))
        try:
            semantic_scores = self.semantic.score(question, [span.text[:900] for span in output[:rerank_limit]], batch_size=32)
        except Exception:
            return output
        for span, semantic_score in zip(output[:rerank_limit], semantic_scores):
            span.score += max(0.0, semantic_score) * 1.15
        output.sort(key=lambda item: (item.score, item.coverage), reverse=True)
        return output

    def coverage_spans(
        self,
        question: str,
        spans: Sequence[ScoredSpan],
        max_parts: int,
        max_chars: int,
    ) -> List[ScoredSpan]:
        selected: List[ScoredSpan] = []
        used_chars = 0
        query_terms = self.query_terms(question)
        term_weight = {term: self.idf_value(term) for term in query_terms}
        total_weight = sum(term_weight.values()) or 1.0
        covered_terms: set[str] = set()
        pool = list(spans[:80])
        max_score = max((span.score for span in pool), default=1.0)
        while pool and len(selected) < max_parts and used_chars < max_chars:
            best_idx = 0
            best_value = -math.inf
            for idx, span in enumerate(pool):
                new_terms = span.matched_terms - covered_terms
                marginal = sum(term_weight.get(term, 0.0) for term in new_terms) / total_weight
                redundancy = max((char_jaccard(span.text, old.text) for old in selected), default=0.0)
                value = 0.48 * (span.score / max_score) + 0.42 * marginal + 0.10 * span.coverage - 0.30 * redundancy
                if value > best_value:
                    best_idx = idx
                    best_value = value
            chosen = pool.pop(best_idx)
            if any(is_subsumed(chosen.text, item.text) for item in selected):
                continue
            selected.append(chosen)
            covered_terms.update(chosen.matched_terms)
            used_chars += len(chosen.text)
        selected.sort(key=lambda item: (item.hit.evidence.source, source_position_key(item.hit.evidence), item.hit.rank))
        return selected

    def build_citations(self, spans: Sequence[ScoredSpan]) -> List[Dict]:
        citations = []
        seen = set()
        for span in spans:
            unit_id = span.hit.evidence.unit_id
            if unit_id in seen:
                continue
            seen.add(unit_id)
            citations.append(
                {
                    "rank": span.hit.rank,
                    "source": span.hit.evidence.source,
                    "title": span.hit.evidence.title,
                    "unit_id": unit_id,
                    "score": round(span.hit.score, 6),
                    "answer_score": round(span.score, 6),
                    "unit_type": span.hit.evidence.unit_type,
                }
            )
        return citations

    def build_source_units(self) -> List[EvidenceUnit]:
        output = []
        for source, units in self.units_by_source.items():
            title = next((unit.title for unit in units if unit.title), source)
            text_parts = []
            for unit in units:
                text_parts.append(evidence_text(unit))
                if sum(len(part) for part in text_parts) > 24000:
                    break
            text = normalize_text(" ".join(text_parts))
            output.append(
                EvidenceUnit(
                    unit_id=stable_id("source", source),
                    parent_id=stable_id("source-parent", source),
                    text=text,
                    source=source,
                    title=title,
                    unit_type="source",
                    heading_path=[],
                    metadata={"unit_count": len(units)},
                )
            )
        return output

    def build_context_units(self, window_size: int, stride: int) -> List[EvidenceUnit]:
        output: List[EvidenceUnit] = []
        for source, units in self.units_by_source.items():
            ordered = sorted(units, key=unit_order_key)
            for start in range(0, len(ordered), max(1, stride)):
                window = ordered[start : start + window_size]
                if len(window) < 2:
                    continue
                text = normalize_text(" ".join(block_text(unit) for unit in window))
                if len(text) < 30:
                    continue
                first = window[0]
                line_indexes = [
                    int(unit.metadata.get("line_index", -1))
                    for unit in window
                    if isinstance(unit.metadata.get("line_index", -1), int)
                ]
                start_line = min(line_indexes) if line_indexes else start
                end_line = max(line_indexes) if line_indexes else start + len(window) - 1
                output.append(
                    EvidenceUnit(
                        unit_id=stable_id("context", source, str(start), str(start_line), str(end_line)),
                        parent_id=first.parent_id,
                        text=normalize_text(" ".join([first.title, text])),
                        source=source,
                        title=first.title,
                        unit_type="context_window",
                        heading_path=list(first.heading_path),
                        metadata={
                            "block_kind": "context_window",
                            "block_text": text,
                            "window_size": len(window),
                            "start_line": start_line,
                            "end_line": end_line,
                            "child_unit_ids": [unit.unit_id for unit in window],
                        },
                    )
                )
        return output

    @staticmethod
    def group_units_by_source(units: Sequence[EvidenceUnit]) -> Dict[str, List[EvidenceUnit]]:
        grouped: Dict[str, List[EvidenceUnit]] = defaultdict(list)
        for unit in units:
            grouped[unit.source].append(unit)
        return grouped

    @staticmethod
    def build_idf(units: Sequence[EvidenceUnit]) -> Dict[str, float]:
        df: Counter[str] = Counter()
        for unit in units:
            df.update(set(tokenize(evidence_text(unit))))
        total = max(1, len(units))
        return {term: math.log((total + 1) / (count + 1)) + 1.0 for term, count in df.items()}

    def idf_value(self, term: str) -> float:
        return self.idf.get(term, math.log(len(self.units) + 1) + 1.0)


def block_text(unit: EvidenceUnit) -> str:
    return normalize_text(str(unit.metadata.get("block_text") or unit.text))


def evidence_title_text(unit: EvidenceUnit) -> str:
    return normalize_text(" ".join([unit.source, unit.title, " ".join(unit.heading_path)]))


def evidence_text(unit: EvidenceUnit) -> str:
    return normalize_text(" ".join([evidence_title_text(unit), block_text(unit)]))


def weighted_coverage(terms: Iterable[str], text: str, idf: Dict[str, float]) -> float:
    unique_terms = list(dict.fromkeys(term for term in terms if term))
    if not unique_terms:
        return 0.0
    haystack = normalize_compact(text)
    total = sum(idf.get(term, 1.0) for term in unique_terms)
    if total <= 0:
        return 0.0
    matched = 0.0
    for term in unique_terms:
        if normalize_compact(term) in haystack:
            matched += idf.get(term, 1.0)
    return matched / total


def proximity_score(terms: Sequence[str], text: str) -> float:
    compact = normalize_compact(text)
    positions = []
    for term in terms:
        idx = compact.find(normalize_compact(term))
        if idx >= 0:
            positions.append(idx)
    if len(positions) <= 1:
        return 0.0
    window = max(1, max(positions) - min(positions))
    return 1.0 / (1.0 + math.log1p(window))


def length_prior(text: str) -> float:
    length = len(normalize_text(text))
    if length <= 0:
        return 0.0
    if 40 <= length <= 420:
        return 1.0
    if length < 40:
        return length / 40.0
    return max(0.15, 420.0 / length)


def information_density(text: str) -> float:
    cleaned = normalize_text(text)
    if not cleaned:
        return 0.0
    numeric_count = len(re.findall(r"\d+(?:\.\d+)?", cleaned))
    separator_count = sum(cleaned.count(mark) for mark in ("、", "；", ";", "，", ",", "：", ":"))
    bracket_count = sum(cleaned.count(mark) for mark in ("（", "(", "《", "“"))
    length = len(cleaned)
    density = numeric_count * 0.16 + separator_count * 0.035 + bracket_count * 0.025
    if 80 <= length <= 800:
        density += 0.10
    elif length < 30:
        density -= 0.10
    return max(0.0, min(1.0, density))


def candidate_spans(text: str) -> List[str]:
    whole = dedupe_repeated_sentences(normalize_text(text))
    sentences = [normalize_text(item) for item in split_sentences(whole) if normalize_text(item)]
    whole_spans = []
    if 40 <= len(whole) <= 1200:
        whole_spans.append(whole)
    if not sentences:
        return whole_spans
    spans = whole_spans + list(sentences)
    for size in (2, 3):
        for idx in range(0, max(0, len(sentences) - size + 1)):
            spans.append(normalize_text(" ".join(sentences[idx : idx + size])))
    return compact_texts(spans)


def compact_texts(texts: Sequence[str]) -> List[str]:
    output = []
    seen = set()
    for text in texts:
        cleaned = normalize_text(text).strip(" ；;。")
        if not cleaned:
            continue
        key = normalize_compact(cleaned)[:180]
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def dedupe_hits(hits: Sequence[RetrievalHit]) -> List[RetrievalHit]:
    output = []
    seen = set()
    for hit in hits:
        unit_id = hit.evidence.unit_id
        if unit_id in seen:
            continue
        seen.add(unit_id)
        output.append(hit)
    return output


def normalize_compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text).lower())


def matched_terms(terms: Iterable[str], text: str) -> set[str]:
    haystack = normalize_compact(text)
    return {term for term in terms if normalize_compact(term) in haystack}


def dedupe_repeated_sentences(text: str) -> str:
    sentences = [normalize_text(item).strip(" ；;。") for item in split_sentences(text)]
    if len(sentences) <= 1:
        return normalize_text(text)
    output = []
    seen = set()
    for sentence in sentences:
        if not sentence:
            continue
        key = normalize_compact(sentence)
        if key in seen:
            continue
        seen.add(key)
        output.append(sentence)
    if not output:
        return normalize_text(text)
    return normalize_text("。".join(output))


def char_ngrams(text: str, n: int = 3, max_chars: int = 900) -> set[str]:
    compact = normalize_compact(text)
    if len(compact) > max_chars:
        compact = compact[: max_chars * 2 // 3] + compact[-max_chars // 3 :]
    if len(compact) <= n:
        return {compact} if compact else set()
    return {compact[idx : idx + n] for idx in range(0, len(compact) - n + 1)}


def char_jaccard(left: str, right: str) -> float:
    a = char_ngrams(left)
    b = char_ngrams(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def char_overlap_score(question: str, text: str) -> float:
    query_grams = char_ngrams(question, n=2, max_chars=120)
    text_grams = char_ngrams(text, n=2, max_chars=1200)
    if not query_grams:
        return 0.0
    return len(query_grams & text_grams) / len(query_grams)


def unit_order_key(unit: EvidenceUnit) -> tuple[int, str]:
    line_index = unit.metadata.get("line_index")
    if isinstance(line_index, int):
        return (line_index, unit.unit_id)
    section_index = unit.metadata.get("section_index")
    if isinstance(section_index, int):
        return (section_index, unit.unit_id)
    item_index = unit.metadata.get("item_index")
    if isinstance(item_index, int):
        return (item_index, unit.unit_id)
    return (10**9, unit.unit_id)


def source_position_key(unit: EvidenceUnit) -> tuple[int, int, str]:
    line_range = unit_line_range(unit)
    if line_range is not None:
        return (line_range[0], line_range[1], unit.unit_id)
    order, unit_id = unit_order_key(unit)
    return (order, order, unit_id)


def unit_line_range(unit: EvidenceUnit) -> tuple[int, int] | None:
    start_line = unit.metadata.get("start_line")
    end_line = unit.metadata.get("end_line")
    if isinstance(start_line, int) and isinstance(end_line, int):
        return (start_line, end_line)
    line_index = unit.metadata.get("line_index")
    if isinstance(line_index, int):
        return (line_index, line_index)
    return None


def line_range_distance(left: tuple[int, int] | None, right: tuple[int, int] | None) -> int | None:
    if left is None or right is None:
        return None
    if left[0] <= right[1] and right[0] <= left[1]:
        return 0
    if left[1] < right[0]:
        return right[0] - left[1]
    return left[0] - right[1]


def is_subsumed(candidate: str, existing: str) -> bool:
    c = normalize_compact(candidate)
    e = normalize_compact(existing)
    if not c or not e:
        return False
    return c in e or e in c
