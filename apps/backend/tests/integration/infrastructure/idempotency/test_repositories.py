"""Contract tests for SqlIdempotencyStore + SqlInboxStore (real PG).

These adapters rely on a single ``UNIQUE`` index for atomicity:
``INSERT`` is racy, but the database serialises the conflict and the
adapter translates an :class:`IntegrityError` into a ``False`` return.
The behaviour cannot be faithfully reproduced with a mocked session --
the conflict path depends on PostgreSQL's actual constraint
enforcement -- so these tests run against a real PG container with the
unit-scoped savepoint rollback fixture.

Coverage matrix:

* SqlIdempotencyStore
  - reserve happy path (new key)
  - reserve duplicate (same scope+key) -> False
  - attach_result + get_result roundtrip
  - get_result on absent key -> None
* SqlInboxStore
  - try_record happy path (new event_id+consumer)
  - try_record duplicate (same event_id+consumer) -> False
  - try_record allows same event_id under different consumer names
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import registry as _registry  # noqa: F401
from src.infrastructure.idempotency.repositories import (
    SqlIdempotencyStore,
    SqlInboxStore,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# SqlIdempotencyStore
# ---------------------------------------------------------------------------


async def test_reserve_inserts_new_row(db_session: AsyncSession) -> None:
    store = SqlIdempotencyStore(db_session)
    inserted = await store.reserve(
        key="abc123",
        identity_id=uuid.uuid4(),
        scope="order.create",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    assert inserted is True


async def test_reserve_duplicate_scope_key_returns_false(
    db_session: AsyncSession,
) -> None:
    store = SqlIdempotencyStore(db_session)
    identity = uuid.uuid4()
    expires = datetime.now(UTC) + timedelta(hours=1)

    first = await store.reserve(
        key="dup-key",
        identity_id=identity,
        scope="order.create",
        expires_at=expires,
    )
    second = await store.reserve(
        key="dup-key",
        identity_id=identity,
        scope="order.create",
        expires_at=expires,
    )
    assert first is True
    assert second is False


async def test_attach_result_roundtrip(db_session: AsyncSession) -> None:
    store = SqlIdempotencyStore(db_session)
    expires = datetime.now(UTC) + timedelta(hours=1)
    await store.reserve(
        key="round-key",
        identity_id=uuid.uuid4(),
        scope="loyalty.adjust",
        expires_at=expires,
    )
    resource_id = uuid.uuid4()
    await store.attach_result(
        key="round-key", scope="loyalty.adjust", resource_id=resource_id
    )

    fetched = await store.get_result(key="round-key", scope="loyalty.adjust")
    assert fetched == resource_id


async def test_get_result_absent_returns_none(db_session: AsyncSession) -> None:
    store = SqlIdempotencyStore(db_session)
    fetched = await store.get_result(key="missing", scope="order.create")
    assert fetched is None


async def test_attach_result_on_absent_reservation_is_noop(
    db_session: AsyncSession,
) -> None:
    """If the reservation row is gone (TTL pruning, manual cleanup), the
    adapter must not raise -- it logs and walks away. The next
    get_result returns None (no row to attach to)."""
    store = SqlIdempotencyStore(db_session)
    await store.attach_result(
        key="never-reserved", scope="order.create", resource_id=uuid.uuid4()
    )
    fetched = await store.get_result(key="never-reserved", scope="order.create")
    assert fetched is None


# ---------------------------------------------------------------------------
# SqlInboxStore
# ---------------------------------------------------------------------------


async def test_try_record_inserts_new_row(db_session: AsyncSession) -> None:
    store = SqlInboxStore(db_session)
    recorded = await store.try_record(
        event_id=uuid.uuid4(), consumer="order.create_handler"
    )
    assert recorded is True


async def test_try_record_duplicate_event_consumer_returns_false(
    db_session: AsyncSession,
) -> None:
    store = SqlInboxStore(db_session)
    event_id = uuid.uuid4()
    first = await store.try_record(event_id=event_id, consumer="loyalty.consumer")
    second = await store.try_record(event_id=event_id, consumer="loyalty.consumer")
    assert first is True
    assert second is False


async def test_try_record_same_event_distinct_consumers_both_succeed(
    db_session: AsyncSession,
) -> None:
    """Per-consumer isolation -- the uniqueness key is (event_id, consumer)
    so the same outbox event can land in two different consumer's inboxes."""
    store = SqlInboxStore(db_session)
    event_id = uuid.uuid4()
    consumer_a = await store.try_record(event_id=event_id, consumer="consumer.a")
    consumer_b = await store.try_record(event_id=event_id, consumer="consumer.b")
    assert consumer_a is True
    assert consumer_b is True
