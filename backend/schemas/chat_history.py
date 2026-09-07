from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel


class ChatSession(BaseModel):
    session_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessage(BaseModel):
    message_id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: Optional[str] = None
    task_id: Optional[str] = None
    created_at: str
    result: Optional[dict[str, Any]] = None


class RenameSessionRequest(BaseModel):
    title: str
