"""FastAPI dependencies for authentication and authorization.

Provides:
- ``get_auth_context``: Extracts AuthContext (identity_id + session_id) from JWT.
- ``RequirePermission``: Callable dependency that checks session permissions via cache-aside.
- ``get_current_user_id``: Backward-compatible wrapper returning identity_id as uuid.UUID.
"""

import uuid

import structlog
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.identity.domain.exceptions import InsufficientPermissionsError
from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.auth import AuthContext
from src.shared.interfaces.security import IPermissionResolver, ITokenProvider

_bearer_scheme = HTTPBearer(auto_error=False)


@inject
async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_provider: FromDishka[ITokenProvider] = ...,  # type: ignore[assignment]
) -> AuthContext:
    """Extract AuthContext from a JWT Bearer token.

    Decodes the access token and extracts the ``sub`` (identity_id) and
    ``sid`` (session_id) claims. Binds both to structlog context variables
    for downstream request logging.

    Args:
        credentials: The HTTP Bearer token credentials, if present.
        token_provider: JWT token provider for decoding.

    Returns:
        An AuthContext containing the identity and session identifiers.

    Raises:
        UnauthorizedError: If the token is missing or has invalid payload.
    """
    if not credentials:
        raise UnauthorizedError(
            message="Missing authorization token",
            error_code="MISSING_TOKEN",
        )

    payload = token_provider.decode_access_token(credentials.credentials)

    sub = payload.get("sub")
    sid = payload.get("sid")
    if not sub or not sid:
        raise UnauthorizedError(
            message="Invalid token payload: missing sub or sid",
            error_code="INVALID_TOKEN_PAYLOAD",
        )

    try:
        identity_id = uuid.UUID(sub)
        session_id = uuid.UUID(sid)
    except ValueError:
        raise UnauthorizedError(
            message="Invalid token payload: malformed sub or sid",
            error_code="INVALID_TOKEN_PAYLOAD",
        )

    structlog.contextvars.bind_contextvars(
        identity_id=sub,
        session_id=sid,
    )

    return AuthContext(
        identity_id=identity_id,
        session_id=session_id,
    )


class RequirePermission:
    """FastAPI dependency that enforces a specific permission on the session.

    Usage as a route dependency::

        @router.get("/protected", dependencies=[Depends(RequirePermission("orders:read"))])
        async def protected_route(...): ...

    Args:
        codename: The required permission codename (e.g. "orders:read").
    """

    def __init__(self, codename: str) -> None:
        self._codename = codename

    @inject
    async def __call__(
        self,
        auth: AuthContext = Depends(get_auth_context),
        resolver: FromDishka[IPermissionResolver] = ...,  # type: ignore[assignment]
    ) -> AuthContext:
        """Check that the session has the required permission.

        Args:
            auth: The authenticated context from the JWT.
            resolver: Permission resolver (cache-aside with Redis).

        Returns:
            The AuthContext if the permission check passes.

        Raises:
            InsufficientPermissionsError: If the session lacks the permission.
        """
        if not await resolver.has_permission(auth.session_id, self._codename):
            raise InsufficientPermissionsError(codename=self._codename)
        return auth


async def get_current_user_id(
    auth: AuthContext = Depends(get_auth_context),
) -> uuid.UUID:
    """Backward-compatible dependency that returns the identity_id as a UUID.

    Args:
        auth: The authenticated context from the JWT.

    Returns:
        The identity's UUID.
    """
    return auth.identity_id
