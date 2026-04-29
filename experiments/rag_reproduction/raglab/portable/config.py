from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ..config import REPRO_DIR, ROOT_DIR


@dataclass
class PortableRAGConfig:
    path: Path
    raw: Dict[str, Any]
    data_dir: Path
    domain_profile_path: Path | None
    domain_profile: Dict[str, Any]
    result_dir: Path
    index_dir: Path
    dataset_path: Path
    negative_path: Path | None
    top_k: int
    candidate_k: int
    rrf_k: int
    parent_chunk_size: int
    parent_chunk_overlap: int
    child_chunk_size: int
    child_chunk_overlap: int
    max_chunks_per_source: int
    boundary_patterns: Dict[str, List[str]]
    boundary_terms: Dict[str, List[str]]
    allowed_entities: List[str]
    query_expansions: Dict[str, List[str]]
    low_confidence: float
    high_confidence: float
    max_context_chars: int


def load_portable_config(path: str | Path | None = None) -> PortableRAGConfig:
    config_path = Path(path) if path else REPRO_DIR / "configs" / "portable_rag.yaml"
    if not config_path.is_absolute():
        config_path = ROOT_DIR / config_path
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    corpus = raw.get("corpus", {})
    chunking = corpus.get("chunking", {})
    indexes = raw.get("indexes", {})
    fusion = indexes.get("fusion", {})
    retrieval = raw.get("retrieval", {})
    evidence = raw.get("evidence_evaluator", {})
    thresholds = evidence.get("confidence_thresholds", {})
    generation = raw.get("generation", {})
    evaluation = raw.get("evaluation", {})

    data_dir = resolve_path(corpus.get("data_dir", REPRO_DIR / "data"))
    profile = corpus.get("domain_profile")
    profile_path = resolve_path(profile) if profile else None
    domain_profile = load_yaml(profile_path) if profile_path and profile_path.exists() else {}
    result_dir = resolve_path(raw.get("result_dir", REPRO_DIR / "results" / "portable_rag"))
    index_dir = resolve_path(raw.get("index_dir", REPRO_DIR / "indexes" / "portable_rag"))
    dataset_path = resolve_path(evaluation.get("golden_set", REPRO_DIR / "datasets" / "dataset.json"))
    negative_value = evaluation.get("negative_set")
    negative_path = resolve_path(negative_value) if negative_value else None
    result_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    boundary_patterns, boundary_terms = extract_boundary_rules(domain_profile)
    allowed_entities = extract_allowed_entities(domain_profile)
    query_expansions = extract_query_expansions(domain_profile)

    return PortableRAGConfig(
        path=config_path,
        raw=raw,
        data_dir=data_dir,
        domain_profile_path=profile_path,
        domain_profile=domain_profile,
        result_dir=result_dir,
        index_dir=index_dir,
        dataset_path=dataset_path,
        negative_path=negative_path,
        top_k=int(fusion.get("top_k", 8)),
        candidate_k=int(fusion.get("candidate_k", 32)),
        rrf_k=int(fusion.get("rrf_k", 60)),
        parent_chunk_size=int(chunking.get("parent_chunk_size", 1200)),
        parent_chunk_overlap=int(chunking.get("parent_chunk_overlap", 160)),
        child_chunk_size=int(chunking.get("child_chunk_size", 320)),
        child_chunk_overlap=int(chunking.get("child_chunk_overlap", 80)),
        max_chunks_per_source=int(retrieval.get("diversity", {}).get("max_chunks_per_source", 3)),
        boundary_patterns=boundary_patterns,
        boundary_terms=boundary_terms,
        allowed_entities=allowed_entities,
        query_expansions=query_expansions,
        low_confidence=float(thresholds.get("low", 0.35)),
        high_confidence=float(thresholds.get("high", 0.72)),
        max_context_chars=int(generation.get("max_context_chars", 4500)),
    )


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    root_candidate = ROOT_DIR / path
    if root_candidate.exists() or str(value).startswith("experiments/"):
        return root_candidate
    return REPRO_DIR / path


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def extract_boundary_rules(profile: Dict[str, Any]) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    patterns: Dict[str, List[str]] = {}
    terms: Dict[str, List[str]] = {}
    for name, rule in (profile.get("boundaries") or {}).items():
        if not isinstance(rule, dict):
            continue
        pattern_values = rule.get("patterns") or []
        term_values = rule.get("terms") or []
        patterns[str(name)] = [str(item) for item in pattern_values if str(item).strip()]
        terms[str(name)] = [str(item) for item in term_values if str(item).strip()]
    return patterns, terms


def extract_allowed_entities(profile: Dict[str, Any]) -> List[str]:
    entities = ((profile.get("domain") or {}).get("entities") or {})
    values = []
    canonical = entities.get("canonical")
    if canonical:
        values.append(str(canonical))
    values.extend(str(item) for item in entities.get("aliases") or [])
    return list(dict.fromkeys(item for item in values if item.strip()))


def extract_query_expansions(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    terminology = profile.get("terminology") or {}
    expansions: Dict[str, List[str]] = {}
    for row in terminology.get("synonyms") or []:
        if not isinstance(row, dict):
            continue
        term = str(row.get("term", "")).strip()
        aliases = [str(item).strip() for item in row.get("aliases") or [] if str(item).strip()]
        if term and aliases:
            expansions[term] = aliases
    return expansions
