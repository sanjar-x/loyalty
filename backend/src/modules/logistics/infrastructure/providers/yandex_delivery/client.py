"""
Yandex Delivery HTTP client — typed wrapper around ``BaseProviderClient``.

Covers the Yandex Delivery "Other Day" (межгород) API:
pricing calculator, offers (create/confirm), order management,
tracking history, pickup points, labels, and location detection.
"""

import logging
from typing import Any

from src.modules.logistics.infrastructure.providers.base_auth import (
    BearerTokenAuthManager,
)
from src.modules.logistics.infrastructure.providers.base_client import (
    BaseProviderClient,
    ProviderClientConfig,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    PATH_GENERATE_LABELS,
    PATH_HANDOVER_ACT,
    PATH_LOCATION_DETECT,
    PATH_OFFERS_CONFIRM,
    PATH_OFFERS_CREATE,
    PATH_OFFERS_INFO_POST,
    PATH_PICKUP_POINTS_LIST,
    PATH_PRICING_CALCULATOR,
    PATH_REQUEST_ACTUAL_INFO,
    PATH_REQUEST_CANCEL,
    PATH_REQUEST_CREATE,
    PATH_REQUEST_DATETIME_OPTIONS,
    PATH_REQUEST_EDIT,
    PATH_REQUEST_EDIT_STATUS,
    PATH_REQUEST_HISTORY,
    PATH_REQUEST_INFO,
    PATH_REQUEST_ITEMS_INSTANCES_EDIT,
    PATH_REQUEST_ITEMS_REMOVE,
    PATH_REQUEST_PLACES_EDIT,
    PATH_REQUEST_REDELIVERY_OPTIONS,
    PATH_REQUESTS_INFO,
)

logger = logging.getLogger(__name__)


class YandexDeliveryClient:
    """Yandex Delivery API HTTP client.

    Composes ``BaseProviderClient`` for auth/retry and adds typed
    methods for each Yandex Delivery endpoint.

    Usage::

        client = YandexDeliveryClient(base_url, oauth_token)
        async with client:
            result = await client.pricing_calculator({...})
    """

    def __init__(
        self,
        base_url: str,
        oauth_token: str,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._auth = BearerTokenAuthManager(token=oauth_token)
        self._provider_client = BaseProviderClient(
            auth_manager=self._auth,
            config=ProviderClientConfig(
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            ),
        )

    async def __aenter__(self) -> YandexDeliveryClient:
        await self._provider_client.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._provider_client.__aexit__(*exc)

    async def close(self) -> None:
        """Release the underlying httpx connection pool.

        Called by ``YandexDeliveryProviderFactory.close`` at app
        shutdown. Idempotent — repeat calls no-op.
        """
        await self._provider_client.close()

    # ------------------------------------------------------------------ #
    # Pricing                                                              #
    # ------------------------------------------------------------------ #

    async def pricing_calculator(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /pricing-calculator — preliminary cost estimation."""
        resp = await self._provider_client.request(
            "POST", PATH_PRICING_CALCULATOR, json=body
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Offers                                                               #
    # ------------------------------------------------------------------ #

    async def offers_create(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /offers/create — create delivery offers (returns offer_id)."""
        resp = await self._provider_client.request(
            "POST", PATH_OFFERS_CREATE, json=body
        )
        return resp.json()

    async def offers_confirm(self, offer_id: str) -> dict[str, Any]:
        """POST /offers/confirm — confirm an offer, creating the order."""
        resp = await self._provider_client.request(
            "POST", PATH_OFFERS_CONFIRM, json={"offer_id": offer_id}
        )
        return resp.json()

    async def offers_info(
        self,
        body: dict[str, Any],
        *,
        last_mile_policy: str | None = None,
        is_oversized: bool | None = None,
        send_unix: bool | None = None,
    ) -> dict[str, Any]:
        """POST /offers/info — pre-booking delivery intervals.

        Returns ``{"offers": [{"from": ..., "to": ...}, ...]}`` where each
        offer is a UTC time window the courier can deliver in.
        """
        params: dict[str, Any] = {}
        if last_mile_policy is not None:
            params["last_mile_policy"] = last_mile_policy
        if is_oversized is not None:
            params["is_oversized"] = "true" if is_oversized else "false"
        if send_unix is not None:
            params["send_unix"] = "true" if send_unix else "false"
        resp = await self._provider_client.request(
            "POST", PATH_OFFERS_INFO_POST, json=body, params=params or None
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Order management                                                     #
    # ------------------------------------------------------------------ #

    async def request_create(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /request/create — quick 1-step order creation."""
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_CREATE, json=body
        )
        return resp.json()

    async def get_request_info(self, request_id: str) -> dict[str, Any]:
        """GET /request/info — get order info + current status."""
        resp = await self._provider_client.request(
            "GET", PATH_REQUEST_INFO, params={"request_id": request_id}
        )
        return resp.json()

    async def get_requests_info(self, request_ids: list[str]) -> dict[str, Any]:
        """POST /requests/info — batch get orders info."""
        resp = await self._provider_client.request(
            "POST",
            PATH_REQUESTS_INFO,
            json={"request_ids": ",".join(request_ids)},
        )
        return resp.json()

    async def get_request_history(self, request_id: str) -> dict[str, Any]:
        """GET /request/history — status history (tracking events)."""
        resp = await self._provider_client.request(
            "GET", PATH_REQUEST_HISTORY, params={"request_id": request_id}
        )
        return resp.json()

    async def cancel_request(self, request_id: str) -> dict[str, Any]:
        """POST /request/cancel — cancel an order."""
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_CANCEL, json={"request_id": request_id}
        )
        return resp.json()

    async def get_actual_info(self, request_id: str) -> dict[str, Any]:
        """GET /request/actual_info — actual delivery date + interval.

        Only valid for orders that have not yet reached
        ``DELIVERY_DELIVERED`` / ``ERROR`` / ``CANCELLED`` statuses.
        """
        resp = await self._provider_client.request(
            "GET", PATH_REQUEST_ACTUAL_INFO, params={"request_id": request_id}
        )
        return resp.json()

    async def request_datetime_options(self, request_id: str) -> dict[str, Any]:
        """POST /request/datetime_options — intervals for the order's current address."""
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_DATETIME_OPTIONS, json={"request_id": request_id}
        )
        return resp.json()

    async def request_redelivery_options(
        self, request_id: str, destination: dict[str, Any]
    ) -> dict[str, Any]:
        """POST /request/redelivery_options — intervals for a new destination."""
        body: dict[str, Any] = {
            "request_id": request_id,
            "destination": destination,
        }
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_REDELIVERY_OPTIONS, json=body
        )
        return resp.json()

    async def request_edit(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /request/edit — edit recipient / destination / packages."""
        resp = await self._provider_client.request("POST", PATH_REQUEST_EDIT, json=body)
        return resp.json()

    async def request_places_edit(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /request/places/edit — async edit of the box / item layout."""
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_PLACES_EDIT, json=body
        )
        return resp.json()

    async def request_items_instances_edit(
        self, body: dict[str, Any]
    ) -> dict[str, Any]:
        """POST /request/items-instances/edit — async edit of item markings / SKUs."""
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_ITEMS_INSTANCES_EDIT, json=body
        )
        return resp.json()

    async def request_items_remove(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /request/items/remove — async reduce / remove items."""
        resp = await self._provider_client.request(
            "POST", PATH_REQUEST_ITEMS_REMOVE, json=body
        )
        return resp.json()

    async def request_edit_status(self, editing_task_id: str) -> dict[str, Any]:
        """POST /request/edit/status — poll an async editing task."""
        resp = await self._provider_client.request(
            "POST",
            PATH_REQUEST_EDIT_STATUS,
            params={"editing_task_id": editing_task_id},
        )
        return resp.json()

    async def get_handover_act(
        self,
        *,
        request_ids: list[str] | None = None,
        request_codes: list[str] | None = None,
        new_requests: bool | None = None,
        created_since: int | None = None,
        created_until: int | None = None,
        editable_format: bool = False,
    ) -> bytes:
        """POST /request/get-handover-act — bulk handover act PDF / Word.

        At least one filter must be supplied: ``new_requests``,
        ``created_since`` / ``created_until``, ``request_ids`` or
        ``request_codes``. Returns the document body as raw bytes.
        """
        params: dict[str, Any] = {}
        if new_requests is not None:
            params["new_requests"] = "true" if new_requests else "false"
        if created_since is not None:
            params["created_since"] = created_since
        if created_until is not None:
            params["created_until"] = created_until
        if editable_format:
            params["editable_format"] = "true"

        body: dict[str, Any] = {}
        if request_ids:
            body["request_ids"] = request_ids
        if request_codes:
            body["request_codes"] = request_codes

        resp = await self._provider_client.request(
            "POST",
            PATH_HANDOVER_ACT,
            json=body or None,
            params=params or None,
        )
        return resp.content

    # ------------------------------------------------------------------ #
    # Location                                                             #
    # ------------------------------------------------------------------ #

    async def detect_location(self, location: str) -> dict[str, Any]:
        """POST /location/detect — get geo_id for a locality name."""
        resp = await self._provider_client.request(
            "POST", PATH_LOCATION_DETECT, json={"location": location}
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Pickup points                                                        #
    # ------------------------------------------------------------------ #

    async def list_pickup_points(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /pickup-points/list — list drop-off and pickup points."""
        resp = await self._provider_client.request(
            "POST", PATH_PICKUP_POINTS_LIST, json=body
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Labels / documents                                                   #
    # ------------------------------------------------------------------ #

    async def generate_labels(
        self,
        request_ids: list[str],
        *,
        generate_type: str = "one",
        language: str = "ru",
    ) -> bytes:
        """POST /generate-labels — generate PDF labels for orders.

        Returns raw PDF bytes.
        """
        resp = await self._provider_client.request(
            "POST",
            PATH_GENERATE_LABELS,
            json={
                "request_ids": request_ids,
                "generate_type": generate_type,
                "language": language,
            },
        )
        return resp.content
