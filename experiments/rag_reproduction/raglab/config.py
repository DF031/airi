from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[3]
REPRO_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=True)


@dataclass
class ReproConfig:
    data_dir: Path
    index_dir: Path
    result_dir: Path
    dataset_path: Path
    run_name: str = ""
    chunk_size: int = 650
    chunk_overlap: int = 120
    top_k: int = 4
    candidate_k: int = 8
    rrf_k: int = 60
    bm25_weight: float = 0.35
    dense_weight: float = 0.65
    crag_low_confidence: float = 0.35
    crag_high_confidence: float = 0.72
    deepnote_max_steps: int = 3
    deepnote_max_fail_steps: int = 2
    llm_temperature: float = 0.0
    llm_timeout_sec: float = 45.0
    llm_max_retries: int = 8
    llm_retry_sleep_sec: float = 30.0
    llm_request_interval_sec: float = 20.0
    embedding_timeout_sec: float = 20.0
    chat_model: str = "GLM-4.7-flash"
    openai_api_key: str = ""
    openai_base_url: str = ""
    embedding_model: str = "text-embedding-v2"
    embedding_api_key: str = ""
    embedding_base_url: str = ""

    @property
    def resolved_embedding_api_key(self) -> str:
        return self.embedding_api_key or self.openai_api_key

    @property
    def resolved_embedding_base_url(self) -> str:
        return self.embedding_base_url or self.openai_base_url


def _resolve_path(value: str | Path, base: Path = REPRO_DIR) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def load_config(path: str | Path | None = None) -> ReproConfig:
    config_path = Path(path) if path else REPRO_DIR / "configs" / "default.json"
    with config_path.open("r", encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    data = dict(raw)
    data["data_dir"] = _resolve_path(data.get("data_dir", "data"))
    data["index_dir"] = _resolve_path(data.get("index_dir", "indexes"))
    data["result_dir"] = _resolve_path(data.get("result_dir", "results"))
    data["dataset_path"] = _resolve_path(data.get("dataset_path", "datasets/dataset.json"))
    data["chat_model"] = os.getenv("CHAT_MODEL", "GLM-4.7-flash")
    data["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")
    data["openai_base_url"] = os.getenv("OPENAI_BASE_URL", "")
    data["embedding_model"] = os.getenv("EMBEDDING_MODEL", "text-embedding-v2")
    data["embedding_api_key"] = os.getenv("EMBEDDING_API_KEY", "")
    data["embedding_base_url"] = os.getenv("EMBEDDING_BASE_URL", "")

    cfg = ReproConfig(**data)
    cfg.index_dir.mkdir(parents=True, exist_ok=True)
    cfg.result_dir.mkdir(parents=True, exist_ok=True)
    cfg.dataset_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg
