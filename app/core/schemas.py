from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LineEvent(BaseModel):
    user_id: str
    reply_token: str
    message_text: str = Field(min_length=1)
    timestamp: datetime | None = None
    event_type: str = "message"


class Citation(BaseModel):
    source: str
    excerpt: str = ""


class RetrievalResult(BaseModel):
    status: Literal["success", "empty", "error"]
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    answer: str
    tool_calls: list[str] = Field(default_factory=list)
    status: Literal["completed", "fallback", "error"] = "completed"


class RequestContext(BaseModel):
    request_id: str
    event: LineEvent


class LineWebhookPayload(BaseModel):
    events: list[dict] = Field(default_factory=list)


class LineReply(BaseModel):
    reply_token: str
    text: str
