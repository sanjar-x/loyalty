"""Generic :class:`Account` aggregate.

A ledger account is owned by some external entity (a Customer, a
Supplier, an internal float, ...) and carries a :class:`Balance` typed
over a domain-specific ``BalanceKindT``.

The account is the **write boundary**: every state change to the
balances goes through ``credit`` / ``debit`` / ``transfer`` so that
domain events accumulate uniformly in :attr:`AggregateRoot.domain_events`.
The matching journal entries live in :class:`LedgerTransaction` and are
posted by an :class:`ILedger` implementation in the infrastructure
layer — the account itself never mutates a transaction list.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Generic

import attrs

from src.shared.interfaces.entities import AggregateRoot
from src.shared.ledger.balance import Balance, BalanceKindT


@attrs.define
class Account(AggregateRoot, Generic[BalanceKindT]):
    """Ledger account aggregate root.

    Attributes:
        id: Stable account identifier (UUID; usually uuid7 for keyset
            ordering, but the kernel does not enforce a specific UUID
            version).
        owner_type: Discriminator for the entity that owns this account
            ("customer", "supplier", "system", ...). Used by consumer
            modules to route lookups by owner.
        owner_id: External owner identifier.
        currency: ISO-4217 currency code; ledgers in different
            currencies are kept on separate accounts so that arithmetic
            is unambiguous.
        balance: Multi-bucket per-kind running totals.
        version: Optimistic-locking counter — repositories check it on
            update and bump it on persist.
        created_at: UTC timestamp.
        updated_at: UTC timestamp; advanced by every successful mutation.
    """

    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    currency: str
    balance: Balance[BalanceKindT]
    version: int = 0
    created_at: datetime = attrs.Factory(lambda: datetime.now(UTC))
    updated_at: datetime = attrs.Factory(lambda: datetime.now(UTC))

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def amount(self, kind: BalanceKindT) -> int:
        """Shortcut for ``self.balance.get(kind)``."""
        return self.balance.get(kind)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def credit(self, kind: BalanceKindT, amount: int) -> None:
        """Add ``amount`` to the named balance kind.

        Bumps :attr:`updated_at`. Domain-event emission is the
        responsibility of the caller (e.g. ``Ledger.post`` emits a
        single :class:`LedgerTransactionPostedEvent` per transaction
        rather than one event per entry).
        """
        self.balance.credit(kind, amount)
        self._touch()

    def debit(self, kind: BalanceKindT, amount: int) -> None:
        """Subtract ``amount`` from the named balance kind."""
        self.balance.debit(kind, amount)
        self._touch()

    def transfer(
        self,
        *,
        from_kind: BalanceKindT,
        to_kind: BalanceKindT,
        amount: int,
    ) -> None:
        """Move ``amount`` from one balance kind to another atomically."""
        self.balance.transfer(from_kind=from_kind, to_kind=to_kind, amount=amount)
        self._touch()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)
