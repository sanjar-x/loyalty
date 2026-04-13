"""Geo domain value objects.

Contains immutable types for geographic and locale reference data
used across multiple bounded contexts.  Part of the domain layer --
zero infrastructure imports.
"""

import re
from decimal import Decimal

from attrs import frozen

# ------------------------------------------------------------------ #
#  ISO 3166-1 Country
# ------------------------------------------------------------------ #

_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")
_ALPHA3_RE = re.compile(r"^[A-Z]{3}$")
_NUMERIC_RE = re.compile(r"^\d{3}$")


@frozen
class Country:
    """Immutable value object representing a country per ISO 3166-1.

    Attributes:
        alpha2: ISO 3166-1 Alpha-2 code (e.g. ``"KZ"``).
        alpha3: ISO 3166-1 Alpha-3 code (e.g. ``"KAZ"``).
        numeric: Zero-padded 3-digit ISO 3166-1 Numeric code (e.g. ``"398"``).

    Raises:
        ValueError: If any field fails format validation at construction time.
    """

    alpha2: str
    alpha3: str
    numeric: str

    def __attrs_post_init__(self) -> None:
        if not _ALPHA2_RE.match(self.alpha2):
            raise ValueError(
                f"alpha2 must be exactly 2 uppercase ASCII letters, got {self.alpha2!r}"
            )
        if not _ALPHA3_RE.match(self.alpha3):
            raise ValueError(
                f"alpha3 must be exactly 3 uppercase ASCII letters, got {self.alpha3!r}"
            )
        if not _NUMERIC_RE.match(self.numeric):
            raise ValueError(f"numeric must be exactly 3 digits, got {self.numeric!r}")


# ------------------------------------------------------------------ #
#  IETF BCP 47 Language
# ------------------------------------------------------------------ #

_BCP47_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")
_ISO639_1_RE = re.compile(r"^[a-z]{2}$")
_ISO639_23_RE = re.compile(r"^[a-z]{3}$")
_SCRIPT_RE = re.compile(r"^[A-Z][a-z]{3}$")
_DIRECTION_VALUES = frozenset({"ltr", "rtl"})


@frozen
class Language:
    """Immutable value object representing a language per ISO 639 / BCP 47.

    Attributes:
        code: IETF BCP 47 tag (e.g. ``"uz-Latn"``, ``"en"``).
        iso639_1: ISO 639-1 two-letter code, or ``None``.
        iso639_2: ISO 639-2/T three-letter code, or ``None``.
        iso639_3: ISO 639-3 three-letter code, or ``None``.
        script: ISO 15924 script code, or ``None``.
        name_en: English reference name.
        name_native: Endonym.
        direction: Text direction — ``"ltr"`` or ``"rtl"``.

    Raises:
        ValueError: If any field fails format validation at construction time.
    """

    code: str
    iso639_1: str | None
    iso639_2: str | None
    iso639_3: str | None
    script: str | None
    name_en: str
    name_native: str
    direction: str

    def __attrs_post_init__(self) -> None:
        if not _BCP47_RE.match(self.code):
            raise ValueError(f"code must be a valid BCP 47 tag, got {self.code!r}")
        if self.iso639_1 is not None and not _ISO639_1_RE.match(self.iso639_1):
            raise ValueError(
                f"iso639_1 must be exactly 2 lowercase letters, got {self.iso639_1!r}"
            )
        if self.iso639_2 is not None and not _ISO639_23_RE.match(self.iso639_2):
            raise ValueError(
                f"iso639_2 must be exactly 3 lowercase letters, got {self.iso639_2!r}"
            )
        if self.iso639_3 is not None and not _ISO639_23_RE.match(self.iso639_3):
            raise ValueError(
                f"iso639_3 must be exactly 3 lowercase letters, got {self.iso639_3!r}"
            )
        if self.script is not None and not _SCRIPT_RE.match(self.script):
            raise ValueError(
                f"script must be a 4-letter ISO 15924 code (e.g. 'Latn'), got {self.script!r}"
            )
        if not self.name_en or not self.name_en.strip():
            raise ValueError("name_en must be a non-empty string")
        if not self.name_native or not self.name_native.strip():
            raise ValueError("name_native must be a non-empty string")
        if self.direction not in _DIRECTION_VALUES:
            raise ValueError(
                f"direction must be 'ltr' or 'rtl', got {self.direction!r}"
            )


# ------------------------------------------------------------------ #
#  ISO 3166-2 Subdivision
# ------------------------------------------------------------------ #

_CURRENCY_CODE_RE = re.compile(r"^[A-Z]{3}$")
_CURRENCY_NUMERIC_RE = re.compile(r"^\d{3}$")


@frozen
class Currency:
    """Immutable value object representing a currency per ISO 4217.

    Attributes:
        code: ISO 4217 alpha-3 code (e.g. ``"UZS"``).
        numeric: Zero-padded 3-digit numeric code (e.g. ``"860"``).
        name: Common English name (e.g. ``"Uzbekistan Sum"``).
        minor_unit: Number of decimal places (0-4), or ``None`` for
            special codes like ``XXX`` (no currency).

    Raises:
        ValueError: If any field fails format validation at construction time.
    """

    code: str
    numeric: str
    name: str
    minor_unit: int | None

    def __attrs_post_init__(self) -> None:
        if not _CURRENCY_CODE_RE.match(self.code):
            raise ValueError(
                f"code must be exactly 3 uppercase ASCII letters, got {self.code!r}"
            )
        if not _CURRENCY_NUMERIC_RE.match(self.numeric):
            raise ValueError(f"numeric must be exactly 3 digits, got {self.numeric!r}")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if self.minor_unit is not None and not (0 <= self.minor_unit <= 4):
            raise ValueError(f"minor_unit must be 0-4 or None, got {self.minor_unit}")


# ------------------------------------------------------------------ #
#  ISO 3166-2 Subdivision
# ------------------------------------------------------------------ #

_SUBDIVISION_CODE_RE = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,8}$")


@frozen
class Subdivision:
    """Immutable value object representing an ISO 3166-2 subdivision.

    Attributes:
        code: Full ISO 3166-2 code (e.g. ``"UZ-TO"``, ``"RU-MOW"``).
        country_code: Parent country Alpha-2 code.
        type_code: Administrative type token (e.g. ``"PROVINCE"``).
        parent_code: Parent subdivision code for nested levels, or ``None``.
        latitude: Centroid latitude (WGS 84), or ``None``.
        longitude: Centroid longitude (WGS 84), or ``None``.

    Raises:
        ValueError: If ``code`` does not match ISO 3166-2 format.
    """

    code: str
    country_code: str
    type_code: str
    parent_code: str | None
    latitude: Decimal | None
    longitude: Decimal | None

    def __attrs_post_init__(self) -> None:
        if not _SUBDIVISION_CODE_RE.match(self.code):
            raise ValueError(
                f"code must match ISO 3166-2 format (e.g. 'UZ-TO'), got {self.code!r}"
            )
        if not _ALPHA2_RE.match(self.country_code):
            raise ValueError(
                f"country_code must be 2 uppercase letters, got {self.country_code!r}"
            )
        if not self.type_code or not self.type_code.strip():
            raise ValueError("type_code must be a non-empty string")


# ------------------------------------------------------------------ #
#  District (sub-subdivision municipal formation)
# ------------------------------------------------------------------ #

_OKTMO_PREFIX_RE = re.compile(r"^\d{5}$")


@frozen
class District:
    """Immutable value object representing a district-level municipal formation.

    This is the geo level directly below ISO 3166-2 subdivisions.
    Uses a UUID identifier — no international standard code exists.

    Attributes:
        id: Surrogate UUID identifier.
        subdivision_code: Parent subdivision ISO 3166-2 code.
        type_code: District type token (e.g. ``"RU_MUNICIPAL_DISTRICT"``).
        oktmo_prefix: ОКТМО level-2 prefix (5 digits), or ``None``.
        fias_guid: ФИАС/ГАР OBJECTGUID, or ``None``.
        latitude: Centroid latitude (WGS 84), or ``None``.
        longitude: Centroid longitude (WGS 84), or ``None``.

    Raises:
        ValueError: If ``subdivision_code`` or ``oktmo_prefix`` fails format
            validation at construction time.
    """

    id: str
    subdivision_code: str
    type_code: str
    oktmo_prefix: str | None
    fias_guid: str | None
    latitude: Decimal | None
    longitude: Decimal | None

    def __attrs_post_init__(self) -> None:
        if not _SUBDIVISION_CODE_RE.match(self.subdivision_code):
            raise ValueError(
                f"subdivision_code must match ISO 3166-2 format, got {self.subdivision_code!r}"
            )
        if not self.type_code or not self.type_code.strip():
            raise ValueError("type_code must be a non-empty string")
        if self.oktmo_prefix is not None and not _OKTMO_PREFIX_RE.match(
            self.oktmo_prefix
        ):
            raise ValueError(
                f"oktmo_prefix must be exactly 5 digits, got {self.oktmo_prefix!r}"
            )
