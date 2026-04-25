"""
Yandex Delivery booking provider — implements ``IBookingProvider``.

Uses the 2-step offer flow: POST offers/create → POST offers/confirm.
Cancel via POST request/cancel.
"""

import json
import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    BookingRequest,
    BookingResult,
    CancelResult,
    EstimatedDelivery,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    build_offers_create_request,
    parse_cancel_response,
    parse_confirm_response,
    parse_offers_response,
)

logger = logging.getLogger(__name__)


class YandexDeliveryBookingProvider:
    """Yandex Delivery implementation of ``IBookingProvider``.

    Booking flow:
    1. POST /offers/create → returns offers with offer_id (10-min TTL)
    2. Pick first offer, POST /offers/confirm → returns request_id
    """

    def __init__(self, client: YandexDeliveryClient, config: dict[str, Any]) -> None:
        self._client = client
        self._config = config

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def book_shipment(self, request: BookingRequest) -> BookingResult:
        body = build_offers_create_request(request, self._config)

        # Step 1: Create offers
        offers_data = await self._client.offers_create(body)
        offers = parse_offers_response(offers_data)

        if not offers:
            raise ProviderHTTPError(
                status_code=400,
                message="No delivery offers returned by Yandex",
                response_body=json.dumps(offers_data, ensure_ascii=False),
            )

        offer = offers[0]
        offer_id = offer["offer_id"]

        # Step 2: Confirm the offer
        confirm_data = await self._client.offers_confirm(offer_id)
        request_id = parse_confirm_response(confirm_data)

        estimated = _extract_estimated_delivery(offer)

        return BookingResult(
            provider_shipment_id=request_id,
            tracking_number=None,
            estimated_delivery=estimated,
            provider_response_payload=json.dumps(
                {"offer": offer, "confirm": confirm_data},
                ensure_ascii=False,
                default=str,
            ),
        )

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult:
        try:
            data = await self._client.cancel_request(provider_shipment_id)
        except ProviderHTTPError as exc:
            return CancelResult(success=False, reason=str(exc))

        success, reason = parse_cancel_response(data)
        return CancelResult(success=success, reason=reason)


def _extract_estimated_delivery(offer: dict[str, Any]) -> EstimatedDelivery | None:
    """Extract estimated delivery from offer_details."""
    details = offer.get("offer_details", {})
    delivery_interval = details.get("delivery_interval", {})

    max_dt_str = delivery_interval.get("max")
    if max_dt_str:
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(max_dt_str.replace("Z", "+00:00"))
            return EstimatedDelivery(estimated_date=dt)
        except (ValueError, AttributeError) as _exc:
            pass

    return None
