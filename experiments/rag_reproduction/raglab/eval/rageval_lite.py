from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List


def load_dataset(path: Path) -> List[Dict]:
    if path.suffix.lower() == ".jsonl":
        return [
            normalize_sample(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Unsupported dataset JSON structure in {path}")
    return [normalize_sample(item) for item in raw]


def write_dataset(path: Path, rows: List[Dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def stratified_sample_dataset(source_path: Path, output_path: Path, size: int, seed: int = 42) -> Dict:
    dataset = load_dataset(source_path)
    grouped: Dict[str, List[Dict]] = {}
    for item in dataset:
        key = item.get("category") or item.get("source") or "unknown"
        grouped.setdefault(key, []).append(item)

    rng = random.Random(seed)
    for items in grouped.values():
        rng.shuffle(items)

    buckets = sorted(grouped.items(), key=lambda item: item[0])
    selected: List[Dict] = []
    while len(selected) < min(size, len(dataset)):
        changed = False
        for _, items in buckets:
            if items and len(selected) < size:
                selected.append(items.pop())
                changed = True
        if not changed:
            break

    rng.shuffle(selected)
    write_dataset(output_path, selected)
    category_counts: Dict[str, int] = {}
    for item in selected:
        category = item.get("category") or "unknown"
        category_counts[category] = category_counts.get(category, 0) + 1

    report = {
        "source": str(source_path),
        "output": str(output_path),
        "seed": seed,
        "requested_size": size,
        "actual_size": len(selected),
        "category_count": category_counts,
    }
    report_path = output_path.with_suffix(".summary.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[sample] wrote {len(selected)} samples to {output_path}")
    return report


def normalize_sample(item: Dict) -> Dict:
    if "question" in item:
        item.setdefault("answer", "")
        item.setdefault("reference", item.get("answer", ""))
        return item

    labels = item.get("label", [])
    parsed = {}
    for label in labels:
        if not isinstance(label, str) or ":" not in label:
            continue
        key, value = label.split(":", 1)
        parsed[key.strip()] = value.strip()
    return {
        "id": item.get("id", ""),
        "question": item.get("text", ""),
        "answer": parsed.get("answer", ""),
        "reference": parsed.get("cot", parsed.get("answer", "")),
        "source": parsed.get("source", ""),
        "category": parsed.get("category", ""),
        "raw": item,
    }
