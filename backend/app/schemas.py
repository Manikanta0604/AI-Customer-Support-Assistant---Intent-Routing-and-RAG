from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


Intent = Literal["billing", "technical", "account", "product", "complaint", "general"]


class Citation(BaseModel):
    source: str
    section: str | None = None
    passage: str
    score: float


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=3000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message_id: int
    answer: str
    intent: Intent
    confidence: float
    citations: list[Citation]
    escalated: bool
    escalation_id: int | None = None


class Message(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    intent: str | None
    created_at: datetime


class Escalation(BaseModel):
    id: int
    session_id: str
    reason: str
    customer_message: str
    status: Literal["open", "in_progress", "resolved"]
    created_at: datetime


class EscalationUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved"]
