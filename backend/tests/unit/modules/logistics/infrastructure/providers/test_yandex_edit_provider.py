"""
Regression tests for ``YandexDeliveryEditProvider``:

- 3.06 ``edit_order`` returns ``edit_id`` synchronously and surfaces
  ``EditTaskStatus.SUCCESS``; missing ``edit_id`` raises.
- 3.12 / 3.14 / 3.15 wrap ``editing_task_id`` (202) into a PENDING
  ``EditTaskResult`` and forward the request bodies.
- 3.13 ``get_edit_status`` maps the status string and treats
  HTTP 404 as terminal SUCCESS (ticket already swept).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import (
    Address,
    ContactInfo,
    DeliveryType,
    Dimensions,
    EditItemMarking,
    EditItemRemoval,
    EditOrderRequest,
    EditPackage,
    EditPackageItem,
    EditPlaceSwap,
    EditTaskStatus,
    Parcel,
    Weight,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.edit_provider import (
    YandexDeliveryEditProvider,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def yandex_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


def _parcel(grams: int = 500) -> Parcel:
    return Parcel(
        weight=Weight(grams=grams),
        dimensions=Dimensions(length_cm=10, width_cm=10, height_cm=10),
    )


class TestEditOrder:
    @pytest.mark.asyncio
    async def test_returns_success_with_edit_id(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_edit.return_value = {"edit_id": "edit-123"}
        provider = YandexDeliveryEditProvider(yandex_client)

        result = await provider.edit_order(
            EditOrderRequest(
                order_provider_id="order-uuid",
                recipient=ContactInfo(
                    first_name="Ivan", last_name="Ivanov", phone="+79991234567"
                ),
            )
        )

        assert result.task_id == "edit-123"
        assert result.initial_status is EditTaskStatus.SUCCESS
        body = yandex_client.request_edit.await_args.args[0]
        assert body["request_id"] == "order-uuid"
        assert body["recipient_info"]["phone"] == "79991234567"  # no leading "+"

    @pytest.mark.asyncio
    async def test_destination_picks_pickup_when_delivery_type_pvz(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.request_edit.return_value = {"edit_id": "edit-1"}
        provider = YandexDeliveryEditProvider(yandex_client)

        await provider.edit_order(
            EditOrderRequest(
                order_provider_id="order-uuid",
                destination=Address(
                    country_code="RU",
                    city="Moscow",
                    metadata={"platform_station_id": "dst-uuid"},
                ),
                delivery_type=DeliveryType.PICKUP_POINT,
            )
        )

        body = yandex_client.request_edit.await_args.args[0]
        assert body["destination"]["type"] == "platform_station"

    @pytest.mark.asyncio
    async def test_places_get_swapped_with_old_barcode(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.request_edit.return_value = {"edit_id": "edit-1"}
        provider = YandexDeliveryEditProvider(yandex_client)

        await provider.edit_order(
            EditOrderRequest(
                order_provider_id="order-uuid",
                places=(
                    EditPlaceSwap(
                        old_barcode="OLD",
                        new_barcode="NEW",
                        new_parcel=_parcel(800),
                    ),
                ),
            )
        )

        body = yandex_client.request_edit.await_args.args[0]
        assert body["places"][0]["barcode"] == "OLD"
        assert body["places"][0]["place"]["barcode"] == "NEW"
        assert body["places"][0]["place"]["physical_dims"]["weight_gross"] == 800

    @pytest.mark.asyncio
    async def test_missing_edit_id_raises(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_edit.return_value = {}
        provider = YandexDeliveryEditProvider(yandex_client)

        with pytest.raises(ProviderHTTPError):
            await provider.edit_order(
                EditOrderRequest(
                    order_provider_id="order-uuid",
                    recipient=ContactInfo(
                        first_name="Ivan",
                        last_name="Ivanov",
                        phone="+79991234567",
                    ),
                )
            )


class TestEditPackages:
    @pytest.mark.asyncio
    async def test_async_returns_pending_with_task_id(
        self, yandex_client: AsyncMock
    ) -> None:
        yandex_client.request_places_edit.return_value = {"editing_task_id": "task-1"}
        provider = YandexDeliveryEditProvider(yandex_client)

        result = await provider.edit_packages(
            "order-uuid",
            [
                EditPackage(
                    barcode="PKG-1",
                    weight=Weight(grams=500),
                    dimensions=Dimensions(length_cm=10, width_cm=10, height_cm=10),
                    items=(EditPackageItem(item_barcode="item-1", count=2),),
                )
            ],
        )

        assert result.task_id == "task-1"
        assert result.initial_status is EditTaskStatus.PENDING
        body = yandex_client.request_places_edit.await_args.args[0]
        assert body["request_id"] == "order-uuid"
        assert body["places"][0]["barcode"] == "PKG-1"
        assert body["places"][0]["dimensions"]["weight_gross"] == 500
        assert body["places"][0]["items"] == [{"item_barcode": "item-1", "count": 2}]


class TestEditItemsInstances:
    @pytest.mark.asyncio
    async def test_marking_code_is_optional(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_items_instances_edit.return_value = {
            "editing_task_id": "task-2"
        }
        provider = YandexDeliveryEditProvider(yandex_client)

        result = await provider.edit_items_instances(
            "order-uuid",
            [
                EditItemMarking(
                    item_barcode="item-1",
                    article="A1",
                    marking_code=None,
                )
            ],
        )

        assert result.task_id == "task-2"
        body = yandex_client.request_items_instances_edit.await_args.args[0]
        assert body["items_instances"] == [{"item_barcode": "item-1", "article": "A1"}]


class TestRemoveItems:
    @pytest.mark.asyncio
    async def test_passes_remaining_count(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_items_remove.return_value = {"editing_task_id": "task-3"}
        provider = YandexDeliveryEditProvider(yandex_client)

        await provider.remove_items(
            "order-uuid",
            [
                EditItemRemoval(item_barcode="item-1", remaining_count=0),
                EditItemRemoval(item_barcode="item-2", remaining_count=3),
            ],
        )

        body = yandex_client.request_items_remove.await_args.args[0]
        assert body["items_to_remove"] == [
            {"item_barcode": "item-1", "remaining_count": 0},
            {"item_barcode": "item-2", "remaining_count": 3},
        ]


class TestGetEditStatus:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("pending", EditTaskStatus.PENDING),
            ("execution", EditTaskStatus.EXECUTION),
            ("success", EditTaskStatus.SUCCESS),
            ("failure", EditTaskStatus.FAILURE),
        ],
    )
    @pytest.mark.asyncio
    async def test_maps_known_statuses(
        self,
        yandex_client: AsyncMock,
        raw: str,
        expected: EditTaskStatus,
    ) -> None:
        yandex_client.request_edit_status.return_value = {"status": raw}
        provider = YandexDeliveryEditProvider(yandex_client)

        assert await provider.get_edit_status("task-1") is expected

    @pytest.mark.asyncio
    async def test_unknown_falls_back(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_edit_status.return_value = {"status": "weird"}
        provider = YandexDeliveryEditProvider(yandex_client)

        assert await provider.get_edit_status("task-1") is EditTaskStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_404_translated_to_success(self, yandex_client: AsyncMock) -> None:
        yandex_client.request_edit_status.side_effect = ProviderHTTPError(
            status_code=404, message="not found"
        )
        provider = YandexDeliveryEditProvider(yandex_client)

        assert await provider.get_edit_status("task-1") is EditTaskStatus.SUCCESS
