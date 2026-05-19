"""Lightweight factories for Passport-related test fixtures (ADR-011).

Used by Order unit tests that exercise cross-border flows where
``Order.create`` now requires a valid ``passport_snapshot``. Centralised
here so a future change to the snapshot shape is a one-file edit.
"""

import uuid
from datetime import date

from src.modules.order.domain.recipient_snapshot import PassportSnapshot


def make_passport_snapshot(
    *,
    passport_id: uuid.UUID | None = None,
    full_name_ru: str = "Иван Иванов",
    full_name_lat: str = "Ivan Ivanov",
    passport_serial: str = "1234",
    passport_number: str = "567890",
    passport_issue_date: date | None = None,
    birth_date: date | None = None,
    inn: str = "500100732272",
    validation_status: str = "pending",
) -> PassportSnapshot:
    """Build a valid :class:`PassportSnapshot` with sensible defaults."""
    return PassportSnapshot(
        passport_id=str(passport_id or uuid.uuid4()),
        full_name_ru=full_name_ru,
        full_name_lat=full_name_lat,
        passport_serial=passport_serial,
        passport_number=passport_number,
        passport_issue_date=passport_issue_date or date(2015, 5, 22),
        birth_date=birth_date or date(1990, 1, 1),
        inn=inn,
        validation_status=validation_status,
    )
