"""API response models (Pydantic)."""

from pydantic import BaseModel


class ChatResponse(BaseModel):
    """Chat endpoint response with assistant reply."""

    session_id: str
    trace_id: str
    reply: str
    tool_calls_made: list[str] = []


class SessionResponse(BaseModel):
    """Session history retrieval response."""

    session_id: str
    messages: list[dict] = []


class DeleteSessionResponse(BaseModel):
    """Session deletion confirmation."""

    session_id: str
    deleted: bool = True
