from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    user_message: str
    user_id: str = "test_user"
    chat_history: List[ChatMessage] = Field(default_factory=list)


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = None


class RetrievedSource(BaseModel):
    content: str
    source: Optional[str] = None
    score: Optional[float] = None


class AvatarAction(BaseModel):
    expression: str = "warm"
    motion: str = "explain"
    style: str = "normal"
    reason: str = ""


class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
