from __future__ import annotations

import json
import time
from typing import Dict, List

from ..eval.rageval_lite import load_dataset
from .config import PortableRAGConfig
from .eval import aggregate, load_negative_samples, score_negative, score_positive, write_outputs
from .v4 import PortableRAGV4


def evaluate_portable_rag_v4(
    config: PortableRAGConfig,
    top_k: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    negative_size: int | None = None,
    output_name: str = "portable_rag_v4",
) -> Dict:
    positives = load_dataset(config.dataset_path)
    if offset:
        positives = positives[offset:]
    if limit:
        positives = positives[:limit]
    negatives = load_negative_samples(config.negative_path, negative_size)

    system = PortableRAGV4(config)
    rows: List[Dict] = []
    for idx, sample in enumerate(positives, start=1):
        question = sample.get("question", "")
        print(f"[portable-v4-eval] positive {idx}/{len(positives)} {question[:42]}")
        start = time.perf_counter()
        pack = system.answer(question, top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000
        rows.append(score_positive(sample, pack, top_k or config.top_k, latency_ms))

    for idx, sample in enumerate(negatives, start=1):
        question = sample.get("question", "")
        print(f"[portable-v4-eval] negative {idx}/{len(negatives)} {question[:42]}")
        start = time.perf_counter()
        pack = system.answer(question, top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000
        rows.append(score_negative(sample, pack, top_k or config.top_k, latency_ms))

    summary = aggregate(rows)
    summary["metric_note"] = (
        "Portable RAG v4 uses only training-free, domain-agnostic retrieval and "
        "extractive reading signals; usable_proxy remains a diagnostic proxy."
    )
    write_outputs(config, output_name, rows, summary, top_k or config.top_k)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary
