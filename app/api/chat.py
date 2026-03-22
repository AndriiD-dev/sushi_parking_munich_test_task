"""Chat API endpoints.

Thin route handlers that delegate to the orchestrator and session store.
No orchestration or business logic lives here.
"""

import logging

from fastapi import APIRouter, Request

from app.core.security import SecurityDep, limiter
from app.errors.base import InvalidRequestError, SessionNotFoundError
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse, DeleteSessionResponse, SessionResponse
from app.validation.request_guard import validate_chat_request

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("5/minute")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Send a message and receive an assistant reply.

    Validates the request, then delegates to the orchestrator.
    """
    settings = request.app.state.settings
    validate_chat_request(body, settings)

    orchestrator = request.app.state.orchestrator
    if orchestrator is None:
        raise InvalidRequestError(
            "Chat is not available — LLM is not configured. "
            "Set OPENAI_API_KEY in your environment."
        )

    return await orchestrator.handle_message(
        session_id=body.session_id,
        message=body.message.strip(),
        user_lat=body.user_lat,
        user_lon=body.user_lon,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
@limiter.limit("10/minute")
async def get_session(request: Request, session_id: str) -> SessionResponse:
    """Retrieve conversation history for a session."""
    session_store = request.app.state.session_store
    state = session_store.get(session_id)
    if state is None:
        raise SessionNotFoundError(f"Session '{session_id}' not found.")

    # Return a safe copy of messages (filter out tool_calls internals)
    safe_messages = []
    for msg in state.messages:
        safe_msg = {"role": msg["role"]}
        if msg.get("content"):
            safe_msg["content"] = msg["content"]
        safe_messages.append(safe_msg)

    return SessionResponse(session_id=session_id, messages=safe_messages)


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
@limiter.limit("10/minute")
async def delete_session(request: Request, session_id: str) -> DeleteSessionResponse:
    """Delete a session and its conversation history."""
    session_store = request.app.state.session_store
    deleted = session_store.delete(session_id)
    return DeleteSessionResponse(session_id=session_id, deleted=deleted)
