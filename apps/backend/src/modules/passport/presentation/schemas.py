"""Passport endpoint schemas (camelCase wire format)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import Field

from src.shared.schemas import CamelModel


class CreatePassportRequest(CamelModel):
    full_name_ru: str = Field(min_length=1, max_length=255)
    full_name_lat: str = Field(min_length=1, max_length=255)
    passport_serial: str = Field(min_length=4, max_length=4)
    passport_number: str = Field(min_length=6, max_length=6)
    passport_issue_date: date
    birth_date: date
    inn: str = Field(min_length=12, max_length=12)


class UpdatePassportRequest(CamelModel):
    full_name_ru: str | None = None
    full_name_lat: str | None = None
    passport_serial: str | None = None
    passport_number: str | None = None
    passport_issue_date: date | None = None
    birth_date: date | None = None
    inn: str | None = None


class PassportSchema(CamelModel):
    passport_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
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


class PassportListResponse(CamelModel):
    items: list[PassportSchema]


class CreatePassportResponse(CamelModel):
    passport_id: uuid.UUID
