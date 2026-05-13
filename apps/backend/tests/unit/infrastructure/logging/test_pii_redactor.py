"""Unit tests for ``redact_pii`` (D2.3 / SEC-001)."""

from __future__ import annotations

import pytest

from src.infrastructure.logging.pii_redactor import SENSITIVE_FIELDS, redact_pii

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("field", "raw", "expected"),
    [
        # passport_serial — 4 digits, last 2 visible
        ("passport_serial", "1234", "**34"),
        ("passport_serial", "12", "**12"),
        ("passport_serial", "1", "**"),
        # passport_number — 6 digits, last 2 visible
        ("passport_number", "567890", "****90"),
        ("passport_number", "12345", "*****"),
        # inn — 12 digits, last 1 visible
        ("inn", "500100732272", "***********2"),
        ("inn", "1", "*"),
        # phone — last 2 visible
        ("phone", "+79108897762", "+7 (***) ***-**-62"),
        ("phone", "+7 910 889 77 62", "+7 (***) ***-**-62"),
        # email — first + last char of local part visible (3 stars)
        ("email", "ivan@example.com", "i***n@example.com"),
        ("email", "ab@example.com", "**@example.com"),
        ("email", "garbage-no-at", "***"),
        # incoming_declaration / dp_track_number — last 4 visible
        ("incoming_declaration", "IN9876543210", "***3210"),
        ("incoming_declaration", "abc", "***"),
        ("dp_track_number", "DPABCDEFGH", "***EFGH"),
    ],
)
def test_field_masking(field: str, raw: str, expected: str) -> None:
    out = redact_pii({field: raw})
    assert out[field] == expected


def test_top_level_keys_redacted() -> None:
    payload = {
        "order_id": "abc-123",
        "phone": "+79001234567",
        "email": "user@example.com",
        "passport_serial": "1234",
    }
    redacted = redact_pii(payload)
    assert redacted["order_id"] == "abc-123"  # not sensitive — passthrough
    assert redacted["phone"] == "+7 (***) ***-**-67"
    assert redacted["email"] == "u***r@example.com"
    assert redacted["passport_serial"] == "**34"


def test_nested_dict_redacted() -> None:
    payload = {
        "shipment_id": "abc",
        "recipient": {
            "phone": "+79001234567",
            "passport_number": "543210",
        },
    }
    redacted = redact_pii(payload)
    assert redacted["recipient"]["phone"] == "+7 (***) ***-**-67"
    assert redacted["recipient"]["passport_number"] == "****10"


def test_list_of_dicts_redacted() -> None:
    payload = {
        "recipients": [
            {"phone": "+79001112233"},
            {"phone": "+79009998877"},
        ]
    }
    redacted = redact_pii(payload)
    phones = [r["phone"] for r in redacted["recipients"]]
    assert phones == [
        "+7 (***) ***-**-33",
        "+7 (***) ***-**-77",
    ]


def test_camelcase_alias_redacted() -> None:
    """Provider webhooks send ``passportSerial`` / ``incomingDeclaration``
    directly. The alias table normalises them so the mask still applies."""
    payload = {
        "passportSerial": "9876",
        "incomingDeclaration": "IN9876543210",
    }
    redacted = redact_pii(payload)
    assert redacted["passportSerial"] == "**76"
    assert redacted["incomingDeclaration"] == "***3210"


def test_idempotent_double_redact() -> None:
    payload = {"phone": "+79001234567", "inn": "500100732272"}
    once = redact_pii(payload)
    twice = redact_pii(once)
    assert once == twice


def test_non_string_value_passes_through() -> None:
    """Numeric / null PII fields are kept verbatim — masking strings
    only is the documented contract; type stability matters for
    downstream JSON consumers."""
    payload = {"inn": None, "phone": 0, "email": False}
    redacted = redact_pii(payload)
    assert redacted == {"inn": None, "phone": 0, "email": False}


def test_does_not_mutate_input() -> None:
    payload = {"phone": "+79001234567", "nested": {"email": "u@e.com"}}
    snapshot = {"phone": "+79001234567", "nested": {"email": "u@e.com"}}
    redact_pii(payload)
    assert payload == snapshot


def test_sensitive_fields_set_is_complete_per_spec() -> None:
    """Locks the contract — adding or renaming a sensitive field must
    update both the constant and this list (so the masker test above
    still parametrises every field)."""
    expected = frozenset(
        {
            "passport_serial",
            "passport_number",
            "inn",
            "phone",
            "email",
            "incoming_declaration",
            "dp_track_number",
        }
    )
    assert SENSITIVE_FIELDS == expected  # noqa: SIM300 — semantics, not order
