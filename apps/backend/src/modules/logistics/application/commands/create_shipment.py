"""Command handler: create a new Shipment in DRAFT status.

Reads the trusted server-side ``DeliveryQuote`` and resolves the
shipment's address / parcel / sender data from the same server-side
sources the quote was built from:

* ``IPickupPointResolver`` → destination ``Address`` (the cached
  pickup-point response, no extra provider call).
* ``IOriginAddressResolver`` → sender warehouse ``Address`` from
  ``ProviderAccountModel.config_json``.
* The ``Parcel`` weight stored on the quote (we keep a denormalised
  copy on the quote at /rates/quote time so the booking call has the
  exact same value the customer was priced against).

The frontend never re-sends destination, origin, weight or sender —
those would be tampering vectors per BRD §Constraints "Цена доставки
фиксируется в DeliveryQuote".
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.logistics.application.dto import CreateShipmentResult
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.exceptions import (
    QuoteExpiredError,
    QuoteNotFoundError,
)
from src.modules.logistics.domain.interfaces import (
    IDeliveryQuoteRepository,
    IOriginAddressResolver,
    IPickupPointResolver,
    IShipmentRepository,
)
from src.modules.logistics.domain.value_objects import (
    CashOnDelivery,
    ContactInfo,
    Parcel,
    Weight,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

# Hard floor — must match ``PricingWeightAdapter._FALLBACK_DEFAULT_GRAMS``.
# Used only when the persisted quote payload was written by an older
# code path that didn't snapshot the parcel weight.
_FALLBACK_PARCEL_GRAMS = 500


@dataclass(frozen=True)
class CreateShipmentCommand:
    """Input for creating a new shipment from a selected quote.

    Attributes:
        quote_id: Server-side quote identifier (from /rates/quote).
        recipient: Buyer contact details (typed at checkout).
        order_id: Optional caller correlation id (cart / order id).
        cod: Optional cash-on-delivery override (defaults to none —
            assumes the order is already paid online).
    """

    quote_id: uuid.UUID
    recipient: ContactInfo
    order_id: uuid.UUID | None = None
    cod: CashOnDelivery | None = None


__all__ = ["CreateShipmentCommand", "CreateShipmentHandler", "CreateShipmentResult"]


class CreateShipmentHandler:
    """Create a new Shipment in DRAFT status from a server-side quote."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        quote_repo: IDeliveryQuoteRepository,
        pickup_point_resolver: IPickupPointResolver,
        origin_resolver: IOriginAddressResolver,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._quote_repo = quote_repo
        self._pickup_point_resolver = pickup_point_resolver
        self._origin_resolver = origin_resolver
        self._uow = uow
        self._logger = logger.bind(handler="CreateShipmentHandler")

    async def handle(self, command: CreateShipmentCommand) -> CreateShipmentResult:
        """Validate the trusted quote, resolve every field server-side, persist DRAFT."""
        quote = await self._quote_repo.get_by_id(command.quote_id)
        if quote is None:
            raise QuoteNotFoundError(quote_id=command.quote_id)

        if quote.expires_at is not None and quote.expires_at < datetime.now(UTC):
            raise QuoteExpiredError(
                quote_id=command.quote_id,
                expires_at=quote.expires_at,
            )

        provider_code = quote.rate.provider_code
        payload = _decode_provider_payload(quote.provider_payload)

        destination, sender = await self._resolve_destination(
            provider_code=provider_code,
            payload=payload,
        )
        origin = await self._origin_resolver.resolve(provider_code)
        sender = sender or _origin_to_sender(origin)

        parcel = _build_parcel_from_payload(payload)

        async with self._uow:
            shipment = Shipment.create(
                quote=quote,
                origin=origin,
                destination=destination,
                sender=sender,
                recipient=command.recipient,
                parcels=[parcel],
                order_id=command.order_id,
                cod=command.cod,
            )
            shipment = await self._shipment_repo.add(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Shipment created",
            shipment_id=str(shipment.id),
            provider=provider_code,
        )
        return CreateShipmentResult(shipment_id=shipment.id)

    async def _resolve_destination(
        self,
        *,
        provider_code: str,
        payload: dict,
    ):
        """Resolve destination ``Address`` and (optional) point operator contact.

        Pulls the pickup-point ``external_id`` written into the quote's
        ``provider_payload`` at /rates/quote time. The resolver hits the
        cached pickup-point response (Redis, 24h TTL) — no extra
        provider call.
        """
        external_id = payload.get("pickup_point_external_id")
        if not external_id:
            raise ValidationError(
                message=(
                    "Quote was not built against a pickup point — "
                    "courier-mode shipments are not supported via this endpoint."
                ),
                details={"provider_code": provider_code},
            )
        point = await self._pickup_point_resolver.resolve(
            provider_code=provider_code,
            external_id=external_id,
        )
        if point is None:
            raise ValidationError(
                message=(
                    "Pickup point referenced by the quote is no longer cached. "
                    "Re-list /pickup-points and request a fresh /rates/quote."
                ),
                details={
                    "provider_code": provider_code,
                    "pickup_point_external_id": external_id,
                },
            )
        # We do not surface the point-operator contact as the sender —
        # that's our warehouse, not the carrier counter. ``sender`` will
        # be derived from the origin warehouse address below.
        return point.address, None


def _decode_provider_payload(raw: str | None) -> dict:
    """Best-effort JSON decode of ``DeliveryQuote.provider_payload``.

    Returns an empty dict on missing / malformed payloads — older
    quotes (pre /rates/quote) didn't snapshot the pickup point, and
    those are caught by the ``pickup_point_external_id`` check above
    rather than here.
    """
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except TypeError, ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _build_parcel_from_payload(payload: dict) -> Parcel:
    """Reconstruct the parcel the quote was built against.

    /rates/quote stores ``parcel_weight_grams`` on the payload alongside
    the provider-specific quote token, so the booking call uses the
    exact same weight the customer was priced for.
    """
    grams = _coerce_int(payload.get("parcel_weight_grams"))
    if grams is None or grams <= 0:
        grams = _FALLBACK_PARCEL_GRAMS
    return Parcel(weight=Weight(grams=grams))


def _origin_to_sender(origin) -> ContactInfo:
    """Build a placeholder sender contact from the warehouse address.

    Provider booking calls require *some* sender — for marketplace
    flows we keep the warehouse-level contact. Operators override
    this via the admin UI for special intakes.
    """
    return ContactInfo(
        first_name="Loyality",
        last_name="Warehouse",
        phone="+70000000000",
        company_name=origin.metadata.get("warehouse_name") or "Loyality",
    )


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
