"""Minimal LLM client abstraction for testability.

Defines a Protocol for chat completions so the orchestrator depends
on an abstraction, not directly on the OpenAI SDK. The concrete
OpenAIClient wraps the async client with config-driven model/timeout.
"""

import logging
import time
from typing import Any, Protocol

from openai import AsyncOpenAI, APITimeoutError, APIConnectionError

from app.config import Settings
from app.errors.base import UpstreamServiceError
from app.observability.logging import AgentEvent

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM chat completion providers."""

    async def create_chat_completion(
        self,
        messages: list[dict],
        tools: list[dict],
        trace_id: str | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Send a chat completion request. Returns the API response."""
        ...


class OpenAIClient:
    """Concrete OpenAI chat completion client.

    Configuration (model, temperature, timeout, max_tokens) comes
    entirely from the injected Settings instance.
    Logs latency and token usage for every request.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )
        self._model = settings.openai_model
        self._temperature = settings.openai_temperature
        self._max_tokens = settings.openai_max_tokens
        self._reasoning_effort = settings.openai_reasoning_effort

    async def create_chat_completion(
        self,
        messages: list[dict],
        tools: list[dict],
        trace_id: str | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Call OpenAI Chat Completions API.

        Translates OpenAI-specific exceptions into UpstreamServiceError.
        Logs latency and token usage on every call.
        """
        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self._temperature,
                max_completion_tokens=self._max_tokens,
                reasoning_effort=self._reasoning_effort,
            )
        except APITimeoutError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "[%s] OpenAI API timeout after %.1fs: %s", trace_id, elapsed, exc
            )
            raise UpstreamServiceError(
                f"LLM request timed out after {self._client.timeout}s"
            ) from exc
        except APIConnectionError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "[%s] OpenAI connection error after %.1fs: %s", trace_id, elapsed, exc
            )
            raise UpstreamServiceError(
                "Unable to connect to LLM service"
            ) from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Extract and log token usage
        usage = getattr(response, "usage", None)
        tokens = {}
        if usage:
            tokens = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

        logger.info(
            AgentEvent.format(
                "agent.llm.end",
                trace_id=trace_id,
                session_id=session_id,
                model=response.model,
                duration_ms=elapsed_ms,
                **tokens,
            )
        )

        return response
