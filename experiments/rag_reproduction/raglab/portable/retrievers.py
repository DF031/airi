from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

from .schemas import EvidenceUnit, RetrievalHit
from .text import term_recall, tokenize


class BM25Retriever:
    name = "bm25"

    def __init__(self, units: List[EvidenceUnit]):
        self.units = units
        self.tokens = [tokenize(unit.text) for unit in units]
        self.index = BM25Okapi(self.tokens)

    def search(self, query: str, top_k: int) -> List[RetrievalHit]:
        scores = self.index.get_scores(tokenize(query))
        ranked = top_ranked(scores, top_k)
        return [
            RetrievalHit(evidence=self.units[idx], score=float(score), rank=rank, retriever=self.name)
            for rank, (idx, score) in enumerate(ranked, start=1)
        ]


class TfidfRetriever:
    name = "tfidf"

    def __init__(self, units: List[EvidenceUnit]):
        self.units = units
        self.vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False)
        self.matrix = self.vectorizer.fit_transform([unit.text for unit in units])

    def search(self, query: str, top_k: int) -> List[RetrievalHit]:
        query_vec = self.vectorizer.transform([query])
        scores = (self.matrix @ query_vec.T).toarray().ravel()
        ranked = top_ranked(scores, top_k)
        return [
            RetrievalHit(evidence=self.units[idx], score=float(score), rank=rank, retriever=self.name)
            for rank, (idx, score) in enumerate(ranked, start=1)
        ]


class CharNgramTfidfRetriever:
    name = "char_ngram_tfidf"

    def __init__(self, units: List[EvidenceUnit], ngram_range: tuple[int, int] = (2, 4)):
        self.units = units
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=ngram_range,
            lowercase=False,
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform([unit.text for unit in units])

    def search(self, query: str, top_k: int) -> List[RetrievalHit]:
        query_vec = self.vectorizer.transform([query])
        scores = (self.matrix @ query_vec.T).toarray().ravel()
        ranked = top_ranked(scores, top_k)
        return [
            RetrievalHit(evidence=self.units[idx], score=float(score), rank=rank, retriever=self.name)
            for rank, (idx, score) in enumerate(ranked, start=1)
        ]


def top_ranked(scores, top_k: int) -> List[tuple[int, float]]:
    values = np.asarray(scores)
    if top_k <= 0 or values.size == 0:
        return []
    top_k = min(top_k, values.size)
    if top_k == values.size:
        indices = np.argsort(values)[::-1]
    else:
        candidate_indices = np.argpartition(values, -top_k)[-top_k:]
        indices = candidate_indices[np.argsort(values[candidate_indices])[::-1]]
    return [(int(idx), float(values[idx])) for idx in indices if values[idx] > 0]


def rrf_fuse(
    ranked_lists: Iterable[List[RetrievalHit]],
    top_k: int,
    rrf_k: int = 60,
    max_chunks_per_source: int = 3,
) -> List[RetrievalHit]:
    fused: Dict[str, RetrievalHit] = {}
    scores: Dict[str, float] = defaultdict(float)
    methods: Dict[str, List[str]] = defaultdict(list)
    for hits in ranked_lists:
        for hit in hits:
            key = hit.evidence.unit_id
            if key not in fused:
                fused[key] = hit
            scores[key] += 1.0 / (rrf_k + hit.rank)
            methods[key].append(f"{hit.retriever}@{hit.rank}")

    source_count: Dict[str, int] = defaultdict(int)
    output: List[RetrievalHit] = []
    for key, hit in sorted(fused.items(), key=lambda item: scores[item[0]], reverse=True):
        source = hit.evidence.source
        if source_count[source] >= max_chunks_per_source:
            continue
        source_count[source] += 1
        output.append(
            RetrievalHit(
                evidence=hit.evidence,
                score=float(scores[key]),
                rank=len(output) + 1,
                retriever="rrf_hybrid",
                signals={"candidate_methods": methods[key]},
            )
        )
        if len(output) >= top_k:
            break
    return output


def retrieval_confidence(question: str, hits: List[RetrievalHit]) -> float:
    if not hits:
        return 0.0
    query_terms = tokenize(question)
    top_recall = term_recall(query_terms, hits[0].evidence.text)
    context_recall = term_recall(query_terms, " ".join(hit.evidence.text for hit in hits[:5]))
    diversity = len({hit.evidence.source for hit in hits[:5]}) / max(1, min(5, len(hits)))
    return round(min(1.0, top_recall * 0.45 + context_recall * 0.40 + diversity * 0.15), 6)
