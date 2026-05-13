"""
Regression tests: ``Shipment`` carries ``min_days`` / ``max_days``
through ``mark_booked`` even when the booking response only echoes an
``estimated_date`` (CDEK doesn't include period_min/max post-booking).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    EstimatedDelivery,
    Money,
    Parcel,
    ShippingRate,
    Weight,
)

pytestmark = pytest.mark.unit


def _quote(min_days: int | None = 2, max_days: int | None = 4) -> DeliveryQuote:
    return DeliveryQuote(
        id=uuid.uuid4(),
        rate=ShippingRate(
            provider_code=PROVIDER_CDEK,
            service_code="136",
            service_name="Посылка склад-склад",
            delivery_type=DeliveryType.PICKUP_POINT,
            total_cost=Money(amount=45000, currency_code="RUB"),
            base_cost=Money(amount=45000, currency_code="RUB"),
            delivery_days_min=min_days,
            delivery_days_max=max_days,
        ),
        provider_payload="{}",
        quoted_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


def _shipment_args() -> dict:
    return {
        "origin": Address(country_code="RU", city="Moscow"),
        "destination": Address(country_code="RU", city="St. Petersburg"),
        "sender": ContactInfo(
            first_name="Ivan", last_name="Ivanov", phone="+79991234567"
        ),
        "recipient": ContactInfo(
            first_name="Petr", last_name="Petrov", phone="+79997654321"
        ),
        "parcels": [Parcel(weight=Weight(grams=500))],
    }


class TestQuoteSeedsEstimatedDelivery:
    def test_create_seeds_min_max_days_from_quote(self) -> None:
        shipment = Shipment.create(quote=_quote(2, 4), **_shipment_args())
        assert shipment.estimated_delivery is not None
        assert shipment.estimated_delivery.min_days == 2
        assert shipment.estimated_delivery.max_days == 4
        assert shipment.estimated_delivery.estimated_date is None

    def test_create_skips_estimate_when_quote_has_no_period(self) -> None:
        shipment = Shipment.create(quote=_quote(None, None), **_shipment_args())
        assert shipment.estimated_delivery is None


class TestMergeOnBooking:
    def test_book_response_with_only_date_keeps_quote_period(self) -> None:
        shipment = Shipment.create(quote=_quote(2, 4), **_shipment_args())
        shipment.mark_booking_pending()

        booked_estimate = EstimatedDelivery(
            estimated_date=datetime(2026, 5, 1, tzinfo=UTC)
        )
        shipment.mark_booked(
            provider_shipment_id="cdek-uuid",
            tracking_number="100500",
            estimated_delivery=booked_estimate,
        )

        assert shipment.estimated_delivery is not None
        # Days survive the merge.
        assert shipment.estimated_delivery.min_days == 2
        assert shipment.estimated_delivery.max_days == 4
        # New date wins.
        assert shipment.estimated_delivery.estimated_date == datetime(
            2026, 5, 1, tzinfo=UTC
        )

    def test_book_response_can_override_individual_field(self) -> None:
        shipment = Shipment.create(quote=_quote(2, 4), **_shipment_args())
        shipment.mark_booking_pending()
        shipment.mark_booked(
            provider_shipment_id="cdek-uuid",
            tracking_number=None,
            estimated_delivery=EstimatedDelivery(min_days=3, max_days=5),
        )
        assert shipment.estimated_delivery is not None
        assert shipment.estimated_delivery.min_days == 3
        assert shipment.estimated_delivery.max_days == 5

    def test_book_response_none_keeps_quote_estimate(self) -> None:
        shipment = Shipment.create(quote=_quote(2, 4), **_shipment_args())
        shipment.mark_booking_pending()
        shipment.mark_booked(
            provider_shipment_id="cdek-uuid",
            tracking_number=None,
            estimated_delivery=None,
        )
        assert shipment.estimated_delivery is not None
        assert shipment.estimated_delivery.min_days == 2
