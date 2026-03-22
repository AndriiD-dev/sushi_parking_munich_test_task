"""Conversation orchestrator — the main chat loop.

Manages the full lifecycle of a chat request:
1. Validate and normalize the request
2. Resolve user location
3. Append user message to session history
4. Call the LLM with tool schemas
5. Dispatch tool calls if requested
6. Re-call the LLM with tool results
7. Return the final assistant reply

The loop is bounded by config and has timeout/fallback handling.
Logs latencies, tool calls, and token usage for observability.
"""

import json
import logging
import time
import uuid

from app.config import Settings
from app.core.llm_client import LLMClient
from app.core.session_store import SessionStore, ConversationState
from app.core.tool_dispatcher import ToolDispatcher
from app.core.tool_schemas import ToolRegistry
from app.errors.base import (
    ToolArgumentsError,
    UnknownToolError,
    UpstreamServiceError,
)
from app.models.responses import ChatResponse
from app.observability.logging import AgentEvent
from app.services.geo_service import GeospatialHelper

logger = logging.getLogger(__name__)

_FALLBACK_REPLY = (
    "I'm sorry, I wasn't able to complete that request. "
    "Could you please try rephrasing your question?"
)

_LIMIT_REPLY = (
    "I reached my processing limit on that request. "
    "Could you please try rephrasing your question?"
)


class ConversationOrchestrator:
    """Orchestrates the LLM tool-call loop for chat requests.

    Dependencies are injected via constructor for testability.
    No business filtering logic lives here — that stays in services.
    """

    def __init__(
        self,
        session_store: SessionStore,
        tool_dispatcher: ToolDispatcher,
        llm_client: LLMClient,
        geo_service: GeospatialHelper,
        settings: Settings,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._sessions = session_store
        self._dispatcher = tool_dispatcher
        self._llm = llm_client
        self._geo = geo_service
        self._max_iterations = settings.max_tool_iterations

        # Build domain-aware system prompt
        self._tool_registry = tool_registry
        if tool_registry:
            self._tools = tool_registry.get_tools()
            self._system_prompt = self._build_system_prompt(
                settings.system_prompt, tool_registry.get_domain_labels()
            )
        else:
            self._tools = []
            self._system_prompt = settings.system_prompt

    @staticmethod
    def _build_system_prompt(base_prompt: str, domain_labels: list[str]) -> str:
        """Append available-domain info to the base system prompt."""
        if not domain_labels:
            return base_prompt
        if len(domain_labels) == 1:
            domains_text = domain_labels[0]
        else:
            domains_text = ", ".join(domain_labels[:-1]) + " and " + domain_labels[-1]
        suffix = (
            f"\n\n## Available Domains\n"
            f"You currently have access to data about: {domains_text}. "
            f"Only assist with topics covered by these domains."
        )
        return base_prompt + suffix

    @staticmethod
    def _prune_history(messages: list[dict], max_keep: int = 6) -> list[dict]:
        """Keep at most max_keep messages, preserving tool call pairs."""
        if len(messages) <= max_keep:
            return messages

        retained = messages[-max_keep:]

        tool_ids_in_retained = {m.get("tool_call_id") for m in retained if m.get("role") == "tool"}
        assistant_ids_in_retained = {
            tc["id"]
            for m in retained if m.get("role") == "assistant" and m.get("tool_calls")
            for tc in m["tool_calls"]
        }

        missing_assistant_ids = tool_ids_in_retained - assistant_ids_in_retained
        
        if missing_assistant_ids:
            idx = len(messages) - max_keep - 1
            while idx >= 0 and missing_assistant_ids:
                m = messages[idx]
                retained.insert(0, m)
                if m.get("role") == "assistant" and m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        missing_assistant_ids.discard(tc["id"])
                idx -= 1

        return retained

    async def handle_message(
        self,
        session_id: str,
        message: str,
        user_lat: float | None = None,
        user_lon: float | None = None,
    ) -> ChatResponse:
        """Process a chat message through the full orchestration loop.

        Returns a ChatResponse with the assistant's reply and list of
        tool calls made during this request.
        """
        request_start = time.monotonic()
        correlation_id = uuid.uuid4().hex[:12]

        # Sanitize PII from logging
        safe_lat = round(user_lat, 2) if user_lat is not None else None
        safe_lon = round(user_lon, 2) if user_lon is not None else None
        
        logger.info(
            AgentEvent.format(
                "agent.request.new",
                trace_id=correlation_id,
                session_id=session_id,
                message="[REDACTED]",
                coords=f"({safe_lat}, {safe_lon})",
            )
        )

        # Resolve user location
        geo_start = time.monotonic()
        resolved_lat, resolved_lon = self._geo.resolve_user_location(
            user_lat=user_lat,
            user_lon=user_lon,
        )
        geo_ms = (time.monotonic() - geo_start) * 1000
        
        if resolved_lat is not None and resolved_lon is not None:
            logger.info(
                AgentEvent.format(
                    "agent.geo.resolved",
                    trace_id=correlation_id,
                    session_id=session_id,
                    lat=resolved_lat,
                    lon=resolved_lon,
                    duration_ms=int(geo_ms),
                )
            )
        else:
            logger.info(
                AgentEvent.format(
                    "agent.geo.unresolved",
                    trace_id=correlation_id,
                    session_id=session_id,
                    duration_ms=int(geo_ms),
                )
            )

        # Get or create session, append user message
        state = self._sessions.get_or_create(session_id)
        state.messages = self._prune_history(state.messages)
        
        history_len = len(state.messages)
        state.messages.append({"role": "user", "content": message})
        logger.info(
            "[%s] Session history: %d prior messages",
            correlation_id,
            history_len,
        )

        # Build messages for the LLM
        dynamic_system_prompt = self._system_prompt
        if resolved_lat is not None and resolved_lon is not None:
            dynamic_system_prompt += f"\n\n## User Context\nUser's exact current location (origin): {resolved_lat}, {resolved_lon}."
        else:
            dynamic_system_prompt += f"\n\n## User Context\nUser's exact current location is unknown (cannot generate origin routes)."

        llm_messages = [
            {"role": "system", "content": dynamic_system_prompt},
            *state.messages,
        ]

        # Bounded tool-call loop
        tool_calls_made: list[str] = []
        total_prompt_tokens: int = 0
        total_completion_tokens: int = 0

        for iteration in range(self._max_iterations):
            logger.info(
                AgentEvent.format(
                    "agent.llm.start",
                    trace_id=correlation_id,
                    session_id=session_id,
                    iteration=iteration + 1,
                    messages=len(llm_messages),
                )
            )

            try:
                llm_start = time.monotonic()
                response = await self._llm.create_chat_completion(
                    messages=llm_messages,
                    tools=self._tools,
                    trace_id=correlation_id,
                    session_id=session_id,
                )
            except UpstreamServiceError:
                logger.warning(
                    AgentEvent.format(
                        "agent.llm.error",
                        trace_id=correlation_id,
                        session_id=session_id,
                        error="UpstreamServiceError",
                        iteration=iteration + 1,
                    )
                )
                return self._finish_request(
                    correlation_id, request_start, session_id, state,
                    _FALLBACK_REPLY, tool_calls_made,
                    total_prompt_tokens, total_completion_tokens,
                )

            # Accumulate token usage
            usage = getattr(response, "usage", None)
            if usage:
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens

            choice = response.choices[0]
            assistant_msg = choice.message

            # Check for tool calls
            if assistant_msg.tool_calls:
                clarify_call = next((tc for tc in assistant_msg.tool_calls if tc.function.name == "clarify_intent"), None)
                if clarify_call:
                    try:
                        args_dict = json.loads(clarify_call.function.arguments)
                        question = args_dict.get("question", "Could you please clarify?")
                    except (json.JSONDecodeError, TypeError):
                        question = "Could you please clarify?"
                        
                    tool_calls_made.append("clarify_intent")
                    logger.info("[%s] clarify_intent called", correlation_id)
                    
                    content = assistant_msg.content or ""
                    reply = f"{content}\n\n{question}".strip() if content else question
                    
                    # Store as a normal assistant message to avoid dangling tool calls
                    state.messages.append({"role": "assistant", "content": reply})
                    
                    return self._finish_request(
                        correlation_id, request_start, session_id, state,
                        reply, tool_calls_made,
                        total_prompt_tokens, total_completion_tokens,
                    )

                # Append assistant message with tool calls to history
                tool_call_dicts = []
                for tc in assistant_msg.tool_calls:
                    tool_call_dicts.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })

                state.messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content,
                    "tool_calls": tool_call_dicts,
                })
                llm_messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content,
                    "tool_calls": tool_call_dicts,
                })

                # Dispatch each tool call
                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    tool_calls_made.append(tool_name)

                    logger.info(
                        AgentEvent.format(
                            "agent.tool.start",
                            trace_id=correlation_id,
                            session_id=session_id,
                            tool=tool_name,
                        )
                    )

                    dispatch_start = time.monotonic()
                    result_content = self._dispatch_tool_safely(
                        tool_name,
                        tc.function.arguments,
                        resolved_lat,
                        resolved_lon,
                        correlation_id,
                    )
                    dispatch_ms = int((time.monotonic() - dispatch_start) * 1000)

                    # Log result summary
                    try:
                        result_data = json.loads(result_content)
                        result_count = result_data.get("count", "n/a")
                    except (json.JSONDecodeError, AttributeError):
                        result_count = "n/a"

                    logger.info(
                        AgentEvent.format(
                            "agent.tool.end",
                            trace_id=correlation_id,
                            session_id=session_id,
                            tool=tool_name,
                            duration_ms=dispatch_ms,
                            results=result_count,
                        )
                    )

                    tool_result_msg = {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_content,
                    }
                    state.messages.append(tool_result_msg)
                    llm_messages.append(tool_result_msg)

                # Continue loop, re-call LLM with tool results
                continue

            content = assistant_msg.content or ""
            if not content.strip():
                logger.warning(
                    "[%s] Empty assistant response, using fallback",
                    correlation_id,
                )
                content = _FALLBACK_REPLY

            state.messages.append({"role": "assistant", "content": content})
            return self._finish_request(
                correlation_id, request_start, session_id, state,
                content, tool_calls_made,
                total_prompt_tokens, total_completion_tokens,
            )

        # Loop limit reached
        logger.warning(
            "[%s] Tool iteration limit (%d) reached",
            correlation_id,
            self._max_iterations,
        )
        return self._finish_request(
            correlation_id, request_start, session_id, state,
            _LIMIT_REPLY, tool_calls_made,
            total_prompt_tokens, total_completion_tokens,
        )

    def _dispatch_tool_safely(
        self,
        tool_name: str,
        raw_arguments: str,
        user_lat: float | None,
        user_lon: float | None,
        correlation_id: str,
    ) -> str:
        """Dispatch a tool call, returning an error message on failure."""
        try:
            result = self._dispatcher.dispatch(
                tool_name,
                raw_arguments,
                user_lat=user_lat,
                user_lon=user_lon,
            )
            return result
        except UnknownToolError as exc:
            logger.warning("[%s] Unknown tool: %s", correlation_id, exc)
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except ToolArgumentsError as exc:
            logger.warning("[%s] Tool argument error: %s", correlation_id, exc)
            return json.dumps({"error": f"Invalid arguments for tool '{tool_name}': {exc}"})

    def _finish_request(
        self,
        correlation_id: str,
        request_start: float,
        session_id: str,
        state: "ConversationState",
        assistant_reply: str,
        tool_calls: list[str],
        total_prompt_tokens: int,
        total_completion_tokens: int,
    ) -> ChatResponse:
        """Finalize the request, log metrics, and return the response."""
        elapsed_ms = int((time.monotonic() - request_start) * 1000)
        total_tokens = total_prompt_tokens + total_completion_tokens

        logger.info(
            AgentEvent.format(
                "agent.turn.end",
                trace_id=correlation_id,
                session_id=session_id,
                duration_ms=elapsed_ms,
                total_tokens=total_tokens,
                tool_count=len(tool_calls),
            )
        )

        # Append assistant reply to session (guard against double-append)
        last = state.messages[-1] if state.messages else {}
        if last.get("role") != "assistant" or last.get("content") != assistant_reply:
            state.messages.append({"role": "assistant", "content": assistant_reply})

        return ChatResponse(
            session_id=session_id,
            trace_id=correlation_id,
            reply=assistant_reply,
            tool_calls_made=tool_calls,
        )
