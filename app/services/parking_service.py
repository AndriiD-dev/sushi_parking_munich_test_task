"""Parking garage service — search, filter, and detail lookup."""

import logging

from app.models.place import ParkingGarage
from app.services.base import BasePlaceService

logger = logging.getLogger(__name__)


class ParkingService(BasePlaceService[ParkingGarage]):
    """Business logic for querying parking garages.

    Domain-specific filters (payment method, price cap) are
    implemented here. Distance enrichment, radius filtering,
    limiting, and detail lookups are inherited from
    ``BasePlaceService``.
    """

    def search(
        self,
        *,
        payment_method: str | None = None,
        max_price_per_hour: float | None = None,
        max_distance_meters: float | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        reference_lat: float | None = None,
        reference_lon: float | None = None,
        limit: int | None = None,
    ) -> list[ParkingGarage]:
        """Search parking garages with optional filters.

        Returns enriched copies sorted by distance (if coordinates
        available) or by price ascending.
        """
        results = self._repo.find_all()

        # Payment method filter
        if payment_method and payment_method != "any":
            results = [
                r for r in results if payment_method in r.payment_methods
            ]

        # Price filter
        if max_price_per_hour is not None:
            clamped = max(0.0, max_price_per_hour)
            results = [r for r in results if r.price_per_hour <= clamped]

        # Distance enrichment and filtering
        has_coords = user_lat is not None and user_lon is not None
        has_ref = reference_lat is not None and reference_lon is not None
        if has_coords or has_ref:
            results = self._enrich_distances(
                results, 
                user_lat=user_lat, 
                user_lon=user_lon, 
                reference_lat=reference_lat, 
                reference_lon=reference_lon
            )
            if max_distance_meters is not None:
                results = self._filter_by_distance(
                    results, max_distance_meters, use_reference=has_ref
                )
            
            if has_ref:
                results.sort(key=lambda r: r.distance_from_reference_meters or 0.0)
            elif has_coords:
                results.sort(key=lambda r: r.distance_meters or 0.0)
        else:
            results.sort(key=lambda r: r.price_per_hour)

        return self._apply_limit(results, limit)

    def get_details(self, garage_id: str) -> ParkingGarage | None:
        """Return full details for a specific parking garage."""
        return self._repo.find_by_id(garage_id)
