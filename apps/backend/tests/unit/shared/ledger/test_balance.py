"""Contract tests for :class:`Balance` (REFACT-001 PR-6a / ADR-007).

Pure-domain tests: no DB, no Dishka, no module imports. Exercise the
multi-bucket integer accumulator's invariants — empty construction,
read-side defaults, credit / debit / transfer semantics, the
non-negative invariant + ``allow_negative`` opt-out, and snapshot
immutability.
"""

from __future__ import annotations

import enum

import pytest

from src.shared.ledger.balance import Balance
from src.shared.ledger.exceptions import InsufficientBalanceError

pytestmark = pytest.mark.unit


class _Kind(enum.StrEnum):
    AVAILABLE = "available"
    PENDING = "pending"
    LIFETIME = "lifetime"


# ---------------------------------------------------------------------------
# Constructor + read API
# ---------------------------------------------------------------------------


class TestEmpty:
    def test_initialises_named_kinds_to_zero(self):
        balance = Balance.empty(kinds=_Kind)
        assert balance.get(_Kind.AVAILABLE) == 0
        assert balance.get(_Kind.PENDING) == 0
        assert balance.get(_Kind.LIFETIME) == 0

    def test_allow_negative_defaults_to_empty_frozenset(self):
        balance = Balance.empty(kinds=_Kind)
        assert balance.allow_negative == frozenset()

    def test_allow_negative_passed_through(self):
        balance = Balance.empty(kinds=_Kind, allow_negative={_Kind.PENDING})
        assert balance.allow_negative == frozenset({_Kind.PENDING})


class TestReadAccessors:
    def test_get_returns_zero_for_untouched_kind(self):
        balance = Balance(amounts={}, allow_negative=frozenset())
        assert balance.get(_Kind.AVAILABLE) == 0

    def test_snapshot_returns_defensive_copy(self):
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 100)
        snap = balance.snapshot()
        snap[_Kind.AVAILABLE] = 9999  # ty: ignore[invalid-assignment]
        assert balance.get(_Kind.AVAILABLE) == 100  # original untouched


# ---------------------------------------------------------------------------
# credit
# ---------------------------------------------------------------------------


class TestCredit:
    def test_adds_to_existing_amount(self):
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 100)
        balance.credit(_Kind.AVAILABLE, 50)
        assert balance.get(_Kind.AVAILABLE) == 150

    def test_initialises_unseen_kind(self):
        balance = Balance(amounts={}, allow_negative=frozenset())
        balance.credit(_Kind.AVAILABLE, 100)
        assert balance.get(_Kind.AVAILABLE) == 100

    def test_zero_amount_rejected(self):
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="must be positive"):
            balance.credit(_Kind.AVAILABLE, 0)

    def test_negative_amount_rejected(self):
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="must be positive"):
            balance.credit(_Kind.AVAILABLE, -5)


# ---------------------------------------------------------------------------
# debit
# ---------------------------------------------------------------------------


class TestDebit:
    def test_subtracts_from_existing_amount(self):
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 100)
        balance.debit(_Kind.AVAILABLE, 30)
        assert balance.get(_Kind.AVAILABLE) == 70

    def test_below_zero_rejected_by_default(self):
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.AVAILABLE, 50)
        with pytest.raises(InsufficientBalanceError) as exc_info:
            balance.debit(_Kind.AVAILABLE, 100)
        assert exc_info.value.details["kind"] == "available"
        assert exc_info.value.details["requested"] == 100
        assert exc_info.value.details["available"] == 50
        # Original amount untouched after rejection.
        assert balance.get(_Kind.AVAILABLE) == 50

    def test_below_zero_allowed_when_kind_in_allow_negative(self):
        balance = Balance.empty(kinds=_Kind, allow_negative={_Kind.PENDING})
        balance.debit(_Kind.PENDING, 100)
        assert balance.get(_Kind.PENDING) == -100

    def test_zero_amount_rejected(self):
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="must be positive"):
            balance.debit(_Kind.AVAILABLE, 0)

    def test_negative_amount_rejected(self):
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="must be positive"):
            balance.debit(_Kind.AVAILABLE, -10)


# ---------------------------------------------------------------------------
# transfer
# ---------------------------------------------------------------------------


class TestTransfer:
    def test_moves_amount_between_kinds(self):
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.PENDING, 100)
        balance.transfer(from_kind=_Kind.PENDING, to_kind=_Kind.AVAILABLE, amount=60)
        assert balance.get(_Kind.PENDING) == 40
        assert balance.get(_Kind.AVAILABLE) == 60

    def test_same_kind_rejected(self):
        balance = Balance.empty(kinds=_Kind)
        with pytest.raises(ValueError, match="distinct kinds"):
            balance.transfer(
                from_kind=_Kind.AVAILABLE,
                to_kind=_Kind.AVAILABLE,
                amount=10,
            )

    def test_atomic_on_insufficient_source(self):
        # Debit fails -> no credit applied. Both sides remain at original.
        balance = Balance.empty(kinds=_Kind)
        balance.credit(_Kind.PENDING, 50)
        with pytest.raises(InsufficientBalanceError):
            balance.transfer(
                from_kind=_Kind.PENDING,
                to_kind=_Kind.AVAILABLE,
                amount=100,
            )
        assert balance.get(_Kind.PENDING) == 50  # debit reverted
        assert balance.get(_Kind.AVAILABLE) == 0  # credit never applied
