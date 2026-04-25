"""
Yandex Delivery edit provider — implements ``IEditProvider``.

Wraps the five edit-style endpoints into a single capability:

- POST /api/b2b/platform/request/edit (3.06) — recipient / destination /
  package swap. Returns a synchronous ``edit_id``.
- POST /api/b2b/platform/request/places/edit (3.12) — async, full
  package layout replacement. Returns 202 + ``editing_task_id``.
- POST /api/b2b/platform/request/items-instances/edit (3.14) — async,
  per-item article + marking patch. Returns 202 + ``editing_task_id``.
- POST /api/b2b/platform/request/items/remove (3.15) — async, item
  count reduction / removal. Returns 202 + ``editing_task_id``.
- POST /api/b2b/platform/request/edit/status (3.13) — poll the async
  ticket by ``editing_task_id``.

For 3.06 the API returns a *synchronous* ``edit_id`` rather than an
async ``editing_task_id``; we still wrap it in ``EditTaskResult`` with
``initial_status = SUCCESS`` so callers can use a single polling /
inspection flow regardless of which mutation they invoked. Polling
3.13 with an ``edit_id`` yields ``404 not_found``, which the caller
must treat as "already complete".
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    ContactInfo,
    DeliveryType,
    EditItemMarking,
    EditItemRemoval,
    EditOrderRequest,
    EditPackage,
    EditPlaceSwap,
    EditTaskResult,
    EditTaskStatus,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    LAST_MILE_COURIER,
    LAST_MILE_PICKUP,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    build_redelivery_destination,
)

logger = logging.getLogger(__name__)


_YANDEX_EDIT_STATUS_MAP: dict[str, EditTaskStatus] = {
    "pending": EditTaskStatus.PENDING,
    "execution": EditTaskStatus.EXECUTION,
    "success": EditTaskStatus.SUCCESS,
    "failure": EditTaskStatus.FAILURE,
}


class YandexDeliveryEditProvider:
    """Yandex Delivery implementation of ``IEditProvider``."""

    def __init__(self, client: YandexDeliveryClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    # ------------------------------------------------------------------ #
    # 3.06 — recipient / destination / packages                            #
    # ------------------------------------------------------------------ #

    async def edit_order(self, request: EditOrderRequest) -> EditTaskResult:
        body = _build_edit_order_body(request)
        async with self._client:
            data = await self._client.request_edit(body)

        edit_id = (data.get("edit_id") or "") if isinstance(data, dict) else ""
        if not edit_id:
            raise ProviderHTTPError(
                status_code=0,
                message="Yandex /request/edit returned no edit_id",
                response_body=json.dumps(data, ensure_ascii=False, default=str),
            )
        # 3.06 finishes synchronously — surface SUCCESS so callers can
        # short-circuit polling.
        return EditTaskResult(
            task_id=edit_id,
            initial_status=EditTaskStatus.SUCCESS,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )

    # ------------------------------------------------------------------ #
    # 3.12 — packages full replacement                                     #
    # ------------------------------------------------------------------ #

    async def edit_packages(
        self,
        order_provider_id: str,
        packages: list[EditPackage],
    ) -> EditTaskResult:
        body: dict[str, Any] = {
            "request_id": order_provider_id,
            "places": [_build_edit_package(p) for p in packages],
        }
        async with self._client:
            data = await self._client.request_places_edit(body)
        return _async_edit_result(data)

    # ------------------------------------------------------------------ #
    # 3.14 — per-item marking / article patch                              #
    # ------------------------------------------------------------------ #

    async def edit_items_instances(
        self,
        order_provider_id: str,
        items: list[EditItemMarking],
    ) -> EditTaskResult:
        body: dict[str, Any] = {
            "request_id": order_provider_id,
            "items_instances": [_build_item_instance(i) for i in items],
        }
        async with self._client:
            data = await self._client.request_items_instances_edit(body)
        return _async_edit_result(data)

    # ------------------------------------------------------------------ #
    # 3.15 — reduce / remove items                                         #
    # ------------------------------------------------------------------ #

    async def remove_items(
        self,
        order_provider_id: str,
        items: list[EditItemRemoval],
    ) -> EditTaskResult:
        body: dict[str, Any] = {
            "request_id": order_provider_id,
            "items_to_remove": [
                {"item_barcode": i.item_barcode, "remaining_count": i.remaining_count}
                for i in items
            ],
        }
        async with self._client:
            data = await self._client.request_items_remove(body)
        return _async_edit_result(data)

    # ------------------------------------------------------------------ #
    # 3.13 — async ticket status                                           #
    # ------------------------------------------------------------------ #

    async def get_edit_status(self, task_id: str) -> EditTaskStatus:
        async with self._client:
            try:
                data = await self._client.request_edit_status(task_id)
            except ProviderHTTPError as exc:
                # 404 is the documented signal that the ticket completed
                # and has been swept — treat as SUCCESS rather than a
                # hard failure to keep the polling loop simple.
                if exc.status_code == 404:
                    return EditTaskStatus.SUCCESS
                raise
        raw_status = (data.get("status") or "") if isinstance(data, dict) else ""
        return _YANDEX_EDIT_STATUS_MAP.get(raw_status, EditTaskStatus.UNKNOWN)


# ---------------------------------------------------------------------------
# Body builders
# ---------------------------------------------------------------------------


def _build_edit_order_body(request: EditOrderRequest) -> dict[str, Any]:
    body: dict[str, Any] = {"request_id": request.order_provider_id}
    if request.recipient is not None:
        body["recipient_info"] = _build_recipient(request.recipient)
    if request.destination is not None:
        last_mile = (
            LAST_MILE_PICKUP
            if request.delivery_type == DeliveryType.PICKUP_POINT
            else LAST_MILE_COURIER
        )
        body["destination"] = build_redelivery_destination(
            request.destination, last_mile
        )
    if request.places:
        body["places"] = [_build_place_swap(p) for p in request.places]
    return body


def _build_recipient(contact: ContactInfo) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        # Yandex requires the phone number without a leading "+"
        "phone": contact.phone_e164_digits,
    }
    if contact.middle_name:
        payload["patronymic"] = contact.middle_name
    if contact.email:
        payload["email"] = contact.email
    return payload


def _build_place_swap(swap: EditPlaceSwap) -> dict[str, Any]:
    parcel = swap.new_parcel
    physical: dict[str, Any] = {"weight_gross": parcel.weight.grams}
    if parcel.dimensions:
        physical["dx"] = parcel.dimensions.length_cm
        physical["dy"] = parcel.dimensions.width_cm
        physical["dz"] = parcel.dimensions.height_cm
    return {
        "barcode": swap.old_barcode,
        "place": {
            "physical_dims": physical,
            "barcode": swap.new_barcode,
        },
    }


def _build_edit_package(package: EditPackage) -> dict[str, Any]:
    return {
        "barcode": package.barcode,
        "dimensions": {
            "weight_gross": package.weight.grams,
            "dx": package.dimensions.length_cm,
            "dy": package.dimensions.width_cm,
            "dz": package.dimensions.height_cm,
        },
        "items": [
            {"item_barcode": item.item_barcode, "count": item.count}
            for item in package.items
        ],
    }


def _build_item_instance(item: EditItemMarking) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "item_barcode": item.item_barcode,
        "article": item.article,
    }
    if item.marking_code:
        payload["marking_code"] = item.marking_code
    return payload


# ---------------------------------------------------------------------------
# Async ticket helper
# ---------------------------------------------------------------------------


def _async_edit_result(data: Any) -> EditTaskResult:
    """Wrap a 202 ``editing_task_id`` response into ``EditTaskResult``."""
    task_id = (data.get("editing_task_id") or "") if isinstance(data, dict) else ""
    if not task_id:
        raise ProviderHTTPError(
            status_code=0,
            message="Yandex async edit returned no editing_task_id",
            response_body=json.dumps(data, ensure_ascii=False, default=str)
            if data
            else None,
        )
    return EditTaskResult(
        task_id=task_id,
        initial_status=EditTaskStatus.PENDING,
        raw_response=json.dumps(data, ensure_ascii=False, default=str)
        if data
        else None,
    )
