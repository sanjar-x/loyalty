"""Domain events emitted by the ledger.

The shared ledger emits a single :class:`LedgerTransactionPostedEvent`
per successful ``Ledger.post`` call. Aggregate is the **account** (the
write boundary), not the transaction (which is one row in the journal
that the account owns).

Consumer modules subscribe to this event when they need to react to
balance changes — analytics, audit dashboards, customer-support
notifications. The event payload carries enough context to dispatch
without re-reading the ledger.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class LedgerEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all shared-ledger events."""

    aggregate_type: str = "ledger_account"


@dataclass(frozen=True)
class LedgerTransactionPostedEvent(
    LedgerEvent,
    required_fields=("transaction_id", "account_id"),
    aggregate_id_field="account_id",
):
    """Emitted after a transaction is successfully posted.

    Carried fields:

    * ``transaction_id`` — the new transaction's ID.
    * ``account_id`` — the affected account's ID (also the aggregate ID).
    * ``transaction_kind`` — discriminator (``"referral_reward_release"``,
      ``"order_spend"``, ...).
    * ``net_amount`` — signed sum of the entry amounts. A consumer can
      use this for a quick "credit/debit/wash" classification without
      re-reading the entries.
    * ``correlation_id`` — copied from the transaction for trace-linkage.
    """

    transaction_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None
    transaction_kind: str = ""
    net_amount: int = 0
    correlation_id: uuid.UUID | None = None
    event_type: str = "LedgerTransactionPostedEvent"
