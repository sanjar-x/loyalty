"""SQL implementation of :class:`ILedger` for the loyalty wallet
(REFACT-001 PR-6b / ADR-006 / ADR-007).

First concrete consumer of the shared ledger kernel introduced in
PR-6a. Persists both the mutated :class:`LoyaltyAccountModel` and a
new :class:`LoyaltyTransactionModel` journal row in the same database
transaction, locks the account row via ``SELECT ... FOR UPDATE`` for
serialised concurrency, and emits exactly one
:class:`LedgerTransactionPostedEvent` on the in-memory account so the
outbox relay can fan it out.

This module is the **pattern reference** for any future ledger
consumer (cashback, supplier payouts, refund pool). To add another
consumer:

1. Declare a per-domain ``BalanceKindT`` enum (e.g.
   ``CashbackBalanceKind``).
2. Mirror this file under your module's
   ``infrastructure/repositories/``.
3. Bind the implementation as ``ILedger[YourBalanceKindT]`` in your
   provider.

ADR-007 §"What lives where" — persistence is intentionally local to
the consumer module so table names / indexes / FK constraints stay
where the business meaning lives.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.referral.domain.value_objects import LoyaltyBalanceKind
from src.modules.referral.infrastructure.models import (
    LoyaltyAccountModel,
    LoyaltyTransactionModel,
)
from shared.context import get_request_id
from shared.exceptions import NotFoundError
from shared.interfaces.logger import ILogger
from shared.ledger import (
    Account,
    EmptyLedgerTransactionError,
    ILedger,
    LedgerEntry,
    LedgerTransaction,
    LedgerTransactionPostedEvent,
)


def _new_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


class SqlLoyaltyLedger(ILedger[LoyaltyBalanceKind]):
    """Concrete loyalty-wallet ledger.

    Persists mutations atomically inside the active UoW transaction.
    The caller is responsible for the surrounding ``async with
    self._uow:``; this class never starts its own transaction — it
    only serialises one account row via ``SELECT ... FOR UPDATE``.
    """

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(adapter="SqlLoyaltyLedger")

    async def post(
        self,
        *,
        account: Account[LoyaltyBalanceKind],
        kind: str,
        entries: Sequence[LedgerEntry[LoyaltyBalanceKind]],
        reference_type: str | None = None,
        reference_id: uuid.UUID | None = None,
    ) -> LedgerTransaction[LoyaltyBalanceKind]:
        if not entries:
            raise EmptyLedgerTransactionError()

        # 1. Lock the account row (serialised by row-level FOR UPDATE).
        stmt = (
            select(LoyaltyAccountModel)
            .where(LoyaltyAccountModel.id == account.id)
            .with_for_update()
        )
        orm_account = (await self._session.execute(stmt)).scalar_one_or_none()
        if orm_account is None:
            raise NotFoundError(
                message=f"Loyalty account {account.id} does not exist",
                error_code="LOYALTY_ACCOUNT_NOT_FOUND",
                details={"account_id": str(account.id)},
            )

        # 2. Apply each entry to the in-memory Account; signed amount
        #    routes through credit/debit (kernel rejects zero entries
        #    at LedgerEntry construction).
        for entry in entries:
            if entry.amount > 0:
                account.credit(entry.kind, entry.amount)
            else:
                account.debit(entry.kind, -entry.amount)

        # 3. Build the journal transaction with the post-mutation snapshot.
        snapshot = account.balance.snapshot()
        request_id = get_request_id()
        correlation_id_str = (
            request_id if request_id and request_id != "UNKNOWN" else None
        )

        tx = LedgerTransaction[LoyaltyBalanceKind](
            id=_new_id(),
            account_id=account.id,
            kind=kind,
            entries=tuple(entries),
            balance_snapshot=snapshot,
            reference_type=reference_type,
            reference_id=reference_id,
            # Kernel types correlation_id as UUID; the request-context
            # ID is an opaque string so we leave the kernel field None
            # and persist the original string on the ORM row below.
            correlation_id=None,
        )

        # 4. Push the in-memory Account state onto the ORM row.
        orm_account.available_kopecks = account.amount(LoyaltyBalanceKind.AVAILABLE)
        orm_account.pending_kopecks = account.amount(LoyaltyBalanceKind.PENDING)
        orm_account.lifetime_kopecks = account.amount(LoyaltyBalanceKind.LIFETIME)
        orm_account.version = account.version + 1
        orm_account.updated_at = datetime.now(UTC)

        # 5. Persist the journal row. Per-bucket deltas + post-mutation
        #    balances are unrolled into named columns for direct SQL
        #    reconciliation; the generic kernel snapshot is reconstructed
        #    on read.
        orm_tx = LoyaltyTransactionModel(
            id=tx.id,
            account_id=tx.account_id,
            kind=tx.kind,
            amount_available_delta=sum(
                e.amount for e in entries if e.kind == LoyaltyBalanceKind.AVAILABLE
            ),
            amount_pending_delta=sum(
                e.amount for e in entries if e.kind == LoyaltyBalanceKind.PENDING
            ),
            amount_lifetime_delta=sum(
                e.amount for e in entries if e.kind == LoyaltyBalanceKind.LIFETIME
            ),
            balance_after_available=snapshot.get(LoyaltyBalanceKind.AVAILABLE, 0),
            balance_after_pending=snapshot.get(LoyaltyBalanceKind.PENDING, 0),
            balance_after_lifetime=snapshot.get(LoyaltyBalanceKind.LIFETIME, 0),
            reference_type=tx.reference_type,
            reference_id=tx.reference_id,
            correlation_id=correlation_id_str,
        )
        self._session.add(orm_tx)
        await self._session.flush()

        # 6. Sync the in-memory Account.version to what we just wrote so
        #    a subsequent post() in the same transaction sees the new
        #    value.
        account.version += 1

        # 7. Emit exactly one LedgerTransactionPostedEvent per call so
        #    the outbox relay can fan it out (analytics / audit / UI
        #    notifications). Account is the aggregate (write boundary),
        #    not the transaction (a row owned by the account).
        account.add_domain_event(
            LedgerTransactionPostedEvent(
                transaction_id=tx.id,
                account_id=tx.account_id,
                transaction_kind=tx.kind,
                net_amount=tx.net,
                correlation_id=tx.correlation_id,
            )
        )

        self._logger.info(
            "loyalty_ledger.posted",
            account_id=str(tx.account_id),
            transaction_id=str(tx.id),
            kind=tx.kind,
            net_amount=tx.net,
            entry_count=len(entries),
        )
        return tx
