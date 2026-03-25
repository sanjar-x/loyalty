"""Unit of Work implementation backed by SQLAlchemy AsyncSession.

Coordinates transactional writes within the Image Backend.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import ConflictError, UnprocessableEntityError
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


class UnitOfWork(IUnitOfWork):
    """Transactional Unit of Work for the Image Backend."""

    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            await self.rollback()

    async def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        await self._session.flush()

    def register_aggregate(self, aggregate: Any) -> None:
        """No-op — outbox pattern not used in Image Backend."""
        pass

    async def commit(self) -> None:
        """Commit the transaction.

        Raises:
            UnprocessableEntityError: On foreign key violations (sqlstate 23503).
            ConflictError: On other integrity constraint violations.
        """
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self.rollback()
            sqlstate = getattr(e.orig, "sqlstate", None)

            if sqlstate == "23503":
                raise UnprocessableEntityError(
                    message="Business logic error",
                    error_code="FOREIGN_KEY_VIOLATION",
                ) from e

            raise ConflictError(
                message="Conflict! Record already exists or violates DB constraints.",
                error_code="DB_INTEGRITY_ERROR",
            ) from e

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self._session.rollback()
