"""Dynamic tool schema registry for OpenAI Function Calling.

The ``ToolRegistry`` manages tool schemas at runtime. Each domain
registers its search and details tool schemas during startup; the
registry exposes only the tools for currently-enabled domains to
the LLM.

The ``clarify_intent`` utility tool is always included.
"""

import logging
from typing import Any, Callable, Type

from pydantic import BaseModel
from app.validation.tool_response import SearchResponse, DetailsResponse, ClarifyResponse, TimeResponse, RouteResponse

logger = logging.getLogger(__name__)

# ── Domain-agnostic utility tools ─────────────────────────────────

CLARIFY_INTENT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "clarify_intent",
        "description": (
            "Use this when the user's intent is unclear or references a prior "
            "list item that cannot be resolved from session history. Ask a short "
            "clarifying question."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific clarifying question to ask the user.",
                },
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    },
}

GET_CURRENT_TIME_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": (
            "Get the current local time in Munich. "
            "Use this to answer questions like 'what is open right now?'"
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}

GET_ROUTE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "generate_google_maps_route",
        "description": (
            "Generate a Google Maps Directions URL from the user's current location "
            "to one or more destinations. Use this when the user asks for a route, "
            "directions, or navigation."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "destinations": {
                    "type": "array",
                    "description": "An ordered list of destination coordinates.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number", "description": "Latitude of the destination."},
                            "lon": {"type": "number", "description": "Longitude of the destination."}
                        },
                        "required": ["lat", "lon"],
                        "additionalProperties": False,
                    }
                }
            },
            "required": ["destinations"],
            "additionalProperties": False,
        },
    },
}


# ── Sushi tool schemas ────────────────────────────────────────────

SUSHI_SEARCH_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "search_sushi_restaurants",
        "description": (
            "Search for sushi restaurants near Marienplatz, Munich. "
            "Returns name, address, rating, price range, payment methods, "
            "opening hours, and distance_meters (from user) if user location is available. "
            "If reference coordinates are provided, it also returns distance_from_reference_meters. "
            "Pass null for max_distance_meters to return all restaurants "
            "without distance filtering — recommended for initial searches."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": ["string", "null"],
                    "description": "Text search on restaurant name or address.",
                },
                "min_rating": {
                    "type": ["number", "null"],
                    "description": "Minimum rating filter (0-5).",
                },
                "max_distance_meters": {
                    "type": ["number", "null"],
                    "description": (
                        "Maximum distance from the USER in metres. NEVER use this "
                        "to search for places near other places. If the user asks for "
                        "places near another place, pass null to get all results. "
                        "Default to null unless asked for a tight radius."
                    ),
                },
                "payment_method": {
                    "type": ["string", "null"],
                    "enum": ["cash", "card", "contactless", "any", None],
                    "description": "Filter by accepted payment method.",
                },
                "limit": {
                    "type": ["integer", "null"],
                    "description": "Maximum number of results to return. Defaults to 5, maximum 10.",
                },
                "sort_by": {
                    "type": ["string", "null"],
                    "enum": ["distance", "rating", "price", None],
                    "description": "Sort results by this field ascending (or descending for rating). Defaults to distance.",
                },
                "reference_lat": {
                    "type": ["number", "null"],
                    "description": (
                        "Optional custom reference latitude. ONLY use this if the user EXPLICITLY "
                        "names a specific place (like 'near Stachus' or 'next to the museum'). "
                        "DO NOT use this for general searches — let the system use the user's location by default."
                    ),
                },
                "reference_lon": {
                    "type": ["number", "null"],
                    "description": "Optional custom reference longitude. Must be used together with reference_lat.",
                },
            },
            "required": [
                "query", "min_rating", "max_distance_meters",
                "payment_method", "limit", "sort_by",
                "reference_lat", "reference_lon",
            ],
            "additionalProperties": False,
        },
    },
}

SUSHI_DETAILS_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "get_sushi_restaurant_details",
        "description": (
            "Get full details for a specific sushi restaurant by its ID. "
            "Use this when the user asks for more information about a listed restaurant."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "restaurant_id": {
                    "type": "string",
                    "description": "The unique ID of the sushi restaurant.",
                },
            },
            "required": ["restaurant_id"],
            "additionalProperties": False,
        },
    },
}


# ── Parking tool schemas ──────────────────────────────────────────

PARKING_SEARCH_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "search_parking_garages",
        "description": (
            "Search for parking garages near Marienplatz, Munich. "
            "Returns name, address, price per hour, payment methods, "
            "total spaces, opening hours, and distance_meters (from user) if user location is available. "
            "If reference coordinates are provided, it also returns distance_from_reference_meters. "
            "Pass null for max_distance_meters to return all garages "
            "without distance filtering — recommended for initial searches."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "payment_method": {
                    "type": ["string", "null"],
                    "enum": ["cash", "card", "contactless", "app", "any", None],
                    "description": "Filter by accepted payment method.",
                },
                "max_distance_meters": {
                    "type": ["number", "null"],
                    "description": (
                        "Maximum distance from the USER (or the reference point) in metres. "
                        "Default to null to allow full results."
                    ),
                },
                "reference_lat": {
                    "type": ["number", "null"],
                    "description": (
                        "Optional custom reference latitude. ONLY use this if the user EXPLICITLY "
                        "names a specific place (like 'near Stachus' or 'next to the museum'). "
                        "DO NOT use this for general searches — let the system use the user's location by default."
                    ),
                },
                "reference_lon": {
                    "type": ["number", "null"],
                    "description": "Optional custom reference longitude. Must be used together with reference_lat.",
                },
                "max_price_per_hour": {
                    "type": ["number", "null"],
                    "description": "Maximum price per hour in euros.",
                },
                "limit": {
                    "type": ["integer", "null"],
                    "description": "Maximum number of results to return. Defaults to 5, maximum 10.",
                },
            },
            "required": [
                "payment_method", "max_distance_meters",
                "max_price_per_hour", "limit",
                "reference_lat", "reference_lon",
            ],
            "additionalProperties": False,
        },
    },
}

PARKING_DETAILS_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "get_parking_garage_details",
        "description": (
            "Get full details for a specific parking garage by its ID. "
            "Use this when the user asks for more information about a listed garage."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "garage_id": {
                    "type": "string",
                    "description": "The unique ID of the parking garage.",
                },
            },
            "required": ["garage_id"],
            "additionalProperties": False,
        },
    },
}


# ── Tool Registry ────────────────────────────────────────────────


class ToolRegistry:
    """Dynamic registry of tool schemas for enabled domains.

    Domains register their search + details tool schemas at startup.
    The registry provides:
    - ``get_tools()`` — full tool list for the LLM (enabled domains + clarify_intent).
    - ``get_search_tool_names()`` — set of search tool names for coordinate injection.
    - ``get_domain_labels()`` — human-readable labels for the system prompt.
    """

    def __init__(self) -> None:
        self._search_schemas: list[dict] = []
        self._details_schemas: list[dict] = []
        self._search_tool_names: set[str] = set()
        self._domain_labels: list[str] = []
        self._response_models: dict[str, Type[BaseModel]] = {
            "clarify_intent": ClarifyResponse,
            "get_current_time": TimeResponse,
            "generate_google_maps_route": RouteResponse,
        }

    def register_domain(
        self,
        label: str,
        search_schema: dict,
        details_schema: dict,
        search_response_model: Type[BaseModel] = SearchResponse,
        details_response_model: Type[BaseModel] = DetailsResponse,
    ) -> None:
        """Register a domain's tool schemas.

        Args:
            label: Human-readable label (e.g. 'sushi restaurants').
            search_schema: OpenAI tool schema for the search function.
            details_schema: OpenAI tool schema for the details function.
        """
        self._search_schemas.append(search_schema)
        self._details_schemas.append(details_schema)

        search_name = search_schema["function"]["name"]
        details_name = details_schema["function"]["name"]
        
        self._search_tool_names.add(search_name)
        self._domain_labels.append(label)
        
        # Register response models for validation
        self._response_models[search_name] = search_response_model
        self._response_models[details_name] = details_response_model

        logger.info(
            "Registered tool schemas for domain '%s': %s, %s",
            label,
            search_name,
            details_schema["function"]["name"],
        )

    def get_tools(self) -> list[dict]:
        """Return the combined list of tools for the LLM payload."""
        return [
            CLARIFY_INTENT_TOOL,
            GET_CURRENT_TIME_TOOL,
            GET_ROUTE_TOOL,
            *self._search_schemas,
            *self._details_schemas,
        ]

    def get_search_tool_names(self) -> set[str]:
        """Return the set of search tool names (for coordinate injection)."""
        return set(self._search_tool_names)

    def get_domain_labels(self) -> list[str]:
        """Return human-readable domain labels for the system prompt."""
        return list(self._domain_labels)

    def get_tool_names(self) -> set[str]:
        """Return all registered tool names."""
        return set(self._response_models.keys())

    def get_response_model(self, name: str) -> Type[BaseModel] | None:
        """Return the response Pydantic model for a tool."""
        return self._response_models.get(name)
