"""Contract tests for :class:`Account` (REFACT-001 PR-6a / ADR-007).

Pure-domain tests: no DB, no Dishka, no module imports. Exercise the
generic ``Account`` aggregate's read accessors, mutation forwarding to
:class:`Balance`, ``updated_at`` advancement, optimistic-locking
``version`` field, and :class:`AggregateRoot` event-buffer mixin.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from shared.interfaces.entities import ModuleDomainEvent
from shared.ledger.account import Account
from shared.ledger.balance import Balance
from shared.ledger.exceptions import InsufficientBalanceError

pytestmark = pytest.mark.unit


class _Kind(enum.StrEnum):
    AVAILABLE = "available"
    PENDING = "pending"
    LIFETIME = "lifetime"


def _make_account(
    *,
    balance: Balance[_Kind] | None = None,
    owner_type: str = "customer",
) -> Account[_Kind]:
    return Account(
        id=uuid.uuid4(),
        owner_type=owner_type,
        owner_id=uuid.uuid4(),
        currency="RUB",
        balance=balance if balance is not None else Balance.empty(kinds=_Kind),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_required_fields_assigned(self):
        account_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        balance = Balance.empty(kinds=_Kind)
        account = Account(
            id=account_id,
            owner_type="customer",
            owner_id=owner_id,
            currency="RUB",
            balance=balance,
        )
        assert account.id == account_id
        assert account.owner_type == "customer"
        assert account.owner_id == owner_id
        assert account.currency == "RUB"
        assert account.balance is balance

    def test_default_version_is_zero(self):
        assert _make_account().version == 0

    def test_default_timestamps_are_recent_utc(self):
        before = datetime.now(UTC)
        account = _make_account()
        after = datetime.now(UTC)
        assert before <= account.created_at <= after
        assert before <= account.updated_at <= after

    def test_arbitrary_owner_type_accepted(self):
        # Kernel imposes no enum on owner_type — consumer modules choose.
        account = _make_account(owner_type="supplier")
        assert account.owner_type == "supplier"


# ---------------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------------


class TestAmount:
    def test_returns_zero_for_empty_balance(self):
        account = _make_account()
        assert account.amount(_Kind.AVAILABLE) == 0

    def test_reflects_balance_state(self):
        account = _make_account()
        account.credit(_Kind.AVAILABLE, 250)
        assert account.amount(_Kind.AVAILABLE) == 250


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class TestCredit:
    def test_forwards_to_balance(self):
        account = _make_account()
        account.credit(_Kind.AVAILABLE, 100)
        assert account.balance.get(_Kind.AVAILABLE) == 100

    def test_advances_updated_at(self):
        account = _make_account()
        original = account.updated_at - timedelta(seconds=1)
        account.updated_at = original
        account.credit(_Kind.AVAILABLE, 100)
        assert account.updated_at > original


class TestDebit:
    def test_forwards_to_balance(self):
        account = _make_account()
        account.credit(_Kind.AVAILABLE, 100)
        account.debit(_Kind.AVAILABLE, 30)
        assert account.balance.get(_Kind.AVAILABLE) == 70

    def test_propagates_insufficient_balance(self):
        account = _make_account()
        account.credit(_Kind.AVAILABLE, 50)
        with pytest.raises(InsufficientBalanceError):
            account.debit(_Kind.AVAILABLE, 100)
        # Balance left untouched after rejection.
        assert account.balance.get(_Kind.AVAILABLE) == 50

    def test_advances_updated_at(self):
        account = _make_account()
        account.credit(_Kind.AVAILABLE, 100)
        original = account.updated_at - timedelta(seconds=1)
        account.updated_at = original
        account.debit(_Kind.AVAILABLE, 50)
        assert account.updated_at > original


class TestTransfer:
    def test_forwards_to_balance(self):
        account = _make_account()
        account.credit(_Kind.PENDING, 100)
        account.transfer(from_kind=_Kind.PENDING, to_kind=_Kind.AVAILABLE, amount=60)
        assert account.balance.get(_Kind.PENDING) == 40
        assert account.balance.get(_Kind.AVAILABLE) == 60

    def test_atomic_on_failure(self):
        account = _make_account()
        account.credit(_Kind.PENDING, 50)
        with pytest.raises(InsufficientBalanceError):
            account.transfer(
                from_kind=_Kind.PENDING,
                to_kind=_Kind.AVAILABLE,
                amount=100,
            )
        assert account.balance.get(_Kind.PENDING) == 50
        assert account.balance.get(_Kind.AVAILABLE) == 0

    def test_advances_updated_at(self):
        account = _make_account()
        account.credit(_Kind.PENDING, 100)
        original = account.updated_at - timedelta(seconds=1)
        account.updated_at = original
        account.transfer(from_kind=_Kind.PENDING, to_kind=_Kind.AVAILABLE, amount=10)
        assert account.updated_at > original


# ---------------------------------------------------------------------------
# AggregateRoot mixin
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProbeEvent(
    ModuleDomainEvent,
    required_fields=("account_id",),
    aggregate_id_field="account_id",
):
    aggregate_type: str = "ledger_account"
    account_id: uuid.UUID | None = None
    event_type: str = "_ProbeEvent"


class TestAggregateRootBuffer:
    def test_starts_with_empty_event_buffer(self):
        account = _make_account()
        assert account.domain_events == []

    def test_add_domain_event_buffers(self):
        account = _make_account()
        event = _ProbeEvent(account_id=account.id)
        account.add_domain_event(event)
        assert account.domain_events == [event]

    def test_clear_domain_events_drops_buffered(self):
        account = _make_account()
        account.add_domain_event(_ProbeEvent(account_id=account.id))
        account.clear_domain_events()
        assert account.domain_events == []

    def test_domain_events_returns_defensive_copy(self):
        account = _make_account()
        event = _ProbeEvent(account_id=account.id)
        account.add_domain_event(event)
        snapshot = account.domain_events
        snapshot.clear()
        assert account.domain_events == [event]


# ---------------------------------------------------------------------------
# Generic typing — kernel accepts any consumer-supplied BalanceKindT.
# ---------------------------------------------------------------------------


class _AltKind(enum.StrEnum):
    REWARD = "reward"
    EXPIRED = "expired"


class TestGenericOverBalanceKind:
    def test_account_accepts_alternative_kind_enum(self):
        balance = Balance.empty(kinds=_AltKind)
        account = Account(
            id=uuid.uuid4(),
            owner_type="customer",
            owner_id=uuid.uuid4(),
            currency="USD",
            balance=balance,
        )
        account.credit(_AltKind.REWARD, 500)
        assert account.amount(_AltKind.REWARD) == 500
