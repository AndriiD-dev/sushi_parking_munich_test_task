"""Domain-specific exception types.

These provide clear, specific failure semantics across the application
without relying on generic Exception catches.
"""


class AppError(Exception):
    """Base exception for all application-specific errors."""


class DatasetLoadError(AppError):
    """Raised when a dataset file cannot be read or parsed."""


class DatasetValidationError(AppError):
    """Raised when dataset records fail validation in strict mode."""


class ConfigurationError(AppError):
    """Raised when configuration values are invalid or inconsistent."""


class GeolocationError(AppError):
    """Raised when geolocation resolution encounters an unrecoverable error."""


class InvalidRequestError(AppError):
    """Raised when a user request fails semantic validation.

    Carries an optional ``field`` attribute to indicate which request
    field caused the failure, enabling structured error responses.
    """

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class UnknownToolError(AppError):
    """Raised when the model requests a tool not in the registry."""


class ToolArgumentsError(AppError):
    """Raised when tool call arguments are malformed or invalid."""


class SessionNotFoundError(AppError):
    """Raised when a requested session does not exist."""


class UpstreamServiceError(AppError):
    """Raised when an upstream dependency (e.g. OpenAI) fails."""


class ProcessingLimitError(AppError):
    """Raised when the orchestration loop exceeds its configured limit."""
