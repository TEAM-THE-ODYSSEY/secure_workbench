from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ToolCall(BaseModel):
    tool_name: str
    tool_input: Any


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
