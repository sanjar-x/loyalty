"""Recipient domain value objects.

Holds only shipping-side coordinates: FullName (RU + Lat — used in
greeting / shipping labels), Phone, Email. The customs-side CustomsData
VO + ``RecipientValidationStatus`` enum moved to the new ``passport``
bounded context in Sprint 1.5 Part 2 (ADR-011).
"""

from __future__ import annotations

import re

from attrs import frozen

_FULL_NAME_LAT_RE = re.compile(r"^[A-Za-z][A-Za-z\- ]{0,99}$")
_FULL_NAME_RU_RE = re.compile(r"^[А-Яа-яЁё][А-Яа-яЁё\- ]{0,99}$")
_PHONE_E164_RE = re.compile(r"^\+7\d{10}$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@frozen
class FullName:
    """Shipping recipient's full name (RU + Latin).

    Russian alphabet is what's printed on the parcel label; Latin
    transliteration mirrors what the cross-border courier prints on
    the customs sticker (independent of the passport name — by design,
    you can ship a parcel addressed «To Anna's grandma» without
    bringing grandma's passport into it).
    """

    ru: str
    lat: str

    @classmethod
    def parse(cls, *, ru: str, lat: str) -> FullName:
        from src.modules.recipient.domain.exceptions import (
            InvalidRecipientFieldError,
        )

        ru_stripped = (ru or "").strip()
        lat_stripped = (lat or "").strip()
        if not _FULL_NAME_RU_RE.match(ru_stripped):
            raise InvalidRecipientFieldError(
                field="full_name_ru",
                reason="cyrillic letters, hyphen and spaces only (1..100 chars)",
            )
        if not _FULL_NAME_LAT_RE.match(lat_stripped):
            raise InvalidRecipientFieldError(
                field="full_name_lat",
                reason="latin letters, hyphen and spaces only (1..100 chars)",
            )
        return cls(ru=ru_stripped, lat=lat_stripped)


@frozen
class Phone:
    e164: str

    @classmethod
    def parse(cls, value: str) -> Phone:
        from src.modules.recipient.domain.exceptions import (
            InvalidRecipientFieldError,
        )

        v = (value or "").replace(" ", "").replace("-", "")
        if not _PHONE_E164_RE.match(v):
            raise InvalidRecipientFieldError(
                field="phone",
                reason="must be in +7XXXXXXXXXX (E.164) format",
            )
        return cls(e164=v)


@frozen
class Email:
    value: str

    @classmethod
    def parse(cls, value: str) -> Email:
        from src.modules.recipient.domain.exceptions import (
            InvalidRecipientFieldError,
        )

        v = (value or "").strip()
        if len(v) > 254 or not _EMAIL_RE.match(v):
            raise InvalidRecipientFieldError(
                field="email", reason="invalid email format"
            )
        return cls(value=v)
