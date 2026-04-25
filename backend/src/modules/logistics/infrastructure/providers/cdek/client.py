"""
CDEK HTTP client — typed wrapper around BaseProviderClient.

Covers ALL CDEK API v2 endpoint groups: calculator, orders, delivery
points (with pagination), intakes, print (waybills + barcodes),
webhooks, location lookup, delivery intervals, and reverse operations.

The async document/order creation pattern (POST → poll GET → download)
is encapsulated in helper methods.
"""

import asyncio
import logging
from typing import Any

from src.modules.logistics.infrastructure.providers.base_auth import (
    OAuth2ClientCredentialsAuthManager,
)
from src.modules.logistics.infrastructure.providers.base_client import (
    BaseProviderClient,
    ProviderClientConfig,
)
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_TOKEN_PATH,
)
from src.modules.logistics.infrastructure.providers.errors import (
    ProviderHTTPError,
)

logger = logging.getLogger(__name__)


class CdekClient:
    """CDEK API v2 HTTP client.

    Composes ``BaseProviderClient`` for auth/retry and adds typed
    methods for each CDEK endpoint group.

    Usage::

        client = CdekClient(base_url, client_id, client_secret)
        async with client:
            rates = await client.calculate_tariff_list({...})
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        token_url = f"{base_url}{CDEK_TOKEN_PATH}"
        self._auth = OAuth2ClientCredentialsAuthManager(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._provider_client = BaseProviderClient(
            auth_manager=self._auth,
            config=ProviderClientConfig(
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            ),
        )

    async def __aenter__(self) -> CdekClient:
        await self._provider_client.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._provider_client.__aexit__(*exc)

    async def close(self) -> None:
        """Release the underlying httpx connection pool.

        Called by ``CdekProviderFactory.close`` at app shutdown.
        Idempotent — repeat calls no-op.
        """
        await self._provider_client.close()

    # ------------------------------------------------------------------ #
    # Calculator                                                          #
    # ------------------------------------------------------------------ #

    async def calculate_tariff_list(self, body: dict) -> dict:
        """POST /v2/calculator/tarifflist — all available tariffs."""
        resp = await self._provider_client.request(
            "POST", "/v2/calculator/tarifflist", json=body
        )
        return resp.json()

    async def calculate_tariff(self, body: dict) -> dict:
        """POST /v2/calculator/tariff — single tariff rate."""
        resp = await self._provider_client.request(
            "POST", "/v2/calculator/tariff", json=body
        )
        return resp.json()

    async def calculate_tariff_and_service(self, body: dict) -> dict:
        """POST /v2/calculator/tariffAndService — tariffs + additional services."""
        resp = await self._provider_client.request(
            "POST", "/v2/calculator/tariffAndService", json=body
        )
        return resp.json()

    async def list_available_tariffs(self, params: dict | None = None) -> dict:
        """GET /v2/calculator/alltariffs — available tariff catalogue."""
        resp = await self._provider_client.request(
            "GET", "/v2/calculator/alltariffs", params=params
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Orders                                                              #
    # ------------------------------------------------------------------ #

    async def create_order(self, body: dict) -> dict:
        """POST /v2/orders — register a new order (async, returns 202)."""
        resp = await self._provider_client.request("POST", "/v2/orders", json=body)
        return resp.json()

    async def get_order(self, uuid: str) -> dict:
        """GET /v2/orders/{uuid} — order info including statuses."""
        resp = await self._provider_client.request("GET", f"/v2/orders/{uuid}")
        return resp.json()

    async def get_order_by_params(self, params: dict) -> dict:
        """GET /v2/orders — order by cdek_number or im_number."""
        resp = await self._provider_client.request("GET", "/v2/orders", params=params)
        return resp.json()

    async def update_order(self, body: dict) -> dict:
        """PATCH /v2/orders — update an existing order."""
        resp = await self._provider_client.request("PATCH", "/v2/orders", json=body)
        return resp.json()

    async def delete_order(self, uuid: str) -> dict:
        """DELETE /v2/orders/{uuid} — cancel/delete an order."""
        resp = await self._provider_client.request("DELETE", f"/v2/orders/{uuid}")
        return resp.json()

    async def register_client_return(
        self, order_uuid: str, body: dict | None = None
    ) -> dict:
        """POST /v2/orders/{uuid}/clientReturn — register client return."""
        resp = await self._provider_client.request(
            "POST", f"/v2/orders/{order_uuid}/clientReturn", json=body or {}
        )
        return resp.json()

    async def register_refusal(self, order_uuid: str, body: dict | None = None) -> dict:
        """POST /v2/orders/{uuid}/refusal — register delivery refusal."""
        resp = await self._provider_client.request(
            "POST", f"/v2/orders/{order_uuid}/refusal", json=body or {}
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Delivery points (with pagination)                                   #
    # ------------------------------------------------------------------ #

    async def list_delivery_points(self, params: dict) -> list[dict]:
        """GET /v2/deliverypoints — single page of offices/postamats."""
        resp = await self._provider_client.request(
            "GET", "/v2/deliverypoints", params=params
        )
        return resp.json()

    async def list_all_delivery_points(
        self,
        params: dict,
        *,
        page_size: int = 200,
        max_pages: int = 50,
    ) -> list[dict]:
        """Paginate through all delivery points matching *params*.

        CDEK uses ``page`` + ``size`` query params for pagination.
        Returns a flat list of all offices across pages.

        Logs a warning when the ``max_pages`` ceiling is reached and the
        last page was full — the list may have been silently truncated.
        Operators should either narrow the query (``country_code``,
        ``city``) or raise ``max_pages``.
        """
        all_points: list[dict] = []
        page_params = {**params, "size": page_size}
        last_batch_full = False

        for page in range(max_pages):
            page_params["page"] = page
            batch = await self.list_delivery_points(page_params)
            if not batch:
                break
            all_points.extend(batch)
            if len(batch) < page_size:
                last_batch_full = False
                break
            last_batch_full = True
        else:
            # for-else: max_pages exhausted without an early break.
            if last_batch_full:
                logger.warning(
                    "CDEK delivery_points pagination ceiling reached "
                    "(page_size=%d × max_pages=%d = %d points); response may "
                    "be truncated. Narrow the query or raise max_pages.",
                    page_size,
                    max_pages,
                    page_size * max_pages,
                )

        return all_points

    # ------------------------------------------------------------------ #
    # Intakes — courier pickup requests                                   #
    # ------------------------------------------------------------------ #

    async def create_intake(self, body: dict) -> dict:
        """POST /v2/intakes — register courier pickup request."""
        resp = await self._provider_client.request("POST", "/v2/intakes", json=body)
        return resp.json()

    async def get_intake(self, uuid: str) -> dict:
        """GET /v2/intakes/{uuid} — intake info with statuses."""
        resp = await self._provider_client.request("GET", f"/v2/intakes/{uuid}")
        return resp.json()

    async def delete_intake(self, uuid: str) -> dict:
        """DELETE /v2/intakes/{uuid} — cancel intake request."""
        resp = await self._provider_client.request("DELETE", f"/v2/intakes/{uuid}")
        return resp.json()

    async def get_intake_available_days(self, body: dict) -> dict:
        """POST /v2/intakes/availableDays — dates available for courier pickup."""
        resp = await self._provider_client.request(
            "POST", "/v2/intakes/availableDays", json=body
        )
        return resp.json()

    async def get_order_intakes(self, order_uuid: str) -> dict:
        """GET /v2/orders/{orderUuid}/intakes — all intakes for an order."""
        resp = await self._provider_client.request(
            "GET", f"/v2/orders/{order_uuid}/intakes"
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Print — waybills + barcodes                                         #
    # ------------------------------------------------------------------ #

    async def create_waybill(self, order_uuids: list[str]) -> dict:
        """POST /v2/print/orders — request waybill generation."""
        body = {"orders": [{"order_uuid": uid} for uid in order_uuids]}
        resp = await self._provider_client.request(
            "POST", "/v2/print/orders", json=body
        )
        return resp.json()

    async def get_waybill_status(self, uuid: str) -> dict:
        """GET /v2/print/orders/{uuid} — check waybill generation status."""
        resp = await self._provider_client.request("GET", f"/v2/print/orders/{uuid}")
        return resp.json()

    async def download_waybill_pdf(self, uuid: str) -> bytes:
        """GET /v2/print/orders/{uuid}.pdf — download generated waybill."""
        resp = await self._provider_client.request(
            "GET", f"/v2/print/orders/{uuid}.pdf"
        )
        return resp.content

    async def create_barcode(self, order_uuids: list[str]) -> dict:
        """POST /v2/print/barcodes — request barcode label generation."""
        body = {"orders": [{"order_uuid": uid} for uid in order_uuids]}
        resp = await self._provider_client.request(
            "POST", "/v2/print/barcodes", json=body
        )
        return resp.json()

    async def get_barcode_status(self, uuid: str) -> dict:
        """GET /v2/print/barcodes/{uuid} — check barcode generation status."""
        resp = await self._provider_client.request("GET", f"/v2/print/barcodes/{uuid}")
        return resp.json()

    async def download_barcode_pdf(self, uuid: str) -> bytes:
        """GET /v2/print/barcodes/{uuid}.pdf — download generated barcode."""
        resp = await self._provider_client.request(
            "GET", f"/v2/print/barcodes/{uuid}.pdf"
        )
        return resp.content

    async def _poll_print_document(
        self,
        status_fn,
        download_fn,
        *,
        max_attempts: int = 10,
        poll_interval: float = 2.0,
    ) -> bytes:
        """Generic async document polling: check status → download when READY.

        CDEK terminal codes for print forms are ``READY`` (success),
        ``INVALID`` (rejected — e.g. malformed order_uuid) and
        ``REMOVED`` (operator deleted the print job). All non-READY
        terminal codes raise a ``ProviderHTTPError``.

        Sorts ``statuses`` by ``date_time`` before picking the latest;
        the API doesn't guarantee chronological ordering.
        """
        terminal_failures = {"INVALID", "REMOVED"}
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(poll_interval)
            status_resp = await status_fn()
            raw_statuses = status_resp.get("entity", {}).get("statuses", [])
            sorted_statuses = sorted(
                (s for s in raw_statuses if isinstance(s, dict)),
                key=lambda s: s.get("date_time", ""),
            )
            if sorted_statuses:
                latest = sorted_statuses[-1]
                code = latest.get("code")
                if code == "READY":
                    return await download_fn()
                if code in terminal_failures:
                    raise ProviderHTTPError(
                        status_code=0,
                        message=(
                            f"Document generation {code.lower()}: "
                            f"{latest.get('name', '')}"
                        ),
                        response_body=str(status_resp),
                    )
            logger.debug(
                "Document not ready yet (attempt %d/%d)", attempt, max_attempts
            )

        raise ProviderHTTPError(
            status_code=0,
            message=f"Document generation timed out after {max_attempts} attempts",
        )

    async def get_waybill_pdf_with_polling(
        self,
        order_uuid: str,
        *,
        max_attempts: int = 10,
        poll_interval: float = 2.0,
    ) -> bytes:
        """Create waybill → poll → download PDF."""
        create_resp = await self.create_waybill([order_uuid])
        doc_uuid = create_resp.get("entity", {}).get("uuid", "")
        if not doc_uuid:
            raise ProviderHTTPError(
                status_code=0,
                message="No UUID in waybill creation response",
                response_body=str(create_resp),
            )
        return await self._poll_print_document(
            lambda: self.get_waybill_status(doc_uuid),
            lambda: self.download_waybill_pdf(doc_uuid),
            max_attempts=max_attempts,
            poll_interval=poll_interval,
        )

    async def get_barcode_pdf_with_polling(
        self,
        order_uuid: str,
        *,
        max_attempts: int = 10,
        poll_interval: float = 2.0,
    ) -> bytes:
        """Create barcode → poll → download PDF."""
        create_resp = await self.create_barcode([order_uuid])
        doc_uuid = create_resp.get("entity", {}).get("uuid", "")
        if not doc_uuid:
            raise ProviderHTTPError(
                status_code=0,
                message="No UUID in barcode creation response",
                response_body=str(create_resp),
            )
        return await self._poll_print_document(
            lambda: self.get_barcode_status(doc_uuid),
            lambda: self.download_barcode_pdf(doc_uuid),
            max_attempts=max_attempts,
            poll_interval=poll_interval,
        )

    # ------------------------------------------------------------------ #
    # Location services — city / region / coordinate lookup               #
    # ------------------------------------------------------------------ #

    async def list_cities(self, params: dict) -> list[dict]:
        """GET /v2/location/cities — search cities by name, code, etc."""
        resp = await self._provider_client.request(
            "GET", "/v2/location/cities", params=params
        )
        return resp.json()

    async def list_regions(self, params: dict) -> list[dict]:
        """GET /v2/location/regions — search regions."""
        resp = await self._provider_client.request(
            "GET", "/v2/location/regions", params=params
        )
        return resp.json()

    async def suggest_cities(self, params: dict) -> list[dict]:
        """GET /v2/location/suggest/cities — city name autocomplete."""
        resp = await self._provider_client.request(
            "GET", "/v2/location/suggest/cities", params=params
        )
        return resp.json()

    async def get_postal_codes(self, params: dict) -> list[dict]:
        """GET /v2/location/postalcodes — postal codes for a city."""
        resp = await self._provider_client.request(
            "GET", "/v2/location/postalcodes", params=params
        )
        return resp.json()

    async def get_location_by_coordinates(self, params: dict) -> list[dict]:
        """GET /v2/location/coordinates — resolve location from lat/lng."""
        resp = await self._provider_client.request(
            "GET", "/v2/location/coordinates", params=params
        )
        return resp.json()

    # ------------------------------------------------------------------ #
    # Delivery scheduling                                                 #
    # ------------------------------------------------------------------ #

    async def get_delivery_intervals(self, params: dict) -> dict:
        """GET /v2/delivery/intervals — delivery time slots for order."""
        resp = await self._provider_client.request(
            "GET", "/v2/delivery/intervals", params=params
        )
        return resp.json()

    async def get_estimated_delivery_intervals(self, body: dict) -> dict:
        """POST /v2/delivery/estimatedIntervals — pre-order delivery slots."""
        resp = await self._provider_client.request(
            "POST", "/v2/delivery/estimatedIntervals", json=body
        )
        return resp.json()

    async def register_delivery(self, body: dict) -> dict:
        """POST /v2/delivery — register delivery agreement."""
        resp = await self._provider_client.request("POST", "/v2/delivery", json=body)
        return resp.json()

    async def get_delivery(self, uuid: str) -> dict:
        """GET /v2/delivery/{uuid} — delivery agreement info."""
        resp = await self._provider_client.request("GET", f"/v2/delivery/{uuid}")
        return resp.json()

    # ------------------------------------------------------------------ #
    # Webhooks                                                            #
    # ------------------------------------------------------------------ #

    async def list_webhooks(self) -> dict:
        """GET /v2/webhooks — list webhook subscriptions."""
        resp = await self._provider_client.request("GET", "/v2/webhooks")
        return resp.json()

    async def get_webhook(self, uuid: str) -> dict:
        """GET /v2/webhooks/{uuid} — specific webhook subscription info."""
        resp = await self._provider_client.request("GET", f"/v2/webhooks/{uuid}")
        return resp.json()

    async def create_webhook(self, url: str, webhook_type: str) -> dict:
        """POST /v2/webhooks — subscribe to webhook events."""
        body: dict[str, Any] = {"url": url, "type": webhook_type}
        resp = await self._provider_client.request("POST", "/v2/webhooks", json=body)
        return resp.json()

    async def delete_webhook(self, uuid: str) -> dict:
        """DELETE /v2/webhooks/{uuid} — unsubscribe."""
        resp = await self._provider_client.request("DELETE", f"/v2/webhooks/{uuid}")
        return resp.json()

    # ------------------------------------------------------------------ #
    # Misc — checks, prealerts, reverse                                   #
    # ------------------------------------------------------------------ #

    async def check_reverse_availability(self, body: dict) -> dict:
        """POST /v2/reverse/availability — check if reverse delivery is possible."""
        resp = await self._provider_client.request(
            "POST", "/v2/reverse/availability", json=body
        )
        return resp.json()

    async def create_prealert(self, body: dict) -> dict:
        """POST /v2/prealert — register prealert."""
        resp = await self._provider_client.request("POST", "/v2/prealert", json=body)
        return resp.json()

    async def get_prealert(self, uuid: str) -> dict:
        """GET /v2/prealert/{uuid} — prealert info."""
        resp = await self._provider_client.request("GET", f"/v2/prealert/{uuid}")
        return resp.json()

    async def get_checks(self, params: dict) -> dict:
        """GET /v2/check — fiscal receipt information."""
        resp = await self._provider_client.request("GET", "/v2/check", params=params)
        return resp.json()

    async def get_registries(self, params: dict | None = None) -> dict:
        """GET /v2/registries — shipment registries info."""
        resp = await self._provider_client.request(
            "GET", "/v2/registries", params=params
        )
        return resp.json()
