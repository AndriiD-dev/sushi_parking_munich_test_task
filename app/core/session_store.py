"""In-memory session store for conversation state.

Each session maintains an OpenAI-compatible message list for multi-turn
conversations. Sessions expire after the configured TTL.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ConversationState:
    """Per-session conversation state."""

    session_id: str
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    last_active: datetime = field(default_factory=_now)


class SessionStore:
    """In-memory store mapping session IDs to conversation state.

    Thread safety note: this is suitable for single-process async
    servers (uvicorn with one worker). For multi-process or
    distributed deployments, swap in Redis.
    """

    def __init__(self, ttl_minutes: int = 30, max_sessions: int = 1000) -> None:
        self._store: dict[str, ConversationState] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_sessions = max_sessions

    def get_or_create(self, session_id: str) -> ConversationState:
        """Return existing session or create a new one, evicting oldest if full."""
        self._lazy_cleanup()
        if session_id in self._store:
            state = self._store[session_id]
            state.last_active = _now()
            return state

        # If at capacity, evict the least recently used
        if len(self._store) >= self._max_sessions:
            oldest_sid = min(self._store, key=lambda k: self._store[k].last_active)
            logger.warning("Session limit reached (%d), evicting oldest session: %s", self._max_sessions, oldest_sid)
            self.delete(oldest_sid)

        state = ConversationState(session_id=session_id)
        self._store[session_id] = state
        logger.info("Session created: %s", session_id)
        return state

    def get(self, session_id: str) -> ConversationState | None:
        """Return session state or None if not found / expired."""
        self._lazy_cleanup()
        state = self._store.get(session_id)
        if state is not None:
            state.last_active = _now()
        return state

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        removed = self._store.pop(session_id, None) is not None
        if removed:
            logger.info("Session deleted: %s", session_id)
        return removed

    def add_message(self, session_id: str, message: dict) -> None:
        """Append a message to an existing session's history."""
        state = self._store.get(session_id)
        if state is not None:
            state.messages.append(message)
            state.last_active = _now()

    def count(self) -> int:
        """Return the number of active sessions."""
        return len(self._store)

    def _lazy_cleanup(self) -> None:
        """Remove expired sessions. Called lazily on access."""
        now = _now()
        expired = [
            sid
            for sid, state in self._store.items()
            if (now - state.last_active) > self._ttl
        ]
        for sid in expired:
            del self._store[sid]
            logger.info("Session expired and removed: %s", sid)
