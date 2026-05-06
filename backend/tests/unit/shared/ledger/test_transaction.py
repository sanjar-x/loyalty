"""Contract tests for :class:`LedgerEntry` / :class:`LedgerTransaction`
(REFACT-001 PR-6a / ADR-007).

Pure-domain tests: no DB, no Dishka, no module imports. Cover the
construction-time invariants (zero-amount entry, empty-entries
transaction), the immutable / frozen contract, the ``total_credit`` /
``total_debit`` / ``net`` aggregate accessors, and optional reference
field defaults.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

import attrs
import pytest

from src.shared.ledger.exceptions import (
    EmptyLedgerTransactionError,
    InvalidLedgerEntryError,
)
from src.shared.ledger.transaction import LedgerEntry, LedgerTransaction

pytestmark = pytest.mark.unit


class _Kind(enum.StrEnum):
    AVAILABLE = "available"
    PENDING = "pending"
    LIFETIME = "lifetime"


# ---------------------------------------------------------------------------
# LedgerEntry
# ---------------------------------------------------------------------------


class TestLedgerEntry:
    def test_positive_amount_accepted(self):
        entry = LedgerEntry(kind=_Kind.AVAILABLE, amount=100)
        assert entry.kind == _Kind.AVAILABLE
        assert entry.amount == 100

    def test_negative_amount_accepted(self):
        # Negative entries model debits in a double-entry transaction.
        entry = LedgerEntry(kind=_Kind.PENDING, amount=-50)
        assert entry.amount == -50

    def test_zero_amount_rejected(self):
        with pytest.raises(InvalidLedgerEntryError) as exc_info:
            LedgerEntry(kind=_Kind.AVAILABLE, amount=0)
        assert exc_info.value.details["reason"] == "amount must be non-zero"

    def test_is_frozen(self):
        entry = LedgerEntry(kind=_Kind.AVAILABLE, amount=100)
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            entry.amount = 200  # ty: ignore[invalid-assignment]


# ---------------------------------------------------------------------------
# LedgerTransaction — construction
# ---------------------------------------------------------------------------


def _make_tx(
    *,
    entries: tuple[LedgerEntry[_Kind], ...] = (
        LedgerEntry(kind=_Kind.AVAILABLE, amount=100),
    ),
    balance_snapshot: dict[_Kind, int] | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
) -> LedgerTransaction[_Kind]:
    return LedgerTransaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        kind="referral_reward_release",
        entries=entries,
        balance_snapshot=balance_snapshot
        if balance_snapshot is not None
        else {_Kind.AVAILABLE: 100, _Kind.PENDING: 0, _Kind.LIFETIME: 0},
        reference_type=reference_type,
        reference_id=reference_id,
        correlation_id=correlation_id,
    )


class TestConstruction:
    def test_required_fields_assigned(self):
        tx_id = uuid.uuid4()
        account_id = uuid.uuid4()
        entries = (LedgerEntry(kind=_Kind.AVAILABLE, amount=100),)
        snapshot = {_Kind.AVAILABLE: 100}
        tx = LedgerTransaction(
            id=tx_id,
            account_id=account_id,
            kind="referral_reward_release",
            entries=entries,
            balance_snapshot=snapshot,
        )
        assert tx.id == tx_id
        assert tx.account_id == account_id
        assert tx.kind == "referral_reward_release"
        assert tx.entries == entries
        assert tx.balance_snapshot == snapshot

    def test_empty_entries_rejected(self):
        with pytest.raises(EmptyLedgerTransactionError):
            LedgerTransaction(
                id=uuid.uuid4(),
                account_id=uuid.uuid4(),
                kind="noop",
                entries=(),
                balance_snapshot={},
            )

    def test_optional_reference_fields_default_to_none(self):
        tx = _make_tx()
        assert tx.reference_type is None
        assert tx.reference_id is None
        assert tx.correlation_id is None

    def test_occurred_at_defaults_to_utc_now(self):
        before = datetime.now(UTC)
        tx = _make_tx()
        after = datetime.now(UTC)
        assert before <= tx.occurred_at <= after

    def test_optional_reference_fields_pass_through(self):
        ref_id = uuid.uuid4()
        corr_id = uuid.uuid4()
        tx = _make_tx(
            reference_type="reward",
            reference_id=ref_id,
            correlation_id=corr_id,
        )
        assert tx.reference_type == "reward"
        assert tx.reference_id == ref_id
        assert tx.correlation_id == corr_id


class TestFrozen:
    def test_is_frozen(self):
        tx = _make_tx()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            tx.kind = "other_kind"  # ty: ignore[invalid-assignment]


# ---------------------------------------------------------------------------
# Aggregate accessors
# ---------------------------------------------------------------------------


class TestAggregateAccessors:
    def test_total_credit_sums_positive_entries_only(self):
        tx = _make_tx(
            entries=(
                LedgerEntry(kind=_Kind.AVAILABLE, amount=100),
                LedgerEntry(kind=_Kind.PENDING, amount=-30),
                LedgerEntry(kind=_Kind.LIFETIME, amount=50),
            )
        )
        assert tx.total_credit == 150  # 100 + 50

    def test_total_debit_sums_negative_entries_only(self):
        tx = _make_tx(
            entries=(
                LedgerEntry(kind=_Kind.AVAILABLE, amount=100),
                LedgerEntry(kind=_Kind.PENDING, amount=-30),
                LedgerEntry(kind=_Kind.LIFETIME, amount=-20),
            )
        )
        # debit reported as a negative integer (signed convention).
        assert tx.total_debit == -50

    def test_net_is_signed_sum_of_all_entries(self):
        tx = _make_tx(
            entries=(
                LedgerEntry(kind=_Kind.AVAILABLE, amount=100),
                LedgerEntry(kind=_Kind.PENDING, amount=-30),
            )
        )
        assert tx.net == 70

    def test_net_zero_for_pure_transfer(self):
        # ``release``: PENDING -> AVAILABLE is a wash on the net total.
        tx = _make_tx(
            entries=(
                LedgerEntry(kind=_Kind.PENDING, amount=-100),
                LedgerEntry(kind=_Kind.AVAILABLE, amount=100),
            )
        )
        assert tx.net == 0
        assert tx.total_credit == 100
        assert tx.total_debit == -100

    def test_single_credit_entry(self):
        tx = _make_tx(
            entries=(LedgerEntry(kind=_Kind.AVAILABLE, amount=100),),
        )
        assert tx.total_credit == 100
        assert tx.total_debit == 0
        assert tx.net == 100
