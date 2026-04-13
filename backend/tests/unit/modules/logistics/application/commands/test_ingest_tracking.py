"""Unit tests for IngestTrackingHandler."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.logistics.application.commands.ingest_tracking import (
    IngestTrackingCommand,
    IngestTrackingHandler,
)
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    Money,
    Parcel,
    ShippingRate,
    TrackingEvent,
    TrackingStatus,
    Weight,
)

pytestmark = pytest.mark.unit


def _make_address() -> Address:
    return Address(
        country_code="RU",
        city="Москва",
        postal_code="101000",
        street="Тверская",
        house="1",
    )


def _make_contact() -> ContactInfo:
    return ContactInfo(
        first_name="Иван",
        last_name="Иванов",
        phone="+79001234567",
    )


def _make_booked_shipment(
    provider_shipment_id: str = "CDEK-12345",
) -> Shipment:
    quote = DeliveryQuote(
        id=uuid.uuid4(),
        rate=ShippingRate(
            provider_code=PROVIDER_CDEK,
            service_code="136",
            service_name="Посылка",
            delivery_type=DeliveryType.PICKUP_POINT,
            total_cost=Money(amount=50000, currency_code="RUB"),
            base_cost=Money(amount=50000, currency_code="RUB"),
        ),
        provider_payload="{}",
        quoted_at=datetime.now(UTC),
    )
    shipment = Shipment.create(
        quote=quote,
        origin=_make_address(),
        destination=_make_address(),
        sender=_make_contact(),
        recipient=_make_contact(),
        parcels=[Parcel(weight=Weight(grams=1000))],
    )
    shipment.mark_booking_pending()
    shipment.mark_booked(provider_shipment_id=provider_shipment_id)
    shipment.clear_domain_events()
    return shipment


def _make_event(
    status: TrackingStatus = TrackingStatus.IN_TRANSIT,
    timestamp: datetime | None = None,
) -> TrackingEvent:
    return TrackingEvent(
        status=status,
        provider_status_code="3",
        provider_status_name="In transit",
        timestamp=timestamp or datetime.now(UTC),
        location="Moscow",
        description="Package in transit",
    )


class TestIngestTrackingHandler:
    def _make_handler(self):
        repo = AsyncMock()
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        logger = MagicMock()
        logger.bind = MagicMock(return_value=logger)
        handler = IngestTrackingHandler(
            shipment_repo=repo,
            uow=uow,
            logger=logger,
        )
        return handler, repo, uow

    @pytest.mark.asyncio
    async def test_ingests_new_events(self):
        handler, repo, uow = self._make_handler()
        shipment = _make_booked_shipment()
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        event = _make_event()
        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            events=[event],
        )

        result = await handler.handle(cmd)

        assert result.shipment_id == shipment.id
        assert result.new_events_count == 1
        repo.update.assert_awaited_once()
        uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_shipment_not_found(self):
        handler, repo, _uow = self._make_handler()
        repo.get_by_provider_shipment_id.return_value = None

        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="NONEXISTENT",
            events=[_make_event()],
        )

        with pytest.raises(ShipmentNotFoundError) as exc_info:
            await handler.handle(cmd)

        assert exc_info.value.details["provider_shipment_id"] == "NONEXISTENT"

    @pytest.mark.asyncio
    async def test_deduplicates_existing_events(self):
        handler, repo, _uow = self._make_handler()
        shipment = _make_booked_shipment()
        existing_event = _make_event(
            status=TrackingStatus.ACCEPTED,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        )
        shipment.append_tracking_event(existing_event)
        repo.get_by_provider_shipment_id.return_value = shipment

        # Try to ingest the same event again
        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            events=[existing_event],
        )

        result = await handler.handle(cmd)
        assert result.new_events_count == 0
        assert len(shipment.tracking_events) == 1
        repo.update.assert_not_awaited()
        _uow.commit.assert_not_awaited()
