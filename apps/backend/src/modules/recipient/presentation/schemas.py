"""Recipient endpoint schemas (camelCase wire format).

Post-Sprint-1.5 Part 2: customs fields removed from request /
response. Customers manage passports separately via
``/api/v1/passports``.
"""

import uuid
from datetime import datetime

from pydantic import Field

from src.shared.schemas import CamelModel


class CreateRecipientRequest(CamelModel):
    full_name_ru: str = Field(min_length=1, max_length=255)
    full_name_lat: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=2, max_length=20)
    email: str = Field(min_length=3, max_length=255)


class UpdateRecipientRequest(CamelModel):
    full_name_ru: str | None = None
    full_name_lat: str | None = None
    phone: str | None = None
    email: str | None = None


class RecipientSchema(CamelModel):
    recipient_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    version: int = 0


class RecipientListResponse(CamelModel):
    items: list[RecipientSchema]


class CreateRecipientResponse(CamelModel):
    recipient_id: uuid.UUID
