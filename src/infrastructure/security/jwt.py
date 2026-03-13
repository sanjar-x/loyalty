import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.bootstrap.config import settings
from src.shared.exceptions import UnauthorizedError
from src.shared.interfaces.security import ITokenProvider


class JwtTokenProvider(ITokenProvider):
    """
    Реализация генерации и расшифровки Access-токенов через JWT.
    """

    def create_access_token(
        self, payload_data: dict[str, Any], expires_minutes: int | None = None
    ) -> str:
        to_encode = payload_data.copy()

        now = datetime.now(tz=UTC)
        if expires_minutes is not None:
            expire = now + timedelta(minutes=expires_minutes)
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update(
            {
                "exp": expire,
                "iat": now,
                "jti": str(uuid.uuid4()),
            }
        )

        encoded_jwt: str = jwt.encode(
            to_encode,
            key=settings.SECRET_KEY.get_secret_value(),
            algorithm=settings.ALGORITHM,
        )
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            decoded_token: dict[str, Any] = jwt.decode(
                jwt=token,
                key=settings.SECRET_KEY.get_secret_value(),
                algorithms=[settings.ALGORITHM],
            )
            return decoded_token

        except ExpiredSignatureError as e:
            raise UnauthorizedError(
                message="Срок действия токена истек. Авторизуйтесь заново.",
                error_code="TOKEN_EXPIRED",
            ) from e
        except InvalidTokenError as e:
            raise UnauthorizedError(
                message="Невалидный токен доступа.", error_code="INVALID_TOKEN"
            ) from e
