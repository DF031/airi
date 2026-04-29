from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from backend.core.config import Settings
from backend.rag.retrievers.base import BaseRetriever
from backend.rag.retrievers.portable_v4 import PortableV4Retriever

if TYPE_CHECKING:
    from langchain_community.vectorstores import FAISS

    from backend.rag.index_manager import KnowledgeIndex


def build_retriever(
    index: "KnowledgeIndex | None",
    vector_store: "FAISS | None",
    settings: Settings,
    client: AsyncOpenAI,
) -> BaseRetriever:
    strategy = settings.rag_strategy.lower()

    if settings.use_portable_rag_v4:
        return PortableV4Retriever(settings)

    if index is None or vector_store is None:
        raise RuntimeError(f"RAG strategy {settings.rag_strategy} requires a loaded vector index")

    if strategy == "naive":
        from backend.rag.retrievers.naive import NaiveRetriever

        return NaiveRetriever(vector_store, settings)

    documents = index.all_documents()
    if strategy == "hybrid":
        from backend.rag.retrievers.hybrid import HybridRetriever

        return HybridRetriever(vector_store, documents, settings)
    if strategy == "hyde":
        from backend.rag.retrievers.hyde import HyDERetriever
        from backend.rag.retrievers.naive import NaiveRetriever

        return HyDERetriever(NaiveRetriever(vector_store, settings), settings, client)
    if strategy == "crag":
        from backend.rag.retrievers.crag import CorrectiveRetriever
        from backend.rag.retrievers.naive import NaiveRetriever

        return CorrectiveRetriever(NaiveRetriever(vector_store, settings), settings, client)
    if strategy == "hybrid_crag":
        from backend.rag.retrievers.crag import CorrectiveRetriever
        from backend.rag.retrievers.hybrid import HybridRetriever

        return CorrectiveRetriever(HybridRetriever(vector_store, documents, settings), settings, client)

    print(f"[rag] unknown RAG_STRATEGY={settings.rag_strategy}, fallback to naive")
    from backend.rag.retrievers.naive import NaiveRetriever

    return NaiveRetriever(vector_store, settings)
