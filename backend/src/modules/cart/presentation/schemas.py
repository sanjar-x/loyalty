"""
Pydantic request/response schemas for Cart customer-facing endpoints.

All schemas inherit from CamelModel for automatic snake_case → camelCase.
"""

import uuid
from datetime import datetime

from pydantic import Field

from src.shared.schemas import CamelModel

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AddItemRequest(CamelModel):
    sku_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=99)


class UpdateQuantityRequest(CamelModel):
    quantity: int = Field(ge=1, le=99)


class InitiateCheckoutRequest(CamelModel):
    pickup_point_id: uuid.UUID


class ConfirmCheckoutRequest(CamelModel):
    attempt_id: uuid.UUID


class MergeCartRequest(CamelModel):
    anonymous_token: str = Field(min_length=1, max_length=512)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class MoneyResponse(CamelModel):
    amount: int = Field(description="Amount in smallest currency unit (kopecks)")
    currency: str = "RUB"


class CartItemResponse(CamelModel):
    id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str | None = None
    variant_label: str | None = None
    image_url: str | None = None
    quantity: int
    unit_price: MoneyResponse | None = None
    line_total: MoneyResponse | None = None
    supplier_type: str
    added_at: datetime


class CartGroupResponse(CamelModel):
    supplier_type: str
    items: list[CartItemResponse]
    subtotal: MoneyResponse


class CartResponse(CamelModel):
    id: uuid.UUID
    status: str
    item_count: int
    total: MoneyResponse
    groups: list[CartGroupResponse]
    frozen_until: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CartSummaryResponse(CamelModel):
    item_count: int
    total: MoneyResponse


class CheckoutInitiatedResponse(CamelModel):
    attempt_id: uuid.UUID
    snapshot_id: uuid.UUID
    expires_at: datetime


class CheckoutConfirmedResponse(CamelModel):
    order_id: uuid.UUID


class AnonymousTokenResponse(CamelModel):
    token: str


class AddItemResponse(CamelModel):
    cart_id: uuid.UUID
    item_id: uuid.UUID
