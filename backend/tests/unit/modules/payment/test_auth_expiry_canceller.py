"""Unit tests for AuthExpiryCanceller (B3).

Asserts:
* Empty selector → ``run()`` returns 0 without invoking the fail handler.
* Each expired id is dispatched to ``FailPaymentIntentHandler`` with the
  ``auth_expired`` reason.
* PaymentIntentNotFoundError on a single intent doesn't poison the batch.
* Generic exceptions on a single intent are logged and skipped.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.modules.payment.application.commands.fail_payment_intent import (
    FailPaymentIntentCommand,
)
from src.modules.payment.domain.exceptions import PaymentIntentNotFoundError
from src.modules.payment.infrastructure.services.auth_expiry_canceller import (
    AUTH_EXPIRED_REASON,
    AuthExpiryCanceller,
)

pytestmark = pytest.mark.unit


class _FakeRepo:
    def __init__(self, ids: list[uuid.UUID]) -> None:
        self._ids = ids
        self.calls: list[tuple[datetime, int]] = []

    async def find_expired_authorized(
        self, *, now: datetime, limit: int = 100
    ) -> list[uuid.UUID]:
        self.calls.append((now, limit))
        return list(self._ids)

    # The canceller never touches these — IPaymentIntentRepository methods we
    # don't need are intentionally absent so a mistaken call would AttributeError
    # in tests instead of silently passing.


class _FakeFailHandler:
    def __init__(self, *, raise_for: dict[uuid.UUID, Exception] | None = None) -> None:
        self._raise_for = raise_for or {}
        self.calls: list[FailPaymentIntentCommand] = []

    async def handle(self, command: FailPaymentIntentCommand) -> None:
        self.calls.append(command)
        if command.intent_id in self._raise_for:
            raise self._raise_for[command.intent_id]


class _NoopLogger:
    def bind(self, **_: Any) -> _NoopLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        return None

    def warning(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        return None

    def exception(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        return None

    def error(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        return None

    def debug(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        return None


def _make_canceller(
    *,
    expired_ids: list[uuid.UUID],
    raise_for: dict[uuid.UUID, Exception] | None = None,
) -> tuple[AuthExpiryCanceller, _FakeRepo, _FakeFailHandler]:
    repo = _FakeRepo(expired_ids)
    handler = _FakeFailHandler(raise_for=raise_for)
    canceller = AuthExpiryCanceller(repo, handler, _NoopLogger())  # ty: ignore[invalid-argument-type]
    return canceller, repo, handler


async def test_empty_batch_returns_zero_without_invoking_handler() -> None:
    canceller, repo, handler = _make_canceller(expired_ids=[])
    failed = await canceller.run()
    assert failed == 0
    assert handler.calls == []
    # Selector is still consulted once per tick.
    assert len(repo.calls) == 1
    assert repo.calls[0][1] == 100  # default batch_size


async def test_each_expired_id_is_failed_with_auth_expired_reason() -> None:
    ids = [uuid.uuid4() for _ in range(3)]
    canceller, _, handler = _make_canceller(expired_ids=ids)

    failed = await canceller.run()

    assert failed == 3
    assert [c.intent_id for c in handler.calls] == ids
    assert {c.reason for c in handler.calls} == {AUTH_EXPIRED_REASON}


async def test_not_found_does_not_poison_batch() -> None:
    ids = [uuid.uuid4() for _ in range(3)]
    canceller, _, handler = _make_canceller(
        expired_ids=ids,
        raise_for={ids[1]: PaymentIntentNotFoundError(intent_id=str(ids[1]))},
    )

    failed = await canceller.run()

    # Two succeed; one race-deleted intent is logged + skipped (not counted).
    assert failed == 2
    assert [c.intent_id for c in handler.calls] == ids


async def test_generic_exception_is_logged_and_skipped() -> None:
    ids = [uuid.uuid4(), uuid.uuid4()]
    canceller, _, handler = _make_canceller(
        expired_ids=ids,
        raise_for={ids[0]: RuntimeError("transient db blip")},
    )

    failed = await canceller.run()

    # First intent threw; second is still attempted.
    assert failed == 1
    assert [c.intent_id for c in handler.calls] == ids


async def test_batch_size_propagated_to_selector() -> None:
    canceller, repo, _ = _make_canceller(expired_ids=[])
    await canceller.run(batch_size=42)
    assert repo.calls[0][1] == 42


async def test_now_is_recent_utc_datetime() -> None:
    canceller, repo, _ = _make_canceller(expired_ids=[])
    before = datetime.now(UTC)
    await canceller.run()
    after = datetime.now(UTC)
    captured_now = repo.calls[0][0]
    assert before <= captured_now <= after
    assert captured_now.tzinfo is UTC
