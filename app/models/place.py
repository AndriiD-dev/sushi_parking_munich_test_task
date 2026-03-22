"""Domain entities for places near Marienplatz.

Uses frozen dataclasses for immutability. A shared ``BasePlace`` defines
the fields common to every point-of-interest type; concrete subclasses
add only domain-specific attributes.

The optional ``distance_meters`` field is populated via
``dataclasses.replace()`` during service-layer enrichment — shared
repository state is never mutated.
"""

from dataclasses import dataclass, field
from enum import Enum


class PaymentMethod(str, Enum):
    """Supported payment methods across all place types."""

    CASH = "cash"
    CARD = "card"
    CONTACTLESS = "contactless"
    APP = "app"

    @classmethod
    def values(cls) -> set[str]:
        """Return the set of valid string values."""
        return {m.value for m in cls}


@dataclass(frozen=True)
class BasePlace:
    """Shared fields for every point-of-interest type.

    All concrete place models must inherit from this class so that
    repositories, services, and the geo-enrichment pipeline can
    operate generically.
    """

    id: str
    name: str
    address: str
    lat: float
    lon: float
    payment_methods: tuple[str, ...] = field(default_factory=tuple)
    opening_hours: str = ""
    distance_meters: float | None = None
    distance_from_reference_meters: float | None = None


@dataclass(frozen=True)
class SushiRestaurant(BasePlace):
    """A sushi restaurant near Marienplatz."""

    rating: float = 0.0
    price_range: str = ""


@dataclass(frozen=True)
class ParkingGarage(BasePlace):
    """A parking garage near Marienplatz."""

    price_per_hour: float = 0.0
    total_spaces: int = 0
