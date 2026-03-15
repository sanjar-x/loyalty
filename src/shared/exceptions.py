# src/shared/exceptions.py
from typing import Any


class AppException(Exception):
    """Базовый класс для всех ожидаемых ошибок приложения."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message: str = message
        self.status_code: int = status_code
        self.error_code: str = error_code
        self.details: dict[str, Any] | None = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(
        self,
        message: str = "Ресурс не найден",
        error_code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code,
            details=details,
        )


class BadRequestError(AppException):
    def __init__(
        self,
        message: str = "Неверный запрос",
        error_code: str = "BAD_REQUEST",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )


class UnauthorizedError(AppException):
    def __init__(
        self,
        message: str = "Необходима авторизация",
        error_code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class ForbiddenError(AppException):
    def __init__(
        self,
        message: str = "Доступ запрещен. Недостаточно прав.",
        error_code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class ConflictError(AppException):
    def __init__(
        self,
        message: str = "Конфликт текущего состояния ресурса",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code,
            details=details,
        )


class ValidationError(AppException):
    """Ошибка валидации данных (в том числе бизнес-правил)."""

    def __init__(
        self,
        message: str = "Ошибка валидации данных",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )


class UnprocessableEntityError(AppException):
    def __init__(
        self,
        message: str = "Невозможно обработать сущность (ошибка бизнес-логики)",
        error_code: str = "UNPROCESSABLE_ENTITY",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 422, error_code, details)


class ServiceUnavailableError(AppException):
    def __init__(
        self,
        message: str = "Внешний сервис временно недоступен",
        error_code: str = "SERVICE_UNAVAILABLE",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=503,
            error_code=error_code,
            details=details,
        )
