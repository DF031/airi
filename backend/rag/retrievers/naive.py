import asyncio
from typing import List

from langchain_community.vectorstores import FAISS

from backend.core.config import Settings
from backend.rag.retrievers.base import BaseRetriever, RetrievedDocument


class NaiveRetriever(BaseRetriever):
    def __init__(self, vector_store: FAISS, settings: Settings):
        self.vector_store = vector_store
        self.settings = settings

    async def retrieve(self, query: str) -> List[RetrievedDocument]:
        docs_with_scores = await asyncio.wait_for(
            asyncio.to_thread(
                self.vector_store.similarity_search_with_score,
                query,
                k=self.settings.retrieval_top_k,
            ),
            timeout=self.settings.retrieval_timeout_sec,
        )
        results: List[RetrievedDocument] = []
        for doc, score in docs_with_scores:
            results.append(
                RetrievedDocument(
                    content=doc.page_content,
                    source=str(doc.metadata.get("source", "")),
                    score=float(score),
                )
            )
        return results
