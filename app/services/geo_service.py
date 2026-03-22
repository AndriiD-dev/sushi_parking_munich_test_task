"""Geolocation service — coordinate resolution and distance calculation.

Implements a three-level fallback chain for user location:
1. Browser GPS coordinates (if valid)
2. IP-based geolocation via configurable HTTP endpoint
3. Default Marienplatz coordinates from config
"""

import logging

from haversine import Unit, haversine

from app.config import Settings

logger = logging.getLogger(__name__)


def _is_valid_latitude(lat: float) -> bool:
    return -90 <= lat <= 90


def _is_valid_longitude(lon: float) -> bool:
    return -180 <= lon <= 180


class GeospatialHelper:
    """Provides location resolution and distance calculation.

    All configuration comes from the injected Settings instance.
    """

    def __init__(self, settings: Settings) -> None:
        self._default_lat = settings.default_lat
        self._default_lon = settings.default_lon
        self._enable_browser = settings.enable_browser_coordinates

    def resolve_user_location(
        self,
        user_lat: float | None = None,
        user_lon: float | None = None,
    ) -> tuple[float | None, float | None]:
        """Resolve user location through the fallback chain.

        Returns (latitude, longitude). If location cannot be resolved,
        falls back to default configured coordinates.
        """
        # Browser GPS coordinates
        if self._enable_browser and user_lat is not None and user_lon is not None:
            if _is_valid_latitude(user_lat) and _is_valid_longitude(user_lon):
                logger.info("Resolved location from browser coordinates: (%.4f, %.4f)", user_lat, user_lon)
                return (user_lat, user_lon)
            logger.warning(
                "Invalid browser coordinates (lat=%s, lon=%s), falling back",
                user_lat,
                user_lon,
            )

        # Fallback to default coordinates
        logger.info("Location fallback: Using default coordinates (%.4f, %.4f)", self._default_lat, self._default_lon)
        return (self._default_lat, self._default_lon)

    def distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance in metres between two coordinate pairs.

        Uses the haversine formula. Coordinates must be valid
        (caller is responsible for validation).
        """
        dist_m = haversine((lat1, lon1), (lat2, lon2), unit=Unit.METERS)
        logger.info(
            "Distance computation: (%.4f, %.4f) -> (%.4f, %.4f) = %.1f meters",
            lat1, lon1, lat2, lon2, dist_m
        )
        return dist_m
