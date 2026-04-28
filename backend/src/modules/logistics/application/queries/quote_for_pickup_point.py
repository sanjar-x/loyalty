"""Query handler: compute a single delivery quote for a chosen pickup point.

This is the checkout-flow narrow path:

1. Frontend already called ``/logistics/pickup-points`` and showed the
   user a map. The user clicked a marker. The frontend now knows only
   ``(provider_code, external_id)`` for that marker.
2. Frontend calls ``POST /logistics/rates/quote`` with that pair plus
   the cart's ``sku_ids``.
3. This handler:
   - Resolves the destination ``Address`` from the pickup-point cache
     warmed by ``ListPickupPointsHandler`` (no extra provider call).
   - Resolves the sender warehouse from the operator's
     ``ProviderAccountModel.config_json``.
   - Estimates parcel weight from category-level pricing settings
     (China dropship — exact SKU weight is unknown until intake).
   - Calls *only* the chosen provider's :class:`IRateProvider`.
   - Picks the matching service tariff (or the cheapest one as
     fallback) and persists the quote with a 30-minute TTL.

The result is the single line the customer needs: «доставка 320 ₽,
3-5 дней» plus a server-trusted ``quote_id`` that the upcoming
``PlaceOrderHandler`` will exchange for a booked shipment.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import attrs

from src.modules.logistics.domain.exceptions import (
    NoEligibleProvidersError,
    RateCalculationError,
)
from src.modules.logistics.domain.interfaces import (
    IDeliveryQuoteRepository,
    IOriginAddressResolver,
    IPickupPointResolver,
    IShippingProviderRegistry,
    ISkuWeightResolver,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    DeliveryQuote,
    Money,
    Parcel,
    PickupPoint,
    ProviderCode,
    Weight,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CartItemRef:
    """One line in the cart at quoting time.

    The handler does not load Cart aggregate — the storefront sends a
    flat list so guest carts (no DB row) and authenticated carts share
    the same path.
    """

    sku_id: uuid.UUID
    quantity: int = 1

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("CartItemRef.quantity must be positive")


@dataclass(frozen=True)
class QuoteForPickupPointQuery:
    """Input for the checkout-flow narrow quote.

    Attributes:
        items: SKUs and per-line quantities to ship.
        provider_code: Logistics provider that owns the chosen pickup point.
        pickup_point_external_id: External id from the pickup-point listing.
        service_code: Optional tariff override (when the user explicitly
            picked a service besides the default ranked-cheapest one).
    """

    items: list[CartItemRef]
    provider_code: ProviderCode
    pickup_point_external_id: str
    service_code: str | None = None


@dataclass(frozen=True)
class QuoteForPickupPointResult:
    """Single quote returned to the storefront.

    The frontend renders this as one line («Доставка 320 ₽ — 3-5 дн.»)
    and stores ``quote_id`` until the user confirms the order.
    """

    quote_id: uuid.UUID
    provider_code: ProviderCode
    service_code: str
    service_name: str
    delivery_type: str
    delivery_amount: int  # smallest currency unit (kopecks)
    currency: str
    delivery_days_min: int | None
    delivery_days_max: int | None
    quoted_at: datetime
    expires_at: datetime  # always set — DEFAULT_QUOTE_TTL = 30 min
    fallback_alternatives: list[str] = field(default_factory=list)
    """``service_code``s of the other returned tariffs — surfaced so the
    frontend can offer a "show more options" toggle without a re-quote."""


class QuoteForPickupPointHandler:
    """Build one ``DeliveryQuote`` for a single chosen pickup point."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        pickup_point_resolver: IPickupPointResolver,
        origin_resolver: IOriginAddressResolver,
        weight_resolver: ISkuWeightResolver,
        quote_repo: IDeliveryQuoteRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._pickup_point_resolver = pickup_point_resolver
        self._origin_resolver = origin_resolver
        self._weight_resolver = weight_resolver
        self._quote_repo = quote_repo
        self._uow = uow
        self._logger = logger.bind(handler="QuoteForPickupPointHandler")

    async def handle(
        self, query: QuoteForPickupPointQuery
    ) -> QuoteForPickupPointResult:
        if not query.items:
            raise ValidationError(message="Cart is empty — no SKUs to quote")

        pickup_point = await self._resolve_destination(query)
        origin = await self._origin_resolver.resolve(query.provider_code)
        parcel = await self._build_parcel(query)

        provider = self._registry.get_rate_provider(query.provider_code)
        try:
            quotes = await provider.calculate_rates(
                origin=origin,
                destination=pickup_point.address,
                parcels=[parcel],
            )
        except Exception as exc:
            self._logger.warning(
                "Provider rate call failed",
                provider=query.provider_code,
                pickup_point=query.pickup_point_external_id,
                error=str(exc),
            )
            raise RateCalculationError(
                details={
                    "provider_code": query.provider_code,
                    "pickup_point_external_id": query.pickup_point_external_id,
                    "error": str(exc),
                }
            ) from exc

        chosen, alternatives = _select_quote(quotes, query.service_code)
        if chosen is None:
            raise RateCalculationError(
                details={
                    "provider_code": query.provider_code,
                    "pickup_point_external_id": query.pickup_point_external_id,
                    "reason": "provider returned no tariffs",
                }
            )

        # Snapshot pickup-point id + parcel weight onto the quote payload
        # so ``CreateShipmentHandler`` can rebuild the destination address
        # and parcel without trusting the frontend.
        chosen = _annotate_payload(
            chosen,
            pickup_point_external_id=query.pickup_point_external_id,
            parcel_weight_grams=parcel.weight.grams,
        )

        async with self._uow:
            persisted = await self._quote_repo.add(chosen)
            await self._uow.commit()

        return _build_result(persisted, alternatives)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_destination(
        self, query: QuoteForPickupPointQuery
    ) -> PickupPoint:
        point = await self._pickup_point_resolver.resolve(
            provider_code=query.provider_code,
            external_id=query.pickup_point_external_id,
        )
        if point is None:
            # The frontend always lists pickup-points before the user
            # clicks one, so a miss means either: cache TTL elapsed
            # while the user lingered on the map, or the storefront
            # supplied a stale id. Either way the corrective action is
            # to re-list — we surface a clear 4xx instead of pretending
            # to quote against an unknown address.
            raise NoEligibleProvidersError(
                details={
                    "provider_code": query.provider_code,
                    "pickup_point_external_id": query.pickup_point_external_id,
                    "reason": (
                        "pickup_point not found in cache — call "
                        "/logistics/pickup-points first"
                    ),
                }
            )
        if point.provider_code != query.provider_code:
            raise NoEligibleProvidersError(
                details={
                    "provider_code": query.provider_code,
                    "actual_provider_code": point.provider_code,
                    "pickup_point_external_id": query.pickup_point_external_id,
                    "reason": "provider_code does not match cached pickup_point",
                }
            )
        return point

    async def _build_parcel(self, query: QuoteForPickupPointQuery) -> Parcel:
        sku_ids = [item.sku_id for item in query.items]
        weights = await self._weight_resolver.resolve_weight_grams(sku_ids)
        # Sum per-unit category weight × line quantity. Missing SKUs are
        # *not* treated as zero — they would make the parcel weightless
        # and CDEK / Yandex would reject the resulting quote. We fall
        # back to the same default the resolver uses (its own fallback
        # is the system default 500 g) by demanding every SKU resolves.
        missing = [sid for sid in sku_ids if sid not in weights]
        if missing:
            raise ValidationError(
                message="One or more SKUs are unknown to the catalog",
                details={"missing_sku_ids": [str(sid) for sid in missing]},
            )
        total_grams = sum(weights[item.sku_id] * item.quantity for item in query.items)
        if total_grams <= 0:
            # Belt-and-braces: weights map is positive by adapter contract,
            # but a future bug shouldn't melt the request.
            raise ValidationError(
                message="Computed parcel weight is non-positive",
                details={"total_grams": total_grams},
            )
        return Parcel(weight=Weight(grams=int(total_grams)))


def _annotate_payload(
    quote: DeliveryQuote,
    *,
    pickup_point_external_id: str,
    parcel_weight_grams: int,
) -> DeliveryQuote:
    """Attach checkout-context fields to ``DeliveryQuote.provider_payload``.

    The provider adapter writes its own opaque token into the payload
    (``offer_id`` for Yandex, ``tariff_code`` for CDEK). We additionally
    snapshot the inputs the booking handler will need to rebuild the
    request without re-trusting the frontend:

    * ``pickup_point_external_id`` — destination resolution at booking.
    * ``parcel_weight_grams`` — exact weight the customer was priced for.

    The provider's own keys are preserved unchanged.
    """
    try:
        existing = json.loads(quote.provider_payload) if quote.provider_payload else {}
    except (TypeError, ValueError):
        existing = {}
    if not isinstance(existing, dict):
        existing = {"_provider_raw": existing}
    existing["pickup_point_external_id"] = pickup_point_external_id
    existing["parcel_weight_grams"] = int(parcel_weight_grams)
    return attrs.evolve(
        quote,
        provider_payload=json.dumps(existing, ensure_ascii=False),
    )


def _select_quote(
    quotes: list[DeliveryQuote],
    requested_service_code: str | None,
) -> tuple[DeliveryQuote | None, list[str]]:
    """Pick the quote to surface to the customer plus service-code alternatives.

    Selection rules:

    1. If ``requested_service_code`` is supplied and exactly matches a
       returned tariff, prefer it (e.g. user toggled "express" on the UI).
    2. Otherwise pick the cheapest by ``rate.total_cost.amount`` so the
       headline price is the best the provider offers for that point.
    3. ``alternatives`` is the list of *other* service codes returned
       on the same call — frontend can offer them without re-quoting.

    Tie-break on equal cost: shorter ``delivery_days_min`` wins, then
    insertion order (stable sort preserves provider ranking).
    """
    if not quotes:
        return None, []
    chosen: DeliveryQuote | None = None
    if requested_service_code is not None:
        chosen = next(
            (q for q in quotes if q.rate.service_code == requested_service_code),
            None,
        )
    if chosen is None:
        chosen = min(
            quotes,
            key=lambda q: (
                q.rate.total_cost.amount,
                q.rate.delivery_days_min
                if q.rate.delivery_days_min is not None
                else 10**6,
            ),
        )
    alternatives = [q.rate.service_code for q in quotes if q is not chosen]
    return chosen, alternatives


def _build_result(
    quote: DeliveryQuote,
    alternatives: list[str],
) -> QuoteForPickupPointResult:
    cost: Money = quote.rate.total_cost
    # Defensive: ``DEFAULT_QUOTE_TTL`` always stamps expires_at; falling
    # back to ``quoted_at`` for a future provider that skips it makes the
    # quote immediately expired and forces a re-quote.
    expires_at = quote.expires_at if quote.expires_at is not None else quote.quoted_at
    return QuoteForPickupPointResult(
        quote_id=quote.id,
        provider_code=quote.rate.provider_code,
        service_code=quote.rate.service_code,
        service_name=quote.rate.service_name,
        delivery_type=quote.rate.delivery_type.value,
        delivery_amount=cost.amount,
        currency=cost.currency_code,
        delivery_days_min=quote.rate.delivery_days_min,
        delivery_days_max=quote.rate.delivery_days_max,
        quoted_at=quote.quoted_at,
        expires_at=expires_at,
        fallback_alternatives=alternatives,
    )


# Re-export the destination address type so consumers can type-hint without
# importing from ``domain`` directly.
__all__ = [
    "CartItemRef",
    "QuoteForPickupPointHandler",
    "QuoteForPickupPointQuery",
    "QuoteForPickupPointResult",
]


# Quiet unused-import false positives in narrow type-only usages above.
_ = Address
