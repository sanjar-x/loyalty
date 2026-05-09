"""Unit tests for ``parse_if_match`` + ``attach_etag`` (C4.1)."""

from __future__ import annotations

import pytest
from fastapi import Response

from src.api.dependencies.etag import attach_etag, parse_if_match

pytestmark = pytest.mark.unit


def test_parse_returns_none_when_header_absent() -> None:
    assert parse_if_match(None) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('"v5"', 5),
        ("v7", 7),
        ('  "v123"  ', 123),
        ('"v0"', 0),
    ],
)
def test_parse_extracts_version(raw: str, expected: int) -> None:
    assert parse_if_match(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        '"v"',  # missing digit
        "5",  # missing v prefix
        '"abc"',
        '"v1.0"',
        'W/"v5"',  # weak validator — we use strong only
    ],
)
def test_parse_returns_none_for_malformed(raw: str) -> None:
    """Malformed values fall through as None — the route handler then
    treats this as 'no precondition' and falls back to legacy locking."""
    assert parse_if_match(raw) is None


def test_attach_etag_writes_strong_validator() -> None:
    response = Response()
    attach_etag(response, version=42)
    assert response.headers["ETag"] == '"v42"'
    # Strong validator — no leading W/ prefix.
    assert not response.headers["ETag"].startswith("W/")
