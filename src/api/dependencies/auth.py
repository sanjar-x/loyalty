# src/api/dependencies/auth.py
"""
FastAPI-зависимость для аутентификации и привязки user_id к контексту логирования.

Использование в защищённых маршрутах:
    @router.get("/protected")
    async def protected_route(user_id: str = Depends(get_current_user_id)):
        ...
"""

from typing import Any

import structlog
from dishka.integrations.fastapi import FromDishka
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.security import ITokenProvider

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_provider: FromDishka[ITokenProvider] = ...,  # type: ignore[assignment]
) -> str:
    """
    Извлекает user_id из JWT и привязывает его к structlog-контексту.

    После вызова этой зависимости все логи в рамках запроса
    автоматически содержат поле user_id.
    """
    if not credentials:
        raise UnauthorizedError(
            message="Отсутствует токен авторизации.",
            error_code="MISSING_TOKEN",
        )

    payload: dict[str, Any] = token_provider.decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise UnauthorizedError(
            message="Невалидный токен: отсутствует sub.",
            error_code="INVALID_TOKEN_PAYLOAD",
        )

    # Привязываем user_id к контексту — все последующие логи включат это поле
    structlog.contextvars.bind_contextvars(user_id=user_id)

    return user_id
