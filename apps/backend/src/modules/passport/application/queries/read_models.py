"""Read models for the Passport query side."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import NamedTuple


class PassportReadModel(NamedTuple):
    passport_id: uuid.UUID
    identity_id: uuid.UUID
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
    version: int
