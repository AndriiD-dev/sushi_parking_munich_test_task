"""Startup validation for JSON dataset records.

Validates individual records for required fields, coordinate ranges,
and payment method values. Supports strict (fail-fast) and lenient
(skip-and-warn) modes controlled by configuration.
"""

import logging

from app.errors.base import DatasetValidationError
from app.models.place import PaymentMethod

logger = logging.getLogger(__name__)


def validate_coordinates(lat: float, lon: float) -> list[str]:
    """Return a list of validation errors for coordinate values."""
    errors: list[str] = []
    if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
        errors.append(f"lat must be between -90 and 90, got {lat}")
    if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
        errors.append(f"lon must be between -180 and 180, got {lon}")
    return errors


def validate_payment_methods(methods: list, valid_methods: set[str]) -> list[str]:
    """Return a list of validation errors for payment method values."""
    errors: list[str] = []
    for method in methods:
        if method not in valid_methods:
            errors.append(f"unsupported payment method: {method!r}")
    return errors


def validate_sushi_record(
    record: dict,
    index: int,
    required_fields: set[str],
    payment_methods: set[str],
) -> list[str]:
    """Validate a single sushi restaurant JSON record.

    Returns a list of error strings. An empty list means the record is valid.
    """
    errors: list[str] = []
    prefix = f"sushi record [{index}]"

    missing = required_fields - set(record.keys())
    if missing:
        errors.append(f"{prefix}: missing required fields: {missing}")
        return errors

    errors.extend(f"{prefix}: {e}" for e in validate_coordinates(record["lat"], record["lon"]))

    if not isinstance(record["rating"], (int, float)) or record["rating"] < 0 or record["rating"] > 5:
        errors.append(f"{prefix}: rating must be between 0 and 5, got {record['rating']}")

    if "payment_methods" in record:
        errors.extend(
            f"{prefix}: {e}" for e in validate_payment_methods(record["payment_methods"], payment_methods)
        )

    return errors


def validate_parking_record(
    record: dict,
    index: int,
    required_fields: set[str],
    payment_methods: set[str],
) -> list[str]:
    """Validate a single parking garage JSON record.

    Returns a list of error strings. An empty list means the record is valid.
    """
    errors: list[str] = []
    prefix = f"parking record [{index}]"

    missing = required_fields - set(record.keys())
    if missing:
        errors.append(f"{prefix}: missing required fields: {missing}")
        return errors

    errors.extend(f"{prefix}: {e}" for e in validate_coordinates(record["lat"], record["lon"]))

    if not isinstance(record["price_per_hour"], (int, float)) or record["price_per_hour"] < 0:
        errors.append(f"{prefix}: price_per_hour must be non-negative, got {record['price_per_hour']}")

    if "payment_methods" in record:
        errors.extend(
            f"{prefix}: {e}" for e in validate_payment_methods(record["payment_methods"], payment_methods)
        )

    return errors


def check_duplicate_ids(records: list[dict]) -> list[str]:
    """Return validation errors for duplicate IDs in a record list."""
    seen: set[str] = set()
    errors: list[str] = []
    for i, record in enumerate(records):
        record_id = record.get("id")
        if record_id is None:
            continue  # Missing ID is caught by required-field validation
        if record_id in seen:
            errors.append(f"record [{i}]: duplicate id {record_id!r}")
        seen.add(record_id)
    return errors


def validate_records(
    records: list[dict],
    validate_fn: callable,
    *,
    strict: bool,
    dataset_name: str,
    required_fields: set[str] = None,
    payment_methods: set[str] = None,
) -> list[dict]:
    """Validate a list of records, returning only valid ones.

    In strict mode, raises DatasetValidationError on the first invalid record.
    In lenient mode, skips invalid records and logs warnings.
    Always raises on duplicate IDs regardless of mode.
    """
    # Check for duplicate IDs first
    dup_errors = check_duplicate_ids(records)
    if dup_errors:
        msg = f"{dataset_name}: duplicate IDs found: {'; '.join(dup_errors)}"
        if strict:
            raise DatasetValidationError(msg)
        logger.warning(msg + " — duplicates will use first occurrence")

    valid: list[dict] = []
    seen_ids: set[str] = set()
    skipped = 0

    for i, record in enumerate(records):
        record_id = record.get("id")

        # Skip duplicate IDs (keep first occurrence)
        if record_id in seen_ids:
            skipped += 1
            continue

        errors = validate_fn(
            record, 
            i, 
            required_fields=required_fields, 
            payment_methods=payment_methods
        )
        if errors:
            msg = f"{dataset_name}: {'; '.join(errors)}"
            if strict:
                raise DatasetValidationError(msg)
            logger.warning("Skipping invalid record: %s", msg)
            skipped += 1
            continue

        if record_id is not None:
            seen_ids.add(record_id)
        valid.append(record)

    if skipped > 0:
        logger.info("%s: skipped %d invalid record(s)", dataset_name, skipped)

    return valid
