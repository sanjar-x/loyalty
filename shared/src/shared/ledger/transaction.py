"""Append-only ledger transaction (journal entry).

A :class:`LedgerTransaction` is the immutable record of a single
posting against an :class:`Account`. Every transaction carries:

* one or more :class:`LedgerEntry` rows (the per-kind deltas applied);
* a :class:`Balance` snapshot taken **after** the entries were applied
  (so reconciliation does not need to replay history);
* a discriminator string (``kind``) classifying the financial event
  ("referral_reward_release", "order_spend", "manual_adjustment", ...);
* an optional reference tuple (``reference_type``, ``reference_id``)
  that points at the originating domain entity (a reward, an order,
  a refund, ...);
* a ``correlation_id`` for distributed-tracing log linkage.

Transactions are **frozen**. Any state change requires a new transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Generic

import attrs

from shared.ledger.balance import BalanceKindT
from shared.ledger.exceptions import (
    EmptyLedgerTransactionError,
    InvalidLedgerEntryError,
)


@attrs.frozen
class LedgerEntry(Generic[BalanceKindT]):
    """Single signed delta applied to a single balance kind.

    Multiple entries on the same :class:`LedgerTransaction` model multi-
    bucket moves (e.g. credit ``available`` + debit ``pending`` in one
    atomic ``release`` operation).

    Attributes:
        kind: Which balance kind is affected.
        amount: Signed delta. Positive = credit, negative = debit.
            Zero is rejected at construction — empty entries are bugs,
            not no-ops.
    """

    kind: BalanceKindT
    amount: int

    def __attrs_post_init__(self) -> None:
        if self.amount == 0:
            raise InvalidLedgerEntryError(reason="amount must be non-zero")


@attrs.frozen
class LedgerTransaction(Generic[BalanceKindT]):
    """Single posted journal entry — atomic, append-only.

    Attributes:
        id: Stable transaction identifier (uuid7 recommended for
            keyset-ordered listings).
        account_id: The :class:`Account` the entries were applied to.
        kind: Free-form discriminator naming the financial event
            (e.g. ``"referral_reward_release"``).
        entries: One or more :class:`LedgerEntry` rows. Empty
            transactions are rejected at construction.
        balance_snapshot: Per-kind running totals **after** this
            transaction was applied. Persisted alongside the row so
            that reconciliation, customer-support drilldown and
            offline replay never have to rebuild balances by summation.
        reference_type: Free-form discriminator for the originating
            entity (``"reward"`` / ``"order"`` / ``"refund"`` / ...).
        reference_id: Identifier of the originating entity; ``None``
            for system-level adjustments.
        correlation_id: Request-context correlation ID propagated from
            the caller (matches the value that ends up on the
            corresponding :class:`OutboxMessage`).
        occurred_at: UTC timestamp when the transaction was posted.
    """

    id: uuid.UUID
    account_id: uuid.UUID
    kind: str
    entries: tuple[LedgerEntry[BalanceKindT], ...]
    balance_snapshot: Mapping[BalanceKindT, int]
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None
    occurred_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))

    def __attrs_post_init__(self) -> None:
        if not self.entries:
            raise EmptyLedgerTransactionError()

    # ------------------------------------------------------------------
    # Convenience read accessors
    # ------------------------------------------------------------------

    @property
    def total_credit(self) -> int:
        """Sum of all positive entry amounts."""
        return sum(entry.amount for entry in self.entries if entry.amount > 0)

    @property
    def total_debit(self) -> int:
        """Sum of all negative entry amounts (returned as a negative integer)."""
        return sum(entry.amount for entry in self.entries if entry.amount < 0)

    @property
    def net(self) -> int:
        """Net effect of this transaction across all balance kinds."""
        return sum(entry.amount for entry in self.entries)
