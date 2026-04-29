from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List

from ..documents import iter_source_files, read_file
from .schemas import EvidenceUnit, PortableDocument, stable_id
from .text import normalize_text


STRUCTURED_CACHE_VERSION = "portable_structured_v2.1"
LINE_SPACE_RE = re.compile(r"[ \t\r\f\v]+")
MAJOR_HEADING_RE = re.compile(r"^(第[一二三四五六七八九十百]+[章节条]|[一二三四五六七八九十]+、)")
LIST_ITEM_RE = re.compile(r"^\s*(?:\d+[.、]|[（(][一二三四五六七八九十百]+[）)])")
KV_RE = re.compile(r"^(?P<key>[^:：]{2,36})[:：]\s*(?P<value>.+)$")
PHONE_RE = re.compile(r"(?:\d{3,4}[-－]?\d{7,8}|\d{11}|\b\d{7,8}\b)")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
DATE_RE = re.compile(r"\d{4}\s*年|\d{1,2}\s*月\s*\d{0,2}\s*日?|\d{1,2}[:：]\d{2}|周[一二三四五六日天]")
TABLE_ROW_RE = re.compile(r"\s{2,}|\t+")


def load_structured_documents(data_dir: Path) -> List[PortableDocument]:
    documents = []
    for path in iter_structured_source_files(data_dir):
        try:
            raw_text = read_file(path)
        except Exception as exc:
            print(f"[portable-v2] skipped {path}: {exc}")
            continue
        text = normalize_text(raw_text)
        if not text:
            continue
        source = str(path.relative_to(data_dir))
        documents.append(
            PortableDocument(
                doc_id=stable_id(source, str(path.stat().st_size), str(path.stat().st_mtime_ns)),
                text=text,
                source=source,
                title=path.stem,
                metadata={"suffix": path.suffix.lower(), "raw_text": raw_text},
            )
        )
    return documents


def iter_structured_source_files(data_dir: Path) -> Iterable[Path]:
    return iter_source_files(data_dir) if data_dir.exists() else []


def build_or_load_structured_units(
    data_dir: Path,
    cache_path: Path,
    rebuild: bool = False,
) -> tuple[List[PortableDocument], List[EvidenceUnit]]:
    cache_key = {
        "version": STRUCTURED_CACHE_VERSION,
        "data_dir": str(data_dir.resolve()) if data_dir.exists() else str(data_dir),
    }
    if cache_path.exists() and not rebuild:
        rows = [json.loads(line) for line in cache_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if rows and rows[0].get("cache_key") == cache_key:
            documents = [PortableDocument(**row["document"]) for row in rows[1:] if "document" in row]
            units = [unit_from_json(row["unit"]) for row in rows[1:] if "unit" in row]
            if units:
                return documents, units

    documents = load_structured_documents(data_dir)
    units = build_structured_units(documents)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"cache_key": cache_key}, ensure_ascii=False)]
    lines.extend(json.dumps({"document": document_to_cache(document)}, ensure_ascii=False) for document in documents)
    lines.extend(json.dumps({"unit": unit.__dict__}, ensure_ascii=False) for unit in units)
    cache_path.write_text("\n".join(lines), encoding="utf-8")
    return documents, units


def build_structured_units(documents: List[PortableDocument]) -> List[EvidenceUnit]:
    units: List[EvidenceUnit] = []
    for document in documents:
        raw_text = str(document.metadata.get("raw_text", ""))
        lines = logical_lines(raw_text)
        if not lines:
            lines = split_fallback_sentences(document.text)
        units.extend(extract_document_units(document, lines))
    return units


def extract_document_units(document: PortableDocument, lines: List[str]) -> List[EvidenceUnit]:
    units: List[EvidenceUnit] = []
    heading_path: List[str] = []
    section_buffer: List[str] = []
    section_start = 0
    section_counter = 0
    line_index = 0

    while line_index < len(lines):
        line = lines[line_index]
        if is_major_heading(line):
            section_counter = flush_section_block(
                units=units,
                document=document,
                heading_path=heading_path,
                lines=section_buffer,
                section_start=section_start,
                section_counter=section_counter,
            )
            heading_path = update_heading_path(heading_path, line)
            section_buffer = [line]
            section_start = line_index
            line_index += 1
            continue

        section_buffer.append(line)

        kv = parse_key_value(line)
        if kv:
            units.append(make_unit(document, heading_path, line_index, "kv", f"{kv['key']}：{kv['value']}", kv))

        if is_list_item(line):
            list_items, next_index = collect_list_items(lines, line_index)
            if len(list_items) >= 2:
                heading = heading_path[-1] if heading_path else document.title
                block_text = "；".join([heading] + list_items) if heading else "；".join(list_items)
                units.append(
                    make_unit(
                        document=document,
                        heading_path=heading_path,
                        line_index=line_index,
                        block_kind="list",
                        text=block_text,
                        metadata={"items": list_items, "list_size": len(list_items)},
                    )
                )
                for offset, item in enumerate(list_items):
                    units.append(
                        make_unit(
                            document=document,
                            heading_path=heading_path,
                            line_index=line_index + offset,
                            block_kind="list_item",
                            text=item,
                            metadata={"item_index": offset, "items_total": len(list_items)},
                        )
                    )
                line_index = next_index
                continue

        table_cells = parse_table_row(line)
        if table_cells:
            units.append(
                make_unit(
                    document=document,
                    heading_path=heading_path,
                    line_index=line_index,
                    block_kind="table_row",
                    text=" | ".join(table_cells),
                    metadata={"cells": table_cells, "cell_count": len(table_cells)},
                )
            )

        if is_salient_fact(line):
            units.append(
                make_unit(
                    document=document,
                    heading_path=heading_path,
                    line_index=line_index,
                    block_kind="fact",
                    text=line,
                    metadata={"salient": True},
                )
            )
        line_index += 1

    flush_section_block(
        units=units,
        document=document,
        heading_path=heading_path,
        lines=section_buffer,
        section_start=section_start,
        section_counter=section_counter,
    )
    return dedupe_units(units)


def flush_section_block(
    units: List[EvidenceUnit],
    document: PortableDocument,
    heading_path: List[str],
    lines: List[str],
    section_start: int,
    section_counter: int,
) -> int:
    text = " ".join(part for part in lines if part).strip()
    if len(text) >= 40:
        units.append(
            make_unit(
                document=document,
                heading_path=heading_path,
                line_index=section_start,
                block_kind="section",
                text=text,
                metadata={"section_index": section_counter, "line_count": len(lines)},
            )
        )
        return section_counter + 1
    return section_counter


def dedupe_units(units: List[EvidenceUnit]) -> List[EvidenceUnit]:
    output: List[EvidenceUnit] = []
    seen = set()
    for unit in units:
        key = (unit.source, unit.unit_type, normalize_text(unit.text))
        if key in seen:
            continue
        seen.add(key)
        output.append(unit)
    return output


def document_to_cache(document: PortableDocument) -> dict:
    metadata = dict(document.metadata)
    metadata.pop("raw_text", None)
    return {
        "doc_id": document.doc_id,
        "text": document.text,
        "source": document.source,
        "title": document.title,
        "metadata": metadata,
    }


def make_unit(
    document: PortableDocument,
    heading_path: List[str],
    line_index: int,
    block_kind: str,
    text: str,
    metadata: dict,
) -> EvidenceUnit:
    enriched = enrich_block_text(document.title, heading_path, text)
    parent_parts = heading_path[:] if heading_path else [document.title]
    parent_id = stable_id(document.doc_id, "section", *parent_parts)
    document_metadata = {key: value for key, value in document.metadata.items() if key != "raw_text"}
    return EvidenceUnit(
        unit_id=stable_id(document.doc_id, block_kind, str(line_index), enriched[:120]),
        parent_id=parent_id,
        text=enriched,
        source=document.source,
        title=document.title,
        unit_type=block_kind,
        heading_path=heading_path[:],
        metadata={
            **document_metadata,
            **metadata,
            "line_index": line_index,
            "block_kind": block_kind,
            "block_text": normalize_text(text),
        },
    )


def enrich_block_text(title: str, heading_path: List[str], text: str) -> str:
    prefix = [part for part in [title, " > ".join(heading_path)] if part]
    if prefix:
        return f"{' | '.join(prefix)} | {normalize_text(text)}"
    return normalize_text(text)


def logical_lines(raw_text: str) -> List[str]:
    lines = []
    for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        normalized = normalize_line(line)
        if not normalized or is_low_value_line(normalized):
            continue
        lines.append(normalized)
    return merge_fragmented_lines(lines)


def normalize_line(text: str) -> str:
    return LINE_SPACE_RE.sub(" ", text.replace("\u3000", " ")).strip()


def is_low_value_line(line: str) -> bool:
    if len(line) <= 1:
        return True
    if re.fullmatch(r"[-—_·.。．\s\d]+", line):
        return True
    if re.fullmatch(r"(目录|附件|附表|第\s*\d+\s*页)", line):
        return True
    return False


def merge_fragmented_lines(lines: List[str]) -> List[str]:
    merged: List[str] = []
    buffer = ""
    for line in lines:
        if not buffer:
            buffer = line
            continue
        if should_merge_line(buffer, line):
            buffer = f"{buffer} {line}"
        else:
            merged.append(buffer)
            buffer = line
    if buffer:
        merged.append(buffer)
    return merged


def should_merge_line(previous: str, current: str) -> bool:
    if len(previous) < 24 and not re.search(r"[。！？；;]$", previous):
        return True
    if re.match(r"^[，、；：:）)]", current):
        return True
    if is_list_item(current):
        return False
    return False


def is_major_heading(line: str) -> bool:
    return bool(MAJOR_HEADING_RE.match(line))


def is_list_item(line: str) -> bool:
    return bool(LIST_ITEM_RE.match(line))


def collect_list_items(lines: List[str], start_index: int) -> tuple[List[str], int]:
    items = []
    index = start_index
    while index < len(lines) and is_list_item(lines[index]):
        items.append(clean_list_item(lines[index]))
        index += 1
    return items, index


def clean_list_item(text: str) -> str:
    return normalize_text(re.sub(r"^\s*(?:\d+[.、]|[（(][一二三四五六七八九十百]+[）)])\s*", "", text))


def parse_key_value(line: str) -> dict | None:
    match = KV_RE.match(line)
    if not match:
        return None
    key = normalize_text(match.group("key"))
    value = normalize_text(match.group("value"))
    if len(key) > 36 or len(value) > 180:
        return None
    return {"key": key, "value": value}


def parse_table_row(line: str) -> List[str]:
    parts = [normalize_text(part) for part in TABLE_ROW_RE.split(line) if normalize_text(part)]
    if len(parts) >= 3 and any(VALUE_RELATED(part) for part in parts):
        return parts
    return []


def VALUE_RELATED(text: str) -> bool:
    return bool(PHONE_RE.search(text) or EMAIL_RE.search(text) or DATE_RE.search(text) or re.search(r"\d", text))


def is_salient_fact(line: str) -> bool:
    return bool(PHONE_RE.search(line) or EMAIL_RE.search(line) or DATE_RE.search(line) or len(line) <= 96)


def update_heading_path(heading_path: List[str], line: str) -> List[str]:
    cleaned = normalize_text(line)
    if cleaned.startswith("第"):
        return [cleaned]
    if re.match(r"^[一二三四五六七八九十]+、", cleaned):
        return heading_path[:1] + [cleaned]
    return [cleaned]


def split_fallback_sentences(text: str) -> List[str]:
    parts = [part.strip() for part in re.split(r"(?<=[。！？；;!?])|\.(?=\s)", text) if part.strip()]
    return parts


def unit_from_json(data: dict) -> EvidenceUnit:
    return EvidenceUnit(
        unit_id=data["unit_id"],
        parent_id=data["parent_id"],
        text=data["text"],
        source=data["source"],
        title=data.get("title", ""),
        unit_type=data.get("unit_type", "fact"),
        heading_path=list(data.get("heading_path", [])),
        metadata=dict(data.get("metadata", {})),
    )
