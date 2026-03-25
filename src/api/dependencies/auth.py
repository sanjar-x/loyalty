"""FastAPI dependency for API-key authentication.

The Image Backend uses a simple API-key mechanism for service-to-service
authentication.  The key is passed in the ``X-API-Key`` header and
validated against the ``INTERNAL_API_KEY`` setting.
"""

import hmac

import structlog
from fastapi import Header, Query

from src.bootstrap.config import settings
from src.shared.exceptions import UnauthorizedError

logger = structlog.get_logger(__name__)


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key: str | None = Query(None),
) -> None:
    """Validate API key from header or query param (needed for SSE).

    Raises:
        UnauthorizedError: If the key is missing or invalid.
    """
    key = x_api_key or api_key
    internal_key = settings.INTERNAL_API_KEY.get_secret_value()
    if not internal_key:
        return  # auth disabled in dev

    if not key or not hmac.compare_digest(key, internal_key):
        raise UnauthorizedError(
            message="Invalid API key.",
            error_code="INVALID_API_KEY",
        )
