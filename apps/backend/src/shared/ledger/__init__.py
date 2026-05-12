"""Generic double-entry ledger (shared kernel).

The kernel provides:

* :class:`Balance` — multi-bucket integer accumulator generic over a
  consumer-supplied ``BalanceKindT`` enum.
* :class:`Account` — aggregate root that owns a :class:`Balance` and
  forwards mutations through it.
* :class:`LedgerEntry` / :class:`LedgerTransaction` — the immutable
  journal-entry pair (multi-entry ⇒ multi-bucket atomic moves).
* :class:`ILedger` — the outbound port that consumer modules implement
  in their ``infrastructure`` layer to persist accounts and
  transactions.
* :class:`LedgerTransactionPostedEvent` — single domain event emitted
  per successful post.
* A small exception hierarchy
  (:class:`LedgerError`, :class:`InsufficientBalanceError`,
  :class:`InvalidLedgerEntryError`,
  :class:`EmptyLedgerTransactionError`).

Persistence (table names, indexes, FK constraints) is intentionally
**not** part of this kernel — it belongs to whichever module owns the
business meaning of the accounts. The same generic ``ILedger`` and
domain types are reused by ``referral`` (loyalty wallet), and will be
reused by future modules (cashback, supplier payouts, refund pool, …)
without per-module re-invention.
"""

from src.shared.ledger.account import Account
from src.shared.ledger.balance import Balance, BalanceKindT
from src.shared.ledger.events import LedgerEvent, LedgerTransactionPostedEvent
from src.shared.ledger.exceptions import (
    EmptyLedgerTransactionError,
    InsufficientBalanceError,
    InvalidLedgerEntryError,
    LedgerError,
)
from src.shared.ledger.ports import ILedger
from src.shared.ledger.transaction import LedgerEntry, LedgerTransaction

__all__ = [
    "Account",
    "Balance",
    "BalanceKindT",
    "EmptyLedgerTransactionError",
    "ILedger",
    "InsufficientBalanceError",
    "InvalidLedgerEntryError",
    "LedgerEntry",
    "LedgerError",
    "LedgerEvent",
    "LedgerTransaction",
    "LedgerTransactionPostedEvent",
]
