"""Abstract base classes for place repositories.

``PlacesRepository`` defines the read-only interface.
``BaseJsonRepository`` adds a reusable JSON-loading pipeline so
concrete implementations (sushi, parking, etc.) only need to supply
a record-mapping factory and a validator function.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar, Union

from app.config import DomainConfig
from app.errors.base import DatasetLoadError
from app.models.place import BasePlace
from app.validation.dataset_validator import validate_records

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BasePlace)


class PlacesRepository(ABC, Generic[T]):
    """Uniform read interface for in-memory place data stores.

    Concrete implementations load data once at startup and expose
    immutable read-only access. No business filtering logic belongs
    here — that is the service layer's responsibility.
    """

    @abstractmethod
    def find_all(self) -> list[T]:
        """Return all loaded entities."""
        ...

    @abstractmethod
    def find_by_id(self, place_id: str) -> T | None:
        """Return a single entity by ID, or None if not found."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return the total number of loaded entities."""
        ...


class BaseJsonRepository(PlacesRepository[T]):
    """Generic JSON-backed repository that handles file I/O, parsing,
    validation, and indexing uniformly for any ``BasePlace`` subtype.

    Subclasses must implement:
    - ``_dataset_name`` — human-readable label for log messages.
    - ``_record_validator`` — per-record validation function.
    - ``_map_record`` — factory that converts a validated dict to ``T``.
    """

    def __init__(self, domain: "DomainConfig") -> None:
        self._domain = domain
            
        self._items: list[T] = []
        self._index: dict[str, T] = {}
        self._load()

    @property
    @abstractmethod
    def _dataset_name(self) -> str:
        """Human-readable name for log/error messages (e.g. 'sushi')."""
        ...

    @property
    @abstractmethod
    def _record_validator(self) -> Callable[..., list[str]]:
        """Validation function: ``(record, index, required_fields, payment_methods) -> list[error_strings]``."""
        ...

    @abstractmethod
    def _map_record(self, record: dict) -> T:
        """Convert a validated dict to a domain entity."""
        ...

    def _load(self) -> None:
        """Load, validate, and index records from a JSON file.

        Raises:
            DatasetLoadError: If the file is missing, unreadable,
                or contains invalid JSON.
        """
        path = Path(self._domain.dataset_path)
        name = self._domain.name

        if not path.is_file():
            raise DatasetLoadError(f"{name} dataset not found: {path}")

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DatasetLoadError(
                f"Cannot read {name} dataset: {exc}"
            ) from exc

        try:
            raw_records = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise DatasetLoadError(
                f"{name} dataset is not valid JSON: {exc}"
            ) from exc

        if not isinstance(raw_records, list):
            raise DatasetLoadError(f"{name} dataset must be a JSON array")

        valid_records = validate_records(
            raw_records,
            self._record_validator,
            strict=self._domain.strict,
            dataset_name=name,
            required_fields=self._domain.required_fields,
            payment_methods=self._domain.payment_methods,
        )

        for record in valid_records:
            entity = self._map_record(record)
            self._items.append(entity)
            self._index[entity.id] = entity

        logger.info(
            "Loaded %d %s record(s) from %s",
            len(self._items),
            name,
            path,
        )


    def find_all(self) -> list[T]:
        """Return all loaded entities."""
        return list(self._items)

    def find_by_id(self, place_id: str) -> T | None:
        """Return a single entity by ID, or None."""
        return self._index.get(place_id)

    def count(self) -> int:
        """Return total entity count."""
        return len(self._items)
