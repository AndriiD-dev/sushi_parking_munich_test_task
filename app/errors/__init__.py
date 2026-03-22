"""Domain-specific exceptions."""

from app.errors.base import (
    AppError,
    ConfigurationError,
    DatasetLoadError,
    DatasetValidationError,
    GeolocationError,
    InvalidRequestError,
    ProcessingLimitError,
    SessionNotFoundError,
    ToolArgumentsError,
    UnknownToolError,
    UpstreamServiceError,
)

__all__ = [
    "AppError",
    "ConfigurationError",
    "DatasetLoadError",
    "DatasetValidationError",
    "GeolocationError",
    "InvalidRequestError",
    "ProcessingLimitError",
    "SessionNotFoundError",
    "ToolArgumentsError",
    "UnknownToolError",
    "UpstreamServiceError",
]
