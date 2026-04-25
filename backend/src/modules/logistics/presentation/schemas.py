"""
Pydantic request/response schemas for the Logistics API.

Presentation layer — maps between JSON request bodies / responses
and application-layer commands/queries.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Common nested schemas
# ---------------------------------------------------------------------------


class AddressSchema(BaseModel):
    country_code: str = Field(
        ..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code"
    )
    city: str = Field(..., min_length=1)
    region: str | None = None
    postal_code: str | None = None
    street: str | None = None
    house: str | None = None
    apartment: str | None = None
    subdivision_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    raw_address: str | None = None
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Provider-specific address references (e.g. fias_guid, cdek_city_code)",
    )


class ContactInfoSchema(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    middle_name: str | None = None
    email: str | None = None
    company_name: str | None = None


class WeightSchema(BaseModel):
    grams: int = Field(..., gt=0, description="Weight in grams")


class DimensionsSchema(BaseModel):
    length_cm: int = Field(..., gt=0)
    width_cm: int = Field(..., gt=0)
    height_cm: int = Field(..., gt=0)


class MoneySchema(BaseModel):
    amount: int = Field(
        ..., ge=0, description="Amount in smallest currency unit (e.g. kopecks)"
    )
    currency_code: str = Field(
        ..., min_length=3, max_length=3, description="ISO 4217 currency code"
    )


class ParcelSchema(BaseModel):
    weight: WeightSchema
    dimensions: DimensionsSchema | None = None
    declared_value: MoneySchema | None = None
    description: str | None = None


class CashOnDeliverySchema(BaseModel):
    amount: MoneySchema
    payment_method: str | None = Field(
        None, description='e.g. "cash", "card", "postpay"'
    )


# ---------------------------------------------------------------------------
# Rate calculation
# ---------------------------------------------------------------------------


class CalculateRatesRequest(BaseModel):
    origin: AddressSchema
    destination: AddressSchema
    parcels: list[ParcelSchema] = Field(..., min_length=1)


class ShippingRateSchema(BaseModel):
    provider_code: str
    service_code: str
    service_name: str
    delivery_type: str
    total_cost: MoneySchema
    base_cost: MoneySchema
    insurance_cost: MoneySchema | None = None
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None


class DeliveryQuoteSchema(BaseModel):
    id: uuid.UUID
    rate: ShippingRateSchema
    provider_payload: str
    quoted_at: datetime
    expires_at: datetime | None = None


class CalculateRatesResponse(BaseModel):
    quotes: list[DeliveryQuoteSchema]
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="Provider-specific errors (provider_code → message)",
    )


# ---------------------------------------------------------------------------
# Shipment CRUD
# ---------------------------------------------------------------------------


class CreateShipmentRequest(BaseModel):
    """Create shipment from a server-side quote.

    Only quote_id is required — price, provider, service details are
    looked up from the trusted server-side DeliveryQuote record.
    """

    quote_id: uuid.UUID = Field(..., description="ID of the selected DeliveryQuote")
    origin: AddressSchema
    destination: AddressSchema
    sender: ContactInfoSchema
    recipient: ContactInfoSchema
    parcels: list[ParcelSchema] = Field(..., min_length=1)
    order_id: uuid.UUID | None = None
    cod: CashOnDeliverySchema | None = None


class ShipmentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID | None
    provider_code: str
    service_code: str
    delivery_type: str
    status: str
    provider_shipment_id: str | None
    tracking_number: str | None
    quoted_cost: MoneySchema
    latest_tracking_status: str | None
    created_at: datetime
    updated_at: datetime
    booked_at: datetime | None
    cancelled_at: datetime | None


class BookShipmentResponse(BaseModel):
    shipment_id: uuid.UUID
    provider_shipment_id: str
    tracking_number: str | None


class CancelShipmentResponse(BaseModel):
    shipment_id: uuid.UUID


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------


class TrackingEventSchema(BaseModel):
    status: str
    provider_status_code: str
    provider_status_name: str
    timestamp: datetime
    location: str | None = None
    description: str | None = None


class TrackingResponse(BaseModel):
    shipment_id: uuid.UUID
    tracking_number: str | None
    latest_status: str | None
    events: list[TrackingEventSchema]


# ---------------------------------------------------------------------------
# Pickup points
# ---------------------------------------------------------------------------


class PickupPointsRequest(BaseModel):
    country_code: str | None = Field(
        None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code"
    )
    city: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: int | None = None
    provider_code: str | None = None
    delivery_type: str | None = None


class PickupPointSchema(BaseModel):
    provider_code: str
    external_id: str
    name: str
    pickup_point_type: str
    address: AddressSchema
    work_schedule: str | None = None
    phone: str | None = None
    is_cash_allowed: bool
    is_card_allowed: bool
    weight_limit_grams: int | None = None


class PickupPointsResponse(BaseModel):
    points: list[PickupPointSchema]
    errors: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Intake (courier pickup) schemas
# ---------------------------------------------------------------------------


class IntakeWindowSchema(BaseModel):
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    is_workday: bool = True


class AvailableIntakeDaysRequest(BaseModel):
    provider_code: str
    address: AddressSchema
    until: str | None = Field(None, description="Optional upper bound (YYYY-MM-DD)")


class AvailableIntakeDaysResponse(BaseModel):
    provider_code: str
    windows: list[IntakeWindowSchema]


class CreateIntakeRequest(BaseModel):
    intake_date: str = Field(..., description="Pickup date (YYYY-MM-DD)")
    intake_time_from: str = Field(..., description="Earliest pickup time (HH:MM)")
    intake_time_to: str = Field(..., description="Latest pickup time (HH:MM)")
    comment: str | None = None
    lunch_time_from: str | None = None
    lunch_time_to: str | None = None
    need_call: bool = False


class CreateIntakeResponse(BaseModel):
    shipment_id: uuid.UUID
    provider_intake_id: str
    status: str


class IntakeStatusResponse(BaseModel):
    provider_intake_id: str
    status: str


class CancelIntakeResponse(BaseModel):
    success: bool


# ---------------------------------------------------------------------------
# Delivery schedule schemas
# ---------------------------------------------------------------------------


class DeliveryIntervalSchema(BaseModel):
    start_time: str
    end_time: str
    date: str | None = None


class DeliveryIntervalsResponse(BaseModel):
    provider_code: str
    intervals: list[DeliveryIntervalSchema]


class EstimatedDeliveryIntervalsRequest(BaseModel):
    provider_code: str
    origin: AddressSchema
    destination: AddressSchema
    tariff_code: int = Field(..., ge=1)


# ---------------------------------------------------------------------------
# Returns / refusals schemas
# ---------------------------------------------------------------------------


class ClientReturnRequest(BaseModel):
    tariff_code: int = Field(..., ge=1)
    return_address: AddressSchema
    sender: ContactInfoSchema
    recipient: ContactInfoSchema


class RefusalRequestSchema(BaseModel):
    reason: str | None = Field(
        None,
        description="Free-form audit note. Not forwarded to the provider.",
    )


class ReturnResponse(BaseModel):
    shipment_id: uuid.UUID
    success: bool
    provider_return_id: str | None = None
    reason: str | None = None


class ReverseAvailabilityRequestSchema(BaseModel):
    provider_code: str
    tariff_code: int = Field(..., ge=1)
    sender_phones: list[str] = Field(..., min_length=1, max_length=10)
    recipient_phones: list[str] = Field(..., min_length=1, max_length=10)
    from_location: AddressSchema | None = None
    to_location: AddressSchema | None = None
    shipment_point: str | None = None
    delivery_point: str | None = None
    sender_contragent_type: str | None = Field(
        None, description="LEGAL_ENTITY or INDIVIDUAL"
    )
    recipient_contragent_type: str | None = Field(
        None, description="LEGAL_ENTITY or INDIVIDUAL"
    )


class ReverseAvailabilityResponse(BaseModel):
    provider_code: str
    is_available: bool
    reason: str | None = None


# ---------------------------------------------------------------------------
# Actual delivery info (Yandex 3.05)
# ---------------------------------------------------------------------------


class ActualDeliveryInfoSchema(BaseModel):
    delivery_date: str = Field(..., description="ISO date YYYY-MM-DD")
    interval_start: str = Field(..., description="Local time HH:MM")
    interval_end: str = Field(..., description="Local time HH:MM")
    timezone_offset: str | None = Field(
        None, description='Original tz suffix (e.g. "+03:00")'
    )


class ActualDeliveryInfoResponse(BaseModel):
    shipment_id: uuid.UUID
    info: ActualDeliveryInfoSchema | None = None


# ---------------------------------------------------------------------------
# Edit operations (Yandex 3.06 / 3.12 / 3.13 / 3.14 / 3.15)
# ---------------------------------------------------------------------------


class EditTaskResponse(BaseModel):
    shipment_id: uuid.UUID
    task_id: str
    initial_status: str


class EditTaskStatusResponse(BaseModel):
    provider_code: str
    task_id: str
    status: str


class EditPlaceSwapSchema(BaseModel):
    old_barcode: str = Field(..., min_length=1)
    new_barcode: str = Field(..., min_length=1)
    new_parcel: ParcelSchema


class EditOrderRequest(BaseModel):
    """At least one of recipient / destination / places must be supplied."""

    recipient: ContactInfoSchema | None = None
    destination: AddressSchema | None = None
    delivery_type: str | None = Field(
        None, description="courier | pickup_point | post_office"
    )
    places: list[EditPlaceSwapSchema] = Field(default_factory=list)


class EditPackageItemSchema(BaseModel):
    item_barcode: str = Field(..., min_length=1)
    count: int = Field(..., ge=0)


class EditPackageSchema(BaseModel):
    barcode: str = Field(..., min_length=1)
    weight: WeightSchema
    dimensions: DimensionsSchema
    items: list[EditPackageItemSchema] = Field(..., min_length=1)


class EditPackagesRequest(BaseModel):
    packages: list[EditPackageSchema] = Field(..., min_length=1)


class EditItemMarkingSchema(BaseModel):
    item_barcode: str = Field(..., min_length=1)
    article: str = Field(..., min_length=1)
    marking_code: str | None = None


class EditOrderItemsRequest(BaseModel):
    items: list[EditItemMarkingSchema] = Field(..., min_length=1)


class EditItemRemovalSchema(BaseModel):
    item_barcode: str = Field(..., min_length=1)
    remaining_count: int = Field(..., ge=0, description="0 removes the item entirely")


class RemoveOrderItemsRequest(BaseModel):
    removals: list[EditItemRemovalSchema] = Field(..., min_length=1)
