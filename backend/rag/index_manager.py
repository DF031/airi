from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from backend.core.config import Settings
from backend.rag.document_loader import load_documents, split_documents


class KnowledgeIndex:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.resolved_embedding_api_key,
            base_url=settings.resolved_embedding_base_url,
            model=settings.embedding_model,
            chunk_size=20,
            timeout=settings.retrieval_timeout_sec,
            max_retries=1,
            check_embedding_ctx_length=False,
        )
        self.vector_store: FAISS | None = None
        self.loaded_index_dir: Path | None = None

    @property
    def index_dir(self) -> Path:
        return self.settings.active_index_dir

    def load_or_build(self) -> FAISS:
        if (self.index_dir / "index.faiss").exists() and (self.index_dir / "index.pkl").exists():
            self.vector_store = FAISS.load_local(
                str(self.index_dir),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            self.loaded_index_dir = self.index_dir
            print(f"[rag] loaded index from {self.index_dir}")
            return self.vector_store

        legacy_dir = self._legacy_index_dir()
        if legacy_dir and (legacy_dir / "index.faiss").exists() and (legacy_dir / "index.pkl").exists():
            self.vector_store = FAISS.load_local(
                str(legacy_dir),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            self.loaded_index_dir = legacy_dir
            print(f"[rag] loaded legacy experiment index from {legacy_dir}")
            return self.vector_store
        return self.build()

    def build(self) -> FAISS:
        docs = load_documents(self.settings.knowledge_dir)
        chunks: List[Document] = split_documents(docs, self.settings)
        if not chunks:
            raise RuntimeError(f"No supported documents found in {self.settings.knowledge_dir}")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(str(self.index_dir))
        self.loaded_index_dir = self.index_dir
        print(f"[rag] built {len(chunks)} chunks into {self.index_dir}")
        return self.vector_store

    def all_documents(self) -> List[Document]:
        if self.vector_store is None:
            return []
        return list(self.vector_store.docstore._dict.values())

    def _legacy_index_dir(self) -> Path | None:
        root = Path(__file__).resolve().parents[2]
        strategy = self.settings.rag_strategy.lower()
        legacy_map = {
            "naive": root / "rag_experiments" / "faiss_index_baseline",
            "hyde": root / "rag_experiments" / "faiss_index_baseline",
            "crag": root / "rag_experiments" / "faiss_index_baseline",
            "hybrid": root / "rag_experiments" / "faiss_index_exp1",
            "hybrid_crag": root / "rag_experiments" / "faiss_index_exp1",
            "graph_lite": root / "rag_experiments" / "faiss_index_exp2",
        }
        return legacy_map.get(strategy)
