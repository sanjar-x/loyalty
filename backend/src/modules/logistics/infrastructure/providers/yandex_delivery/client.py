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
    PATH_LOCATION_DETECT,
    PATH_OFFERS_CONFIRM,
    PATH_OFFERS_CREATE,
    PATH_PICKUP_POINTS_LIST,
    PATH_PRICING_CALCULATOR,
    PATH_REQUEST_CANCEL,
    PATH_REQUEST_CREATE,
    PATH_REQUEST_HISTORY,
    PATH_REQUEST_INFO,
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
