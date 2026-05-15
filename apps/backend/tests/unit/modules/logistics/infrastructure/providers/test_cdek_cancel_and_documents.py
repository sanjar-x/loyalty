"""
Phase-1 regression tests for CDEK cancellation + document capabilities:

* ``CdekBookingProvider.cancel_shipment`` tries ``DELETE /v2/orders``
  first (only valid in «Создан») and transparently falls back to
  ``POST /v2/orders/{uuid}/refusal`` once the order is moving — surfacing
  both reasons when neither path works.
* ``CdekDocumentProvider`` exposes the barcode label (ШК места) via the
  CDEK-specific ``get_barcode_label`` alongside the protocol ``get_label``
  waybill path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.infrastructure.providers.cdek.booking_provider import (
    CdekBookingProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.document_provider import (
    CdekDocumentProvider,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

pytestmark = pytest.mark.unit


@pytest.fixture
def cdek_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


class TestCancelShipmentFallback:
    @pytest.mark.asyncio
    async def test_delete_success_short_circuits(self, cdek_client: AsyncMock) -> None:
        cdek_client.delete_order.return_value = {"requests": [{"state": "ACCEPTED"}]}
        provider = CdekBookingProvider(cdek_client)

        result = await provider.cancel_shipment("ship-1")

        assert result.success is True
        cdek_client.delete_order.assert_awaited_once_with("ship-1")
        cdek_client.register_refusal.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_invalid_falls_back_to_refusal(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.delete_order.return_value = {
            "requests": [
                {
                    "state": "INVALID",
                    "errors": [{"code": "v2_entity_not_ready", "message": "moving"}],
                }
            ]
        }
        cdek_client.register_refusal.return_value = {
            "requests": [{"state": "ACCEPTED"}]
        }
        provider = CdekBookingProvider(cdek_client)

        result = await provider.cancel_shipment("ship-2")

        assert result.success is True
        cdek_client.register_refusal.assert_awaited_once_with("ship-2", None)

    @pytest.mark.asyncio
    async def test_delete_http_error_falls_back_to_refusal(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.delete_order.side_effect = ProviderHTTPError(
            status_code=400, message="cannot delete"
        )
        cdek_client.register_refusal.return_value = {"requests": []}
        provider = CdekBookingProvider(cdek_client)

        result = await provider.cancel_shipment("ship-3")

        assert result.success is True
        cdek_client.register_refusal.assert_awaited_once_with("ship-3", None)

    @pytest.mark.asyncio
    async def test_both_paths_fail_surfaces_both_reasons(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.delete_order.return_value = {
            "requests": [
                {"state": "INVALID", "errors": [{"code": "e1", "message": "del-fail"}]}
            ]
        }
        cdek_client.register_refusal.return_value = {
            "requests": [
                {"state": "INVALID", "errors": [{"code": "e2", "message": "ref-fail"}]}
            ]
        }
        provider = CdekBookingProvider(cdek_client)

        result = await provider.cancel_shipment("ship-4")

        assert result.success is False
        assert "del-fail" in (result.reason or "")
        assert "ref-fail" in (result.reason or "")


class TestDocumentProvider:
    @pytest.mark.asyncio
    async def test_get_label_returns_waybill_pdf(self, cdek_client: AsyncMock) -> None:
        cdek_client.get_waybill_pdf_with_polling.return_value = b"WAYBILL_PDF"
        provider = CdekDocumentProvider(cdek_client)

        result = await provider.get_label("ship-1")

        assert result.document_bytes == b"WAYBILL_PDF"
        assert result.content_type == "application/pdf"
        cdek_client.get_waybill_pdf_with_polling.assert_awaited_once_with("ship-1")

    @pytest.mark.asyncio
    async def test_get_barcode_label_returns_barcode_pdf(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.get_barcode_pdf_with_polling.return_value = b"BARCODE_PDF"
        provider = CdekDocumentProvider(cdek_client)

        result = await provider.get_barcode_label("ship-1")

        assert result.document_bytes == b"BARCODE_PDF"
        assert result.content_type == "application/pdf"
        cdek_client.get_barcode_pdf_with_polling.assert_awaited_once_with("ship-1")
