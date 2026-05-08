"""
Shared Pydantic base schemas.

* :class:`CamelModel` — base ``BaseModel`` with snake_case → camelCase
  alias generation. Every presentation request/response inherits this.
* :class:`MoneySchema` — canonical wire shape for monetary values
  (``{ amount, currency }``). Promoted from catalog in CAT-018.
* :class:`PaginatedResponse[S]` — generic paginated list response with
  ``items / total / offset / limit + has_next``. Promoted in REC-032.
* :data:`I18nDict` + :func:`validate_i18n_keys` — ISO 639-1 + required
  ``ru/en`` locale validation for translatable fields. Promoted in
  REC-032.
* :data:`BoundedJsonDict` + :func:`validate_bounded_json_dict` — JSON
  bomb protection (size + nesting limits). Promoted in REC-032.

Typical usage:
    from src.shared.schemas import (
        CamelModel,
        MoneySchema,
        PaginatedResponse,
        I18nDict,
    )
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Generic, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Pydantic base with automatic snake_case-to-camelCase aliasing.

    Attributes:
        model_config: Enables population by Python field name while
            serializing to camelCase aliases for JSON consumers.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class MoneySchema(CamelModel):
    """Project-wide canonical wire shape for monetary values.

    ``amount`` is in the smallest currency unit (kopecks for RUB,
    fen for CNY, cents for USD — per ISO 4217 ``minor_unit``).
    ``currency`` is a 3-letter ISO 4217 code, uppercase. Lives in the
    shared kernel so every module's wire contract for money is
    identical (CAT-001 / CAT-018).
    """

    amount: int = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


# ---------------------------------------------------------------------------
# PaginatedResponse — generic paginated list (REC-032 D3)
# ---------------------------------------------------------------------------


_S = TypeVar("_S")


class PaginatedResponse(CamelModel, Generic[_S]):
    """Generic paginated list response with camelCase serialization.

    Promoted from ``catalog/presentation/schemas.py`` in REC-032 — the
    same shape was duplicated in supplier without ``has_next`` and
    inlined as ad-hoc ``*ListResponse`` classes in identity / pricing /
    order. Single source of truth here.
    """

    items: list[_S]
    total: int
    offset: int
    limit: int

    @computed_field
    @property
    def has_next(self) -> bool:
        """True when more items exist beyond the current page."""
        return self.offset + len(self.items) < self.total


# ---------------------------------------------------------------------------
# I18nDict — translatable string maps (REC-032 D4)
# ---------------------------------------------------------------------------

_LANG_CODE_RE = re.compile(r"^[a-z]{2}$")
_MAX_I18N_ENTRIES = 20
_MAX_I18N_VALUE_LENGTH = 10_000
_REQUIRED_LOCALES = {"ru", "en"}


def validate_i18n_keys(value: dict[str, str]) -> dict[str, str]:
    """Validate i18n dict: ISO 639-1 keys, required locales, bounded
    entries and value lengths.

    Used by ``I18nDict`` (catalog Brand / Category / Product titles,
    pricing context names, …). Promoted from catalog in REC-032.
    """
    if len(value) > _MAX_I18N_ENTRIES:
        raise ValueError(
            f"Too many language entries: {len(value)} (max {_MAX_I18N_ENTRIES})"
        )
    missing = _REQUIRED_LOCALES - value.keys()
    if missing:
        raise ValueError(
            f"Missing required locales: {', '.join(sorted(missing))}. "
            f"Both 'ru' and 'en' must be provided."
        )
    for key, val in value.items():
        if not _LANG_CODE_RE.match(key):
            raise ValueError(
                f"Invalid language code '{key}'. "
                f"Keys must be ISO 639-1 two-letter lowercase codes (e.g. 'en', 'ru')."
            )
        if len(val) > _MAX_I18N_VALUE_LENGTH:
            raise ValueError(
                f"Value for '{key}' too long: {len(val)} chars "
                f"(max {_MAX_I18N_VALUE_LENGTH})"
            )
    return value


I18nDict = Annotated[dict[str, str], AfterValidator(validate_i18n_keys)]
"""A ``dict[str, str]`` whose keys are validated as ISO 639-1 language codes."""


# ---------------------------------------------------------------------------
# BoundedJsonDict — JSON bomb protection (REC-032 D4 ride-along)
# ---------------------------------------------------------------------------

_MAX_JSON_DICT_BYTES = 10_240  # 10 KB
_MAX_JSON_DICT_DEPTH = 4


def _check_nesting_depth(obj: Any, current: int = 0) -> int:
    """Return the maximum nesting depth of a JSON-like object."""
    if current > _MAX_JSON_DICT_DEPTH:
        return current
    if isinstance(obj, dict):
        if not obj:
            return current
        return max(_check_nesting_depth(v, current + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return current
        return max(_check_nesting_depth(v, current + 1) for v in obj)
    return current


def validate_bounded_json_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Reject dicts that are too large or too deeply nested (JSON bomb protection)."""
    serialized_size = len(json.dumps(value, default=str))
    if serialized_size > _MAX_JSON_DICT_BYTES:
        raise ValueError(
            f"JSON object too large: {serialized_size} bytes "
            f"(max {_MAX_JSON_DICT_BYTES} bytes)"
        )
    depth = _check_nesting_depth(value)
    if depth > _MAX_JSON_DICT_DEPTH:
        raise ValueError(
            f"JSON object too deeply nested: depth {depth} (max {_MAX_JSON_DICT_DEPTH})"
        )
    return value


BoundedJsonDict = Annotated[dict[str, Any], AfterValidator(validate_bounded_json_dict)]
"""A ``dict[str, Any]`` with size (10 KB) and nesting depth (4) limits."""
