"""Recipient read-models (customer + admin views)."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class RecipientReadModel:
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


@dataclass(frozen=True)
class RecipientListPage:
    items: list[RecipientReadModel]
