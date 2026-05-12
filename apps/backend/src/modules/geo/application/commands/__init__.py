"""Geo admin command handlers.

Provides ``safe_commit`` — a thin wrapper around ``session.commit()``
that translates SQLAlchemy ``IntegrityError`` into the application
exception hierarchy, matching the behaviour of ``UnitOfWork.commit()``
used by modules with domain entities.
"""

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import ConflictError, UnprocessableEntityError

logger = structlog.get_logger(__name__)


async def safe_commit(session: AsyncSession) -> None:
    """Commit the current transaction, translating DB constraint errors.

    * FK violations → :class:`UnprocessableEntityError` (422)
    * Unique / other constraint violations → :class:`ConflictError` (409)
    """
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        detail = str(exc.orig) if exc.orig else str(exc)
        logger.warning("integrity_error", detail=detail)

        if "foreign key" in detail.lower() or "violates foreign key" in detail.lower():
            raise UnprocessableEntityError(
                message="Operation violates a foreign-key constraint.",
                error_code="FK_VIOLATION",
                details={"detail": detail},
            ) from exc

        raise ConflictError(
            message="Operation violates a uniqueness or check constraint.",
            error_code="CONSTRAINT_VIOLATION",
            details={"detail": detail},
        ) from exc
