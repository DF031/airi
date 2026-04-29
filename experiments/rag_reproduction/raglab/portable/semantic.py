from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np


@dataclass
class SemanticReranker:
    model: object
    model_path: Path

    @classmethod
    def try_create(cls) -> "SemanticReranker | None":
        model_path = find_local_sentence_model()
        if model_path is None:
            return None
        if not ensure_torch_importable():
            return None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(str(model_path), device="cpu")
        except Exception:
            return None
        return cls(model=model, model_path=model_path)

    def score(self, query: str, texts: Sequence[str], batch_size: int = 32) -> list[float]:
        if not texts:
            return []
        embeddings = self.embed([self.format_query(query), *texts], batch_size=batch_size)
        query_vec = embeddings[0]
        doc_vecs = embeddings[1:]
        return [float(np.dot(query_vec, doc_vec)) for doc_vec in doc_vecs]

    def embed(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            embeddings = self.model.encode(
                list(texts),
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return np.asarray(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed([self.format_query(query)], batch_size=1)[0]

    def format_query(self, query: str) -> str:
        if "bge-" in str(self.model_path).lower():
            return "为这个句子生成表示以用于检索相关文章：" + query
        return query


def find_local_sentence_model() -> Path | None:
    env_path = os.environ.get("PORTABLE_RAG_SENTENCE_MODEL")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    candidates.extend(
        [
            home
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--BAAI--bge-small-zh-v1.5"
            / "snapshots"
            / "7999e1d3359715c523056ef9478215996d62a620",
            home
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
            / "snapshots"
            / "86741b4e3f5cb7765a600d3a3d55a0f6a6cb443d",
            home
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--sentence-transformers--all-MiniLM-L6-v2"
            / "snapshots"
            / "c9745ed1d9f207416be6d2e6f8de32d1f16199bec",
        ]
    )
    for path in candidates:
        if (path / "config.json").exists() and (path / "tokenizer.json").exists():
            return path
    return None


def ensure_torch_importable() -> bool:
    try:
        import torch  # noqa: F401

        refresh_transformers_torch_cache()
        return True
    except Exception:
        pass

    extra_sites = []
    env_site = os.environ.get("PORTABLE_RAG_TORCH_SITE")
    if env_site:
        extra_sites.append(Path(env_site))
    extra_sites.extend(
        [
            Path("C:/Anaconda3/Lib/site-packages"),
            Path(os.environ.get("CONDA_PREFIX", "")) / "Lib" / "site-packages",
        ]
    )
    for site in extra_sites:
        if not site.exists():
            continue
        site_text = str(site)
        if site_text not in sys.path:
            sys.path.append(site_text)
        try:
            import torch  # noqa: F401

            refresh_transformers_torch_cache()
            return True
        except Exception:
            continue
    return False


def refresh_transformers_torch_cache() -> None:
    module = sys.modules.get("transformers.utils.import_utils")
    if module is None:
        return
    for name in ("is_torch_available", "get_torch_version"):
        func = getattr(module, name, None)
        cache_clear = getattr(func, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()
