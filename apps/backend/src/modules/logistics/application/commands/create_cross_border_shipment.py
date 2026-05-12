"""Command handler: create + book a DobroPost cross-border shipment.

Admin-managed flow (no customer-facing rate calc, no DeliveryQuote):

1. Manager buys the item from a Chinese marketplace (external).
2. Manager pastes the China track number (``incomingDeclaration``)
   into admin UI and submits this command.
3. Handler creates a ``Shipment`` aggregate via
   ``Shipment.create_admin_managed`` (DRAFT) and books it through
   ``DobroPostBookingProvider`` (one synchronous call — DobroPost's
   ``POST /api/shipment`` returns the full shipment with ``id`` +
   ``dptrackNumber`` immediately).
4. Resulting shipment ends in BOOKED with ``provider_shipment_id`` =
   DobroPost numeric id (stringified) and ``tracking_number`` =
   ``dptrackNumber``.

Two-phase pattern (DB → external → DB) keeps the carrier call outside
the database transaction — same shape as ``BookShipmentHandler``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.commands.dobropost_payload import (
    DobroPostShipmentPayload,
)
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.exceptions import (
    BookingError,
    ProviderUnavailableError,
)
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_DOBROPOST,
    Address,
    BookingRequest,
    ContactInfo,
    DeliveryType,
    Money,
    Parcel,
    Weight,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateCrossBorderShipmentCommand:
    """Admin-supplied input for procurement of a cross-border order.

    Attributes:
        order_id: Loyality order id (cross-module reference; will be
            resolved by the order module when implemented).
        payload: Typed DobroPost-specific data (passport, item, tariff,
            China track). Validated by the dataclass at construction.
        sender: Loyality warehouse / partner contact at DobroPost
            drop-off in China. Comes from
            ``IOriginAddressResolver`` config in production.
        warehouse_address: DobroPost China warehouse where the parcel
            is dropped off — origin of the cross-border shipment.
        destination_address: RU customs / DobroPost RF warehouse — the
            *cross-border* destination, NOT the customer's pickup
            point. Last-mile shipment carries the actual customer
            destination.
        recipient_contact: Customer contact info (name + phone) — used
            for tracking notifications. Passport / address inside
            ``payload.recipient`` is the canonical customs identity.
        quoted_cost_minor_units: Pre-computed margin-aware shipping
            cost in RUB minor units (kopecks) from pricing module.
            Stored on the Shipment for drift detection.
        parcel_weight_grams: Estimated parcel weight from
            ``ISkuWeightResolver`` (catalog category × pricing
            ``weight_g``) — must match the value the customer was
            quoted on so any future drift comparison stays
            meaningful. DobroPost itself charges by ``dpTariffId``,
            so this number does not affect carrier billing — it is
            kept purely for Loyality-side audit / pricing alignment.
    """

    order_id: uuid.UUID
    payload: DobroPostShipmentPayload
    sender: ContactInfo
    warehouse_address: Address
    destination_address: Address
    recipient_contact: ContactInfo
    quoted_cost_minor_units: int
    parcel_weight_grams: int

    def __post_init__(self) -> None:
        if self.quoted_cost_minor_units < 0:
            raise ValueError("quoted_cost_minor_units must be non-negative")
        if self.parcel_weight_grams <= 0:
            raise ValueError("parcel_weight_grams must be positive")


@dataclass(frozen=True)
class CreateCrossBorderShipmentResult:
    """Output of ``CreateCrossBorderShipmentHandler``."""

    shipment_id: uuid.UUID
    provider_shipment_id: str
    tracking_number: str | None


class CreateCrossBorderShipmentHandler:
    """Create + book a cross-border (DobroPost) shipment in one shot."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._uow = uow
        self._logger = logger.bind(handler="CreateCrossBorderShipmentHandler")

    async def handle(
        self, command: CreateCrossBorderShipmentCommand
    ) -> CreateCrossBorderShipmentResult:
        # Phase 1: persist DRAFT → BOOKING_PENDING
        async with self._uow:
            shipment = Shipment.create_admin_managed(
                provider_code=PROVIDER_DOBROPOST,
                service_code=str(command.payload.dp_tariff_id),
                delivery_type=DeliveryType.PICKUP_POINT,
                origin=command.warehouse_address,
                destination=command.destination_address,
                sender=command.sender,
                recipient=command.recipient_contact,
                parcels=[
                    Parcel(
                        weight=Weight(grams=command.parcel_weight_grams),
                        description=command.payload.item.description,
                    )
                ],
                quoted_cost=Money(
                    amount=command.quoted_cost_minor_units, currency_code="RUB"
                ),
                provider_payload=command.payload.to_json(),
                order_id=command.order_id,
            )
            shipment.mark_booking_pending()
            shipment = await self._shipment_repo.add(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        # Phase 2: call DobroPost outside the DB transaction.
        booking_provider = self._registry.get_booking_provider(PROVIDER_DOBROPOST)
        booking_request = BookingRequest(
            shipment_id=shipment.id,
            origin=shipment.origin,
            destination=shipment.destination,
            sender=shipment.sender,
            recipient=shipment.recipient,
            parcels=shipment.parcels,
            service_code=shipment.service_code,
            delivery_type=shipment.delivery_type,
            provider_payload=shipment.provider_payload or "",
        )

        try:
            result = await booking_provider.book_shipment(booking_request)
        except ValidationError:
            # 4xx from DobroPost — operator-correctable input. The
            # shipment was never accepted at the carrier, so we
            # short-circuit to FAILED locally and rethrow the typed
            # 400 to the admin caller (NOT 502).
            await self._mark_shipment_failed(shipment.id, reason="validation_error")
            raise
        except ProviderUnavailableError:
            # 5xx / transport — transient. Same local FAILED transition,
            # but caller sees 503 so they know to retry.
            await self._mark_shipment_failed(shipment.id, reason="provider_unavailable")
            raise
        except Exception as exc:
            # Unknown — preserve historical behaviour: log + FAILED + 502.
            self._logger.error(
                "DobroPost booking failed (unknown error)",
                shipment_id=str(shipment.id),
                error=str(exc),
            )
            await self._mark_shipment_failed(shipment.id, reason=str(exc))
            raise BookingError(
                message=f"DobroPost booking failed: {exc}",
                details={"shipment_id": str(shipment.id)},
            ) from exc

        # Phase 3: persist BOOKED.
        async with self._uow:
            refreshed = await self._shipment_repo.get_by_id(shipment.id)
            if refreshed is None:
                # Race with parallel mutation — extremely unlikely.
                self._logger.error(
                    "Shipment vanished between booking and persist",
                    shipment_id=str(shipment.id),
                )
                raise BookingError(
                    message="Shipment disappeared during DobroPost booking",
                    details={"shipment_id": str(shipment.id)},
                )

            refreshed.mark_booked(
                provider_shipment_id=result.provider_shipment_id,
                tracking_number=result.tracking_number,
                estimated_delivery=result.estimated_delivery,
            )
            await self._shipment_repo.update(refreshed)
            self._uow.register_aggregate(refreshed)
            await self._uow.commit()

        self._logger.info(
            "Cross-border shipment booked",
            shipment_id=str(shipment.id),
            provider_shipment_id=result.provider_shipment_id,
            dp_track=result.tracking_number,
            incoming_declaration=command.payload.incoming_declaration,
        )
        return CreateCrossBorderShipmentResult(
            shipment_id=shipment.id,
            provider_shipment_id=result.provider_shipment_id,
            tracking_number=result.tracking_number,
        )

    async def _mark_shipment_failed(
        self, shipment_id: uuid.UUID, *, reason: str
    ) -> None:
        """Persist BOOKING_PENDING → FAILED in its own UoW.

        Used by every error branch in :py:meth:`handle` so the local FSM
        stays consistent regardless of which exception was raised by the
        provider adapter. Idempotent against an already-FAILED shipment.
        """
        async with self._uow:
            refreshed = await self._shipment_repo.get_by_id(shipment_id)
            if refreshed is None:
                self._logger.error(
                    "Shipment vanished while marking failed",
                    shipment_id=str(shipment_id),
                )
                return
            refreshed.mark_booking_failed(reason=reason)
            await self._shipment_repo.update(refreshed)
            self._uow.register_aggregate(refreshed)
            await self._uow.commit()
