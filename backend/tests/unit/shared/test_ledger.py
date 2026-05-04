"""Tests for the shared double-entry ledger.

Covers:

* :class:`Balance` — credit/debit/transfer arithmetic, allow-negative
  semantics, value-validation rejections.
* :class:`Account` — aggregate-level mutations advance ``updated_at``.
* :class:`LedgerEntry` / :class:`LedgerTransaction` — frozen-dataclass
  invariants (no zero-amount entry, no empty transaction).
* :class:`LedgerTransactionPostedEvent` — required-field contract
  inherited from :class:`ModuleDomainEvent`.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

import attrs
import pytest

from src.shared.ledger import (
    Account,
    Balance,
    EmptyLedgerTransactionError,
    InsufficientBalanceError,
    InvalidLedgerEntryError,
    LedgerEntry,
    LedgerTransaction,
    LedgerTransactionPostedEvent,
)


class _Kind(StrEnum):
    AVAILABLE = "available"
    PENDING = "pending"
    LIFETIME = "lifetime"


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


class TestBalanceArithmetic:
    def test_empty_initialises_all_kinds_to_zero(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        assert balance.get(_Kind.AVAILABLE) == 0
        assert balance.get(_Kind.PENDING) == 0
        assert balance.get(_Kind.LIFETIME) == 0

    def test_credit_adds_amount(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 250)
        balance.credit(_Kind.AVAILABLE, 100)
        assert balance.get(_Kind.AVAILABLE) == 350

    def test_debit_subtracts_amount(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 500)
        balance.debit(_Kind.AVAILABLE, 200)
        assert balance.get(_Kind.AVAILABLE) == 300

    def test_credit_rejects_zero_and_negative(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="positive"):
            balance.credit(_Kind.AVAILABLE, 0)
        with pytest.raises(ValueError, match="positive"):
            balance.credit(_Kind.AVAILABLE, -10)

    def test_debit_rejects_zero_and_negative(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="positive"):
            balance.debit(_Kind.AVAILABLE, 0)
        with pytest.raises(ValueError, match="positive"):
            balance.debit(_Kind.AVAILABLE, -10)


class TestBalanceNonNegativeInvariant:
    def test_debit_below_zero_raises_when_kind_is_strict(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 100)
        with pytest.raises(InsufficientBalanceError) as exc_info:
            balance.debit(_Kind.AVAILABLE, 250)
        assert exc_info.value.details["requested"] == 250
        assert exc_info.value.details["available"] == 100
        # After failure the balance is unchanged
        assert balance.get(_Kind.AVAILABLE) == 100

    def test_debit_below_zero_allowed_when_kind_opted_in(self) -> None:
        # PENDING is allowed to go negative — late-refund clawback case.
        balance = Balance.empty(kinds=_Kind, allow_negative=frozenset({_Kind.PENDING}))
        balance.debit(_Kind.PENDING, 150)
        assert balance.get(_Kind.PENDING) == -150


class TestBalanceTransfer:
    def test_transfer_moves_amount(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.PENDING, 250)
        balance.transfer(from_kind=_Kind.PENDING, to_kind=_Kind.AVAILABLE, amount=250)
        assert balance.get(_Kind.PENDING) == 0
        assert balance.get(_Kind.AVAILABLE) == 250

    def test_transfer_rejects_same_kind(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="distinct kinds"):
            balance.transfer(from_kind=_Kind.PENDING, to_kind=_Kind.PENDING, amount=10)

    def test_transfer_atomic_on_insufficient_source(self) -> None:
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.PENDING, 100)
        with pytest.raises(InsufficientBalanceError):
            balance.transfer(
                from_kind=_Kind.PENDING, to_kind=_Kind.AVAILABLE, amount=250
            )
        # destination must remain untouched
        assert balance.get(_Kind.PENDING) == 100
        assert balance.get(_Kind.AVAILABLE) == 0


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


def _account() -> Account[_Kind]:
    return Account(
        id=uuid.uuid4(),
        owner_type="customer",
        owner_id=uuid.uuid4(),
        currency="RUB",
        balance=Balance.empty(kinds=_Kind),
    )


class TestAccountMutations:
    def test_credit_advances_timestamp(self) -> None:
        account = _account()
        before = account.updated_at
        account.credit(_Kind.AVAILABLE, 100)
        assert account.updated_at >= before
        assert account.amount(_Kind.AVAILABLE) == 100

    def test_debit_advances_timestamp(self) -> None:
        account = _account()
        account.credit(_Kind.AVAILABLE, 200)
        before = account.updated_at
        account.debit(_Kind.AVAILABLE, 50)
        assert account.updated_at >= before
        assert account.amount(_Kind.AVAILABLE) == 150

    def test_transfer(self) -> None:
        account = _account()
        account.credit(_Kind.PENDING, 250)
        account.transfer(from_kind=_Kind.PENDING, to_kind=_Kind.AVAILABLE, amount=250)
        assert account.amount(_Kind.PENDING) == 0
        assert account.amount(_Kind.AVAILABLE) == 250


# ---------------------------------------------------------------------------
# LedgerEntry / LedgerTransaction
# ---------------------------------------------------------------------------


class TestLedgerEntry:
    def test_zero_amount_rejected(self) -> None:
        with pytest.raises(InvalidLedgerEntryError, match="non-zero"):
            LedgerEntry(kind=_Kind.AVAILABLE, amount=0)

    def test_positive_and_negative_amounts_accepted(self) -> None:
        credit = LedgerEntry(kind=_Kind.AVAILABLE, amount=100)
        debit = LedgerEntry(kind=_Kind.PENDING, amount=-50)
        assert credit.amount == 100
        assert debit.amount == -50


class TestLedgerTransaction:
    def _make_transaction(
        self, *, entries: tuple[LedgerEntry[_Kind], ...]
    ) -> LedgerTransaction[_Kind]:
        return LedgerTransaction(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            kind="test_event",
            entries=entries,
            balance_snapshot={k: 0 for k in _Kind},
        )

    def test_empty_entries_rejected(self) -> None:
        with pytest.raises(EmptyLedgerTransactionError):
            self._make_transaction(entries=())

    def test_aggregates_credit_debit_net(self) -> None:
        tx = self._make_transaction(
            entries=(
                LedgerEntry(kind=_Kind.AVAILABLE, amount=250),
                LedgerEntry(kind=_Kind.PENDING, amount=-250),
                LedgerEntry(kind=_Kind.LIFETIME, amount=250),
            )
        )
        assert tx.total_credit == 500
        assert tx.total_debit == -250
        assert tx.net == 250

    def test_is_frozen(self) -> None:
        tx = self._make_transaction(
            entries=(LedgerEntry(kind=_Kind.AVAILABLE, amount=100),)
        )
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            tx.kind = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Domain event
# ---------------------------------------------------------------------------


class TestLedgerTransactionPostedEvent:
    def test_construction_requires_transaction_and_account_ids(self) -> None:
        with pytest.raises(ValueError, match="transaction_id is required"):
            LedgerTransactionPostedEvent(
                account_id=uuid.uuid4(),
                transaction_kind="x",
                net_amount=10,
            )
        with pytest.raises(ValueError, match="account_id is required"):
            LedgerTransactionPostedEvent(
                transaction_id=uuid.uuid4(),
                transaction_kind="x",
                net_amount=10,
            )

    def test_aggregate_id_is_account_id(self) -> None:
        account_id = uuid.uuid4()
        event = LedgerTransactionPostedEvent(
            transaction_id=uuid.uuid4(),
            account_id=account_id,
            transaction_kind="referral_reward_release",
            net_amount=250,
        )
        assert event.aggregate_id == str(account_id)
        assert event.aggregate_type == "ledger_account"
        assert event.event_type == "LedgerTransactionPostedEvent"
