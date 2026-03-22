"""Static descriptor registry for application domains.

This module provides `DomainDescriptor`, a dataclass that bundles all the
classes, schemas, validators, and method mappings required to instantiate
and wire up a specific domain (like sushi or parking).

By defining domains here, `main.py` can initialize everything using a
fully generic loop, avoiding hardcoded domain names.
"""

from dataclasses import dataclass
from typing import Callable, Any

from app.core.tool_schemas import (
    SUSHI_SEARCH_SCHEMA, SUSHI_DETAILS_SCHEMA,
    PARKING_SEARCH_SCHEMA, PARKING_DETAILS_SCHEMA,
)
from app.repositories.parking_repository import ParkingRepository
from app.repositories.sushi_repository import SushiRepository
from app.services.parking_service import ParkingService
from app.services.sushi_service import SushiService
from app.validation.tool_args import VALIDATORS


@dataclass(frozen=True)
class DomainDescriptor:
    """Bundles all components related to a single place domain."""

    repo_class: type
    """The repository class for loading data (e.g. SushiRepository)."""

    service_class: type
    """The service class containing business logic (e.g. SushiService)."""

    search_schema: dict[str, Any]
    """OpenAI function schema dict for the domain's search tool."""

    details_schema: dict[str, Any]
    """OpenAI function schema dict for the domain's details tool."""

    search_validator: Callable[[dict[str, Any]], dict[str, Any]]
    """Validation function for the search tool's arguments."""

    details_validator: Callable[[dict[str, Any]], dict[str, Any]]
    """Validation function for the details tool's arguments."""

    tool_handlers: dict[str, str]
    """Mapping from tool_name -> service_method_name.
    Example: {"search_sushi_restaurants": "search"}
    """


# Central registry mapping domain_name (from config) to its descriptor
DOMAIN_REGISTRY: dict[str, DomainDescriptor] = {
    "sushi": DomainDescriptor(
        repo_class=SushiRepository,
        service_class=SushiService,
        search_schema=SUSHI_SEARCH_SCHEMA,
        details_schema=SUSHI_DETAILS_SCHEMA,
        search_validator=VALIDATORS["search_sushi_restaurants"],
        details_validator=VALIDATORS["get_sushi_restaurant_details"],
        tool_handlers={
            "search_sushi_restaurants": "search",
            "get_sushi_restaurant_details": "get_details",
        },
    ),
    "parking": DomainDescriptor(
        repo_class=ParkingRepository,
        service_class=ParkingService,
        search_schema=PARKING_SEARCH_SCHEMA,
        details_schema=PARKING_DETAILS_SCHEMA,
        search_validator=VALIDATORS["search_parking_garages"],
        details_validator=VALIDATORS["get_parking_garage_details"],
        tool_handlers={
            "search_parking_garages": "search",
            "get_parking_garage_details": "get_details",
        },
    ),
}
