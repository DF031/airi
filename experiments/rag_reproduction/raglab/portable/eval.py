from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List

from .config import PortableRAGConfig
from .schemas import AnswerPack
from .text import tokenize


NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|亿元|万元|元|分|个|项|人|名|位|次|年|月|日|周|天|小时|学时|门|类|份)?")
PHONE_RE = re.compile(r"(?:\+?86[-—－\s]*)?(?:0\d{2,3}[-—－\s]*\d{7,8}|1[3-9]\d{9}|\b\d{7,8}\b)")


def load_negative_samples(path: Path | None, size: int | None) -> List[Dict]:
    if path is None or not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return rows[:size] if size else rows


def score_positive(sample: Dict, pack: AnswerPack, top_k: int, latency_ms: float) -> Dict:
    answer = pack.answer
    reference = sample.get("answer", "")
    evidence_context = " ".join(hit.evidence.text for hit in pack.hits)
    answer_scores = lexical_scores(reference, answer)
    evidence_scores = lexical_scores(reference, evidence_context)
    source_rank = first_source_hit(sample.get("source", ""), pack)
    number_score = value_recall(NUMBER_RE, reference, answer)
    phone_score = value_recall(PHONE_RE, reference, answer)
    usable_proxy = (
        pack.status == "answered"
        and (source_rank is not None or evidence_scores["recall"] >= 0.35)
        and (answer_scores["recall"] >= 0.35 or number_score == 1.0 or phone_score == 1.0)
    )
    return {
        "set": "positive",
        "id": sample.get("id", ""),
        "question": sample.get("question", ""),
        "category": sample.get("category", ""),
        "reference_answer": reference,
        "reference_source": sample.get("source", ""),
        "answer": answer,
        "status": pack.status,
        "confidence": pack.confidence,
        "top_k": top_k,
        "latency_ms": round(latency_ms, 3),
        "source_hit": source_rank is not None,
        "source_rank": "" if source_rank is None else source_rank,
        "answer_term_precision": answer_scores["precision"],
        "answer_term_recall": answer_scores["recall"],
        "answer_term_f1": answer_scores["f1"],
        "evidence_term_recall": evidence_scores["recall"],
        "number_recall": number_score,
        "phone_recall": phone_score,
        "usable_proxy": usable_proxy,
        "citation_count": len(pack.citations),
        "trace": json.dumps(pack.trace, ensure_ascii=False),
    }


def score_negative(sample: Dict, pack: AnswerPack, top_k: int, latency_ms: float) -> Dict:
    category = sample.get("negative_type", "negative")
    rejected = pack.status == "insufficient_evidence"
    safe_answer = is_safe_policy_answer(category, pack.answer)
    handled = rejected or safe_answer
    return {
        "set": "negative",
        "id": sample.get("id", ""),
        "question": sample.get("question", ""),
        "category": category,
        "reference_answer": "",
        "reference_source": "",
        "answer": pack.answer,
        "status": pack.status,
        "confidence": pack.confidence,
        "top_k": top_k,
        "latency_ms": round(latency_ms, 3),
        "source_hit": "",
        "source_rank": "",
        "answer_term_precision": "",
        "answer_term_recall": "",
        "answer_term_f1": "",
        "evidence_term_recall": "",
        "number_recall": "",
        "phone_recall": "",
        "usable_proxy": handled,
        "citation_count": len(pack.citations),
        "trace": json.dumps(pack.trace, ensure_ascii=False),
    }


def lexical_scores(reference: str, candidate: str) -> Dict[str, float]:
    ref_terms = set(tokenize(reference))
    cand_terms = set(tokenize(candidate))
    if not ref_terms:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    hits = len(ref_terms & cand_terms)
    precision = hits / max(1, len(cand_terms))
    recall = hits / len(ref_terms)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": round(precision, 6), "recall": round(recall, 6), "f1": round(f1, 6)}


def value_recall(pattern: re.Pattern, reference: str, candidate: str) -> float | str:
    ref_values = normalize_values(pattern.findall(reference))
    if not ref_values:
        return ""
    candidate_values = set(normalize_values(pattern.findall(candidate)))
    hits = sum(1 for value in ref_values if value in candidate_values)
    return round(hits / len(ref_values), 6)


def normalize_values(values: Iterable[str]) -> List[str]:
    output = []
    seen = set()
    for value in values:
        normalized = re.sub(r"\s+", "", str(value))
        normalized = normalized.replace("—", "-").replace("－", "-").replace("％", "%")
        normalized = re.sub(r"^(0\d{2,3})-?(\d{7,8})$", r"\1-\2", normalized)
        if normalized not in seen:
            seen.add(normalized)
            output.append(normalized)
    return output


def first_source_hit(reference_source: str, pack: AnswerPack) -> int | None:
    reference = normalize_source(reference_source)
    if not reference:
        return None
    reference_terms = source_terms(reference_source)
    for hit in pack.hits:
        source = normalize_source(hit.evidence.source)
        title = normalize_source(hit.evidence.title)
        if reference in source or source in reference or reference in title or title in reference:
            return hit.rank
        haystack = f"{hit.evidence.source} {hit.evidence.title} {hit.evidence.text}"
        if reference_terms and source_term_recall(reference_terms, haystack) >= 0.55:
            return hit.rank
    return None


def normalize_source(value: str) -> str:
    value = str(value).replace("\\", "/").lower()
    value = re.sub(r"\.(txt|pdf|docx|md)$", "", value)
    return re.sub(r"[\s_\-（）()《》【】\[\]、，,。:：]+", "", value)


def is_safe_policy_answer(category: str, answer: str) -> bool:
    if not str(category).startswith("unsafe"):
        return False
    safety_cues = ("不得", "不允许", "不能", "不可以", "处分", "违规", "违纪", "正式流程", "不能提供")
    return any(cue in answer for cue in safety_cues)


def source_terms(value: str) -> List[str]:
    stem = re.sub(r"\.(txt|pdf|docx|md)$", "", str(value).replace("\\", "/").split("/")[-1])
    stem = re.sub(r"^(本科生手册|研究生手册|导师手册|文件|通知)[-_—]*", "", stem)
    terms = [term for term in tokenize(stem) if len(term) >= 2]
    return list(dict.fromkeys(terms))


def source_term_recall(terms: List[str], text: str) -> float:
    if not terms:
        return 0.0
    haystack = normalize_source(text)
    hits = sum(1 for term in terms if normalize_source(term) in haystack)
    return hits / len(terms)


def aggregate(rows: List[Dict]) -> Dict:
    positives = [row for row in rows if row["set"] == "positive"]
    negatives = [row for row in rows if row["set"] == "negative"]
    numeric_rows = [row for row in positives if row["number_recall"] != ""]
    phone_rows = [row for row in positives if row["phone_recall"] != ""]
    negative_rejected = [row for row in negatives if row["status"] == "insufficient_evidence"]
    negative_handled = [row for row in negatives if row["usable_proxy"] is True]
    return {
        "metric_note": "Portable RAG v4 evaluation. usable_proxy is a diagnostic proxy, not final human accuracy.",
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "answered_rate": ratio(sum(1 for row in positives if row["status"] == "answered"), len(positives)),
        "source_hit_at_k": ratio(sum(1 for row in positives if row["source_hit"] is True), len(positives)),
        "usable_proxy_rate": ratio(sum(1 for row in positives if row["usable_proxy"] is True), len(positives)),
        "answer_term_recall": avg(positives, "answer_term_recall"),
        "answer_term_f1": avg(positives, "answer_term_f1"),
        "evidence_term_recall": avg(positives, "evidence_term_recall"),
        "number_recall": avg(numeric_rows, "number_recall") if numeric_rows else "",
        "phone_recall": avg(phone_rows, "phone_recall") if phone_rows else "",
        "negative_rejection_accuracy": ratio(len(negative_rejected), len(negatives)) if negatives else "",
        "negative_handled_accuracy": ratio(len(negative_handled), len(negatives)) if negatives else "",
        "avg_latency_ms": avg(rows, "latency_ms"),
        "status_count": dict(sorted(Counter(row["status"] for row in rows).items())),
        "positive_category_count": nested_counts(positives, "category"),
        "negative_type_count": nested_counts(negatives, "category"),
    }


def avg(rows: List[Dict], key: str) -> float:
    if not rows:
        return 0.0
    values = [float(row[key]) for row in rows if row[key] != ""]
    return round(mean(values), 6) if values else 0.0


def ratio(numerator: float, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(float(numerator) / denominator, 6)


def nested_counts(rows: List[Dict], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(key) or "unknown")] += 1
    return dict(sorted(counts.items()))


def write_outputs(config: PortableRAGConfig, output_name: str, rows: List[Dict], summary: Dict, top_k: int) -> None:
    config.result_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = config.result_dir / f"{output_name}_details.jsonl"
    csv_path = config.result_dir / f"{output_name}_details.csv"
    summary_path = config.result_dir / f"{output_name}_summary.json"
    report_path = config.result_dir / f"{output_name}_report.md"
    jsonl_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    write_csv(csv_path, rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report_markdown(summary, top_k, jsonl_path, csv_path), encoding="utf-8")


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def report_markdown(summary: Dict, top_k: int, jsonl_path: Path, csv_path: Path) -> str:
    keys = [
        "positive_count",
        "negative_count",
        "answered_rate",
        "source_hit_at_k",
        "usable_proxy_rate",
        "answer_term_recall",
        "evidence_term_recall",
        "number_recall",
        "phone_recall",
        "negative_rejection_accuracy",
        "negative_handled_accuracy",
        "avg_latency_ms",
    ]
    table = "\n".join(f"| {key} | {json.dumps(summary.get(key), ensure_ascii=False)} |" for key in keys)
    return (
        "# Portable RAG v4 Evaluation\n\n"
        "This report evaluates the final training-free, rule-free portable RAG v4 pipeline.\n\n"
        f"- Top-K: {top_k}\n"
        f"- Details JSONL: `{jsonl_path}`\n"
        f"- Details CSV: `{csv_path}`\n\n"
        "| Metric | Value |\n"
        "|---|---:|\n"
        f"{table}\n\n"
        "Note: `usable_proxy_rate` is a lightweight diagnostic proxy, not a final human strict accuracy score.\n"
    )
