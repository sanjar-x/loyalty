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
    *,
    provider_code: str = PROVIDER_CDEK,
    order_id: uuid.UUID | None = None,
) -> Shipment:
    quote = DeliveryQuote(
        id=uuid.uuid4(),
        rate=ShippingRate(
            provider_code=provider_code,
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
        order_id=order_id,
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


class TestRussianCarrierBridge:
    """LOG-002 — bridge from new tracking events to RussianCarrierTrackingEvent."""

    def _make_handler(self):
        repo = AsyncMock()
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        # enqueue_external_event is sync on the real UoW — mock it as MagicMock
        # so awaits don't trip on it.
        uow.enqueue_external_event = MagicMock()
        logger = MagicMock()
        logger.bind = MagicMock(return_value=logger)
        handler = IngestTrackingHandler(
            shipment_repo=repo,
            uow=uow,
            logger=logger,
        )
        return handler, repo, uow

    @pytest.mark.asyncio
    async def test_bridges_in_transit_to_outbox(self):
        handler, repo, uow = self._make_handler()
        order_id = uuid.uuid4()
        shipment = _make_booked_shipment(order_id=order_id)
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            events=[_make_event(status=TrackingStatus.IN_TRANSIT)],
        )
        await handler.handle(cmd)

        uow.enqueue_external_event.assert_called_once()
        kwargs = uow.enqueue_external_event.call_args.kwargs
        assert kwargs["event_type"] == "RussianCarrierTrackingEvent"
        assert kwargs["aggregate_type"] == "shipment"
        assert kwargs["aggregate_id"] == str(shipment.id)
        assert kwargs["payload"]["order_id"] == str(order_id)
        assert kwargs["payload"]["canonical_status"] == "IN_TRANSIT"
        assert kwargs["payload"]["provider_code"] == PROVIDER_CDEK

    @pytest.mark.asyncio
    async def test_does_not_bridge_dobropost(self):
        from src.modules.logistics.domain.value_objects import PROVIDER_DOBROPOST

        handler, repo, uow = self._make_handler()
        order_id = uuid.uuid4()
        shipment = _make_booked_shipment(
            provider_code=PROVIDER_DOBROPOST,
            order_id=order_id,
        )
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_DOBROPOST,
            provider_shipment_id="DP-12345",
            events=[_make_event(status=TrackingStatus.IN_TRANSIT)],
        )
        await handler.handle(cmd)

        uow.enqueue_external_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_bridge_unmapped_status(self):
        handler, repo, uow = self._make_handler()
        shipment = _make_booked_shipment(order_id=uuid.uuid4())
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            # ACCEPTED has no Order action → no bridge
            events=[_make_event(status=TrackingStatus.ACCEPTED)],
        )
        await handler.handle(cmd)

        uow.enqueue_external_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_bridge_when_no_order_id(self):
        handler, repo, uow = self._make_handler()
        # order_id=None — shipment created out-of-band, not tied to an Order
        shipment = _make_booked_shipment(order_id=None)
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            events=[_make_event(status=TrackingStatus.IN_TRANSIT)],
        )
        await handler.handle(cmd)

        uow.enqueue_external_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_bridges_each_added_event(self):
        handler, repo, uow = self._make_handler()
        shipment = _make_booked_shipment(order_id=uuid.uuid4())
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            events=[
                _make_event(
                    status=TrackingStatus.IN_TRANSIT,
                    timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                ),
                _make_event(
                    status=TrackingStatus.READY_FOR_PICKUP,
                    timestamp=datetime(2026, 5, 2, tzinfo=UTC),
                ),
                # Unmapped status — should not bridge a third event.
                _make_event(
                    status=TrackingStatus.ACCEPTED,
                    timestamp=datetime(2026, 5, 3, tzinfo=UTC),
                ),
            ],
        )
        await handler.handle(cmd)

        # 2 mapped events bridged, 1 unmapped skipped.
        assert uow.enqueue_external_event.call_count == 2
        statuses = [
            c.kwargs["payload"]["canonical_status"]
            for c in uow.enqueue_external_event.call_args_list
        ]
        assert statuses == ["IN_TRANSIT", "AT_PICKUP_POINT"]

    @pytest.mark.asyncio
    async def test_event_id_is_deterministic(self):
        """Same (shipment, status, timestamp) → same UUID5 across runs.

        This is the property that lets the outbox dedupe duplicate
        webhook deliveries without involving the consumer-side inbox.
        """
        handler, repo, uow = self._make_handler()
        shipment = _make_booked_shipment(order_id=uuid.uuid4())
        repo.get_by_provider_shipment_id.return_value = shipment
        repo.update.return_value = shipment

        ts = datetime(2026, 5, 1, 12, 34, 56, tzinfo=UTC)
        cmd = IngestTrackingCommand(
            provider_code=PROVIDER_CDEK,
            provider_shipment_id="CDEK-12345",
            events=[_make_event(status=TrackingStatus.IN_TRANSIT, timestamp=ts)],
        )
        await handler.handle(cmd)

        first_event_id = uow.enqueue_external_event.call_args.kwargs["event_id"]

        # Re-run with a fresh handler/uow but identical inputs — id must match.
        handler2, repo2, uow2 = self._make_handler()
        shipment2 = _make_booked_shipment(order_id=uuid.uuid4())
        # Force the SAME shipment id so the seed matches.
        object.__setattr__(shipment2, "id", shipment.id)
        repo2.get_by_provider_shipment_id.return_value = shipment2
        repo2.update.return_value = shipment2
        await handler2.handle(cmd)

        second_event_id = uow2.enqueue_external_event.call_args.kwargs["event_id"]
        assert first_event_id == second_event_id
