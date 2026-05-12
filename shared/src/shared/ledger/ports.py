"""Outbound ports (Hexagonal Architecture) for the ledger.

The :class:`ILedger` protocol is the single interface command handlers
depend on to credit/debit/transfer balances. Implementations live in
each consumer module's ``infrastructure`` layer (so that table names,
indexes, and SQL dialects are local to the module that owns the
account schema), but the contract is shared so that the same handler
can run against the loyalty ledger, a future cashback ledger, or a
test stub without code duplication.

A typical implementation:

1. Locks the account row (``SELECT ... FOR UPDATE``).
2. Applies the entries via :meth:`Account.credit/debit/transfer`.
3. Builds a new :class:`LedgerTransaction` carrying the post-mutation
   balance snapshot.
4. Persists the account update + the transaction row in the same
   database transaction (Unit-of-Work boundary).
5. Emits :class:`LedgerTransactionPostedEvent` via the account's
   ``add_domain_event`` so that the outbox relay can fan it out.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Generic, Protocol

from shared.ledger.account import Account
from shared.ledger.balance import BalanceKindT
from shared.ledger.transaction import LedgerEntry, LedgerTransaction


class ILedger(Protocol, Generic[BalanceKindT]):
    """Append-only double-entry ledger boundary.

    Implementations MUST:

    * apply ``entries`` atomically (all or nothing);
    * persist the post-mutation :class:`Account` and the new
      :class:`LedgerTransaction` in the same database transaction;
    * advance ``Account.version`` by one;
    * emit exactly one :class:`LedgerTransactionPostedEvent` per call;
    * preserve ``correlation_id`` end-to-end (request → transaction
      → outbox message).
    """

    async def post(
        self,
        *,
        account: Account[BalanceKindT],
        kind: str,
        entries: Sequence[LedgerEntry[BalanceKindT]],
        reference_type: str | None = None,
        reference_id: uuid.UUID | None = None,
    ) -> LedgerTransaction[BalanceKindT]:
        """Apply ``entries`` to ``account`` and persist a new transaction.

        Args:
            account: The account being mutated.
            kind: Free-form discriminator naming the financial event.
            entries: One or more :class:`LedgerEntry` rows.
            reference_type: Originating-entity discriminator
                (``"reward"`` / ``"order"`` / ...). Optional for
                system-level adjustments.
            reference_id: Originating-entity identifier. Optional.

        Returns:
            The newly persisted :class:`LedgerTransaction`.

        Raises:
            InsufficientBalanceError: a debit would push a non-negative
                kind below zero.
            EmptyLedgerTransactionError: ``entries`` was empty.
        """
        ...
