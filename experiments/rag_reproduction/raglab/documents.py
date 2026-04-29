from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List
from xml.etree import ElementTree

from pypdf import PdfReader

from .config import ReproConfig
from .schemas import CorpusDocument


SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}
WHITESPACE = re.compile(r"\s+")
CORPUS_VERSION = "fine_grained_ocr_v3"
SIGNAL_CHAR_RE = re.compile(r"[\w\u4e00-\u9fff]")
OCR_MIN_SIGNAL_CHARS = 80
OCR_RENDER_DPI = 180
OCR_CACHE_DIR = Path(__file__).resolve().parents[1] / "indexes" / "ocr_cache"
VALUE_RE = re.compile(r"\d{1,4}(?:\.\d+)?\s*(?:年|月|日|:|：|元|分|%|％|个|项|人|名|次|周|天|小时|学时|室|楼)?")
ARTICLE_RE = re.compile(r"(?=第[一二三四五六七八九十百]+条)")
SECTION_RE = re.compile(r"(?=(?:^| )+[一二三四五六七八九十]+、)")
NUMBERED_RE = re.compile(r"(?=(?:^| )(?:(?:[1-9]\d*)[.、]|（[一二三四五六七八九十]+）))")
HIGH_VALUE_TERMS = (
    "学生综合服务楼",
    "学生综合服务大楼",
    "学校综合档案馆",
    "电话",
    "邮箱",
    "地点",
    "办公室",
    "报名",
    "截止",
    "初赛",
    "复赛",
    "决赛",
    "创青春",
    "国企",
    "青年组",
    "闭幕式",
    "开营",
    "报到",
    "入住",
    "入住酒店",
    "费用",
    "总计",
    "预算",
    "住宿",
    "培训",
    "交通",
    "资助",
    "奖学金",
    "申请",
    "条件",
    "材料",
    "职责",
    "程序",
    "流程",
    "步骤",
    "包括",
    "主要包括",
    "不得",
    "不能",
    "不予",
    "处分",
    "取消",
    "返还",
    "通报批评",
    "机器人",
    "机器人制造",
    "ARJ21",
    "大数据",
    "金融",
    "跨境电商",
    "阿里巴巴",
    "上飞",
    "上海上飞",
    "飞机装备",
    "名校进名企",
    "澳门大学",
    "口腔科",
    "预约通道",
)


def normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text.replace("\u3000", " ")).strip()


def normalize_line(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text.replace("\u3000", " ")).strip()


def stable_id(*parts: str) -> str:
    return hashlib.sha1("||".join(parts).encode("utf-8", errors="ignore")).hexdigest()[:16]


def read_txt(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf(path: Path) -> str:
    candidates = [read_pdf_with_pypdf(path), read_pdf_with_pdftotext(path)]
    best = max(candidates, key=lambda item: len(SIGNAL_CHAR_RE.findall(item)))
    if has_enough_pdf_text(best):
        return best
    ocr_text = read_pdf_with_ocr(path)
    if has_enough_pdf_text(ocr_text):
        return ocr_text
    return best


def read_pdf_with_pypdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def read_pdf_with_pdftotext(path: Path) -> str:
    executable = shutil.which("pdftotext") or r"C:\texlive\2025\bin\windows\pdftotext.exe"
    if not Path(executable).exists():
        return ""
    try:
        completed = subprocess.run(
            [executable, "-layout", "-enc", "UTF-8", str(path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60,
        )
    except Exception:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout or ""


def has_enough_pdf_text(text: str) -> bool:
    return len(SIGNAL_CHAR_RE.findall(text or "")) >= OCR_MIN_SIGNAL_CHARS


def read_pdf_with_ocr(path: Path) -> str:
    cache_path = ocr_cache_path(path)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore")

    executable = shutil.which("pdftoppm") or r"C:\texlive\2025\bin\windows\pdftoppm.exe"
    if not Path(executable).exists():
        print(f"[ocr] pdftoppm not found; skipped scanned PDF OCR: {path.name}")
        return ""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:
        print(f"[ocr] rapidocr unavailable; skipped scanned PDF OCR: {path.name}: {exc}")
        return ""

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rag_pdf_ocr_") as tmp:
        prefix = Path(tmp) / "page"
        try:
            completed = subprocess.run(
                [executable, "-r", str(OCR_RENDER_DPI), "-png", str(path), str(prefix)],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except Exception as exc:
            print(f"[ocr] failed to render {path.name}: {exc}")
            return ""
        if completed.returncode != 0:
            print(f"[ocr] failed to render {path.name}: {completed.stderr[:160]}")
            return ""

        images = sorted(Path(tmp).glob("page-*.png"), key=page_image_order)
        if not images:
            return ""
        print(f"[ocr] extracting scanned PDF: {path.name} pages={len(images)}")
        ocr = RapidOCR()
        pages = []
        for page_no, image_path in enumerate(images, start=1):
            try:
                result, _ = ocr(str(image_path))
            except Exception as exc:
                print(f"[ocr] page {page_no} failed in {path.name}: {exc}")
                continue
            text = ocr_rows_to_text(result or [])
            if text:
                pages.append(f"第{page_no}页\n{text}")

    output = "\n\n".join(pages)
    if output:
        cache_path.write_text(output, encoding="utf-8")
    return output


def ocr_cache_path(path: Path) -> Path:
    stat = path.stat()
    cache_key = stable_id(str(path.resolve()), str(stat.st_size), str(stat.st_mtime_ns))
    return OCR_CACHE_DIR / f"{cache_key}.txt"


def page_image_order(path: Path) -> int:
    match = re.search(r"-(\d+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def ocr_rows_to_text(rows: List) -> str:
    lines = []
    for row in rows:
        if len(row) < 3:
            continue
        text = normalize_line(str(row[1]))
        try:
            score = float(row[2])
        except (TypeError, ValueError):
            score = 0.0
        if text and score >= 0.45:
            lines.append(text)
    return "\n".join(lines)


def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts = [node.text or "" for node in root.findall(".//w:t", namespace)]
    return "\n".join(texts)


def read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return read_txt(path)
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix == ".docx":
        return read_docx(path)
    return ""


def iter_source_files(data_dir: Path) -> Iterable[Path]:
    for path in sorted(data_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []
    step = max(1, chunk_size - chunk_overlap)
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind(mark) for mark in ["。", "！", "？", "；", "\n", " "])
            if cut > chunk_size * 0.45:
                end = start + cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - chunk_overlap) if chunk_overlap else start + step
    return [chunk for chunk in chunks if chunk]


def logical_lines(raw: str) -> List[str]:
    lines = []
    for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = normalize_line(line)
        if not line or is_low_value_line(line):
            continue
        lines.append(line)
    return merge_fragmented_lines(lines)


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
    if len(previous) < 28 and not re.search(r"[。！？；;]$", previous):
        return True
    if re.match(r"^[，、；：:）)]", current):
        return True
    if re.match(r"^(?:[A-Za-z0-9]+|年|月|日|元|室|楼|电话|邮箱)", current) and not re.search(r"[。！？；;]$", previous):
        return True
    return False


def build_fine_grained_chunks(raw: str, rel_source: str, title: str) -> List[tuple[str, str]]:
    chunks: List[tuple[str, str]] = []
    normalized = normalize_text(raw)
    lines = logical_lines(raw)

    chunks.extend(("article", chunk) for chunk in extract_article_chunks(normalized))
    chunks.extend(("section", chunk) for chunk in extract_section_chunks(normalized))
    chunks.extend(("numbered", chunk) for chunk in extract_numbered_chunks(normalized))
    chunks.extend(("line_window", chunk) for chunk in extract_line_windows(lines))
    chunks.extend(("sentence_window", chunk) for chunk in extract_sentence_windows(normalized))

    output: List[tuple[str, str]] = []
    seen = set()
    for node_type, chunk in chunks:
        chunk = normalize_text(chunk)
        if not is_high_value_chunk(chunk):
            continue
        if not (24 <= len(chunk) <= 1200):
            continue
        content = enrich_chunk_with_title(chunk, rel_source, title)
        key = re.sub(r"\s+", "", content)[:260]
        if key in seen:
            continue
        seen.add(key)
        output.append((node_type, content))
    return output


def enrich_chunk_with_title(chunk: str, rel_source: str, title: str) -> str:
    label = title or Path(rel_source).stem
    if label and label not in chunk:
        return f"文档：{label}。{chunk}"
    return chunk


def extract_article_chunks(text: str) -> List[str]:
    return bounded_parts(ARTICLE_RE.split(text), 80, 1100)


def extract_section_chunks(text: str) -> List[str]:
    return bounded_parts(SECTION_RE.split(text), 80, 1000)


def extract_numbered_chunks(text: str) -> List[str]:
    parts = bounded_parts(NUMBERED_RE.split(text), 32, 650)
    windows = []
    for idx, part in enumerate(parts):
        if idx + 1 < len(parts):
            windows.append(f"{part} {parts[idx + 1]}")
        windows.append(part)
    return windows


def bounded_parts(parts: List[str], min_len: int, max_len: int) -> List[str]:
    output = []
    for part in parts:
        part = normalize_text(part)
        if min_len <= len(part) <= max_len:
            output.append(part)
        elif len(part) > max_len:
            output.extend(split_text(part, max_len, 80))
    return output


def extract_line_windows(lines: List[str]) -> List[str]:
    windows: List[str] = []
    for idx, line in enumerate(lines):
        if not line_has_signal(line):
            continue
        for radius in (0, 1, 2, 4):
            left = max(0, idx - radius)
            right = min(len(lines), idx + radius + 1)
            window = " ".join(lines[left:right])
            if 24 <= len(window) <= 1000:
                windows.append(window)
    return windows


def extract_sentence_windows(text: str) -> List[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[。！？；;!?])|\.(?=\s)", text) if part.strip()]
    windows = []
    for idx, sentence in enumerate(sentences):
        if not line_has_signal(sentence):
            continue
        left = max(0, idx - 1)
        right = min(len(sentences), idx + 2)
        windows.append(" ".join(sentences[left:right]))
        windows.append(sentence)
    return windows


def line_has_signal(text: str) -> bool:
    return bool(VALUE_RE.search(text) or any(term in text for term in HIGH_VALUE_TERMS))


def is_high_value_chunk(text: str) -> bool:
    if any(term in text for term in HIGH_VALUE_TERMS):
        return True
    if VALUE_RE.search(text) and re.search(r"(第[一二三四五六七八九十百]+条|[1-9][.、]|（[一二三四五六七八九十]+）)", text):
        return True
    return False


def build_corpus(config: ReproConfig, rebuild: bool = False) -> List[CorpusDocument]:
    cache_path = config.index_dir / "campus_chunks.jsonl"
    if cache_path.exists() and not rebuild:
        cached = [
            CorpusDocument(**json.loads(line))
            for line in cache_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if cached and cached[0].metadata.get("corpus_version") == CORPUS_VERSION:
            return cached
        print("[corpus] cache version changed; rebuilding fine-grained corpus")

    docs: List[CorpusDocument] = []
    for source_path in iter_source_files(config.data_dir):
        try:
            raw_text = read_file(source_path)
            raw = normalize_text(raw_text)
        except Exception as exc:
            print(f"[corpus] skipped {source_path}: {exc}")
            continue
        if not raw:
            continue
        rel_source = str(source_path.relative_to(config.data_dir))
        title = source_path.stem
        for idx, (node_type, chunk) in enumerate(build_fine_grained_chunks(raw_text, rel_source, title)):
            docs.append(
                CorpusDocument(
                    doc_id=stable_id(rel_source, node_type, str(idx), chunk[:100]),
                    content=chunk,
                    source=rel_source,
                    title=title,
                    metadata={
                        "chunk_index": idx,
                        "suffix": source_path.suffix.lower(),
                        "node_type": node_type,
                        "corpus_version": CORPUS_VERSION,
                    },
                )
            )
        for idx, chunk in enumerate(split_text(raw, config.chunk_size, config.chunk_overlap)):
            docs.append(
                CorpusDocument(
                    doc_id=stable_id(rel_source, str(idx), chunk[:80]),
                    content=chunk,
                    source=rel_source,
                    title=title,
                    metadata={
                        "chunk_index": idx,
                        "suffix": source_path.suffix.lower(),
                        "node_type": "base_chunk",
                        "corpus_version": CORPUS_VERSION,
                    },
                )
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        "\n".join(json.dumps(doc.__dict__, ensure_ascii=False) for doc in docs),
        encoding="utf-8",
    )
    print(f"[corpus] built {len(docs)} chunks from {config.data_dir}")
    return docs
