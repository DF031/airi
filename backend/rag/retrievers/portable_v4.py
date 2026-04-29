import asyncio
from pathlib import Path
from typing import Any, List

from backend.core.config import Settings
from backend.rag.retrievers.base import BaseRetriever, RetrievedDocument


class PortableV4Retriever(BaseRetriever):
    """Adapter that brings the research PortableRAGV4 pipeline into the app."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.config_path = settings.portable_rag_config
        self.top_k = max(1, settings.portable_rag_top_k)
        self._pipeline: Any | None = None
        self._lock = asyncio.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def is_loading(self) -> bool:
        return self._lock.locked()

    async def warmup(self) -> None:
        await self._get_pipeline()

    async def retrieve(self, query: str) -> List[RetrievedDocument]:
        pipeline = await self._get_pipeline()
        answer_pack = await asyncio.to_thread(pipeline.answer, query, self.top_k)
        return self._to_documents(answer_pack)

    async def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        async with self._lock:
            if self._pipeline is None:
                self._pipeline = await asyncio.to_thread(self._build_pipeline)
        return self._pipeline

    def _build_pipeline(self) -> Any:
        from experiments.rag_reproduction.raglab.portable.v4 import PortableRAGV4

        config_path = Path(self.config_path)
        print(f"[rag] loading PortableRAGV4 from {config_path}")
        pipeline = PortableRAGV4.from_config(str(config_path))
        print(
            "[rag] PortableRAGV4 ready: "
            f"{len(pipeline.documents)} docs, {len(pipeline.units)} evidence units"
        )
        return pipeline

    def describe(self) -> dict[str, Any]:
        description = {
            "engine": "portable_rag_v4",
            "loaded": self._pipeline is not None,
            "loading": self._lock.locked(),
            "config_path": str(self.config_path),
            "top_k": self.top_k,
        }
        if self._pipeline is not None:
            description.update(
                {
                    "document_count": len(self._pipeline.documents),
                    "evidence_unit_count": len(self._pipeline.units),
                    "context_unit_count": len(self._pipeline.context_units),
                    "semantic_enabled": self._pipeline.semantic is not None,
                    "semantic_context_index": self._pipeline.semantic_context_embeddings is not None,
                }
            )
        return description

    def _to_documents(self, answer_pack: Any) -> List[RetrievedDocument]:
        shared_metadata = {
            "portable_v4_answer": answer_pack.answer,
            "portable_v4_status": answer_pack.status,
            "portable_v4_confidence": float(answer_pack.confidence),
            "portable_v4_citations": answer_pack.citations,
            "portable_v4_trace": answer_pack.trace,
        }
        documents: List[RetrievedDocument] = []
        for hit in answer_pack.hits:
            evidence = hit.evidence
            documents.append(
                RetrievedDocument(
                    content=self._content_from_hit(hit),
                    source=evidence.source,
                    score=float(hit.score) if hit.score is not None else None,
                    metadata={
                        **shared_metadata,
                        "unit_id": evidence.unit_id,
                        "unit_type": evidence.unit_type,
                        "title": evidence.title,
                        "heading_path": evidence.heading_path,
                        "retriever": hit.retriever,
                        "signals": hit.signals,
                    },
                )
            )

        if not documents:
            documents.append(
                RetrievedDocument(
                    content="",
                    source="portable_rag_v4",
                    score=float(answer_pack.confidence),
                    metadata={**shared_metadata, "answer_hint_only": True},
                )
            )
        return documents

    @staticmethod
    def _content_from_hit(hit: Any) -> str:
        evidence = hit.evidence
        body = str(evidence.metadata.get("block_text") or evidence.text).strip()
        title = str(evidence.title or evidence.source).strip()
        heading = " > ".join(str(item).strip() for item in evidence.heading_path if str(item).strip())
        parts = [part for part in (title, heading, body) if part]
        return "\n".join(parts)
