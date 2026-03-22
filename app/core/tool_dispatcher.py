"""Tool dispatcher — maps tool names to service handlers.

Responsibilities:
- Maintain registry of tool name → handler
- Parse raw JSON arguments safely
- Validate arguments before dispatch
- Serialize results to JSON strings
- Return controlled errors for unknown/malformed tool calls
"""

import json
import logging
from typing import Any, Callable
from app.core.tool_schemas import ToolRegistry
from app.errors.base import ToolArgumentsError, UnknownToolError
from app.validation.tool_args import validate_tool_args

logger = logging.getLogger(__name__)


class ToolDispatcher:
    """Routes tool calls to registered handlers.

    Each handler is a thin callable that delegates to a service method.
    The dispatcher is responsible for argument parsing/validation and
    result serialization — not for business logic.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        settings: "Settings",
    ) -> None:
        from app.config import Settings  # Type hinting only
        self._registry: dict[str, Callable[..., Any]] = {}
        self._tool_registry = registry
        self._settings = settings
        self._search_tool_names: set[str] = registry.get_search_tool_names()

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a tool handler by name."""
        self._registry[name] = handler
        logger.debug("Registered tool handler: %s", name)

    def dispatch(
        self,
        tool_name: str,
        raw_arguments: str,
        *,
        user_lat: float | None = None,
        user_lon: float | None = None,
    ) -> str:
        """Dispatch a single tool call and return a JSON result string.

        Args:
            tool_name: The function name from the model's tool call.
            raw_arguments: The raw JSON string of arguments.
            user_lat: Resolved user latitude for distance-aware queries.
            user_lon: Resolved user longitude for distance-aware queries.

        Returns:
            JSON-serialized result string.

        Raises:
            UnknownToolError: If the tool name is not registered.
            ToolArgumentsError: If arguments are malformed or invalid.
        """
        # Check tool exists
        handler = self._registry.get(tool_name)
        if handler is None:
            raise UnknownToolError(f"Unknown tool: {tool_name}")

        # Parse JSON arguments
        try:
            raw_args = json.loads(raw_arguments) if raw_arguments else {}
        except (json.JSONDecodeError, TypeError) as exc:
            raise ToolArgumentsError(
                f"Malformed JSON arguments for tool '{tool_name}': {exc}"
            ) from exc

        if not isinstance(raw_args, dict):
            raise ToolArgumentsError(
                f"Tool arguments must be a JSON object, got {type(raw_args).__name__}"
            )

        raw_args = {k: v for k, v in raw_args.items() if v is not None}

        # Validate arguments
        validated_args = validate_tool_args(tool_name, raw_args, self._settings)

        # Inject user coordinates for tools that need it
        if tool_name in self._search_tool_names or tool_name == "generate_google_maps_route":
            if user_lat is not None and user_lon is not None:
                validated_args["user_lat"] = user_lat
                validated_args["user_lon"] = user_lon

        # Execute handler
        logger.info("Dispatching tool: %s", tool_name)
        result = handler(**validated_args)

        # Validate and serialize result against schema
        return self._serialize_result(tool_name, result)

    def _serialize_result(self, tool_name: str, result: Any) -> str:
        """Validate result against Pydantic schema and return JSON string."""
        model = self._tool_registry.get_response_model(tool_name)
        
        if model is None:
            # Fallback for unregistered tools
            logger.warning("No response model found for tool: %s", tool_name)
            return json.dumps(result, default=str)

        try:
            if result is None:
                # Handle details not found
                if "details" in tool_name:
                    return json.dumps({"result": "No matching item found."})
                return json.dumps({"results": [], "count": 0})

            if isinstance(result, list):
                # Search tools return lists, wrap in SearchResponse
                items = [self._to_dict(item) for item in result]
                validated = model.model_validate({"results": items, "count": len(items)})
                return validated.model_dump_json(exclude_none=True)

            # Single item (DetailsResponse, ClarifyResponse, TimeResponse)
            data = self._to_dict(result) if not isinstance(result, dict) else result
            validated = model.model_validate(data)
            return validated.model_dump_json(exclude_none=True)

        except Exception as exc:
            logger.error(
                "Strict validation failed for tool '%s' return: %s", 
                tool_name, exc, exc_info=True
            )
            return json.dumps({"error": "Internal data validation failed."}, ensure_ascii=False)

    @staticmethod
    def _to_dict(obj: Any) -> dict:
        """Convert any result item to a dictionary for Pydantic validation."""
        if hasattr(obj, "__dict__"):
            # Dataclasses or objects
            from dataclasses import asdict, is_dataclass
            if is_dataclass(obj):
                d = asdict(obj)
                # Convert tuples to lists for JSON/Pydantic
                for key, val in d.items():
                    if isinstance(val, tuple):
                        d[key] = list(val)
                return d
            return obj.__dict__
        return obj
