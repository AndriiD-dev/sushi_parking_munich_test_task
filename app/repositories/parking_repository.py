"""Parking garage repository — loads and indexes parking.json at startup."""

from typing import Callable

from app.models.place import ParkingGarage
from app.repositories.base import BaseJsonRepository
from app.validation.dataset_validator import validate_parking_record


class ParkingRepository(BaseJsonRepository[ParkingGarage]):
    """In-memory repository for parking garages.

    Inherits JSON loading, validation, indexing, and read access from
    ``BaseJsonRepository``. Only the record-mapping factory and
    domain-specific metadata are defined here.
    """

    @property
    def _dataset_name(self) -> str:
        return "parking"

    @property
    def _record_validator(self) -> Callable[..., list[str]]:
        return validate_parking_record

    def _map_record(self, record: dict) -> ParkingGarage:
        return ParkingGarage(
            id=str(record["id"]),
            name=record["name"],
            address=record["address"],
            lat=float(record["lat"]),
            lon=float(record["lon"]),
            price_per_hour=float(record["price_per_hour"]),
            payment_methods=tuple(record.get("payment_methods", [])),
            total_spaces=int(record.get("total_spaces", 0)),
            opening_hours=record.get("opening_hours", ""),
        )
