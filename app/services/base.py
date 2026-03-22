"""Abstract base service for place-type domains.

``BasePlaceService`` encapsulates the dependency wiring (repository,
geo-helper, settings) and the distance-enrichment pipeline that is
identical across every domain. Concrete services override ``search``
to add domain-specific filters but delegate common work here.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Generic, TypeVar

from app.config import Settings
from app.models.place import BasePlace
from app.repositories.base import PlacesRepository
from app.services.geo_service import GeospatialHelper

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BasePlace)


class BasePlaceService(ABC, Generic[T]):
    """Shared business logic for any place-type domain.

    Provides:
    - Dependency injection via ``__init__``.
    - ``get_details`` — uniform ID lookup.
    - ``_enrich_distances`` — haversine enrichment for a list of entities.
    - ``_filter_by_distance`` — radius filtering after enrichment.
    - ``_apply_limit`` — configurable result-set capping.
    """

    def __init__(
        self,
        repository: PlacesRepository[T],
        geo: GeospatialHelper,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._geo = geo
        self._default_limit = settings.default_limit
        self._max_limit = settings.max_limit
        self._max_radius = settings.max_radius_meters

    @abstractmethod
    def search(self, **kwargs) -> list[T]:
        """Domain-specific search with filters.

        Subclasses implement this, calling the shared helpers below
        for distance enrichment, filtering, and limiting.
        """
        ...

    def get_details(self, item_id: str) -> T | None:
        """Return full details for a single entity by ID."""
        return self._repo.find_by_id(item_id)

    def _enrich_distances(
        self,
        items: list[T],
        user_lat: float | None = None,
        user_lon: float | None = None,
        reference_lat: float | None = None,
        reference_lon: float | None = None,
    ) -> list[T]:
        """Return copies of *items* with ``distance_meters`` and/or 
        ``distance_from_reference_meters`` populated.

        Original repository objects are never mutated.
        """
        enriched: list[T] = []
        for item in items:
            kwargs = {}
            if user_lat is not None and user_lon is not None:
                dist = self._geo.distance(user_lat, user_lon, item.lat, item.lon)
                kwargs["distance_meters"] = round(dist, 1)
            if reference_lat is not None and reference_lon is not None:
                dist_ref = self._geo.distance(reference_lat, reference_lon, item.lat, item.lon)
                kwargs["distance_from_reference_meters"] = round(dist_ref, 1)
            
            if kwargs:
                enriched.append(replace(item, **kwargs))
            else:
                enriched.append(item)
        return enriched

    def _filter_by_distance(
        self,
        items: list[T],
        max_distance_meters: float,
        use_reference: bool = False,
    ) -> list[T]:
        """Keep only items within *max_distance_meters* of the relevant point
        (clamped to the configured maximum radius)."""
        radius = min(max_distance_meters, self._max_radius)
        return [
            item for item in items
            if (item.distance_from_reference_meters if use_reference else item.distance_meters) is not None
            and (item.distance_from_reference_meters if use_reference else item.distance_meters) <= radius
        ]

    def _apply_limit(self, items: list[T], limit: int | None) -> list[T]:
        """Cap the result set to an effective limit."""
        effective = min(limit or self._default_limit, self._max_limit)
        return items[:effective]
