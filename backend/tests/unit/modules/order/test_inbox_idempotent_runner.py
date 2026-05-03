"""Unit tests for the ``_run_idempotent`` helper used by Order TaskIQ tasks.

We don't exercise TaskIQ itself here — only the inbox-dedup wrapper.
"""

import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.domain.interfaces import IInboxStore
from src.modules.order.infrastructure.tasks import _run_idempotent

pytestmark = pytest.mark.unit


class _FakeInbox(IInboxStore):
    def __init__(self, *, accept_first_only: bool = True) -> None:
        self._seen: set[tuple[str, str]] = set()
        self._accept_first_only = accept_first_only

    async def try_record(self, *, event_id: uuid.UUID, consumer: str) -> bool:
        key = (str(event_id), consumer)
        if not self._accept_first_only:
            self._seen.add(key)
            return True
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
class TestRunIdempotent:
    async def test_first_delivery_runs_body_and_commits(self) -> None:
        inbox = _FakeInbox()
        session = _FakeSession()
        ran = False

        async def body() -> None:
            nonlocal ran
            ran = True

        result = await _run_idempotent(
            payload={"event_id": str(uuid.uuid4())},
            consumer_name="test.consumer",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body,
        )
        assert ran is True
        assert session.commits == 1
        assert result == {"status": "ok", "deduplicated": False}

    async def test_duplicate_delivery_short_circuits(self) -> None:
        inbox = _FakeInbox()
        session = _FakeSession()
        event_id = str(uuid.uuid4())

        async def body() -> None:
            pass

        first = await _run_idempotent(
            payload={"event_id": event_id},
            consumer_name="test.consumer",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body,
        )
        assert first["deduplicated"] is False

        ran_again = False

        async def body2() -> None:
            nonlocal ran_again
            ran_again = True

        second = await _run_idempotent(
            payload={"event_id": event_id},
            consumer_name="test.consumer",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body2,
        )
        assert second["deduplicated"] is True
        assert ran_again is False
        # Commit only happened on the first execution.
        assert session.commits == 1

    async def test_missing_event_id_falls_back_to_non_idempotent(self) -> None:
        inbox = _FakeInbox()
        session = _FakeSession()
        ran = False

        async def body() -> None:
            nonlocal ran
            ran = True

        result = await _run_idempotent(
            payload={"some": "payload"},  # no event_id
            consumer_name="test.consumer",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body,
        )
        assert ran is True
        assert result == {"status": "ok", "deduplicated": False}

    async def test_invalid_event_id_treated_as_missing(self) -> None:
        inbox = _FakeInbox()
        session = _FakeSession()
        ran = False

        async def body() -> None:
            nonlocal ran
            ran = True

        await _run_idempotent(
            payload={"event_id": "not-a-uuid"},
            consumer_name="test.consumer",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body,
        )
        assert ran is True

    async def test_per_consumer_isolation(self) -> None:
        """Same event_id, different consumers — both should run."""
        inbox = _FakeInbox()
        session = _FakeSession()
        event_id = str(uuid.uuid4())

        ran_a = ran_b = False

        async def body_a() -> None:
            nonlocal ran_a
            ran_a = True

        async def body_b() -> None:
            nonlocal ran_b
            ran_b = True

        a = await _run_idempotent(
            payload={"event_id": event_id},
            consumer_name="consumer.A",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body_a,
        )
        b = await _run_idempotent(
            payload={"event_id": event_id},
            consumer_name="consumer.B",
            inbox=inbox,
            session=cast(AsyncSession, session),
            body=body_b,
        )
        assert a["deduplicated"] is False
        assert b["deduplicated"] is False
        assert ran_a is True
        assert ran_b is True
