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
_NUMERIC_MIN = 1
_NUMERIC_MAX = 999


@frozen
class Country:
    """Immutable value object representing a country per ISO 3166-1.

    Attributes:
        alpha2: ISO 3166-1 Alpha-2 code (e.g. ``"KZ"``).
        alpha3: ISO 3166-1 Alpha-3 code (e.g. ``"KAZ"``).
        numeric: ISO 3166-1 Numeric code (e.g. ``398``).
        name: Common short name in English (e.g. ``"Kazakhstan"``).

    Raises:
        ValueError: If any field fails format validation at construction time.
    """

    alpha2: str
    alpha3: str
    numeric: int
    name: str

    def __attrs_post_init__(self) -> None:
        if not _ALPHA2_RE.match(self.alpha2):
            raise ValueError(
                f"alpha2 must be exactly 2 uppercase ASCII letters, got {self.alpha2!r}"
            )
        if not _ALPHA3_RE.match(self.alpha3):
            raise ValueError(
                f"alpha3 must be exactly 3 uppercase ASCII letters, got {self.alpha3!r}"
            )
        if not (_NUMERIC_MIN <= self.numeric <= _NUMERIC_MAX):
            raise ValueError(
                f"numeric must be between {_NUMERIC_MIN} and {_NUMERIC_MAX}, got {self.numeric}"
            )
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")

    @property
    def numeric_str(self) -> str:
        """Zero-padded 3-digit ISO numeric code (e.g. ``"008"``)."""
        return f"{self.numeric:03d}"


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
            raise ValueError(f"direction must be 'ltr' or 'rtl', got {self.direction!r}")


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
        category_code: Administrative category token (e.g. ``"PROVINCE"``).
        parent_code: Parent subdivision code for nested levels, or ``None``.
        latitude: Centroid latitude (WGS 84), or ``None``.
        longitude: Centroid longitude (WGS 84), or ``None``.

    Raises:
        ValueError: If ``code`` does not match ISO 3166-2 format.
    """

    code: str
    country_code: str
    category_code: str
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
        if not self.category_code or not self.category_code.strip():
            raise ValueError("category_code must be a non-empty string")
