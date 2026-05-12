"""DobroPost gateway adapters.

Two implementations:

* ``DobroPostGatewayStub`` — deterministic UUID-based stub. Used when
  ``DOBROPOST_USE_STUB=true`` (dev / CI). No external calls.
* ``DobroPostGatewayReal`` — production adapter wrapping
  ``DobroPostHttpClient``. Reads the order's RecipientSnapshot directly
  via ``AsyncSession`` and POSTs ``/api/shipment``. Persists the
  ``int-id ↔ shipment_uuid`` bridge in ``dobropost_shipment_mappings``
  so cancel / update calls can resolve the integer id later.

Both implement ``IDobroPostGateway``. Selection happens in the Dishka
provider via ``settings.DOBROPOST_USE_STUB``.

DobroPost constraints (research §10.3):
* ``incoming_declaration`` < 16 chars (validated in domain).
* ``numberOfItemPieces`` ≤ 4 per shipment — over-budget orders log a
  warning; multi-shipment splitting is a future iteration.
"""

from __future__ import annotations

import contextlib
import hashlib
import random
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bootstrap.config import settings
from src.modules.order.application.ports import (
    IDobroPostGateway,
    IDobroPostShipmentMappingRepository,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.infrastructure.adapters.dobropost_client import (
    DobroPostHttpClient,
    build_shipment_payload,
    build_update_shipment_payload,
)
from src.modules.order.infrastructure.models import OrderModel
from shared.interfaces.logger import ILogger

logger = structlog.get_logger(__name__)


def _deterministic_uuid(seed: str) -> uuid.UUID:
    return uuid.UUID(bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16])


class DobroPostGatewayStub(IDobroPostGateway):
    """Deterministic stub — for dev / CI / contract tests."""

    def __init__(
        self,
        mapping_repo: IDobroPostShipmentMappingRepository,
        logger: ILogger,
    ) -> None:
        self._mapping_repo = mapping_repo
        self._logger = logger.bind(adapter="DobroPostGatewayStub")

    async def book_cross_border(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        incoming_declaration: str,
        idempotency_key: str,
    ) -> uuid.UUID:
        shipment_uuid = _deterministic_uuid(
            f"dobropost-stub:{order_id}:{incoming_declaration}"
        )
        # Stable pseudo-int id so cancel / update can find the row in dev.
        rng = random.Random(int.from_bytes(shipment_uuid.bytes, "big"))
        dp_id = rng.randint(10_000_000, 99_999_999)
        await self._mapping_repo.add(
            order_id=order_id,
            shipment_uuid=shipment_uuid,
            dp_shipment_id=dp_id,
            incoming_declaration=incoming_declaration,
            dp_track_number=f"DP{dp_id}",
        )
        self._logger.info(
            "dobropost.stub.book_cross_border",
            order_id=str(order_id),
            shipment_id=str(shipment_uuid),
            dp_shipment_id=dp_id,
            incoming_declaration=incoming_declaration,
            idempotency_key=idempotency_key,
        )
        return shipment_uuid

    async def cancel_cross_border(
        self, *, shipment_id: uuid.UUID, idempotency_key: str
    ) -> None:
        mapping = await self._mapping_repo.get_by_shipment_uuid(shipment_id)
        self._logger.info(
            "dobropost.stub.cancel_cross_border",
            shipment_id=str(shipment_id),
            dp_shipment_id=(mapping.dp_shipment_id if mapping else None),
            idempotency_key=idempotency_key,
        )

    async def update_recipient(
        self, *, order_id: uuid.UUID, idempotency_key: str
    ) -> None:
        mapping = await self._mapping_repo.get_by_order_id(order_id)
        self._logger.info(
            "dobropost.stub.update_recipient",
            order_id=str(order_id),
            dp_shipment_id=(mapping.dp_shipment_id if mapping else None),
            idempotency_key=idempotency_key,
        )


class DobroPostGatewayReal(IDobroPostGateway):
    """Production DobroPost adapter — invokes the HTTP API.

    Reads the order row (and its recipient snapshot) directly via
    AsyncSession to fill the customs payload. Returns a UUID derived
    from the integer DobroPost id; the integer id is also stored in
    ``dobropost_shipment_mappings`` for cancel / PUT lookups.
    """

    def __init__(
        self,
        client: DobroPostHttpClient,
        session: AsyncSession,
        mapping_repo: IDobroPostShipmentMappingRepository,
        logger: ILogger,
    ) -> None:
        self._client = client
        self._session = session
        self._mapping_repo = mapping_repo
        self._logger = logger.bind(adapter="DobroPostGatewayReal")

    async def book_cross_border(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        incoming_declaration: str,
        idempotency_key: str,
    ) -> uuid.UUID:
        row = await self._load_order(order_id)
        items_payload = [
            {
                "name": it.product_name,
                "quantity": it.quantity,
                "unit_price_amount": it.unit_price_amount,
                "currency": it.currency,
            }
            for it in row.items
        ]
        total_pieces = sum(it.quantity for it in row.items)
        if total_pieces > 4:
            self._logger.warning(
                "dobropost.book.over_4_pieces",
                order_id=str(order_id),
                pieces=total_pieces,
            )

        snapshot = self._snapshot_from_row(row)
        payload = build_shipment_payload(
            full_name_lat=snapshot.full_name_lat,
            phone=snapshot.phone,
            email=snapshot.email,
            passport_serial=snapshot.passport_serial,
            passport_number=snapshot.passport_number,
            passport_issue_date=snapshot.passport_issue_date,
            birth_date=snapshot.birth_date,
            inn=snapshot.inn,
            incoming_declaration=incoming_declaration,
            items=items_payload,
            pickup_address="",  # filled by routing engine in a future SPEC
            pickup_postcode="",
            tariff_id=settings.DOBROPOST_DEFAULT_TARIFF_ID,
        )
        response = await self._client.create_shipment(payload)
        dp_id_raw = response.get("id")
        if dp_id_raw is None:
            self._logger.error("dobropost.book.no_id", response=response)
            raise RuntimeError("DobroPost create_shipment response missing 'id'")
        try:
            dp_id = int(dp_id_raw)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"DobroPost create_shipment returned non-int id: {dp_id_raw!r}"
            ) from exc
        track = response.get("dpTrackNumber") or response.get("dptrackNumber")
        shipment_uuid = _deterministic_uuid(f"dobropost-real:{dp_id}")
        await self._mapping_repo.add(
            order_id=order_id,
            shipment_uuid=shipment_uuid,
            dp_shipment_id=dp_id,
            incoming_declaration=incoming_declaration,
            dp_track_number=str(track) if track else None,
        )
        with contextlib.suppress(Exception):
            row.cross_border_tracking = str(track or dp_id)
        self._logger.info(
            "dobropost.book.ok",
            order_id=str(order_id),
            dobropost_id=dp_id,
            shipment_uuid=str(shipment_uuid),
        )
        return shipment_uuid

    async def cancel_cross_border(
        self, *, shipment_id: uuid.UUID, idempotency_key: str
    ) -> None:
        mapping = await self._mapping_repo.get_by_shipment_uuid(shipment_id)
        if mapping is None:
            self._logger.warning(
                "dobropost.cancel.no_mapping",
                shipment_id=str(shipment_id),
            )
            return
        await self._client.delete_shipment(mapping.dp_shipment_id)
        self._logger.info(
            "dobropost.cancel.ok",
            shipment_id=str(shipment_id),
            dp_shipment_id=mapping.dp_shipment_id,
        )

    async def update_recipient(
        self, *, order_id: uuid.UUID, idempotency_key: str
    ) -> None:
        mapping = await self._mapping_repo.get_by_order_id(order_id)
        if mapping is None:
            self._logger.warning(
                "dobropost.update_recipient.no_mapping",
                order_id=str(order_id),
            )
            return
        row = await self._load_order(order_id)
        snapshot = self._snapshot_from_row(row)
        payload = build_update_shipment_payload(
            shipment_id=mapping.dp_shipment_id,
            full_name_lat=snapshot.full_name_lat,
            phone=snapshot.phone,
            email=snapshot.email,
            passport_serial=snapshot.passport_serial,
            passport_number=snapshot.passport_number,
            passport_issue_date=snapshot.passport_issue_date,
            birth_date=snapshot.birth_date,
            inn=snapshot.inn,
        )
        await self._client.update_shipment(payload)
        self._logger.info(
            "dobropost.update_recipient.ok",
            order_id=str(order_id),
            dp_shipment_id=mapping.dp_shipment_id,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_order(self, order_id: uuid.UUID) -> OrderModel:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(selectinload(OrderModel.items))
        )
        return (await self._session.execute(stmt)).scalar_one()

    @staticmethod
    def _snapshot_from_row(row: OrderModel) -> RecipientSnapshot:
        return RecipientSnapshot(
            recipient_id=str(row.recipient_id),
            full_name_ru=row.recipient_full_name_ru,
            full_name_lat=row.recipient_full_name_lat,
            phone=row.recipient_phone,
            email=row.recipient_email,
            passport_serial=row.recipient_passport_serial,
            passport_number=row.recipient_passport_number,
            passport_issue_date=row.recipient_passport_issue_date,
            birth_date=row.recipient_birth_date,
            inn=row.recipient_inn,
        )
