"""Fake logistics provider implementations for unit testing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.modules.logistics.domain.value_objects import (
    Address,
    BookingRequest,
    BookingResult,
    CancelResult,
    DeliveryType,
    DocumentResult,
    Money,
    Parcel,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
    ShippingRate,
    TrackingEvent,
    TrackingStatus,
)


class FakeRateProvider:
    """Fake rate provider that returns pre-configured rates."""

    def __init__(
        self,
        code: ProviderCode = ProviderCode.CDEK,
        rates: list[ShippingRate] | None = None,
    ) -> None:
        self._code = code
        self._rates = rates or [
            ShippingRate(
                provider_code=code,
                service_code="test-tariff",
                service_name="Test Delivery",
                delivery_type=DeliveryType.COURIER,
                total_cost=Money(amount=50000, currency_code="RUB"),
                base_cost=Money(amount=50000, currency_code="RUB"),
            ),
        ]

    def provider_code(self) -> ProviderCode:
        return self._code

    async def calculate_rates(
        self, origin: Address, destination: Address, parcels: list[Parcel]
    ) -> list[ShippingRate]:
        return self._rates


class FakeBookingProvider:
    """Fake booking provider that always succeeds."""

    def __init__(
        self,
        code: ProviderCode = ProviderCode.CDEK,
        should_fail: bool = False,
    ) -> None:
        self._code = code
        self._should_fail = should_fail
        self.booked_requests: list[BookingRequest] = []
        self.cancelled_ids: list[str] = []

    def provider_code(self) -> ProviderCode:
        return self._code

    async def book_shipment(self, request: BookingRequest) -> BookingResult:
        self.booked_requests.append(request)
        if self._should_fail:
            raise RuntimeError("Fake booking failure")
        return BookingResult(
            provider_shipment_id=f"FAKE-{uuid.uuid4().hex[:8]}",
            tracking_number=f"TN-{uuid.uuid4().hex[:6]}",
        )

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult:
        self.cancelled_ids.append(provider_shipment_id)
        if self._should_fail:
            raise RuntimeError("Fake cancel failure")
        return CancelResult(cancelled=True)


class FakeTrackingProvider:
    """Fake tracking provider that returns pre-configured events."""

    def __init__(
        self,
        code: ProviderCode = ProviderCode.CDEK,
        events: list[TrackingEvent] | None = None,
    ) -> None:
        self._code = code
        self._events = events or [
            TrackingEvent(
                status=TrackingStatus.ACCEPTED,
                provider_status_code="ACCEPTED",
                provider_status_name="Accepted",
                timestamp=datetime.now(UTC),
                location="Test City",
                description="Package accepted",
            ),
        ]

    def provider_code(self) -> ProviderCode:
        return self._code

    async def get_tracking(self, provider_shipment_id: str) -> list[TrackingEvent]:
        return self._events


class FakePickupPointProvider:
    """Fake pickup point provider that returns pre-configured points."""

    def __init__(
        self,
        code: ProviderCode = ProviderCode.CDEK,
        points: list[PickupPoint] | None = None,
    ) -> None:
        self._code = code
        self._points = points or [
            PickupPoint(
                provider_code=code,
                external_id="PVZ-001",
                name="Test PVZ",
                pickup_point_type="PVZ",
                address=Address(
                    country_code="RU",
                    city="Москва",
                    postal_code="101000",
                    street="Тестовая",
                    house="1",
                ),
                work_schedule="09:00-21:00",
                phone="+79001234567",
                is_cash_allowed=True,
                is_card_allowed=True,
                weight_limit_grams=30000,
            ),
        ]

    def provider_code(self) -> ProviderCode:
        return self._code

    async def list_pickup_points(self, query: PickupPointQuery) -> list[PickupPoint]:
        return self._points


class FakeDocumentProvider:
    """Fake document provider."""

    def __init__(self, code: ProviderCode = ProviderCode.CDEK) -> None:
        self._code = code

    def provider_code(self) -> ProviderCode:
        return self._code

    async def get_label_url(self, provider_shipment_id: str) -> DocumentResult:
        return DocumentResult(
            url=f"https://fake-labels.test/{provider_shipment_id}.pdf"
        )
