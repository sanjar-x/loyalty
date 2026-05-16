"""
Logistics admin API router — staff-only endpoints under ``/admin/logistics``.

Provides rate calculation, shipment CRUD, tracking, intake scheduling,
delivery intervals, edits, returns. All endpoints require
``logistics:read`` or ``logistics:write`` permission (staff-level).
"""

import uuid
from datetime import datetime
from typing import Annotated, cast

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Path, Query, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    RequireStaffRole,
)
from src.modules.logistics.application.commands.book_shipment import (
    BookShipmentCommand,
    BookShipmentHandler,
)
from src.modules.logistics.application.commands.cancel_intake import (
    CancelIntakeCommand,
    CancelIntakeHandler,
)
from src.modules.logistics.application.commands.cancel_shipment import (
    CancelShipmentCommand,
    CancelShipmentHandler,
)
from src.modules.logistics.application.commands.create_intake import (
    CreateIntakeCommand,
    CreateIntakeHandler,
)
from src.modules.logistics.application.commands.create_shipment import (
    CreateShipmentCommand,
    CreateShipmentHandler,
)
from src.modules.logistics.application.commands.edit_order import (
    EditOrderCommand,
    EditOrderHandler,
)
from src.modules.logistics.application.commands.edit_order_items import (
    EditOrderItemsCommand,
    EditOrderItemsHandler,
)
from src.modules.logistics.application.commands.edit_order_packages import (
    EditOrderPackagesCommand,
    EditOrderPackagesHandler,
)
from src.modules.logistics.application.commands.register_client_return import (
    RegisterClientReturnCommand,
    RegisterClientReturnHandler,
)
from src.modules.logistics.application.commands.register_refusal import (
    RegisterRefusalCommand,
    RegisterRefusalHandler,
)
from src.modules.logistics.application.commands.remove_order_items import (
    RemoveOrderItemsCommand,
    RemoveOrderItemsHandler,
)
from src.modules.logistics.application.queries.calculate_rates import (
    CalculateRatesHandler,
    CalculateRatesQuery,
)
from src.modules.logistics.application.queries.check_reverse_availability import (
    CheckReverseAvailabilityHandler,
    CheckReverseAvailabilityQuery,
)
from src.modules.logistics.application.queries.get_actual_delivery_info import (
    GetActualDeliveryInfoHandler,
    GetActualDeliveryInfoQuery,
)
from src.modules.logistics.application.queries.get_available_intake_days import (
    GetAvailableIntakeDaysHandler,
    GetAvailableIntakeDaysQuery,
)
from src.modules.logistics.application.queries.get_delivery_intervals import (
    GetDeliveryIntervalsHandler,
    GetDeliveryIntervalsQuery,
)
from src.modules.logistics.application.queries.get_edit_task_status import (
    GetEditTaskStatusHandler,
    GetEditTaskStatusQuery,
)
from src.modules.logistics.application.queries.get_estimated_delivery_intervals import (
    GetEstimatedDeliveryIntervalsHandler,
    GetEstimatedDeliveryIntervalsQuery,
)
from src.modules.logistics.application.queries.get_intake import (
    GetIntakeHandler,
    GetIntakeQuery,
)
from src.modules.logistics.application.queries.get_shipment import (
    GetShipmentHandler,
    GetShipmentQuery,
)
from src.modules.logistics.application.queries.get_tracking import (
    GetTrackingHandler,
    GetTrackingQuery,
)
from src.modules.logistics.application.queries.list_admin_shipments import (
    ListAdminShipmentsHandler,
    ListAdminShipmentsQuery,
)
from src.modules.logistics.application.queries.list_pickup_points import (
    ListPickupPointsHandler,
    ListPickupPointsQuery,
)
from src.modules.logistics.application.queries.quote_for_pickup_point import (
    CartItemRef,
    QuoteForPickupPointHandler,
    QuoteForPickupPointQuery,
)
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.value_objects import (
    Address,
    CashOnDelivery,
    ContactInfo,
    DeliveryType,
    Dimensions,
    EditItemMarking,
    EditItemRemoval,
    EditPackage,
    EditPackageItem,
    EditPlaceSwap,
    Money,
    Parcel,
    PickupPointQuery,
    ShipmentStatus,
    Weight,
)
from src.modules.logistics.presentation.schemas import (
    ActualDeliveryInfoResponse,
    ActualDeliveryInfoSchema,
    AddressSchema,
    AdminShipmentListResponse,
    AdminShipmentProviderFilterLiteral,
    AdminShipmentSummarySchema,
    AvailableIntakeDaysRequest,
    AvailableIntakeDaysResponse,
    BookShipmentResponse,
    CalculateRatesRequest,
    CalculateRatesResponse,
    CancelIntakeResponse,
    CancelShipmentResponse,
    CashOnDeliverySchema,
    ClientReturnRequest,
    ContactInfoSchema,
    CreateIntakeRequest,
    CreateIntakeResponse,
    CreateShipmentRequest,
    DeliveryIntervalSchema,
    DeliveryIntervalsResponse,
    DeliveryQuoteSchema,
    DeliveryTypeLiteral,
    DimensionsSchema,
    EditOrderItemsRequest,
    EditOrderRequest,
    EditPackageSchema,
    EditPackagesRequest,
    EditPlaceSwapSchema,
    EditTaskResponse,
    EditTaskStatusResponse,
    EstimatedDeliveryIntervalsRequest,
    GeoPositionSchema,
    IntakeStatusResponse,
    IntakeWindowSchema,
    MoneySchema,
    ParcelSchema,
    PickupPointSchema,
    PickupPointsRequest,
    PickupPointsResponse,
    ProviderCodeLiteral,
    RateQuoteRequest,
    RateQuoteResponse,
    RefusalRequestSchema,
    RemoveOrderItemsRequest,
    ReturnResponse,
    ReverseAvailabilityRequestSchema,
    ReverseAvailabilityResponse,
    ShipmentResponse,
    ShipmentStatusLiteral,
    ShippingRateSchema,
    TrackingEventSchema,
    TrackingResponse,
    TrackingStatusLiteral,
)
from src.shared.exceptions import ValidationError as AppValidationError

# Permission codenames for logistics resources. ``logistics:read`` covers
# all GET endpoints (rates, shipment / tracking lookup, pickup points,
# delivery intervals, edit-task status, actual delivery info).
# ``logistics:write`` covers every mutating endpoint — booking,
# cancellation, intake scheduling, returns, edit-task submission.
_LOGISTICS_READ = Depends(RequirePermission(codename="logistics:read"))
_LOGISTICS_WRITE = Depends(RequirePermission(codename="logistics:write"))


logistics_router = APIRouter(
    prefix="/admin/logistics",
    tags=["Admin / Logistics / Shipments"],
    route_class=DishkaRoute,
    dependencies=[Depends(RequireStaffRole)],
)


# ---------------------------------------------------------------------------
# Schema → domain mapping helpers
# ---------------------------------------------------------------------------


def _schema_to_address(s: AddressSchema) -> Address:
    """Schema → domain. ``metadata`` and coordinates stay server-side."""
    return Address(
        country_code=s.country_code,
        city=s.city,
        region=s.region,
        postal_code=s.postal_code,
        street=s.street,
        house=s.house,
        apartment=s.apartment,
        subdivision_code=s.subdivision_code,
        raw_address=s.raw_address,
    )


def _address_to_schema(a: Address) -> AddressSchema:
    """Domain → schema. Drops ``metadata`` (provider internals) and the
    ``latitude/longitude`` pair — coordinates are surfaced separately on
    pickup-point responses via :class:`GeoPositionSchema`."""
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


def _schema_to_contact(s: ContactInfoSchema) -> ContactInfo:
    return ContactInfo(
        first_name=s.first_name,
        last_name=s.last_name,
        phone=s.phone,
        middle_name=s.middle_name,
        email=s.email,
        company_name=s.company_name,
    )


def _schema_to_parcel(s: ParcelSchema) -> Parcel:
    return Parcel(
        weight=Weight(grams=s.weight.grams),
        dimensions=(
            Dimensions(
                length_cm=s.dimensions.length_cm,
                width_cm=s.dimensions.width_cm,
                height_cm=s.dimensions.height_cm,
            )
            if s.dimensions
            else None
        ),
        declared_value=(
            Money(
                amount=s.declared_value.amount,
                currency_code=s.declared_value.currency,
            )
            if s.declared_value
            else None
        ),
        description=s.description,
    )


def _schema_to_cod(s: CashOnDeliverySchema | None) -> CashOnDelivery | None:
    if s is None:
        return None
    return CashOnDelivery(
        amount=Money(amount=s.amount.amount, currency_code=s.amount.currency),
        payment_method=s.payment_method,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@logistics_router.post(
    path="/rates",
    status_code=status.HTTP_200_OK,
    response_model=CalculateRatesResponse,
    summary="Calculate shipping rates",
    dependencies=[_LOGISTICS_READ],
)
async def calculate_rates(
    body: CalculateRatesRequest,
    handler: FromDishka[CalculateRatesHandler],
) -> CalculateRatesResponse:
    query = CalculateRatesQuery(
        origin=_schema_to_address(body.origin),
        destination=_schema_to_address(body.destination),
        parcels=[_schema_to_parcel(p) for p in body.parcels],
    )
    result = await handler.handle(query)
    return CalculateRatesResponse(
        quotes=[
            DeliveryQuoteSchema(
                id=q.id,
                rate=ShippingRateSchema(
                    provider_code=cast(ProviderCodeLiteral, q.rate.provider_code),
                    service_code=q.rate.service_code,
                    service_name=q.rate.service_name,
                    delivery_type=q.rate.delivery_type.value,
                    total_cost=MoneySchema(
                        amount=q.rate.total_cost.amount,
                        currency=q.rate.total_cost.currency_code.upper(),
                    ),
                    base_cost=MoneySchema(
                        amount=q.rate.base_cost.amount,
                        currency=q.rate.base_cost.currency_code.upper(),
                    ),
                    insurance_cost=(
                        MoneySchema(
                            amount=q.rate.insurance_cost.amount,
                            currency=q.rate.insurance_cost.currency_code.upper(),
                        )
                        if q.rate.insurance_cost
                        else None
                    ),
                    delivery_days_min=q.rate.delivery_days_min,
                    delivery_days_max=q.rate.delivery_days_max,
                ),
                provider_payload=q.provider_payload,
                quoted_at=q.quoted_at,
                expires_at=q.expires_at,
            )
            for q in result.quotes
        ],
        errors=cast("dict[ProviderCodeLiteral, str]", result.errors),
    )


@logistics_router.post(
    path="/rates/quote",
    status_code=status.HTTP_200_OK,
    response_model=RateQuoteResponse,
    summary="Quote delivery for a chosen pickup point (Checkout flow)",
    dependencies=[_LOGISTICS_READ],
)
async def quote_for_pickup_point(
    body: RateQuoteRequest,
    handler: FromDishka[QuoteForPickupPointHandler],
) -> RateQuoteResponse:
    """Single-quote endpoint matching the BRD checkout sequence.

    The frontend supplies SKU ids and the marker the user clicked
    (``provider_code`` + ``pickup_point_external_id``). The backend
    resolves weight / origin / destination server-side and returns a
    single price-and-eta line plus a ``quote_id`` to use at order time.
    """
    query = QuoteForPickupPointQuery(
        items=[
            CartItemRef(sku_id=item.sku_id, quantity=item.quantity)
            for item in body.items
        ],
        provider_code=body.provider_code,
        pickup_point_external_id=body.pickup_point_external_id,
        service_code=body.service_code,
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


@logistics_router.get(
    path="/shipments",
    status_code=status.HTTP_200_OK,
    response_model=AdminShipmentListResponse,
    summary="List shipments with filters and cursor pagination",
    dependencies=[_LOGISTICS_READ],
)
async def list_admin_shipments(
    handler: FromDishka[ListAdminShipmentsHandler],
    provider: AdminShipmentProviderFilterLiteral | None = Query(
        default=None,
        description="Restrict to a single provider code.",
    ),
    shipment_status: ShipmentStatusLiteral | None = Query(
        default=None,
        alias="status",
        description="Restrict to a single FSM state.",
    ),
    order_id: uuid.UUID | None = Query(
        default=None,
        description="Restrict to shipments linked to a specific order.",
        alias="orderId",
    ),
    created_after: datetime | None = Query(
        default=None,
        description="Inclusive lower bound on ``created_at``.",
        alias="createdAfter",
    ),
    created_before: datetime | None = Query(
        default=None,
        description="Exclusive upper bound on ``created_at``.",
        alias="createdBefore",
    ),
    tracking_number_contains: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        description="Case-insensitive substring match on tracking_number.",
        alias="trackingNumberContains",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Page size."),
    cursor: datetime | None = Query(
        default=None,
        description="``next_cursor`` from the previous response.",
    ),
) -> AdminShipmentListResponse:
    """List shipments for the admin dashboard.

    Cursor pagination is forward-only: the response carries
    ``next_cursor`` (the last row's ``created_at``) when more rows are
    available; pass it back as ``cursor`` to fetch the next page.

    Filters compose with AND semantics. ``provider`` and ``status``
    are validated against closed enums — invalid values surface as
    HTTP 422 from FastAPI's Query validation rather than silently
    falling through.
    """
    query = ListAdminShipmentsQuery(
        provider=provider,
        status=ShipmentStatus(shipment_status) if shipment_status else None,
        order_id=order_id,
        created_after=created_after,
        created_before=created_before,
        tracking_number_contains=tracking_number_contains,
        limit=limit,
        cursor=cursor,
    )
    page = await handler.handle(query)
    return AdminShipmentListResponse(
        items=[
            AdminShipmentSummarySchema(
                id=row.id,
                provider_code=row.provider_code,
                status=cast(ShipmentStatusLiteral, row.status),
                tracking_number=row.tracking_number,
                order_id=row.order_id,
                delivery_type=cast(DeliveryTypeLiteral, row.delivery_type),
                destination_city=row.destination_city,
                quoted_cost=MoneySchema(
                    amount=row.quoted_cost_amount,
                    currency=row.quoted_cost_currency.upper(),
                ),
                latest_tracking_status=cast(
                    "TrackingStatusLiteral | None", row.latest_tracking_status
                ),
                created_at=row.created_at,
                updated_at=row.updated_at,
                booked_at=row.booked_at,
            )
            for row in page.items
        ],
        next_cursor=page.next_cursor,
    )


@logistics_router.post(
    path="/shipments",
    status_code=status.HTTP_201_CREATED,
    response_model=ShipmentResponse,
    summary="Create a shipment (DRAFT)",
    dependencies=[_LOGISTICS_WRITE],
)
async def create_shipment(
    body: CreateShipmentRequest,
    create_handler: FromDishka[CreateShipmentHandler],
    get_handler: FromDishka[GetShipmentHandler],
) -> ShipmentResponse:
    """Create a DRAFT shipment from a server-side quote.

    The frontend supplies only the trusted ``quote_id`` plus the
    recipient contact — origin, destination, weight and provider all
    come from the persisted ``DeliveryQuote`` so the booking call can't
    be tampered with.
    """
    command = CreateShipmentCommand(
        quote_id=body.quote_id,
        recipient=_schema_to_contact(body.recipient),
        order_id=body.order_id,
        cod=_schema_to_cod(body.cod),
    )
    result = await create_handler.handle(command)
    shipment = await get_handler.handle(
        GetShipmentQuery(shipment_id=result.shipment_id)
    )
    return _shipment_to_response(shipment)


@logistics_router.post(
    path="/shipments/{shipmentId}/book",
    status_code=status.HTTP_200_OK,
    response_model=BookShipmentResponse,
    summary="Book a DRAFT shipment with the provider",
    dependencies=[_LOGISTICS_WRITE],
)
async def book_shipment(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    handler: FromDishka[BookShipmentHandler],
) -> BookShipmentResponse:
    result = await handler.handle(BookShipmentCommand(shipment_id=shipment_id))
    return BookShipmentResponse(
        shipment_id=result.shipment_id,
        provider_shipment_id=result.provider_shipment_id,
        tracking_number=result.tracking_number,
    )


@logistics_router.post(
    path="/shipments/{shipmentId}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=CancelShipmentResponse,
    summary="Cancel a booked shipment",
    dependencies=[_LOGISTICS_WRITE],
)
async def cancel_shipment(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    handler: FromDishka[CancelShipmentHandler],
) -> CancelShipmentResponse:
    result = await handler.handle(CancelShipmentCommand(shipment_id=shipment_id))
    return CancelShipmentResponse(shipment_id=result.shipment_id)


@logistics_router.get(
    path="/shipments/{shipmentId}",
    status_code=status.HTTP_200_OK,
    response_model=ShipmentResponse,
    summary="Get shipment details",
    dependencies=[_LOGISTICS_READ],
)
async def get_shipment(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    handler: FromDishka[GetShipmentHandler],
) -> ShipmentResponse:
    shipment = await handler.handle(GetShipmentQuery(shipment_id=shipment_id))
    return _shipment_to_response(shipment)


@logistics_router.get(
    path="/shipments/{shipmentId}/tracking",
    status_code=status.HTTP_200_OK,
    response_model=TrackingResponse,
    summary="Get shipment tracking history",
    dependencies=[_LOGISTICS_READ],
)
async def get_tracking(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    handler: FromDishka[GetTrackingHandler],
) -> TrackingResponse:
    result = await handler.handle(GetTrackingQuery(shipment_id=shipment_id))
    return TrackingResponse(
        shipment_id=result.shipment_id,
        tracking_number=result.tracking_number,
        latest_status=cast("TrackingStatusLiteral | None", result.latest_status),
        events=[
            TrackingEventSchema(
                status=e.status.value,
                provider_status_code=e.provider_status_code,
                provider_status_name=e.provider_status_name,
                timestamp=e.timestamp,
                location=e.location,
                description=e.description,
            )
            for e in result.events
        ],
    )


@logistics_router.post(
    path="/pickup-points",
    status_code=status.HTTP_200_OK,
    response_model=PickupPointsResponse,
    summary="List pickup/delivery points",
    dependencies=[_LOGISTICS_READ],
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
            # No coordinates → cannot render on the map. Skip rather
            # than fail the whole response — providers occasionally
            # ship test rows with empty geocodes.
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
            )
        )
    return PickupPointsResponse(
        points=points,
        errors=cast("dict[ProviderCodeLiteral, str]", result.errors),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Intake (courier pickup) endpoints
# ---------------------------------------------------------------------------


@logistics_router.post(
    path="/intakes/available-days",
    status_code=status.HTTP_200_OK,
    response_model=AvailableIntakeDaysResponse,
    summary="List days when the courier can pick up parcels",
    dependencies=[_LOGISTICS_READ],
)
async def list_available_intake_days(
    body: AvailableIntakeDaysRequest,
    handler: FromDishka[GetAvailableIntakeDaysHandler],
) -> AvailableIntakeDaysResponse:
    query = GetAvailableIntakeDaysQuery(
        provider_code=body.provider_code,
        from_address=_schema_to_address(body.address),
        until=body.until,
    )
    result = await handler.handle(query)
    return AvailableIntakeDaysResponse(
        provider_code=cast(ProviderCodeLiteral, result.provider_code),
        windows=[
            IntakeWindowSchema(date=w.date, is_workday=w.is_workday)
            for w in result.windows
        ],
    )


@logistics_router.post(
    path="/shipments/{shipmentId}/intake",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateIntakeResponse,
    summary="Schedule a courier intake for a booked shipment",
    dependencies=[_LOGISTICS_WRITE],
)
async def create_intake(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: CreateIntakeRequest,
    handler: FromDishka[CreateIntakeHandler],
) -> CreateIntakeResponse:
    command = CreateIntakeCommand(
        shipment_id=shipment_id,
        intake_date=body.intake_date,
        intake_time_from=body.intake_time_from,
        intake_time_to=body.intake_time_to,
        comment=body.comment,
        lunch_time_from=body.lunch_time_from,
        lunch_time_to=body.lunch_time_to,
        need_call=body.need_call,
    )
    result = await handler.handle(command)
    return CreateIntakeResponse(
        shipment_id=result.shipment_id,
        provider_intake_id=result.provider_intake_id,
        status=result.status.value,
    )


@logistics_router.get(
    path="/intakes/{providerCode}/{providerIntakeId}",
    status_code=status.HTTP_200_OK,
    response_model=IntakeStatusResponse,
    summary="Get intake status from the provider",
    dependencies=[_LOGISTICS_READ],
)
async def get_intake_status(
    provider_code: Annotated[str, Path(alias="providerCode")],
    provider_intake_id: Annotated[str, Path(alias="providerIntakeId")],
    handler: FromDishka[GetIntakeHandler],
) -> IntakeStatusResponse:
    result = await handler.handle(
        GetIntakeQuery(
            provider_code=provider_code,
            provider_intake_id=provider_intake_id,
        )
    )
    return IntakeStatusResponse(
        provider_intake_id=result.provider_intake_id,
        status=result.status.value,
    )


@logistics_router.delete(
    path="/intakes/{providerCode}/{providerIntakeId}",
    status_code=status.HTTP_200_OK,
    response_model=CancelIntakeResponse,
    summary="Cancel a scheduled intake",
    dependencies=[_LOGISTICS_WRITE],
)
async def cancel_intake(
    provider_code: Annotated[str, Path(alias="providerCode")],
    provider_intake_id: Annotated[str, Path(alias="providerIntakeId")],
    handler: FromDishka[CancelIntakeHandler],
    shipment_id: uuid.UUID | None = Query(default=None, alias="shipmentId"),
) -> CancelIntakeResponse:
    # ``shipment_id`` is optional but strongly recommended: without
    # it the handler cancels with the carrier but cannot clear
    # ``Shipment.scheduled_intake`` locally, so the next
    # ``CreateIntake`` call would be rejected by the idempotency
    # guard until the operator reconciles by hand.
    result = await handler.handle(
        CancelIntakeCommand(
            provider_code=provider_code,
            provider_intake_id=provider_intake_id,
            shipment_id=shipment_id,
        )
    )
    return CancelIntakeResponse(success=result.success)


# ---------------------------------------------------------------------------
# Delivery schedule endpoints
# ---------------------------------------------------------------------------


@logistics_router.get(
    path="/shipments/{shipmentId}/delivery-intervals",
    status_code=status.HTTP_200_OK,
    response_model=DeliveryIntervalsResponse,
    summary="List available delivery intervals for a booked shipment",
    dependencies=[_LOGISTICS_READ],
)
async def get_delivery_intervals(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    handler: FromDishka[GetDeliveryIntervalsHandler],
) -> DeliveryIntervalsResponse:
    result = await handler.handle(GetDeliveryIntervalsQuery(shipment_id=shipment_id))
    return DeliveryIntervalsResponse(
        provider_code=cast(ProviderCodeLiteral, result.provider_code),
        intervals=[
            DeliveryIntervalSchema(
                start_time=i.start_time,
                end_time=i.end_time,
                date=i.date,
            )
            for i in result.intervals
        ],
    )


@logistics_router.post(
    path="/delivery-intervals/estimate",
    status_code=status.HTTP_200_OK,
    response_model=DeliveryIntervalsResponse,
    summary="Estimate delivery intervals before booking",
    dependencies=[_LOGISTICS_READ],
)
async def estimate_delivery_intervals(
    body: EstimatedDeliveryIntervalsRequest,
    handler: FromDishka[GetEstimatedDeliveryIntervalsHandler],
) -> DeliveryIntervalsResponse:
    query = GetEstimatedDeliveryIntervalsQuery(
        provider_code=body.provider_code,
        origin=_schema_to_address(body.origin),
        destination=_schema_to_address(body.destination),
        tariff_code=body.tariff_code,
    )
    result = await handler.handle(query)
    return DeliveryIntervalsResponse(
        provider_code=cast(ProviderCodeLiteral, result.provider_code),
        intervals=[
            DeliveryIntervalSchema(
                start_time=i.start_time,
                end_time=i.end_time,
                date=i.date,
            )
            for i in result.intervals
        ],
    )


# ---------------------------------------------------------------------------
# Returns / refusals / reverse availability
# ---------------------------------------------------------------------------


@logistics_router.post(
    path="/shipments/{shipmentId}/return",
    status_code=status.HTTP_201_CREATED,
    response_model=ReturnResponse,
    summary="Register a client return shipment",
    dependencies=[_LOGISTICS_WRITE],
)
async def register_client_return(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: ClientReturnRequest,
    handler: FromDishka[RegisterClientReturnHandler],
) -> ReturnResponse:
    command = RegisterClientReturnCommand(
        shipment_id=shipment_id,
        tariff_code=body.tariff_code,
        return_address=_schema_to_address(body.return_address),
        sender=_schema_to_contact(body.sender),
        recipient=_schema_to_contact(body.recipient),
    )
    result = await handler.handle(command)
    return ReturnResponse(
        shipment_id=result.shipment_id,
        success=result.success,
        provider_return_id=result.provider_return_id,
        reason=result.reason,
    )


@logistics_router.post(
    path="/shipments/{shipmentId}/refusal",
    status_code=status.HTTP_201_CREATED,
    response_model=ReturnResponse,
    summary="Register a doorstep refusal",
    dependencies=[_LOGISTICS_WRITE],
)
async def register_refusal(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: RefusalRequestSchema,
    handler: FromDishka[RegisterRefusalHandler],
) -> ReturnResponse:
    result = await handler.handle(
        RegisterRefusalCommand(shipment_id=shipment_id, reason=body.reason)
    )
    return ReturnResponse(
        shipment_id=result.shipment_id,
        success=result.success,
        provider_return_id=result.provider_return_id,
        reason=result.reason,
    )


@logistics_router.post(
    path="/reverse-availability",
    status_code=status.HTTP_200_OK,
    response_model=ReverseAvailabilityResponse,
    summary="Validate that a reverse-shipment route is feasible",
    dependencies=[_LOGISTICS_READ],
)
async def check_reverse_availability(
    body: ReverseAvailabilityRequestSchema,
    handler: FromDishka[CheckReverseAvailabilityHandler],
) -> ReverseAvailabilityResponse:
    query = CheckReverseAvailabilityQuery(
        provider_code=body.provider_code,
        tariff_code=body.tariff_code,
        sender_phones=tuple(body.sender_phones),
        recipient_phones=tuple(body.recipient_phones),
        from_location=(
            _schema_to_address(body.from_location) if body.from_location else None
        ),
        to_location=(
            _schema_to_address(body.to_location) if body.to_location else None
        ),
        shipment_point=body.shipment_point,
        delivery_point=body.delivery_point,
        sender_contragent_type=body.sender_contragent_type,
        recipient_contragent_type=body.recipient_contragent_type,
    )
    result = await handler.handle(query)
    return ReverseAvailabilityResponse(
        provider_code=cast(ProviderCodeLiteral, result.provider_code),
        is_available=result.is_available,
        reason=result.reason,
    )


# ---------------------------------------------------------------------------
# Actual delivery info (Yandex 3.05)
# ---------------------------------------------------------------------------


@logistics_router.get(
    path="/shipments/{shipmentId}/actual-delivery-info",
    status_code=status.HTTP_200_OK,
    response_model=ActualDeliveryInfoResponse,
    summary="Get carrier-confirmed delivery date and interval",
    dependencies=[_LOGISTICS_READ],
)
async def get_actual_delivery_info(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    handler: FromDishka[GetActualDeliveryInfoHandler],
) -> ActualDeliveryInfoResponse:
    result = await handler.handle(GetActualDeliveryInfoQuery(shipment_id=shipment_id))
    info_schema = (
        ActualDeliveryInfoSchema(
            delivery_date=result.info.delivery_date,
            interval_start=result.info.interval_start,
            interval_end=result.info.interval_end,
            timezone_offset=result.info.timezone_offset,
        )
        if result.info is not None
        else None
    )
    return ActualDeliveryInfoResponse(shipment_id=result.shipment_id, info=info_schema)


# ---------------------------------------------------------------------------
# Edit operations (Yandex 3.06 / 3.12 / 3.13 / 3.14 / 3.15)
# ---------------------------------------------------------------------------


@logistics_router.post(
    path="/shipments/{shipmentId}/edit",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Edit recipient / destination / packages on a booked shipment",
    dependencies=[_LOGISTICS_WRITE],
)
async def edit_order(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: EditOrderRequest,
    handler: FromDishka[EditOrderHandler],
) -> EditTaskResponse:
    delivery_type: DeliveryType | None = None
    if body.delivery_type:
        try:
            delivery_type = DeliveryType(body.delivery_type)
        except ValueError:
            valid = [e.value for e in DeliveryType]
            raise AppValidationError(
                message=f"Invalid delivery_type '{body.delivery_type}'. Must be one of: {valid}",
            ) from None

    command = EditOrderCommand(
        shipment_id=shipment_id,
        recipient=_schema_to_contact(body.recipient) if body.recipient else None,
        destination=(
            _schema_to_address(body.destination) if body.destination else None
        ),
        delivery_type=delivery_type,
        places=tuple(_schema_to_place_swap(s) for s in body.places),
    )
    result = await handler.handle(command)
    return EditTaskResponse(
        shipment_id=result.shipment_id,
        task_id=result.task_id,
        initial_status=result.initial_status.value,
    )


@logistics_router.post(
    path="/shipments/{shipmentId}/edit-packages",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Replace package layout (async edit task)",
    dependencies=[_LOGISTICS_WRITE],
)
async def edit_order_packages(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: EditPackagesRequest,
    handler: FromDishka[EditOrderPackagesHandler],
) -> EditTaskResponse:
    command = EditOrderPackagesCommand(
        shipment_id=shipment_id,
        packages=tuple(_schema_to_edit_package(p) for p in body.packages),
    )
    result = await handler.handle(command)
    return EditTaskResponse(
        shipment_id=result.shipment_id,
        task_id=result.task_id,
        initial_status=result.initial_status.value,
    )


@logistics_router.post(
    path="/shipments/{shipmentId}/edit-items",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Patch item articles / marking codes (async edit task)",
    dependencies=[_LOGISTICS_WRITE],
)
async def edit_order_items(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: EditOrderItemsRequest,
    handler: FromDishka[EditOrderItemsHandler],
) -> EditTaskResponse:
    command = EditOrderItemsCommand(
        shipment_id=shipment_id,
        items=tuple(
            EditItemMarking(
                item_barcode=i.item_barcode,
                article=i.article,
                marking_code=i.marking_code,
            )
            for i in body.items
        ),
    )
    result = await handler.handle(command)
    return EditTaskResponse(
        shipment_id=result.shipment_id,
        task_id=result.task_id,
        initial_status=result.initial_status.value,
    )


@logistics_router.post(
    path="/shipments/{shipmentId}/remove-items",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Reduce or remove items from a booked shipment (async edit task)",
    dependencies=[_LOGISTICS_WRITE],
)
async def remove_order_items(
    shipment_id: Annotated[uuid.UUID, Path(alias="shipmentId")],
    body: RemoveOrderItemsRequest,
    handler: FromDishka[RemoveOrderItemsHandler],
) -> EditTaskResponse:
    command = RemoveOrderItemsCommand(
        shipment_id=shipment_id,
        removals=tuple(
            EditItemRemoval(
                item_barcode=r.item_barcode,
                remaining_count=r.remaining_count,
            )
            for r in body.removals
        ),
    )
    result = await handler.handle(command)
    return EditTaskResponse(
        shipment_id=result.shipment_id,
        task_id=result.task_id,
        initial_status=result.initial_status.value,
    )


@logistics_router.get(
    path="/edit-tasks/{providerCode}/{taskId}",
    status_code=status.HTTP_200_OK,
    response_model=EditTaskStatusResponse,
    summary="Poll an asynchronous edit task",
    dependencies=[_LOGISTICS_READ],
)
async def get_edit_task_status(
    provider_code: Annotated[str, Path(alias="providerCode")],
    task_id: Annotated[str, Path(alias="taskId")],
    handler: FromDishka[GetEditTaskStatusHandler],
) -> EditTaskStatusResponse:
    result = await handler.handle(
        GetEditTaskStatusQuery(provider_code=provider_code, task_id=task_id)
    )
    return EditTaskStatusResponse(
        provider_code=cast(ProviderCodeLiteral, result.provider_code),
        task_id=result.task_id,
        status=result.status.value,
    )


def _schema_to_place_swap(s: EditPlaceSwapSchema) -> EditPlaceSwap:
    return EditPlaceSwap(
        old_barcode=s.old_barcode,
        new_barcode=s.new_barcode,
        new_parcel=_schema_to_parcel(s.new_parcel),
    )


def _schema_to_edit_package(p: EditPackageSchema) -> EditPackage:
    return EditPackage(
        barcode=p.barcode,
        weight=Weight(grams=p.weight.grams),
        dimensions=Dimensions(
            length_cm=p.dimensions.length_cm,
            width_cm=p.dimensions.width_cm,
            height_cm=p.dimensions.height_cm,
        ),
        items=tuple(
            EditPackageItem(item_barcode=item.item_barcode, count=item.count)
            for item in p.items
        ),
    )


def _shipment_to_response(shipment: Shipment) -> ShipmentResponse:
    return ShipmentResponse(
        id=shipment.id,
        order_id=shipment.order_id,
        provider_code=cast(ProviderCodeLiteral, shipment.provider_code),
        service_code=shipment.service_code,
        delivery_type=shipment.delivery_type.value,
        status=shipment.status.value,
        provider_shipment_id=shipment.provider_shipment_id,
        tracking_number=shipment.tracking_number,
        quoted_cost=MoneySchema(
            amount=shipment.quoted_cost.amount,
            currency=shipment.quoted_cost.currency_code.upper(),
        ),
        latest_tracking_status=(
            shipment.latest_tracking_status.value
            if shipment.latest_tracking_status
            else None
        ),
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        booked_at=shipment.booked_at,
        cancelled_at=shipment.cancelled_at,
    )
