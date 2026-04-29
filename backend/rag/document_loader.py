from pathlib import Path
from typing import List

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.config import Settings


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".doc", ".docx"}


def load_documents(data_dir: Path) -> List[Document]:
    documents: List[Document] = []
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        return documents

    for path in data_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            if path.suffix.lower() == ".pdf":
                loaded = PyPDFLoader(str(path)).load()
            elif path.suffix.lower() == ".txt":
                loaded = TextLoader(str(path), encoding="utf-8").load()
            else:
                loaded = Docx2txtLoader(str(path)).load()
            for doc in loaded:
                doc.metadata["source"] = str(path)
            documents.extend(loaded)
            print(f"[documents] loaded {path.name}")
        except Exception as exc:
            print(f"[documents] skipped {path}: {exc}")
    return documents


def split_documents(documents: List[Document], settings: Settings) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    return splitter.split_documents(documents)

