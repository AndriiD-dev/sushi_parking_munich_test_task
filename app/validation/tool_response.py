"""Pydantic schemas for strict tool response validation.

These models ensure that the data returned by tools (search results, details, etc.)
strictly follows the structure expected by the LLM and the frontend.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class BaseResponse(BaseModel):
    """Base response model with strict configuration."""
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

class PlaceResponse(BaseResponse):
    """Schema for a single place (sushi or parking) in a tool result."""
    id: str
    name: str
    address: str
    lat: float
    lon: float
    payment_methods: list[str] = Field(default_factory=list)
    opening_hours: str = ""
    distance_meters: float | None = None
    distance_from_reference_meters: float | None = None
    
    # Domain specific (made optional here to allow use in generic search)
    rating: float | None = None
    price_range: str | None = None
    price_per_hour: float | None = None
    total_spaces: int | None = None

class SearchResponse(BaseResponse):
    """Schema for search tool results."""
    results: list[PlaceResponse]
    count: int

class DetailsResponse(PlaceResponse):
    """Schema for details tool results (same as PlaceResponse but used for single item)."""
    pass

class ClarifyResponse(BaseResponse):
    """Schema for clarify_intent tool results."""
    question: str

class TimeResponse(BaseResponse):
    """Schema for get_current_time tool results."""
    time: str

class RouteResponse(BaseResponse):
    """Schema for a generated Google Maps route URL."""
    url: str
