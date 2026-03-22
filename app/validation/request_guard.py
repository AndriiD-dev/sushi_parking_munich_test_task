"""Request validation for chat endpoints.

Performs semantic validation beyond what Pydantic covers:
message content, length, and coordinate consistency/range.
"""

from app.config import Settings
from app.errors.base import InvalidRequestError
from app.models.requests import ChatRequest


def validate_chat_request(request: ChatRequest, settings: Settings) -> None:
    """Validate a ChatRequest semantically.

    Raises InvalidRequestError for:
    - empty or whitespace-only messages
    - messages exceeding max length
    - partial coordinate pairs (one provided, other missing)
    - coordinates outside valid ranges
    """
    # Message must not be whitespace-only (Pydantic already checks empty)
    if not request.message.strip():
        raise InvalidRequestError(
            "Message must not be empty or whitespace-only.",
            field="message",
        )

    # Message length check
    if len(request.message) > settings.max_user_message_chars:
        raise InvalidRequestError(
            f"Message exceeds maximum length of {settings.max_user_message_chars} characters.",
            field="message",
        )

    # Coordinate consistency — if one is provided, both must be
    lat_present = request.user_lat is not None
    lon_present = request.user_lon is not None
    if lat_present != lon_present:
        raise InvalidRequestError(
            "Both user_lat and user_lon must be provided together, or neither.",
            field="user_lat" if not lat_present else "user_lon",
        )

    # Coordinate range validation
    if request.user_lat is not None and not (-90 <= request.user_lat <= 90):
        raise InvalidRequestError(
            "user_lat must be between -90 and 90.",
            field="user_lat",
        )
    if request.user_lon is not None and not (-180 <= request.user_lon <= 180):
        raise InvalidRequestError(
            "user_lon must be between -180 and 180.",
            field="user_lon",
        )
