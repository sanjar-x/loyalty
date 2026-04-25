"""
Logistics API router — public endpoints.

Provides rate calculation, shipment CRUD, tracking, and pickup point listing.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

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
from src.modules.logistics.application.queries.list_pickup_points import (
    ListPickupPointsHandler,
    ListPickupPointsQuery,
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
    Weight,
)
from src.modules.logistics.presentation.schemas import (
    ActualDeliveryInfoResponse,
    ActualDeliveryInfoSchema,
    AddressSchema,
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
    EditOrderItemsRequest,
    EditOrderRequest,
    EditPackageSchema,
    EditPackagesRequest,
    EditPlaceSwapSchema,
    EditTaskResponse,
    EditTaskStatusResponse,
    EstimatedDeliveryIntervalsRequest,
    IntakeStatusResponse,
    IntakeWindowSchema,
    MoneySchema,
    ParcelSchema,
    PickupPointSchema,
    PickupPointsRequest,
    PickupPointsResponse,
    RefusalRequestSchema,
    RemoveOrderItemsRequest,
    ReturnResponse,
    ReverseAvailabilityRequestSchema,
    ReverseAvailabilityResponse,
    ShipmentResponse,
    ShippingRateSchema,
    TrackingEventSchema,
    TrackingResponse,
)
from src.shared.exceptions import ValidationError as AppValidationError

logistics_router = APIRouter(
    prefix="/logistics",
    tags=["Logistics"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Schema → domain mapping helpers
# ---------------------------------------------------------------------------


def _schema_to_address(s: AddressSchema) -> Address:
    return Address(
        country_code=s.country_code,
        city=s.city,
        region=s.region,
        postal_code=s.postal_code,
        street=s.street,
        house=s.house,
        apartment=s.apartment,
        subdivision_code=s.subdivision_code,
        latitude=s.latitude,
        longitude=s.longitude,
        raw_address=s.raw_address,
        metadata=s.metadata,
    )


def _address_to_schema(a: Address) -> AddressSchema:
    return AddressSchema(
        country_code=a.country_code,
        city=a.city,
        region=a.region,
        postal_code=a.postal_code,
        street=a.street,
        house=a.house,
        apartment=a.apartment,
        subdivision_code=a.subdivision_code,
        latitude=a.latitude,
        longitude=a.longitude,
        raw_address=a.raw_address,
        metadata=a.metadata,
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
                currency_code=s.declared_value.currency_code,
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
        amount=Money(amount=s.amount.amount, currency_code=s.amount.currency_code),
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
                    provider_code=q.rate.provider_code,
                    service_code=q.rate.service_code,
                    service_name=q.rate.service_name,
                    delivery_type=q.rate.delivery_type.value,
                    total_cost=MoneySchema(
                        amount=q.rate.total_cost.amount,
                        currency_code=q.rate.total_cost.currency_code,
                    ),
                    base_cost=MoneySchema(
                        amount=q.rate.base_cost.amount,
                        currency_code=q.rate.base_cost.currency_code,
                    ),
                    insurance_cost=(
                        MoneySchema(
                            amount=q.rate.insurance_cost.amount,
                            currency_code=q.rate.insurance_cost.currency_code,
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
        errors=result.errors,
    )


@logistics_router.post(
    path="/shipments",
    status_code=status.HTTP_201_CREATED,
    response_model=ShipmentResponse,
    summary="Create a shipment (DRAFT)",
)
async def create_shipment(
    body: CreateShipmentRequest,
    create_handler: FromDishka[CreateShipmentHandler],
    get_handler: FromDishka[GetShipmentHandler],
) -> ShipmentResponse:
    command = CreateShipmentCommand(
        quote_id=body.quote_id,
        origin=_schema_to_address(body.origin),
        destination=_schema_to_address(body.destination),
        sender=_schema_to_contact(body.sender),
        recipient=_schema_to_contact(body.recipient),
        parcels=[_schema_to_parcel(p) for p in body.parcels],
        order_id=body.order_id,
        cod=_schema_to_cod(body.cod),
    )
    result = await create_handler.handle(command)
    shipment = await get_handler.handle(
        GetShipmentQuery(shipment_id=result.shipment_id)
    )
    return _shipment_to_response(shipment)


@logistics_router.post(
    path="/shipments/{shipment_id}/book",
    status_code=status.HTTP_200_OK,
    response_model=BookShipmentResponse,
    summary="Book a DRAFT shipment with the provider",
)
async def book_shipment(
    shipment_id: uuid.UUID,
    handler: FromDishka[BookShipmentHandler],
) -> BookShipmentResponse:
    result = await handler.handle(BookShipmentCommand(shipment_id=shipment_id))
    return BookShipmentResponse(
        shipment_id=result.shipment_id,
        provider_shipment_id=result.provider_shipment_id,
        tracking_number=result.tracking_number,
    )


@logistics_router.post(
    path="/shipments/{shipment_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=CancelShipmentResponse,
    summary="Cancel a booked shipment",
)
async def cancel_shipment(
    shipment_id: uuid.UUID,
    handler: FromDishka[CancelShipmentHandler],
) -> CancelShipmentResponse:
    result = await handler.handle(CancelShipmentCommand(shipment_id=shipment_id))
    return CancelShipmentResponse(shipment_id=result.shipment_id)


@logistics_router.get(
    path="/shipments/{shipment_id}",
    status_code=status.HTTP_200_OK,
    response_model=ShipmentResponse,
    summary="Get shipment details",
)
async def get_shipment(
    shipment_id: uuid.UUID,
    handler: FromDishka[GetShipmentHandler],
) -> ShipmentResponse:
    shipment = await handler.handle(GetShipmentQuery(shipment_id=shipment_id))
    return _shipment_to_response(shipment)


@logistics_router.get(
    path="/shipments/{shipment_id}/tracking",
    status_code=status.HTTP_200_OK,
    response_model=TrackingResponse,
    summary="Get shipment tracking history",
)
async def get_tracking(
    shipment_id: uuid.UUID,
    handler: FromDishka[GetTrackingHandler],
) -> TrackingResponse:
    result = await handler.handle(GetTrackingQuery(shipment_id=shipment_id))
    return TrackingResponse(
        shipment_id=result.shipment_id,
        tracking_number=result.tracking_number,
        latest_status=result.latest_status,
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
)
async def list_pickup_points(
    body: PickupPointsRequest,
    handler: FromDishka[ListPickupPointsHandler],
) -> PickupPointsResponse:
    try:
        delivery_type = DeliveryType(body.delivery_type) if body.delivery_type else None
    except ValueError:
        valid = [e.value for e in DeliveryType]
        raise AppValidationError(
            message=f"Invalid delivery_type '{body.delivery_type}'. Must be one of: {valid}",
        ) from None

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
    return PickupPointsResponse(
        points=[
            PickupPointSchema(
                provider_code=p.provider_code,
                external_id=p.external_id,
                name=p.name,
                pickup_point_type=p.pickup_point_type.value,
                address=_address_to_schema(p.address),
                work_schedule=p.work_schedule,
                phone=p.phone,
                is_cash_allowed=p.is_cash_allowed,
                is_card_allowed=p.is_card_allowed,
                weight_limit_grams=p.weight_limit_grams,
            )
            for p in result.points
        ],
        errors=result.errors,
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
        provider_code=result.provider_code,
        windows=[
            IntakeWindowSchema(date=w.date, is_workday=w.is_workday)
            for w in result.windows
        ],
    )


@logistics_router.post(
    path="/shipments/{shipment_id}/intake",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateIntakeResponse,
    summary="Schedule a courier intake for a booked shipment",
)
async def create_intake(
    shipment_id: uuid.UUID,
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
    path="/intakes/{provider_code}/{provider_intake_id}",
    status_code=status.HTTP_200_OK,
    response_model=IntakeStatusResponse,
    summary="Get intake status from the provider",
)
async def get_intake_status(
    provider_code: str,
    provider_intake_id: str,
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
    path="/intakes/{provider_code}/{provider_intake_id}",
    status_code=status.HTTP_200_OK,
    response_model=CancelIntakeResponse,
    summary="Cancel a scheduled intake",
)
async def cancel_intake(
    provider_code: str,
    provider_intake_id: str,
    handler: FromDishka[CancelIntakeHandler],
) -> CancelIntakeResponse:
    result = await handler.handle(
        CancelIntakeCommand(
            provider_code=provider_code,
            provider_intake_id=provider_intake_id,
        )
    )
    return CancelIntakeResponse(success=result.success)


# ---------------------------------------------------------------------------
# Delivery schedule endpoints
# ---------------------------------------------------------------------------


@logistics_router.get(
    path="/shipments/{shipment_id}/delivery-intervals",
    status_code=status.HTTP_200_OK,
    response_model=DeliveryIntervalsResponse,
    summary="List available delivery intervals for a booked shipment",
)
async def get_delivery_intervals(
    shipment_id: uuid.UUID,
    handler: FromDishka[GetDeliveryIntervalsHandler],
) -> DeliveryIntervalsResponse:
    result = await handler.handle(GetDeliveryIntervalsQuery(shipment_id=shipment_id))
    return DeliveryIntervalsResponse(
        provider_code=result.provider_code,
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
        provider_code=result.provider_code,
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
    path="/shipments/{shipment_id}/return",
    status_code=status.HTTP_201_CREATED,
    response_model=ReturnResponse,
    summary="Register a client return shipment",
)
async def register_client_return(
    shipment_id: uuid.UUID,
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
    path="/shipments/{shipment_id}/refusal",
    status_code=status.HTTP_201_CREATED,
    response_model=ReturnResponse,
    summary="Register a doorstep refusal",
)
async def register_refusal(
    shipment_id: uuid.UUID,
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
        provider_code=result.provider_code,
        is_available=result.is_available,
        reason=result.reason,
    )


# ---------------------------------------------------------------------------
# Actual delivery info (Yandex 3.05)
# ---------------------------------------------------------------------------


@logistics_router.get(
    path="/shipments/{shipment_id}/actual-delivery-info",
    status_code=status.HTTP_200_OK,
    response_model=ActualDeliveryInfoResponse,
    summary="Get carrier-confirmed delivery date and interval",
)
async def get_actual_delivery_info(
    shipment_id: uuid.UUID,
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
    path="/shipments/{shipment_id}/edit",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Edit recipient / destination / packages on a booked shipment",
)
async def edit_order(
    shipment_id: uuid.UUID,
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
    path="/shipments/{shipment_id}/edit-packages",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Replace package layout (async edit task)",
)
async def edit_order_packages(
    shipment_id: uuid.UUID,
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
    path="/shipments/{shipment_id}/edit-items",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Patch item articles / marking codes (async edit task)",
)
async def edit_order_items(
    shipment_id: uuid.UUID,
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
    path="/shipments/{shipment_id}/remove-items",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EditTaskResponse,
    summary="Reduce or remove items from a booked shipment (async edit task)",
)
async def remove_order_items(
    shipment_id: uuid.UUID,
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
    path="/edit-tasks/{provider_code}/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=EditTaskStatusResponse,
    summary="Poll an asynchronous edit task",
)
async def get_edit_task_status(
    provider_code: str,
    task_id: str,
    handler: FromDishka[GetEditTaskStatusHandler],
) -> EditTaskStatusResponse:
    result = await handler.handle(
        GetEditTaskStatusQuery(provider_code=provider_code, task_id=task_id)
    )
    return EditTaskStatusResponse(
        provider_code=result.provider_code,
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
        provider_code=shipment.provider_code,
        service_code=shipment.service_code,
        delivery_type=shipment.delivery_type.value,
        status=shipment.status.value,
        provider_shipment_id=shipment.provider_shipment_id,
        tracking_number=shipment.tracking_number,
        quoted_cost=MoneySchema(
            amount=shipment.quoted_cost.amount,
            currency_code=shipment.quoted_cost.currency_code,
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
