from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_name: str = "AIRI Digital Human Assistant"
    host: str = "127.0.0.1"
    port: int = 8000

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    chat_provider: str = Field(default="zhipu", alias="CHAT_PROVIDER")
    chat_model: str = Field(default="GLM-4-Flash-250414", alias="CHAT_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        alias="GEMINI_BASE_URL",
    )
    embedding_model: str = Field(default="text-embedding-v2", alias="EMBEDDING_MODEL")
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_base_url: str = Field(default="", alias="EMBEDDING_BASE_URL")

    rag_strategy: str = Field(default="hybrid_crag", alias="RAG_STRATEGY")
    knowledge_dir: Path = Field(default=ROOT_DIR / "knowledge_data", alias="KNOWLEDGE_DIR")
    index_root: Path = Field(default=ROOT_DIR / "data" / "indexes", alias="INDEX_ROOT")
    portable_rag_config: Path = Field(
        default=ROOT_DIR / "experiments" / "rag_reproduction" / "configs" / "portable_rag.yaml",
        alias="PORTABLE_RAG_CONFIG",
    )
    portable_rag_top_k: int = Field(default=8, alias="PORTABLE_RAG_TOP_K")
    portable_rag_init_timeout_sec: float = Field(default=240.0, alias="PORTABLE_RAG_INIT_TIMEOUT_SEC")
    memory_db_path: Path = Field(default=ROOT_DIR / "data" / "memory" / "airi_memory_local.sqlite3", alias="MEMORY_DB_PATH")

    retrieval_top_k: int = Field(default=4, alias="RETRIEVAL_TOP_K")
    retrieval_timeout_sec: float = Field(default=12.0, alias="RETRIEVAL_TIMEOUT_SEC")
    llm_timeout_sec: float = Field(default=30.0, alias="LLM_TIMEOUT_SEC")
    llm_rate_limit_retries: int = Field(default=3, alias="LLM_RATE_LIMIT_RETRIES")
    llm_rate_limit_backoff_sec: float = Field(default=8.0, alias="LLM_RATE_LIMIT_BACKOFF_SEC")
    llm_rate_limit_max_backoff_sec: float = Field(default=30.0, alias="LLM_RATE_LIMIT_MAX_BACKOFF_SEC")
    chunk_size: int = Field(default=600, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")

    enable_memory_extraction: bool = Field(default=True, alias="ENABLE_MEMORY_EXTRACTION")
    enable_hyde: bool = Field(default=True, alias="ENABLE_HYDE")
    enable_crag_judge: bool = Field(default=False, alias="ENABLE_CRAG_JUDGE")
    enable_llm_actions: bool = Field(default=False, alias="ENABLE_LLM_ACTIONS")

    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    dashscope_api_key: str = Field(default="", alias="DASHSCOPE_API_KEY")
    tts_model: str = Field(default="edge-tts", alias="TTS_MODEL")
    tts_voice: str = Field(default="zh-CN-XiaoxiaoNeural", alias="TTS_VOICE")
    tts_rate: str = Field(default="+8%", alias="TTS_RATE")
    tts_cache_dir: Path = Field(default=ROOT_DIR / "data" / "tts_cache", alias="TTS_CACHE_DIR")

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def active_index_dir(self) -> Path:
        return self.index_root / self.rag_strategy

    @property
    def use_portable_rag_v4(self) -> bool:
        return self.rag_strategy.lower() in {"portable_v4", "portable-rag-v4", "v4"}

    @property
    def resolved_embedding_api_key(self) -> str:
        return self.embedding_api_key or self.openai_api_key

    @property
    def resolved_embedding_base_url(self) -> str:
        return self.embedding_base_url or self.openai_base_url

    @property
    def normalized_chat_provider(self) -> str:
        provider = self.chat_provider.lower().strip()
        if provider in {"gemini", "google", "google-gemini"}:
            return "gemini"
        if provider in {"zhipu", "glm", "bigmodel", "zhipuai"}:
            return "zhipu"
        return provider or "zhipu"

    @property
    def resolved_chat_api_key(self) -> str:
        if self.normalized_chat_provider == "gemini":
            return self.gemini_api_key or self.openai_api_key
        return self.openai_api_key

    @property
    def resolved_chat_base_url(self) -> str:
        if self.normalized_chat_provider == "gemini":
            return self.gemini_base_url
        return self.openai_base_url

    @property
    def resolved_chat_model(self) -> str:
        if self.normalized_chat_provider == "gemini" and self.chat_model.startswith("GLM"):
            return "gemini-2.0-flash-lite"
        return self.chat_model

    @property
    def llm_display_name(self) -> str:
        if self.normalized_chat_provider == "gemini":
            return "Gemini"
        if self.normalized_chat_provider == "zhipu":
            return "GLM"
        return self.normalized_chat_provider.upper()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.index_root.mkdir(parents=True, exist_ok=True)
    settings.memory_db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.tts_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
