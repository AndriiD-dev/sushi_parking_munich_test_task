"""Tool argument validation before dispatch.

Validates parsed JSON arguments for each tool against expected
types, ranges, and enum values. Returns clean kwargs dicts or
raises ToolArgumentsError.
"""

from typing import TYPE_CHECKING
from app.errors.base import ToolArgumentsError

if TYPE_CHECKING:
    from app.config import Settings


def _reject_unknown_keys(tool_name: str, args: dict, settings: "Settings") -> None:
    """Raise if args contain keys not allowed for this tool."""
    allowed = settings.allowed_tool_args.get(tool_name, set())
    unknown = set(args.keys()) - allowed
    if unknown:
        raise ToolArgumentsError(
            f"Tool '{tool_name}' received unknown arguments: {unknown}"
        )


def validate_search_sushi_args(args: dict, settings: "Settings") -> dict:
    """Validate and normalize arguments for search_sushi_restaurants."""
    _reject_unknown_keys("search_sushi_restaurants", args, settings)
    validated: dict = {}

    if "query" in args:
        if not isinstance(args["query"], str):
            raise ToolArgumentsError("'query' must be a string")
        validated["query"] = args["query"]

    if "min_rating" in args:
        val = args["min_rating"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'min_rating' must be a number")
        if val < 0 or val > 5:
            raise ToolArgumentsError("'min_rating' must be between 0 and 5")
        validated["min_rating"] = float(val)

    if "max_distance_meters" in args:
        val = args["max_distance_meters"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'max_distance_meters' must be a number")
        if val <= 0:
            raise ToolArgumentsError("'max_distance_meters' must be positive")
        validated["max_distance_meters"] = float(val)

    if "payment_method" in args:
        val = args["payment_method"]
        domain = settings.get_domain("sushi")
        valid_methods = domain.payment_methods if domain else set()
        if val not in valid_methods:
            raise ToolArgumentsError(
                f"'payment_method' must be one of {sorted(valid_methods)}"
            )
        validated["payment_method"] = val

    if "limit" in args:
        val = args["limit"]
        if not isinstance(val, int) or val < 1:
            raise ToolArgumentsError("'limit' must be a positive integer")
        validated["limit"] = val

    if "sort_by" in args:
        val = args["sort_by"]
        if val not in {"distance", "rating", "price"}:
            raise ToolArgumentsError("'sort_by' must be 'distance', 'rating', or 'price'")
        validated["sort_by"] = val

    if "reference_lat" in args:
        val = args["reference_lat"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'reference_lat' must be a number")
        if val < -90 or val > 90:
            raise ToolArgumentsError("'reference_lat' must be between -90 and 90")
        validated["reference_lat"] = float(val)

    if "reference_lon" in args:
        val = args["reference_lon"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'reference_lon' must be a number")
        if val < -180 or val > 180:
            raise ToolArgumentsError("'reference_lon' must be between -180 and 180")
        validated["reference_lon"] = float(val)

    return validated


def validate_sushi_details_args(args: dict, settings: "Settings") -> dict:
    """Validate arguments for get_sushi_restaurant_details."""
    _reject_unknown_keys("get_sushi_restaurant_details", args, settings)

    if "restaurant_id" not in args:
        raise ToolArgumentsError("'restaurant_id' is required")
    if not isinstance(args["restaurant_id"], str):
        raise ToolArgumentsError("'restaurant_id' must be a string")

    return {"restaurant_id": args["restaurant_id"]}


def validate_search_parking_args(args: dict, settings: "Settings") -> dict:
    """Validate and normalize arguments for search_parking_garages."""
    _reject_unknown_keys("search_parking_garages", args, settings)
    validated: dict = {}

    if "payment_method" in args:
        val = args["payment_method"]
        domain = settings.get_domain("parking")
        valid_methods = domain.payment_methods if domain else set()
        if val not in valid_methods:
            raise ToolArgumentsError(
                f"'payment_method' must be one of {sorted(valid_methods)}"
            )
        validated["payment_method"] = val

    if "max_distance_meters" in args:
        val = args["max_distance_meters"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'max_distance_meters' must be a number")
        if val <= 0:
            raise ToolArgumentsError("'max_distance_meters' must be positive")
        validated["max_distance_meters"] = float(val)

    if "max_price_per_hour" in args:
        val = args["max_price_per_hour"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'max_price_per_hour' must be a number")
        if val < 0:
            raise ToolArgumentsError("'max_price_per_hour' must be non-negative")
        validated["max_price_per_hour"] = float(val)

    if "limit" in args:
        val = args["limit"]
        if not isinstance(val, int) or val < 1:
            raise ToolArgumentsError("'limit' must be a positive integer")
        validated["limit"] = val

    if "reference_lat" in args:
        val = args["reference_lat"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'reference_lat' must be a number")
        if val < -90 or val > 90:
            raise ToolArgumentsError("'reference_lat' must be between -90 and 90")
        validated["reference_lat"] = float(val)

    if "reference_lon" in args:
        val = args["reference_lon"]
        if not isinstance(val, (int, float)):
            raise ToolArgumentsError("'reference_lon' must be a number")
        if val < -180 or val > 180:
            raise ToolArgumentsError("'reference_lon' must be between -180 and 180")
        validated["reference_lon"] = float(val)

    return validated


def validate_parking_details_args(args: dict, settings: "Settings") -> dict:
    """Validate arguments for get_parking_garage_details."""
    _reject_unknown_keys("get_parking_garage_details", args, settings)

    if "garage_id" not in args:
        raise ToolArgumentsError("'garage_id' is required")
    if not isinstance(args["garage_id"], str):
        raise ToolArgumentsError("'garage_id' must be a string")

    return {"garage_id": args["garage_id"]}


def validate_clarify_intent_args(args: dict, settings: "Settings") -> dict:
    """Validate arguments for clarify_intent."""
    _reject_unknown_keys("clarify_intent", args, settings)

    if "question" not in args:
        raise ToolArgumentsError("'question' is required")
    if not isinstance(args["question"], str):
        raise ToolArgumentsError("'question' must be a string")

    return {"question": args["question"]}


def validate_get_current_time_args(args: dict, settings: "Settings") -> dict:
    """Validate arguments for get_current_time."""
    _reject_unknown_keys("get_current_time", args, settings)
    return {}


def validate_generate_google_maps_route_args(args: dict, settings: "Settings") -> dict:
    """Validate arguments for generate_google_maps_route."""
    _reject_unknown_keys("generate_google_maps_route", args, settings)
    if "destinations" not in args:
        raise ToolArgumentsError("'destinations' is required")
    if not isinstance(args["destinations"], list):
        raise ToolArgumentsError("'destinations' must be a list")
    for dest in args["destinations"]:
        if not isinstance(dest, dict):
            raise ToolArgumentsError("each destination must be an object")
        if "lat" not in dest or "lon" not in dest:
            raise ToolArgumentsError("each destination must have 'lat' and 'lon'")
        if not isinstance(dest["lat"], (int, float)) or not isinstance(dest["lon"], (int, float)):
            raise ToolArgumentsError("'lat' and 'lon' must be numbers")
    return {"destinations": args["destinations"]}


# Registry mapping tool name → validator function
VALIDATORS: dict[str, callable] = {
    "search_sushi_restaurants": validate_search_sushi_args,
    "get_sushi_restaurant_details": validate_sushi_details_args,
    "search_parking_garages": validate_search_parking_args,
    "get_parking_garage_details": validate_parking_details_args,
    "clarify_intent": validate_clarify_intent_args,
    "get_current_time": validate_get_current_time_args,
    "generate_google_maps_route": validate_generate_google_maps_route_args,
}


def validate_tool_args(tool_name: str, args: dict, settings: "Settings") -> dict:
    """Validate tool arguments using the appropriate validator.

    Returns validated/normalized kwargs dict.
    Raises ToolArgumentsError on any validation failure.
    """
    validator = VALIDATORS.get(tool_name)
    if validator is None:
        raise ToolArgumentsError(f"No validator for tool: {tool_name}")
    return validator(args, settings)
