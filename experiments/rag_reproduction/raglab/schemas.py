from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CorpusDocument:
    doc_id: str
    content: str
    source: str
    title: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    content: str
    source: str
    doc_id: str
    rank: int
    score: Optional[float] = None
    retrieval: str = "dense"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResult:
    method: str
    question: str
    answer: str
    evidences: List[Evidence]
    trace: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidences"] = [asdict(item) for item in self.evidences]
        return data

