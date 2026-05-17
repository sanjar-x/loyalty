"""Public storefront endpoints for the logistics module.

Customer-facing read-only operations needed during checkout:

* ``POST /storefront/logistics/pickup-points`` — list pickup-point
  markers for the carrier-selection map (CDEK / Yandex / Boxberry / …).
* ``POST /storefront/logistics/rates/quote`` — single delivery quote
  for a chosen pickup point (Mini App checkout flow).

Mutations and provider-management endpoints stay under
``/admin/logistics/*`` (see ``router_admin_shipments.py`` and
``router_admin.py``).
"""

from __future__ import annotations

from typing import cast

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.modules.identity.presentation.dependencies import Auth
from src.modules.logistics.application.queries.list_pickup_points import (
    ListPickupPointsHandler,
    ListPickupPointsQuery,
)
from src.modules.logistics.application.queries.quote_for_pickup_point import (
    CartItemRef,
    QuoteForPickupPointHandler,
    QuoteForPickupPointQuery,
)
from src.modules.logistics.domain.value_objects import DeliveryType, PickupPointQuery
from src.modules.logistics.presentation.schemas import (
    DeliveryTypeLiteral,
    DimensionsSchema,
    GeoPositionSchema,
    PickupPointSchema,
    PickupPointServicesSchema,
    PickupPointsRequest,
    PickupPointsResponse,
    ProviderCodeLiteral,
    RateQuoteRequest,
    RateQuoteResponse,
)
from src.shared.exceptions import ValidationError as AppValidationError
from src.shared.schemas import MoneySchema

logistics_storefront_router = APIRouter(
    prefix="/storefront/logistics",
    tags=["Storefront / Logistics"],
    route_class=DishkaRoute,
)


@logistics_storefront_router.post(
    path="/pickup-points",
    status_code=status.HTTP_200_OK,
    response_model=PickupPointsResponse,
    summary="List pickup/delivery points (public storefront map)",
)
async def list_pickup_points(
    body: PickupPointsRequest,
    handler: FromDishka[ListPickupPointsHandler],
) -> PickupPointsResponse:
    """Return pickup-point markers for the storefront map.

    Either ``(latitude AND longitude)`` or ``city`` is required; the
    handler returns 400 if neither is supplied. ``provider_code`` is
    optional — when omitted the response merges all registered providers.
    Pickup points without coordinates are silently dropped (cannot be
    plotted on a map and would crash a frontend that strict-decodes
    ``GeoPositionSchema``).
    """
    has_geo = body.latitude is not None and body.longitude is not None
    if not has_geo and not body.city:
        raise AppValidationError(
            message=(
                "Either (latitude AND longitude) or city is required to "
                "bound the pickup-point search."
            ),
        )

    delivery_type = DeliveryType(body.delivery_type) if body.delivery_type else None

    query = ListPickupPointsQuery(
        query=PickupPointQuery(
            country_code=body.country_code,
            city=body.city,
            postal_code=body.postal_code,
            latitude=body.latitude,
            longitude=body.longitude,
            radius_km=body.radius_km,
            provider_code=body.provider_code,
            delivery_type=delivery_type,
        ),
        provider_code=body.provider_code,
    )
    result = await handler.handle(query)
    points: list[PickupPointSchema] = []
    for p in result.points:
        if p.address.latitude is None or p.address.longitude is None:
            continue
        points.append(
            PickupPointSchema(
                provider_code=cast(ProviderCodeLiteral, p.provider_code),
                external_id=p.external_id,
                name=p.name,
                pickup_point_type=p.pickup_point_type.value,
                position=GeoPositionSchema(
                    latitude=p.address.latitude,
                    longitude=p.address.longitude,
                ),
                address=_address_to_schema(p.address),
                work_schedule=p.work_schedule,
                phone=p.phone,
                is_cash_allowed=p.is_cash_allowed,
                is_card_allowed=p.is_card_allowed,
                weight_limit_grams=p.weight_limit_grams,
                dimensions_limit=(
                    DimensionsSchema(
                        length_cm=p.dimensions_limit.length_cm,
                        width_cm=p.dimensions_limit.width_cm,
                        height_cm=p.dimensions_limit.height_cm,
                    )
                    if p.dimensions_limit
                    else None
                ),
                services=(
                    PickupPointServicesSchema(
                        is_fitting_allowed=p.services.is_fitting_allowed,
                        is_partial_refuse_allowed=p.services.is_partial_refuse_allowed,
                        is_paperless_pickup_allowed=p.services.is_paperless_pickup_allowed,
                        is_unboxing_allowed=p.services.is_unboxing_allowed,
                    )
                    if p.services is not None
                    else None
                ),
            )
        )
    return PickupPointsResponse(
        points=points,
        errors=cast("dict[ProviderCodeLiteral, str]", result.errors),
    )


@logistics_storefront_router.post(
    path="/rates/quote",
    status_code=status.HTTP_200_OK,
    response_model=RateQuoteResponse,
    summary="Quote delivery for a chosen pickup point (Mini App checkout)",
)
async def quote_for_pickup_point(
    body: RateQuoteRequest,
    auth: Auth,
    handler: FromDishka[QuoteForPickupPointHandler],
) -> RateQuoteResponse:
    """Customer-facing single-quote endpoint for the checkout flow.

    Frontend (Mini App) supplies cart SKUs and the marker the user
    clicked (``provider_code`` + ``pickup_point_external_id``). The
    handler reconstructs weight / origin / destination server-side and
    returns a price-and-ETA line plus a ``quote_id`` the upcoming
    place-order call will exchange for a booked shipment.

    Mirrors the admin endpoint at ``/api/v1/admin/logistics/rates/quote``
    on the same handler — the URL split keeps the staff back office and
    the customer checkout on different namespaces, with the admin side
    additionally gated by ``RequireStaffRole``. The customer's
    ``identity_id`` is threaded into the persisted quote row so
    ``CreateOrderFromCartHandler`` can refuse a quote belonging to a
    different customer (CR-2).
    """
    query = QuoteForPickupPointQuery(
        items=[
            CartItemRef(sku_id=item.sku_id, quantity=item.quantity)
            for item in body.items
        ],
        provider_code=body.provider_code,
        pickup_point_external_id=body.pickup_point_external_id,
        service_code=body.service_code,
        identity_id=auth.identity_id,
    )
    result = await handler.handle(query)
    return RateQuoteResponse(
        quote_id=result.quote_id,
        provider_code=cast(ProviderCodeLiteral, result.provider_code),
        service_code=result.service_code,
        service_name=result.service_name,
        delivery_type=cast(DeliveryTypeLiteral, result.delivery_type),
        delivery_amount=MoneySchema(
            amount=result.delivery_amount,
            currency=result.currency.upper(),
        ),
        delivery_days_min=result.delivery_days_min,
        delivery_days_max=result.delivery_days_max,
        quoted_at=result.quoted_at,
        expires_at=result.expires_at,
        fallback_alternatives=list(result.fallback_alternatives),
    )


def _address_to_schema(a):
    """Inline schema mapping — same shape used by the admin router."""
    from src.modules.logistics.presentation.schemas import AddressSchema

    return AddressSchema(
        country_code=a.country_code,
        city=a.city,
        region=a.region,
        postal_code=a.postal_code,
        street=a.street,
        house=a.house,
        apartment=a.apartment,
        subdivision_code=a.subdivision_code,
        raw_address=a.raw_address,
    )
