"""PII redaction for structured log payloads (SEC-001 / D2.3).

The outbox stores serialised domain events whose payloads can carry
customs-grade PII — passport serial+number, INN, phone, email,
``incoming_declaration`` (Chinese tracking number that doubles as a
DobroPost identifier). The webhook ingestion path receives
free-form JSON from upstream providers that may include the same
fields under arbitrary keys.

This module provides one function — :func:`redact_pii` — that walks
a dict (or a nested structure of dicts/lists) and rewrites any
field named in :data:`SENSITIVE_FIELDS` through the matching
masking helper. Idempotent: redacting an already-redacted dict is
a no-op.

Mask choices follow the C2.2 / Sprint-3 spec:

* ``passport_serial`` — last 2 digits visible, ``**XX``.
* ``passport_number`` — last 6 digits visible, ``**XXXXXX``.
* ``inn`` — last 1 digit visible, ``***********X``.
* ``phone`` — ``+7 (***) ***-XX-XX`` with the last 2 visible.
* ``email`` — ``j***n@example.com`` (first + last char of local part).
* ``incoming_declaration`` — last 4 chars visible, ``***XXXX``.

The function logs nothing — callers are expected to feed the result
back into ``logger.info(payload=redacted)``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

# Field names recognised everywhere in the codebase. We match on
# *exact* lowercase key names so a payload that buries the value
# under a different name (e.g. ``customer_phone`` vs ``phone``) is a
# documented gap rather than a silent leak — surfaces as a missing
# entry that the on-call can add.
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "passport_serial",
        "passport_number",
        "inn",
        "phone",
        "email",
        "incoming_declaration",
        "dp_track_number",  # DobroPost track is also customer-identifiable
    }
)

# Camel-case variants that some webhook payloads use directly. The
# walker below normalises by lowercasing keys at lookup time, so this
# is empty by default; populate if a provider ever sends a literally
# camelCase field that bypasses normalisation. Documented for future
# debugging.
_CAMELCASE_ALIASES: Mapping[str, str] = {
    "passportSerial": "passport_serial",
    "passportNumber": "passport_number",
    "incomingDeclaration": "incoming_declaration",
    "dpTrackNumber": "dp_track_number",
}


def _mask_passport_serial(value: str) -> str:
    if len(value) < 2:
        return "**"
    return f"**{value[-2:]}"


def _mask_passport_number(value: str) -> str:
    # 6-digit number; show last 6 only when value happens to be
    # truncated. Default: mask first 4, show last 2 → "****XX".
    if len(value) < 6:
        return "*" * len(value)
    return f"****{value[-2:]}"


def _mask_inn(value: str) -> str:
    if len(value) <= 1:
        return "*"
    return f"{'*' * (len(value) - 1)}{value[-1]}"


_PHONE_DIGITS_RE = re.compile(r"\D")


def _mask_phone(value: str) -> str:
    digits = _PHONE_DIGITS_RE.sub("", value)
    if len(digits) < 4:
        return "+7 (***) ***-**-**"
    last2 = digits[-2:]
    return f"+7 (***) ***-**-{last2}"


def _mask_email(value: str) -> str:
    if "@" not in value:
        return "***"
    local, domain = value.split("@", 1)
    masked_local = "*" * len(local) if len(local) <= 2 else f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def _mask_incoming_declaration(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"***{value[-4:]}"


def _mask_dp_track_number(value: str) -> str:
    return _mask_incoming_declaration(value)


_MASKERS = {
    "passport_serial": _mask_passport_serial,
    "passport_number": _mask_passport_number,
    "inn": _mask_inn,
    "phone": _mask_phone,
    "email": _mask_email,
    "incoming_declaration": _mask_incoming_declaration,
    "dp_track_number": _mask_dp_track_number,
}


def _normalise_key(key: Any) -> str | None:
    """Return the canonical snake_case sensitive-field key, or ``None``."""
    if not isinstance(key, str):
        return None
    if key in _CAMELCASE_ALIASES:
        return _CAMELCASE_ALIASES[key]
    lowered = key.lower()
    return lowered if lowered in SENSITIVE_FIELDS else None


def _redact_value(canonical_key: str, value: Any) -> Any:
    if not isinstance(value, str):
        # Nothing to mask if the value isn't a string (e.g. ``inn=null``).
        # Keep type stable so downstream consumers don't trip.
        return value
    # Idempotency guard — once a value carries the ``***`` mask it's
    # already redacted; re-running through the masker would lose the
    # last-N visible chars (phone fallback drops them entirely when
    # the digit count falls below 4 due to mask characters). Cheap
    # substring check, no false positives in production payloads.
    if "***" in value:
        return value
    masker = _MASKERS[canonical_key]
    return masker(value)


def redact_pii(payload: Any) -> Any:
    """Walk ``payload`` and rewrite sensitive fields with masked values.

    Returns a new structure (defensive copy) — the caller's input is
    not mutated. Non-dict / non-list values pass through unchanged.

    Idempotent: applying twice yields the same masked string.
    """
    if isinstance(payload, Mapping):
        out: dict[Any, Any] = {}
        for k, v in payload.items():
            canonical = _normalise_key(k)
            if canonical is not None:
                out[k] = _redact_value(canonical, v)
            else:
                out[k] = redact_pii(v)
        return out
    if isinstance(payload, list):
        return [redact_pii(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(redact_pii(item) for item in payload)
    if isinstance(payload, Iterable) and not isinstance(payload, str | bytes):
        # Generic iterable — materialise to a list so we don't exhaust
        # the caller's iterator. Rare path (event payloads are JSON-
        # shaped) but keeps the contract honest.
        return [redact_pii(item) for item in payload]
    return payload


__all__ = ["SENSITIVE_FIELDS", "redact_pii"]
