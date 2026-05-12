"""Recipient endpoint schemas (camelCase)."""

import uuid
from datetime import date, datetime

from pydantic import Field

from shared.schemas import CamelModel


class CreateRecipientRequest(CamelModel):
    full_name_ru: str = Field(min_length=1, max_length=255)
    full_name_lat: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=2, max_length=20)
    email: str = Field(min_length=3, max_length=255)
    passport_serial: str = Field(min_length=4, max_length=4)
    passport_number: str = Field(min_length=6, max_length=6)
    passport_issue_date: date
    birth_date: date
    inn: str = Field(min_length=12, max_length=12)


class UpdateRecipientRequest(CamelModel):
    full_name_ru: str | None = None
    full_name_lat: str | None = None
    phone: str | None = None
    email: str | None = None
    passport_serial: str | None = None
    passport_number: str | None = None
    passport_issue_date: date | None = None
    birth_date: date | None = None
    inn: str | None = None


class RecipientSchema(CamelModel):
    recipient_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str
    validation_status: str
    validation_failed_reason: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    version: int = 0


class RecipientListResponse(CamelModel):
    items: list[RecipientSchema]


class CreateRecipientResponse(CamelModel):
    recipient_id: uuid.UUID
