"""Command handler: persist DobroPost passport-validation failure.

Wired into the webhook router as a special branch (the generic
``IngestTrackingHandler`` path doesn't fit — passport validation is a
side-channel, not a tracking event). Looks up the affected ``Shipment``
by DobroPost id and calls :py:meth:`Shipment.flag_passport_validation_failed`,
which records the cause on the aggregate and emits
:class:`ShipmentPassportValidationFailedEvent` via the outbox so a
future CS-notification consumer can react.

The command is idempotent: repeated invocations re-emit the event
(intentional — operators may have closed the previous CS ticket and
need a fresh notification), but the shipment's ``failure_reason``
write is a no-op if already set to the same value.

Also exports :func:`extract_passport_failure_id` — a payload classifier
used by the webhook router to decide which branch (this handler vs the
generic tracking ingest) to dispatch into. Keeping the classifier in
application layer (next to the command) avoids a presentation→infrastructure
import — boundary tests forbid that direction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.value_objects import PROVIDER_DOBROPOST
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


def extract_passport_failure_id(body: bytes) -> int | None:
    """Detect a DobroPost passport-validation **failure** payload.

    Returns the DobroPost ``shipmentId`` (positive int) iff the body
    is a passport-validation webhook with
    ``passportValidationStatus = false``. ``None`` for any other
    shape (status update, passport passed, malformed JSON, etc.) so
    the router falls through to the generic tracking-ingest path.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError, ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    if "passportValidationStatus" not in payload:
        return None
    if bool(payload.get("passportValidationStatus")):
        return None
    shipment_id = payload.get("shipmentId")
    if not isinstance(shipment_id, int) or shipment_id <= 0:
        return None
    return shipment_id


@dataclass(frozen=True)
class HandleDobroPostPassportValidationCommand:
    """Input from ``DobroPostWebhookAdapter._handle_passport_validation``.

    Attributes:
        dp_shipment_id: DobroPost numeric shipment id (the ``id`` field
            from ``POST /api/shipment`` response, stored on the
            ``Shipment`` as ``provider_shipment_id``).
    """

    dp_shipment_id: int


class HandleDobroPostPassportValidationHandler:
    """Persist passport-validation failure on the local Shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._uow = uow
        self._logger = logger.bind(handler="HandleDobroPostPassportValidationHandler")

    async def handle(self, command: HandleDobroPostPassportValidationCommand) -> None:
        async with self._uow:
            shipment = await self._shipment_repo.get_by_provider_shipment_id(
                provider_code=PROVIDER_DOBROPOST,
                provider_shipment_id=str(command.dp_shipment_id),
            )
            if shipment is None:
                # Not raising — webhook router swallows ShipmentNotFoundError
                # to avoid carrier retry storms. Logged loud so operators
                # notice mismatched cross-tenant deliveries.
                self._logger.warning(
                    "Passport-validation webhook for unknown shipment",
                    dp_shipment_id=command.dp_shipment_id,
                )
                raise ShipmentNotFoundError(
                    details={
                        "provider_code": PROVIDER_DOBROPOST,
                        "provider_shipment_id": str(command.dp_shipment_id),
                    }
                )
            shipment.flag_passport_validation_failed()
            await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Passport-validation failure flagged",
            shipment_id=str(shipment.id),
            dp_shipment_id=command.dp_shipment_id,
        )
