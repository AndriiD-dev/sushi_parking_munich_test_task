"""API request models (Pydantic)."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message from the frontend.

    Pydantic handles structural validation (types, required fields).
    Semantic validation (message content, coordinate ranges) is handled
    by the request guard.
    """

    session_id: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=10000)
    user_lat: float | None = None
    user_lon: float | None = None
