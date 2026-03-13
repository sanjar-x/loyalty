# src/infrastructure/database/uow.py
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import ConflictError, UnprocessableEntityError
from src.shared.interfaces.uow import IUnitOfWork


class UnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            await self.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self.rollback()
            sqlstate = getattr(e.orig, "sqlstate", None)

            if sqlstate == "23503":  # foreign_key_violation
                raise UnprocessableEntityError(
                    message="Ошибка бизнес-логики",
                    error_code="FOREIGN_KEY_VIOLATION",
                ) from e

            raise ConflictError(
                message="Конфликт! Запись уже существует или нарушает ограничения БД.",
                error_code="DB_INTEGRITY_ERROR",
            ) from e

    async def rollback(self) -> None:
        await self._session.rollback()
