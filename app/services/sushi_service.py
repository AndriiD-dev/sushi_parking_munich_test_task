"""Sushi restaurant service — search, filter, and detail lookup."""

import logging

from app.models.place import SushiRestaurant
from app.services.base import BasePlaceService

logger = logging.getLogger(__name__)


class SushiService(BasePlaceService[SushiRestaurant]):
    """Business logic for querying sushi restaurants.

    Domain-specific filters (text search, rating, payment method,
    sort order) are implemented here. Distance enrichment, radius
    filtering, limiting, and detail lookups are inherited from
    ``BasePlaceService``.
    """

    def search(
        self,
        *,
        query: str | None = None,
        min_rating: float | None = None,
        payment_method: str | None = None,
        max_distance_meters: float | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        reference_lat: float | None = None,
        reference_lon: float | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
    ) -> list[SushiRestaurant]:
        """Search sushi restaurants with optional filters.

        Returns enriched copies sorted by distance (if coordinates
        available) or by rating descending.
        """
        results = self._repo.find_all()

        # Text search on name and address
        if query:
            q = query.lower()
            results = [
                r for r in results
                if q in r.name.lower() or q in r.address.lower()
            ]

        # Rating filter
        if min_rating is not None:
            clamped = max(0.0, min(5.0, min_rating))
            results = [r for r in results if r.rating >= clamped]

        # Payment method filter
        if payment_method and payment_method != "any":
            results = [
                r for r in results if payment_method in r.payment_methods
            ]

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

        # Sorting
        if sort_by == "rating":
            results.sort(key=lambda r: r.rating, reverse=True)
        elif sort_by == "price":
            results.sort(key=lambda r: len(r.price_range))
        elif has_ref:
            results.sort(key=lambda r: r.distance_from_reference_meters or 0.0)
        elif has_coords:
            results.sort(key=lambda r: r.distance_meters or 0.0)
        else:
            results.sort(key=lambda r: r.rating, reverse=True)

        return self._apply_limit(results, limit)

    def get_details(
        self, restaurant_id: str,
    ) -> SushiRestaurant | None:
        """Return full details for a specific sushi restaurant."""
        return self._repo.find_by_id(restaurant_id)
