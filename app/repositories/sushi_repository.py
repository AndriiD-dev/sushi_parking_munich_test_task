"""Sushi restaurant repository — loads and indexes sushi.json at startup."""

from typing import Callable

from app.models.place import SushiRestaurant
from app.repositories.base import BaseJsonRepository
from app.validation.dataset_validator import validate_sushi_record


class SushiRepository(BaseJsonRepository[SushiRestaurant]):
    """In-memory repository for sushi restaurants.

    Inherits JSON loading, validation, indexing, and read access from
    ``BaseJsonRepository``. Only the record-mapping factory and
    domain-specific metadata are defined here.
    """

    @property
    def _dataset_name(self) -> str:
        return "sushi"

    @property
    def _record_validator(self) -> Callable[..., list[str]]:
        return validate_sushi_record

    def _map_record(self, record: dict) -> SushiRestaurant:
        return SushiRestaurant(
            id=str(record["id"]),
            name=record["name"],
            address=record["address"],
            lat=float(record["lat"]),
            lon=float(record["lon"]),
            rating=float(record["rating"]),
            price_range=record.get("price_range", ""),
            payment_methods=tuple(record.get("payment_methods", [])),
            opening_hours=record.get("opening_hours", ""),
        )
