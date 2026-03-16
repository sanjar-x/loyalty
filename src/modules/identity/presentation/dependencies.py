# src/modules/identity/presentation/dependencies.py
"""
FastAPI dependencies for authentication and authorization.

get_auth_context: Extracts AuthContext (identity_id + session_id) from JWT.
RequirePermission: Callable dependency that checks session permissions via Cache-Aside.
get_current_user_id: Backward-compatible wrapper returning identity_id as uuid.UUID.
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
    """
    Extract AuthContext from JWT Bearer token.
    Token payload must contain 'sub' (identity_id) and 'sid' (session_id).
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

    structlog.contextvars.bind_contextvars(
        identity_id=sub,
        session_id=sid,
    )

    return AuthContext(
        identity_id=uuid.UUID(sub),
        session_id=uuid.UUID(sid),
    )


class RequirePermission:
    def __init__(self, codename: str) -> None:
        self._codename = codename

    @inject
    async def __call__(
        self,
        auth: AuthContext = Depends(get_auth_context),
        resolver: FromDishka[IPermissionResolver] = ...,  # type: ignore[assignment]
    ) -> AuthContext:
        if not await resolver.has_permission(auth.session_id, self._codename):
            raise InsufficientPermissionsError(codename=self._codename)
        return auth


async def get_current_user_id(
    auth: AuthContext = Depends(get_auth_context),
) -> uuid.UUID:
    """Backward-compatible dependency: returns identity_id as uuid.UUID."""
    return auth.identity_id
