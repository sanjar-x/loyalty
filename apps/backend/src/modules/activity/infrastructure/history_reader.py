"""
SQLAlchemy implementation of :class:`IUserActivityReader`.

Reads per-user aggregates from the partitioned ``user_activity_events``
table.  All queries restrict on ``actor_id`` + ``created_at`` so they hit
the partial ``ix_user_activity_events_actor_created`` index and only scan
partitions within the lookback window.

Graceful degradation
--------------------

Any DB failure is logged and results are treated as empty.  Recommendation
handlers fall back to the global cold-start path (trending weekly), so the
homepage «Для вас» feed still renders during a DB hiccup.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.activity.domain.value_objects import ActivityEventType
from src.modules.activity.infrastructure.models import UserActivityEventModel
from src.shared.interfaces.activity import CategoryAffinity
from src.shared.interfaces.logger import ILogger

# Use the canonical enum value so the reader and the Redis tracker writer
# can never drift apart ("product_view" vs "product_viewed" caused a
# silent bug where the warm "Для вас" branch always fell through to the
# cold-start path — events were written with one spelling and read with
# another, and the aggregate queries returned zero rows for every user).
_EVENT_PRODUCT_VIEW = ActivityEventType.PRODUCT_VIEWED.value


class SqlAlchemyUserActivityReader:
    """Concrete :class:`IUserActivityReader` backed by PostgreSQL."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(service="SqlAlchemyUserActivityReader")

    async def get_category_affinities(
        self,
        *,
        user_id: uuid.UUID,
        lookback_days: int = 30,
        limit: int = 5,
    ) -> list[CategoryAffinity]:
        since = self._since(lookback_days)
        stmt = (
            select(
                UserActivityEventModel.category_id,
                func.count().label("weight"),
            )
            .where(
                UserActivityEventModel.actor_id == user_id,
                UserActivityEventModel.event_type == _EVENT_PRODUCT_VIEW,
                UserActivityEventModel.category_id.is_not(None),
                UserActivityEventModel.created_at >= since,
            )
            .group_by(UserActivityEventModel.category_id)
            .order_by(func.count().desc())
            .limit(max(1, min(int(limit), 50)))
        )
        try:
            result = await self._session.execute(stmt)
        except SQLAlchemyError as exc:
            self._logger.warning(
                "activity.history.category_affinities_failed", error=str(exc)
            )
            return []

        return [
            CategoryAffinity(category_id=row.category_id, weight=float(row.weight))
            for row in result.all()
            if row.category_id is not None
        ]

    async def get_recently_viewed_product_ids(
        self,
        *,
        user_id: uuid.UUID,
        lookback_days: int = 30,
        limit: int = 100,
    ) -> list[uuid.UUID]:
        since = self._since(lookback_days)
        safe_limit = max(1, min(int(limit), 500))
        # DISTINCT ON via subquery to dedupe while preserving most-recent order.
        sub = (
            select(
                UserActivityEventModel.product_id,
                func.max(UserActivityEventModel.created_at).label("last_seen"),
            )
            .where(
                UserActivityEventModel.actor_id == user_id,
                UserActivityEventModel.event_type == _EVENT_PRODUCT_VIEW,
                UserActivityEventModel.product_id.is_not(None),
                UserActivityEventModel.created_at >= since,
            )
            .group_by(UserActivityEventModel.product_id)
            .order_by(func.max(UserActivityEventModel.created_at).desc())
            .limit(safe_limit)
        )
        try:
            result = await self._session.execute(sub)
        except SQLAlchemyError as exc:
            self._logger.warning(
                "activity.history.recently_viewed_failed", error=str(exc)
            )
            return []

        return [row.product_id for row in result.all() if row.product_id is not None]

    async def get_activity_event_count(
        self,
        *,
        user_id: uuid.UUID,
        lookback_days: int = 30,
    ) -> int:
        since = self._since(lookback_days)
        stmt = select(func.count()).where(
            UserActivityEventModel.actor_id == user_id,
            UserActivityEventModel.created_at >= since,
        )
        try:
            result = await self._session.execute(stmt)
        except SQLAlchemyError as exc:
            self._logger.warning("activity.history.event_count_failed", error=str(exc))
            return 0
        return int(result.scalar_one() or 0)

    @staticmethod
    def _since(lookback_days: int) -> datetime:
        days = max(1, min(int(lookback_days), 365))
        return datetime.now(UTC) - timedelta(days=days)
