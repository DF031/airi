from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


def stable_id(*parts: str) -> str:
    return hashlib.sha1("||".join(parts).encode("utf-8", errors="ignore")).hexdigest()[:16]


@dataclass(frozen=True)
class PortableDocument:
    doc_id: str
    text: str
    source: str
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    parent_id: str
    text: str
    source: str
    title: str = ""
    unit_type: str = "child"
    heading_path: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalHit:
    evidence: EvidenceUnit
    score: float
    rank: int
    retriever: str
    signals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidence"] = asdict(self.evidence)
        return data


@dataclass
class AnswerPack:
    question: str
    answer: str
    status: str
    confidence: float
    hits: List[RetrievalHit]
    citations: List[Dict[str, Any]]
    trace: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "status": self.status,
            "confidence": self.confidence,
            "hits": [hit.to_dict() for hit in self.hits],
            "citations": self.citations,
            "trace": self.trace,
        }

