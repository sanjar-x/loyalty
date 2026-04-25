"""Integration tests for ``SqlAlchemyUserActivityReader``.

These tests exist to catch the specific class of regression that caused
the original "Для вас" warm-branch outage: the reader was querying
``event_type == 'product_view'`` while the Redis tracker was writing
``'product_viewed'``.  Unit tests with fakes missed it because they
don't exercise the real event_type string against the real column.

The tests seed rows directly via the repository (same path production
uses) and assert that the reader returns them.  A string-level drift of
either side fails these tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.activity.domain.entities import UserActivityEvent
from src.modules.activity.domain.value_objects import ActivityEventType
from src.modules.activity.infrastructure.history_reader import (
    SqlAlchemyUserActivityReader,
)
from src.modules.activity.infrastructure.repository import (
    SqlAlchemyActivityEventRepository,
)


class _NullLogger:
    """Minimal ILogger stub — integration tests don't assert on logs."""

    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


def _event(
    *,
    actor_id: uuid.UUID,
    event_type: str = ActivityEventType.PRODUCT_VIEWED.value,
    category_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> UserActivityEvent:
    return UserActivityEvent(
        id=uuid.uuid4(),
        event_type=event_type,
        actor_id=actor_id,
        session_id="test-session",
        product_id=product_id,
        category_id=category_id,
        search_query=None,
        payload={},
        created_at=created_at or datetime.now(UTC),
    )


@pytest.mark.integration
class TestSqlAlchemyUserActivityReader:
    async def test_category_affinities_returns_product_viewed_events(
        self, db_session: AsyncSession
    ) -> None:
        """Regression guard for the event_type drift bug.

        If either the writer or the reader renames PRODUCT_VIEWED the
        canonical enum breaks and this test fails — whereas the old
        hardcoded-string reader silently returned ``[]``.
        """
        user_id = uuid.uuid4()
        cat_a, cat_b = uuid.uuid4(), uuid.uuid4()
        repo = SqlAlchemyActivityEventRepository(db_session)

        await repo.bulk_add(
            [
                _event(actor_id=user_id, category_id=cat_a),
                _event(actor_id=user_id, category_id=cat_a),
                _event(actor_id=user_id, category_id=cat_b),
                # Different event_type must be excluded from affinity aggregation.
                _event(
                    actor_id=user_id,
                    category_id=cat_a,
                    event_type=ActivityEventType.SEARCH_PERFORMED.value,
                ),
            ]
        )
        await db_session.flush()

        reader = SqlAlchemyUserActivityReader(db_session, _NullLogger())
        affinities = await reader.get_category_affinities(
            user_id=user_id, lookback_days=30, limit=5
        )

        by_id = {a.category_id: a.weight for a in affinities}
        assert by_id[cat_a] == 2.0, (
            "product_viewed events for cat_a must be aggregated; "
            "non-product_viewed events must be excluded"
        )
        assert by_id[cat_b] == 1.0

    async def test_recently_viewed_dedupes_and_respects_lookback(
        self, db_session: AsyncSession
    ) -> None:
        user_id = uuid.uuid4()
        product_a, product_b = uuid.uuid4(), uuid.uuid4()
        now = datetime.now(UTC)
        repo = SqlAlchemyActivityEventRepository(db_session)

        await repo.bulk_add(
            [
                _event(actor_id=user_id, product_id=product_a, created_at=now),
                _event(
                    actor_id=user_id,
                    product_id=product_a,
                    created_at=now - timedelta(hours=1),
                ),
                _event(
                    actor_id=user_id,
                    product_id=product_b,
                    created_at=now - timedelta(hours=2),
                ),
            ]
        )
        await db_session.flush()

        reader = SqlAlchemyUserActivityReader(db_session, _NullLogger())
        viewed = await reader.get_recently_viewed_product_ids(
            user_id=user_id, lookback_days=30, limit=10
        )

        # Deduplicated; ordered by most-recent view (product_a newer than product_b).
        assert viewed == [product_a, product_b]

    async def test_event_count_filters_by_actor_and_lookback(
        self, db_session: AsyncSession
    ) -> None:
        me, other = uuid.uuid4(), uuid.uuid4()
        now = datetime.now(UTC)
        repo = SqlAlchemyActivityEventRepository(db_session)

        await repo.bulk_add(
            [
                _event(actor_id=me, created_at=now),
                _event(actor_id=me, created_at=now - timedelta(days=1)),
                # Outside the 5-day lookback we pass below:
                _event(actor_id=me, created_at=now - timedelta(days=10)),
                # Different actor must not leak into the count:
                _event(actor_id=other, created_at=now),
            ]
        )
        await db_session.flush()

        reader = SqlAlchemyUserActivityReader(db_session, _NullLogger())
        count = await reader.get_activity_event_count(user_id=me, lookback_days=5)
        assert count == 2
