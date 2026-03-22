"""FastAPI exception handlers mapping domain errors to HTTP responses.

Registers centralized handlers so route code stays clean and error
responses are consistent across all endpoints.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.base import (
    InvalidRequestError,
    ProcessingLimitError,
    SessionNotFoundError,
    ToolArgumentsError,
    UnknownToolError,
    UpstreamServiceError,
)

logger = logging.getLogger(__name__)


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    """Build standard error response body."""
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach domain exception handlers to the FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def handle_pydantic_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Convert Pydantic validation errors into stable 422 responses."""
        errors = exc.errors()
        if errors:
            first = errors[0]
            field = ".".join(str(loc) for loc in first.get("loc", []) if loc != "body")
            message = first.get("msg", "Validation error")
            logger.warning("Request validation failed: field=%s msg=%s", field, message)
            return JSONResponse(
                status_code=422,
                content=_error_body(
                    "VALIDATION_ERROR",
                    message,
                    {"field": field} if field else None,
                ),
            )
        return JSONResponse(
            status_code=422,
            content=_error_body("VALIDATION_ERROR", "Request validation failed."),
        )

    @app.exception_handler(InvalidRequestError)
    async def handle_invalid_request(
        request: Request, exc: InvalidRequestError
    ) -> JSONResponse:
        logger.warning("Invalid request: %s (field=%s)", exc, exc.field)
        details = {"field": exc.field} if exc.field else None
        return JSONResponse(
            status_code=400,
            content=_error_body("INVALID_REQUEST", str(exc), details),
        )

    @app.exception_handler(SessionNotFoundError)
    async def handle_session_not_found(
        request: Request, exc: SessionNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_body("SESSION_NOT_FOUND", str(exc)),
        )

    @app.exception_handler(UnknownToolError)
    async def handle_unknown_tool(
        request: Request, exc: UnknownToolError
    ) -> JSONResponse:
        logger.error("Unknown tool requested: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR", "An internal processing error occurred."
            ),
        )

    @app.exception_handler(ToolArgumentsError)
    async def handle_tool_arguments(
        request: Request, exc: ToolArgumentsError
    ) -> JSONResponse:
        logger.error("Tool argument error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR", "An internal processing error occurred."
            ),
        )

    @app.exception_handler(UpstreamServiceError)
    async def handle_upstream(
        request: Request, exc: UpstreamServiceError
    ) -> JSONResponse:
        logger.error("Upstream service error: %s", exc)
        return JSONResponse(
            status_code=502,
            content=_error_body(
                "UPSTREAM_ERROR",
                "An upstream service is temporarily unavailable.",
            ),
        )

    @app.exception_handler(ProcessingLimitError)
    async def handle_processing_limit(
        request: Request, exc: ProcessingLimitError
    ) -> JSONResponse:
        logger.warning("Processing limit reached: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "PROCESSING_LIMIT",
                "The request could not be completed within processing limits.",
            ),
        )
