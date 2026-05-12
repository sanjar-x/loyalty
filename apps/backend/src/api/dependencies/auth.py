"""FastAPI dependency for authentication and binding identity_id to the logging context.

Usage in protected routes::

    @router.get("/protected")
    async def protected_route(identity_id: str = Depends(get_current_identity_id)):
        ...
"""

from typing import Annotated, Any

import structlog
from dishka.integrations.fastapi import FromDishka
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.security import ITokenProvider

_bearer_scheme = HTTPBearer(auto_error=False)

BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
]


async def get_current_identity_id(
    credentials: BearerCredentials,
    token_provider: FromDishka[ITokenProvider],  # type: ignore[assignment]
) -> str:
    """Extract the identity ID from a JWT and bind it to the structlog context.

    After this dependency resolves, every log entry emitted during the
    request will automatically include the ``identity_id`` field.

    Args:
        credentials: Bearer token credentials extracted by the HTTPBearer
            security scheme.  ``None`` when the header is missing.
        token_provider: DI-injected token provider used to decode JWTs.

    Returns:
        The ``sub`` (subject) claim from the JWT, representing the identity ID.

    Raises:
        UnauthorizedError: If the authorization token is missing or the
            token payload does not contain a ``sub`` claim.
    """
    if not credentials:
        raise UnauthorizedError(
            message="Authorization token is missing.",
            error_code="MISSING_TOKEN",
        )

    payload: dict[str, Any] = token_provider.decode_access_token(
        credentials.credentials
    )
    identity_id: str | None = payload.get("sub")
    if not identity_id:
        raise UnauthorizedError(
            message="Invalid token: missing sub claim.",
            error_code="INVALID_TOKEN_PAYLOAD",
        )
    structlog.contextvars.bind_contextvars(identity_id=identity_id)

    return identity_id
