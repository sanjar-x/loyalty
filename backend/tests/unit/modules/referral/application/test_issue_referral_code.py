"""Unit tests for :class:`IssueReferralCodeHandler`."""

from __future__ import annotations

import uuid

import pytest
import structlog

from src.infrastructure.logging.adapter import StructlogAdapter
from src.modules.referral.application.commands.issue_referral_code import (
    IssueReferralCodeCommand,
    IssueReferralCodeHandler,
)
from src.modules.referral.domain.aggregates import ReferralCode
from src.modules.referral.domain.exceptions import (
    ReferralCodeAlreadyIssuedError,
)
from src.modules.referral.domain.ports import (
    ICodeGenerator,
    IReferralCodeRepository,
)
from src.shared.exceptions import ConflictError
from src.shared.interfaces.entities import AggregateRoot
from src.shared.interfaces.uow import IUnitOfWork

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeRepo(IReferralCodeRepository):
    """In-memory ReferralCode repository — flat dict keyed on customer_id."""

    def __init__(self) -> None:
        self._by_customer: dict[uuid.UUID, ReferralCode] = {}
        self._codes_in_use: set[str] = set()
        self._raise_collision_for: set[str] = set()

    async def add(self, code: ReferralCode) -> ReferralCode:
        if code.code in self._raise_collision_for:
            raise ReferralCodeAlreadyIssuedError()
        if code.customer_id in self._by_customer:
            raise ReferralCodeAlreadyIssuedError()
        if code.code in self._codes_in_use:
            raise ReferralCodeAlreadyIssuedError()
        self._by_customer[code.customer_id] = code
        self._codes_in_use.add(code.code)
        return code

    async def get(self, code_id: uuid.UUID) -> ReferralCode | None:
        for c in self._by_customer.values():
            if c.id == code_id:
                return c
        return None

    async def get_by_customer(self, customer_id: uuid.UUID) -> ReferralCode | None:
        return self._by_customer.get(customer_id)

    async def find_by_code(self, code: str) -> ReferralCode | None:
        for c in self._by_customer.values():
            if c.code == code:
                return c
        return None

    async def update(self, code: ReferralCode) -> None:
        self._by_customer[code.customer_id] = code


class _SeqGenerator(ICodeGenerator):
    """Deterministic ICodeGenerator that yields the supplied sequence."""

    def __init__(self, codes: list[str]) -> None:
        self._codes = list(codes)
        self._idx = 0

    def generate(self) -> str:
        code = self._codes[self._idx]
        self._idx += 1
        return code


class _FakeUow(IUnitOfWork):
    def __init__(self) -> None:
        self.commits = 0
        self.aggregates: list[AggregateRoot] = []

    async def __aenter__(self) -> IUnitOfWork:
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        self.aggregates.append(aggregate)

    def enqueue_external_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        event_id=None,
        correlation_id: str | None = None,
    ) -> None:
        return None


def _logger() -> StructlogAdapter:
    return StructlogAdapter(structlog.get_logger("test"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIssueReferralCode:
    async def test_first_call_persists_and_emits_event(self) -> None:
        repo = _FakeRepo()
        handler = IssueReferralCodeHandler(
            code_repo=repo,
            code_generator=_SeqGenerator(["AAAAAAAA"]),
            uow=_FakeUow(),
            logger=_logger(),
        )

        result = await handler.handle(
            IssueReferralCodeCommand(customer_id=uuid.uuid4())
        )

        assert result.code == "AAAAAAAA"
        assert result.deduplicated is False

    async def test_idempotent_when_customer_already_has_code(self) -> None:
        repo = _FakeRepo()
        existing = ReferralCode.issue(customer_id=uuid.uuid4(), code="EXIST123")
        await repo.add(existing)

        handler = IssueReferralCodeHandler(
            code_repo=repo,
            code_generator=_SeqGenerator(["NEWCODE1"]),
            uow=_FakeUow(),
            logger=_logger(),
        )

        result = await handler.handle(
            IssueReferralCodeCommand(customer_id=existing.customer_id)
        )

        assert result.code == "EXIST123"
        assert result.deduplicated is True

    async def test_collision_retries_with_fresh_code(self) -> None:
        repo = _FakeRepo()
        repo._raise_collision_for.add("BUSY1234")
        handler = IssueReferralCodeHandler(
            code_repo=repo,
            code_generator=_SeqGenerator(["BUSY1234", "GOODCODE"]),
            uow=_FakeUow(),
            logger=_logger(),
        )

        result = await handler.handle(
            IssueReferralCodeCommand(customer_id=uuid.uuid4())
        )
        assert result.code == "GOODCODE"

    async def test_retry_budget_exhausted_raises_conflict(self) -> None:
        repo = _FakeRepo()
        # Every code requested in the test collides.
        for c in (
            "A1234567",
            "A2345678",
            "A3456789",
            "A4567890",
            "A5678901",
            "A6789012",
            "A7890123",
            "A8901234",
        ):
            repo._raise_collision_for.add(c)
        handler = IssueReferralCodeHandler(
            code_repo=repo,
            code_generator=_SeqGenerator(
                [
                    "A1234567",
                    "A2345678",
                    "A3456789",
                    "A4567890",
                    "A5678901",
                    "A6789012",
                    "A7890123",
                    "A8901234",
                ]
            ),
            uow=_FakeUow(),
            logger=_logger(),
        )

        with pytest.raises(ConflictError) as exc_info:
            await handler.handle(IssueReferralCodeCommand(customer_id=uuid.uuid4()))
        assert exc_info.value.error_code == "REFERRAL_CODE_COLLISION_RETRY_EXHAUSTED"
