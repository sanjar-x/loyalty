"""Command: refresh the recipient + passport snapshots on an ON_HOLD order.

Used when the customer has corrected the passport details (now on the
:class:`Passport` aggregate — ADR-011) or the recipient profile (name /
phone / email on the :class:`Recipient` aggregate) and wants to retry
cross-border processing. The order remains ON_HOLD — the caller is
expected to follow up with ``ResumeOrder`` once the upstream system
reports the data is valid (DobroPost passport-webhook will also
re-trigger validation automatically).

Allowed only when the order is ON_HOLD with reason=PASSPORT_INVALID
(domain check inside ``Order.refresh_recipient_snapshot``).

After the snapshot is committed locally, the handler invokes
``IDobroPostGateway.update_recipient`` so the corrected payload is
pushed to DobroPost (PUT /api/shipment) for re-validation. Failures of
the upstream call are logged but do not roll back the local commit;
the customer can retry — the local state of the snapshots is the
source of truth.
"""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.application.ports import IDobroPostGateway
from src.modules.order.domain.exceptions import (
    CrossBorderProviderError,
    OrderNotFoundError,
)
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
    IPassportLookup,
    IRecipientLookup,
)
from src.modules.order.domain.recipient_snapshot import (
    PassportSnapshot,
    RecipientSnapshot,
)
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RefreshRecipientSnapshotCommand:
    order_id: uuid.UUID
    identity_id: uuid.UUID | None  # None for admin / system actor


class RefreshRecipientSnapshotHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        recipient_lookup: IRecipientLookup,
        passport_lookup: IPassportLookup,
        history_writer: IOrderStateHistoryWriter,
        dobropost_gateway: IDobroPostGateway,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._recipient_lookup = recipient_lookup
        self._passport_lookup = passport_lookup
        self._history = history_writer
        self._dobropost = dobropost_gateway
        self._uow = uow
        self._logger = logger.bind(handler="RefreshRecipientSnapshotHandler")

    async def handle(self, command: RefreshRecipientSnapshotCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if (
                command.identity_id is not None
                and order.identity_id != command.identity_id
            ):
                raise OrderNotFoundError(order_id=str(command.order_id))

            recipient_id = uuid.UUID(order.recipient_snapshot.recipient_id)
            recipient = await self._recipient_lookup.get(recipient_id)
            if recipient is None or recipient.is_archived:
                raise UnprocessableEntityError(
                    message="Recipient not found or archived",
                    error_code="ORDER_RECIPIENT_INVALID",
                    details={"recipient_id": str(recipient_id)},
                )

            fresh_recipient = RecipientSnapshot(
                recipient_id=str(recipient.recipient_id),
                full_name_ru=recipient.full_name_ru,
                full_name_lat=recipient.full_name_lat,
                phone=recipient.phone,
                email=recipient.email,
            )

            # ADR-011 — refresh the passport snapshot too when the order
            # has one attached. PASSPORT_INVALID holds typically need a
            # passport correction (DaData / DobroPost rejected the
            # customs payload), so re-snapshotting only the recipient
            # would leave the order in the same broken state.
            fresh_passport: PassportSnapshot | None = None
            if order.passport_id is not None:
                passport = await self._passport_lookup.get(order.passport_id)
                if passport is None or passport.is_archived:
                    raise UnprocessableEntityError(
                        message="Passport not found or archived",
                        error_code="ORDER_PASSPORT_INVALID",
                        details={"passport_id": str(order.passport_id)},
                    )
                fresh_passport = PassportSnapshot(
                    passport_id=str(passport.passport_id),
                    full_name_ru=passport.full_name_ru,
                    full_name_lat=passport.full_name_lat,
                    passport_serial=passport.passport_serial,
                    passport_number=passport.passport_number,
                    passport_issue_date=passport.passport_issue_date,
                    birth_date=passport.birth_date,
                    inn=passport.inn,
                    validation_status=passport.validation_status,
                )

            pre = order.status
            order.refresh_recipient_snapshot(
                fresh_recipient, passport_snapshot=fresh_passport
            )
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type=("customer" if command.identity_id else "manager"),
                    actor_id=str(command.identity_id or "admin"),
                ),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()

        # PUT /api/shipment runs *after* the local commit so a DobroPost
        # outage doesn't block the customer's retry. The customer can
        # always invoke this command again (it's idempotent at the
        # business level — the same RecipientSnapshot is pushed).
        try:
            await self._dobropost.update_recipient(
                order_id=command.order_id,
                idempotency_key=f"refresh-recipient:{command.order_id}",
            )
        except CrossBorderProviderError as exc:
            self._logger.warning(
                "order.recipient_refresh.upstream_failed",
                order_id=str(command.order_id),
                reason=str(exc),
            )
        self._logger.info(
            "order.recipient_snapshot_refreshed",
            order_id=str(command.order_id),
        )
