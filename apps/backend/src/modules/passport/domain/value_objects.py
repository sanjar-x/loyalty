"""Passport domain value objects.

Carries the four obligatory DobroPost identifiers (passport
serial + number + issue date, INN, birth date) plus the passport
owner's full name in Russian and Latin alphabets.

Extracted from ``modules.recipient.domain.value_objects`` in Sprint
1.5 Part 2 (ADR-011): customs data and shipping coordinates are two
independent bounded contexts that share only the owning ``identity_id``.
The format-level validators are preserved 1:1 so existing recipients
backfilled into the passports table satisfy the same invariants.

PII storage stays plain for now (TODO: encrypt at rest in prod —
pgcrypto / app-level Fernet). When the encryption story lands it lives
in this module, not in recipient — recipient no longer holds the
sensitive fields.
"""

from __future__ import annotations

import enum
import re
from datetime import UTC, date, datetime

from attrs import frozen

# ---------------------------------------------------------------------------
# Validation status (FSM)
# ---------------------------------------------------------------------------


class PassportValidationStatus(enum.StrEnum):
    """Lifecycle of customs-data validation.

    Transitions::

        PENDING ──► VERIFIED   (DaData / DobroPost validation succeeded)
        PENDING ──► INVALID    (validation failed)
        VERIFIED ──► PENDING   (data edited — re-validation required)
        INVALID  ──► PENDING   (data edited — re-validation required)
    """

    PENDING = "pending"
    VERIFIED = "verified"
    INVALID = "invalid"


# ---------------------------------------------------------------------------
# Format validators (1:1 ported from recipient/domain/value_objects.py)
# ---------------------------------------------------------------------------

_PASSPORT_SERIAL_RE = re.compile(r"^\d{4}$")
_PASSPORT_NUMBER_RE = re.compile(r"^\d{6}$")
_INN_RE = re.compile(r"^\d{12}$")
_FULL_NAME_LAT_RE = re.compile(r"^[A-Za-z][A-Za-z\- ]{0,99}$")
_FULL_NAME_RU_RE = re.compile(r"^[А-Яа-яЁё][А-Яа-яЁё\- ]{0,99}$")

_ISSUE_DATE_MIN = date(1991, 1, 1)
_MIN_AGE_YEARS = 16


def _today_utc() -> date:
    return datetime.now(UTC).date()


# ---------------------------------------------------------------------------
# INN ФЛ checksum — Минфин РФ algorithm (ported)
# ---------------------------------------------------------------------------

_INN_WEIGHTS_11 = (7, 2, 4, 10, 3, 5, 9, 4, 1, 3)
_INN_WEIGHTS_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 1, 3)


def _inn_check_digit(digits: str, weights: tuple[int, ...]) -> int:
    total = sum(int(digits[i]) * w for i, w in enumerate(weights))
    return total % 11 % 10


def _validate_inn_individual(inn: str) -> bool:
    """Validate 12-digit INN (физическое лицо) per Минфин algorithm."""
    if not _INN_RE.match(inn):
        return False
    expected_11 = _inn_check_digit(inn, _INN_WEIGHTS_11)
    expected_12 = _inn_check_digit(inn, _INN_WEIGHTS_12)
    return expected_11 == int(inn[10]) and expected_12 == int(inn[11])


def _is_at_least_age(born: date, min_age: int) -> bool:
    today = _today_utc()
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return years >= min_age


# ---------------------------------------------------------------------------
# FullName (passport owner name, RU + Lat)
# ---------------------------------------------------------------------------


@frozen
class FullName:
    """Passport owner full name.

    Russian alphabet is what's printed on the passport; Latin
    transliteration is what DobroPost forwards to the customs officer.
    Both are required — pre-Sprint-1.5 they were on the Recipient but
    semantically belong to the passport document, not to the shipping
    address.
    """

    ru: str
    lat: str

    @classmethod
    def parse(cls, *, ru: str, lat: str) -> FullName:
        from src.modules.passport.domain.exceptions import (
            InvalidPassportFieldError,
        )

        ru_stripped = (ru or "").strip()
        lat_stripped = (lat or "").strip()
        if not _FULL_NAME_RU_RE.match(ru_stripped):
            raise InvalidPassportFieldError(
                field="full_name_ru",
                reason="cyrillic letters, hyphen and spaces only (1..100 chars)",
            )
        if not _FULL_NAME_LAT_RE.match(lat_stripped):
            raise InvalidPassportFieldError(
                field="full_name_lat",
                reason="latin letters, hyphen and spaces only (1..100 chars)",
            )
        return cls(ru=ru_stripped, lat=lat_stripped)


# ---------------------------------------------------------------------------
# CustomsData VO (same shape as before, lives here now)
# ---------------------------------------------------------------------------


@frozen
class CustomsData:
    """Immutable customs-required identifiers (DobroPost contract).

    Attributes:
        passport_serial: Russian passport serial — 4 digits exactly.
        passport_number: Russian passport number — 6 digits exactly.
        passport_issue_date: When the passport was issued
            (must be ≥ 1991-01-01 and ≤ today).
        birth_date: Recipient's date of birth (must be ≥ 16 years ago).
        inn: 12-digit ИНН ФЛ with valid check digits.
    """

    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str

    @classmethod
    def parse(
        cls,
        *,
        passport_serial: str,
        passport_number: str,
        passport_issue_date: date,
        birth_date: date,
        inn: str,
    ) -> CustomsData:
        from src.modules.passport.domain.exceptions import (
            InvalidCustomsDataError,
        )

        ps = (passport_serial or "").strip()
        pn = (passport_number or "").strip()
        inn_str = (inn or "").strip()

        if not _PASSPORT_SERIAL_RE.match(ps):
            raise InvalidCustomsDataError(
                field="passport_serial", reason="must be 4 digits"
            )
        if not _PASSPORT_NUMBER_RE.match(pn):
            raise InvalidCustomsDataError(
                field="passport_number", reason="must be 6 digits"
            )
        if not (_ISSUE_DATE_MIN <= passport_issue_date <= _today_utc()):
            raise InvalidCustomsDataError(
                field="passport_issue_date",
                reason=f"must be between {_ISSUE_DATE_MIN.isoformat()} and today",
            )
        if not _is_at_least_age(birth_date, _MIN_AGE_YEARS):
            raise InvalidCustomsDataError(
                field="birth_date",
                reason=f"passport holder must be at least {_MIN_AGE_YEARS} years old",
            )
        if not _validate_inn_individual(inn_str):
            raise InvalidCustomsDataError(
                field="inn",
                reason="must be 12 digits with valid check digits",
            )
        return cls(
            passport_serial=ps,
            passport_number=pn,
            passport_issue_date=passport_issue_date,
            birth_date=birth_date,
            inn=inn_str,
        )
