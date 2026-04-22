"""
SQLAlchemy implementation of :class:`ICoViewReader`.

Reads from the ``product_co_view_scores`` table maintained asynchronously
by :func:`refresh_co_view_scores_task`.  No fallback computation is
performed on read — the index ``ix_product_co_view_scores_top`` on
``(product_id, score DESC)`` answers top-N in microseconds.

Graceful degradation
--------------------

Any DB failure is logged and the reader returns an empty list so the
caller can fall back to content-based similarity.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.interfaces.activity import CoViewScore
from src.shared.interfaces.logger import ILogger


class SqlAlchemyCoViewReader:
    """Concrete :class:`ICoViewReader` backed by PostgreSQL."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(service="SqlAlchemyCoViewReader")

    async def get_also_viewed(
        self,
        *,
        product_id: uuid.UUID,
        limit: int = 12,
    ) -> list[CoViewScore]:
        limit = max(1, min(limit, 50))
        stmt = text(
            """
            SELECT co_product_id, score
              FROM product_co_view_scores
             WHERE product_id = :pid
          ORDER BY score DESC, co_product_id
             LIMIT :lim
            """
        )
        try:
            rows = (
                await self._session.execute(
                    stmt, {"pid": product_id, "lim": limit}
                )
            ).all()
        except SQLAlchemyError:
            self._logger.exception("co_view.query_failed", product_id=product_id)
            return []

        return [
            CoViewScore(product_id=row.co_product_id, score=int(row.score))
            for row in rows
        ]
