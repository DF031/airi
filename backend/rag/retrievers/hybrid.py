import asyncio
from typing import Dict, List

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.core.config import Settings
from backend.rag.retrievers.base import BaseRetriever, RetrievedDocument
from backend.rag.retrievers.naive import NaiveRetriever


class HybridRetriever(BaseRetriever):
    def __init__(self, vector_store: FAISS, documents: List[Document], settings: Settings):
        self.vector = NaiveRetriever(vector_store, settings)
        self.settings = settings
        self.bm25 = BM25Retriever.from_documents(documents) if documents else None
        if self.bm25:
            self.bm25.k = max(settings.retrieval_top_k * 2, 6)

    async def retrieve(self, query: str) -> List[RetrievedDocument]:
        try:
            dense = await self.vector.retrieve(query)
        except TimeoutError as exc:
            print(f"[rag] dense retrieval timed out, using bm25 fallback: {exc}")
            dense = []
        except Exception as exc:
            print(f"[rag] dense retrieval failed, using bm25 fallback: {exc}")
            dense = []

        sparse: List[RetrievedDocument] = []
        if self.bm25:
            try:
                bm25_docs = await asyncio.wait_for(
                    asyncio.to_thread(self.bm25.invoke, query),
                    timeout=max(3.0, self.settings.retrieval_timeout_sec / 2),
                )
                sparse = [
                    RetrievedDocument(
                        content=doc.page_content,
                        source=str(doc.metadata.get("source", "")),
                        score=None,
                    )
                    for doc in bm25_docs
                ]
            except Exception as exc:
                print(f"[rag] bm25 retrieval failed: {exc}")

        merged: Dict[str, RetrievedDocument] = {}
        for rank, doc in enumerate(dense):
            key = doc.content[:300]
            doc.score = (doc.score or 0.0) + rank * 0.01
            merged[key] = doc
        for rank, doc in enumerate(sparse):
            key = doc.content[:300]
            if key not in merged:
                doc.score = 1000 + rank
                merged[key] = doc
        return list(merged.values())[: self.settings.retrieval_top_k]
