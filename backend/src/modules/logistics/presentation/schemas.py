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
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    city: str
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
    first_name: str
    last_name: str
    phone: str
    middle_name: str | None = None
    email: str | None = None
    company_name: str | None = None


class WeightSchema(BaseModel):
    grams: int = Field(..., ge=0, description="Weight in grams")


class DimensionsSchema(BaseModel):
    length_cm: int = Field(..., ge=0)
    width_cm: int = Field(..., ge=0)
    height_cm: int = Field(..., ge=0)


class MoneySchema(BaseModel):
    amount: int = Field(
        ..., description="Amount in smallest currency unit (e.g. kopecks)"
    )
    currency_code: str = Field(..., description="ISO 4217 currency code")


class ParcelSchema(BaseModel):
    weight: WeightSchema
    dimensions: DimensionsSchema | None = None
    declared_value: MoneySchema | None = None
    description: str | None = None


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
    country_code: str | None = None
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
# Webhook
# ---------------------------------------------------------------------------


class WebhookPayload(BaseModel):
    """Generic webhook payload — provider-specific parsing in the adapter."""

    raw: dict = Field(default_factory=dict)
