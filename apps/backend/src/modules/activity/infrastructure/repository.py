"""
SQLAlchemy repository for :class:`UserActivityEvent` persistence.

Optimised for append-only bulk writes — no read paths live here (MVP).
"""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.activity.domain.entities import UserActivityEvent
from src.modules.activity.infrastructure.models import UserActivityEventModel


class SqlAlchemyActivityEventRepository:
    """Repository that writes :class:`UserActivityEvent` records in bulk."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_add(self, events: list[UserActivityEvent]) -> int:
        """Persist ``events`` via a single INSERT statement.

        Uses ``ON CONFLICT (id) DO NOTHING`` so the flush task can safely
        retry a batch without raising :class:`IntegrityError` when some
        rows already landed during a partial earlier commit.  Event ids
        are client-generated UUIDv4 and the table has a surrogate PK.

        Returns:
            Number of rows the repository attempted to insert (not the
            number of rows actually affected by the statement — callers
            treat this as idempotent best-effort).
        """
        if not events:
            return 0

        rows = [
            {
                "id": e.id,
                "event_type": e.event_type,
                "actor_id": e.actor_id,
                "session_id": e.session_id,
                "product_id": e.product_id,
                "category_id": e.category_id,
                "search_query": e.search_query,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in events
        ]
        stmt = pg_insert(UserActivityEventModel).values(rows)
        # The table is RANGE-partitioned by ``created_at`` so the primary
        # key is composite ``(id, created_at)`` — PostgreSQL requires the
        # ON CONFLICT target to match an actual unique constraint, which
        # means we cannot target ``id`` alone.  ``created_at`` is a
        # deterministic attribute of the domain event (set once at
        # creation and carried through the Redis buffer), so targeting
        # ``(id, created_at)`` preserves the intended retry-safety
        # semantics — a duplicate of the exact same logical event (same
        # id, same timestamp) becomes a no-op.
        stmt = stmt.on_conflict_do_nothing(index_elements=["id", "created_at"])
        await self._session.execute(stmt)
        return len(rows)
