from dataclasses import dataclass
from dataclasses import field
from typing import Any, Dict, List

from langchain_core.documents import Document


@dataclass
class RetrievedDocument:
    content: str
    source: str = ""
    score: float | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def to_retrieved(documents: List[Document]) -> List[RetrievedDocument]:
    return [
        RetrievedDocument(
            content=doc.page_content,
            source=str(doc.metadata.get("source", "")),
            score=doc.metadata.get("score"),
        )
        for doc in documents
    ]


class BaseRetriever:
    async def retrieve(self, query: str) -> List[RetrievedDocument]:
        raise NotImplementedError
