"""
CDEK booking provider — implements ``IBookingProvider``.

Creates orders via CDEK API and handles the async order creation
pattern (POST → poll GET for confirmation).
"""

import asyncio
import json
import logging

from src.modules.logistics.domain.exceptions import BookingPendingError
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    BookingRequest,
    BookingResult,
    CancelResult,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    build_order_request,
    parse_order_create_response,
    parse_order_info_response,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

logger = logging.getLogger(__name__)


class CdekBookingProvider:
    """CDEK implementation of ``IBookingProvider``.

    CDEK order creation is asynchronous: POST returns 202 with a UUID,
    and actual processing happens in the background.  After creation,
    we poll GET /v2/orders/{uuid} to confirm the order was accepted.

    The default polling window of 30 attempts × 2 s = 60 s reflects
    CDEK's documented "до нескольких минут" SLA for order acceptance.
    If the response carries no ``statuses`` after the window expires,
    we raise ``ProviderHTTPError`` instead of returning a phantom
    ``BookingResult`` — the caller (BookShipmentHandler) is then free
    to retry while the shipment stays in BOOKING_PENDING.
    """

    def __init__(
        self,
        client: CdekClient,
        *,
        max_poll_attempts: int = 30,
        poll_interval: float = 2.0,
    ) -> None:
        self._client = client
        self._max_poll_attempts = max_poll_attempts
        self._poll_interval = poll_interval

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def book_shipment(self, request: BookingRequest) -> BookingResult:
        body = build_order_request(request)

        create_data = await self._client.create_order(body)
        entity_uuid, requests = parse_order_create_response(create_data)

        if not entity_uuid:
            raise ProviderHTTPError(
                status_code=0,
                message="No entity UUID in CDEK order creation response",
                response_body=json.dumps(create_data, ensure_ascii=False),
            )

        # Check for immediate errors in the requests array
        for req in requests:
            if req.get("state") == "INVALID":
                errors = req.get("errors", [])
                error_msgs = "; ".join(
                    f"{e.get('code', '')}: {e.get('message', '')}" for e in errors
                )
                raise ProviderHTTPError(
                    status_code=400,
                    message=f"CDEK order validation failed: {error_msgs}",
                    response_body=json.dumps(create_data, ensure_ascii=False),
                )

        # Poll for order confirmation
        order_data = await self._poll_order_ready(entity_uuid)

        return parse_order_info_response(order_data)

    async def _poll_order_ready(self, uuid: str) -> dict:
        """Poll GET /v2/orders/{uuid} until order is processed.

        Raises ``ProviderHTTPError`` when the polling window expires
        without any tracking statuses appearing — keeps the caller from
        booking a shipment with no provider state.
        """
        last_data: dict = {}
        for attempt in range(1, self._max_poll_attempts + 1):
            await asyncio.sleep(self._poll_interval)
            last_data = await self._client.get_order(uuid)

            entity = last_data.get("entity", last_data)
            statuses = entity.get("statuses", [])

            # Check for error statuses
            requests = last_data.get("requests", [])
            for req in requests:
                if req.get("state") == "INVALID":
                    errors = req.get("errors", [])
                    error_msgs = "; ".join(
                        f"{e.get('code', '')}: {e.get('message', '')}" for e in errors
                    )
                    raise ProviderHTTPError(
                        status_code=400,
                        message=f"CDEK order processing failed: {error_msgs}",
                        response_body=json.dumps(last_data, ensure_ascii=False),
                    )

            if statuses:
                return last_data

            logger.debug(
                "CDEK order %s not ready yet (attempt %d/%d)",
                uuid,
                attempt,
                self._max_poll_attempts,
            )

        elapsed = self._max_poll_attempts * self._poll_interval
        raise BookingPendingError(
            message=(
                f"CDEK order {uuid} did not produce statuses within {elapsed:.0f}s; "
                "shipment remains in BOOKING_PENDING for retry"
            ),
            details={"provider": PROVIDER_CDEK, "provider_shipment_id": uuid},
        )

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult:
        try:
            data = await self._client.delete_order(provider_shipment_id)
        except ProviderHTTPError as exc:
            return CancelResult(success=False, reason=str(exc))

        requests = data.get("requests", [])
        for req in requests:
            if req.get("state") == "INVALID":
                errors = req.get("errors", [])
                error_msgs = "; ".join(
                    f"{e.get('code', '')}: {e.get('message', '')}" for e in errors
                )
                return CancelResult(success=False, reason=error_msgs)

        return CancelResult(success=True)
