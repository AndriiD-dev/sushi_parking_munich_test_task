"""Structured logging setup for the application.

Configures the root logger with a consistent format including timestamps,
log level, and module name. Replaces bare `logging.basicConfig` calls.
"""

import logging
import sys

from app.config import Settings

_APP_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_APP_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(settings: Settings) -> None:
    """Configure application-wide logging from settings.

    Should be called once at startup, before any log messages are emitted.
    Handles uvicorn --reload by replacing existing handlers with our formatter.
    """
    root = logging.getLogger()
    root.setLevel(settings.log_level_int)

    formatter = logging.Formatter(fmt=_APP_LOG_FORMAT, datefmt=_APP_DATE_FORMAT)


    if root.handlers:
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(formatter)
                handler.setLevel(settings.log_level_int)

        has_stdout = any(
            isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
            for h in root.handlers
        )
        if not has_stdout:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(settings.log_level_int)
            handler.setFormatter(formatter)
            root.addHandler(handler)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.log_level_int)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


class AgentEvent:
    """Helper for generating structured log strings for agent actions.

    Follows the pattern: [trace_id] | [event_name] | [key1=val1] [key2=val2]
    """

    @staticmethod
    def format(
        event_name: str,
        trace_id: str | None = None,
        session_id: str | None = None,
        **metadata,
    ) -> str:
        """Format a structured log message."""
        trace_part = trace_id if trace_id else "system"
        msg = f"[{trace_part}] | {event_name}"

        fields = []
        if session_id:
            fields.append(f"session={session_id}")

        for k, v in metadata.items():
            if k in ("email", "phone", "name", "user_id", "address") and v:
                v = f"{str(v)[:1]}***"
            elif k in ("lat", "lon") and v is not None:
                # Mask coordinates beyond 1 decimal place (~11km accuracy)
                try:
                    v = f"{float(v):.1f}***"
                except (ValueError, TypeError):
                    v = "***"
            fields.append(f"{k}={v}")

        if fields:
            msg += f" | {' '.join(fields)}"

        return msg
