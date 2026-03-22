"""Security primitives: Rate limiting and Authentication."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings

logger = logging.getLogger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


def get_security_settings(request: Request) -> Settings:
    """Dependency to retrieve settings from app state."""
    return request.app.state.settings


SecurityDep = Annotated[Settings, Depends(get_security_settings)]
