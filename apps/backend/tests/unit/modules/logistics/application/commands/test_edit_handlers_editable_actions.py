"""
Unit tests for the editable-actions pre-check in the edit command handlers.

The handlers query the carrier's per-order ``available_actions`` (Yandex
3.03) before submitting an edit, so an operator gets a clear, typed
``ConflictError`` instead of an opaque provider 4xx. Covered here for
``EditOrderPackagesHandler`` (single-flag guard) and ``EditOrderHandler``
(conditional, per-field guard); the items / remove-items handlers reuse
the single-flag shape verified for packages.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.logistics.application.commands.edit_order import (
    EditOrderCommand,
    EditOrderHandler,
)
from src.modules.logistics.application.commands.edit_order_packages import (
    EditOrderPackagesCommand,
    EditOrderPackagesHandler,
)
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    Address,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    Dimensions,
    EditableActions,
    EditPackage,
    EditPackageItem,
    EditTaskResult,
    EditTaskStatus,
    Money,
    Parcel,
    ShippingRate,
    Weight,
)
from src.shared.exceptions import ConflictError

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Fixtures / builders
# --------------------------------------------------------------------------- #


def _addr() -> Address:
    return Address(country_code="RU", city="Москва", street="Тверская", house="1")


def _contact() -> ContactInfo:
    return ContactInfo(first_name="Иван", last_name="Иванов", phone="+79001234567")


def _booked_shipment() -> Shipment:
    quote = DeliveryQuote(
        id=uuid.uuid4(),
        rate=ShippingRate(
            provider_code=PROVIDER_YANDEX_DELIVERY,
            service_code="time_interval",
            service_name="Yandex Delivery",
            delivery_type=DeliveryType.COURIER,
            total_cost=Money(amount=50000, currency_code="RUB"),
            base_cost=Money(amount=50000, currency_code="RUB"),
        ),
        provider_payload="{}",
        quoted_at=datetime.now(UTC),
    )
    shipment = Shipment.create(
        quote=quote,
        origin=_addr(),
        destination=_addr(),
        sender=_contact(),
        recipient=_contact(),
        parcels=[Parcel(weight=Weight(grams=1000))],
    )
    shipment.mark_booking_pending()
    shipment.mark_booked(provider_shipment_id="YD-123")
    shipment.clear_domain_events()
    return shipment


def _package() -> EditPackage:
    return EditPackage(
        barcode="PKG-1",
        weight=Weight(grams=500),
        dimensions=Dimensions(length_cm=10, width_cm=10, height_cm=10),
        items=(EditPackageItem(item_barcode="i1", count=1),),
    )


def _deps(
    shipment: Shipment, *, editable: EditableActions
) -> tuple[AsyncMock, MagicMock, AsyncMock, MagicMock, AsyncMock]:
    """Wire the four handler dependencies plus the edit-provider mock.

    ``registry.get_edit_provider`` is synchronous on the real registry,
    so it is a plain ``MagicMock`` returning the async provider mock.
    """
    repo = AsyncMock()
    repo.get_by_id.return_value = shipment
    repo.update.return_value = shipment

    provider = AsyncMock()
    provider.get_editable_actions.return_value = editable

    registry = MagicMock()
    registry.get_edit_provider = MagicMock(return_value=provider)

    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    # register_aggregate is sync on the real UoW — keep it a MagicMock so
    # an un-awaited coroutine warning never fires.
    uow.register_aggregate = MagicMock()

    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return repo, registry, uow, logger, provider


# --------------------------------------------------------------------------- #
# EditOrderPackagesHandler — single-flag guard
# --------------------------------------------------------------------------- #


class TestEditPackagesGuard:
    @pytest.mark.asyncio
    async def test_blocked_when_update_places_false(self) -> None:
        shipment = _booked_shipment()
        repo, registry, uow, logger, provider = _deps(
            shipment, editable=EditableActions(update_places=False)
        )
        handler = EditOrderPackagesHandler(repo, registry, uow, logger)
        command = EditOrderPackagesCommand(
            shipment_id=shipment.id, packages=(_package(),)
        )

        with pytest.raises(ConflictError) as exc:
            await handler.handle(command)

        assert exc.value.error_code == "EDIT_ACTION_NOT_AVAILABLE"
        # The edit must not be submitted once the pre-check fails.
        provider.edit_packages.assert_not_awaited()
        uow.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_proceeds_when_allowed(self) -> None:
        shipment = _booked_shipment()
        repo, registry, uow, logger, provider = _deps(
            shipment, editable=EditableActions()
        )
        provider.edit_packages.return_value = EditTaskResult(
            task_id="task-1", initial_status=EditTaskStatus.PENDING
        )
        handler = EditOrderPackagesHandler(repo, registry, uow, logger)
        command = EditOrderPackagesCommand(
            shipment_id=shipment.id, packages=(_package(),)
        )

        result = await handler.handle(command)

        provider.get_editable_actions.assert_awaited_once_with("YD-123")
        provider.edit_packages.assert_awaited_once()
        assert result.task_id == "task-1"


# --------------------------------------------------------------------------- #
# EditOrderHandler — conditional, per-field guard
# --------------------------------------------------------------------------- #


class TestEditOrderGuard:
    @pytest.mark.asyncio
    async def test_blocks_only_the_unavailable_field(self) -> None:
        shipment = _booked_shipment()
        repo, registry, uow, logger, provider = _deps(
            shipment, editable=EditableActions(update_address=False)
        )
        handler = EditOrderHandler(repo, registry, uow, logger)
        command = EditOrderCommand(shipment_id=shipment.id, destination=_addr())

        with pytest.raises(ConflictError) as exc:
            await handler.handle(command)

        assert exc.value.error_code == "EDIT_ACTION_NOT_AVAILABLE"
        assert "destination" in exc.value.message
        provider.edit_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_allows_recipient_when_only_address_is_blocked(self) -> None:
        # The guard is per-field: a blocked destination must not stop an
        # unrelated recipient-only edit.
        shipment = _booked_shipment()
        repo, registry, uow, logger, provider = _deps(
            shipment, editable=EditableActions(update_address=False)
        )
        provider.edit_order.return_value = EditTaskResult(
            task_id="edit-1", initial_status=EditTaskStatus.SUCCESS
        )
        handler = EditOrderHandler(repo, registry, uow, logger)
        command = EditOrderCommand(shipment_id=shipment.id, recipient=_contact())

        result = await handler.handle(command)

        provider.edit_order.assert_awaited_once()
        assert result.task_id == "edit-1"
