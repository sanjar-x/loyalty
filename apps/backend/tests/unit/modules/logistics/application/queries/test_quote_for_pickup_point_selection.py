"""Unit tests for ``_select_quote`` — the pure tariff-picking helper.

The DB-touching parts of ``QuoteForPickupPointHandler`` are covered by
integration tests; this file pins down only the selection algorithm so
tariff-ranking changes are caught without spinning up Postgres.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.modules.logistics.application.queries.quote_for_pickup_point import (
    _select_quote,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    DeliveryQuote,
    DeliveryType,
    Money,
    ShippingRate,
)

pytestmark = pytest.mark.unit


def _quote(
    *,
    service_code: str,
    cost_kopecks: int,
    days_min: int | None = None,
) -> DeliveryQuote:
    return DeliveryQuote(
        id=uuid.uuid4(),
        rate=ShippingRate(
            provider_code=PROVIDER_CDEK,
            service_code=service_code,
            service_name=f"CDEK {service_code}",
            delivery_type=DeliveryType.PICKUP_POINT,
            total_cost=Money(amount=cost_kopecks, currency_code="RUB"),
            base_cost=Money(amount=cost_kopecks, currency_code="RUB"),
            delivery_days_min=days_min,
            delivery_days_max=days_min,
        ),
        provider_payload="{}",
        quoted_at=datetime.now(UTC),
    )


def test_returns_cheapest_when_no_service_requested() -> None:
    cheap = _quote(service_code="standard", cost_kopecks=20_000)
    pricey = _quote(service_code="express", cost_kopecks=50_000)
    chosen, alternatives = _select_quote([pricey, cheap], None)
    assert chosen is cheap
    assert alternatives == ["express"]


def test_prefers_explicit_service_code_over_cheapest() -> None:
    cheap = _quote(service_code="standard", cost_kopecks=20_000)
    pricey = _quote(service_code="express", cost_kopecks=50_000)
    chosen, alternatives = _select_quote([cheap, pricey], "express")
    assert chosen is pricey
    assert alternatives == ["standard"]


def test_falls_back_to_cheapest_when_requested_service_missing() -> None:
    cheap = _quote(service_code="standard", cost_kopecks=20_000)
    chosen, alternatives = _select_quote([cheap], "ghost-service")
    assert chosen is cheap
    assert alternatives == []


def test_breaks_cost_ties_by_shorter_delivery_days() -> None:
    slow = _quote(service_code="slow", cost_kopecks=30_000, days_min=5)
    fast = _quote(service_code="fast", cost_kopecks=30_000, days_min=2)
    chosen, alternatives = _select_quote([slow, fast], None)
    assert chosen is fast
    assert alternatives == ["slow"]


def test_returns_none_for_empty_input() -> None:
    chosen, alternatives = _select_quote([], None)
    assert chosen is None
    assert alternatives == []
