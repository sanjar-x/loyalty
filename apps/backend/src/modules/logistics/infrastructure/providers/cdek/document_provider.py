"""
CDEK document provider — implements ``IDocumentProvider``.

``get_label`` resolves the standard waybill (квитанция). CDEK also
produces a separate barcode label (ШК места) — exposed via the
CDEK-specific ``get_barcode_label`` so the carrier-agnostic
``IDocumentProvider`` port stays a single ``get_label`` method while the
admin layer can still reach barcodes.

Both follow the same async pattern: POST → poll status → download PDF.
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    DocumentResult,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient


class CdekDocumentProvider:
    """CDEK implementation of ``IDocumentProvider``."""

    def __init__(self, client: CdekClient) -> None:
        self._client: CdekClient = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def get_label(self, provider_shipment_id: str) -> DocumentResult:
        """Generate + download the order waybill (квитанция) PDF."""
        pdf_bytes = await self._client.get_waybill_pdf_with_polling(
            provider_shipment_id,
        )
        return DocumentResult(
            document_bytes=pdf_bytes,
            content_type="application/pdf",
        )

    async def get_barcode_label(self, provider_shipment_id: str) -> DocumentResult:
        """Generate + download the order barcode label (ШК места) PDF.

        CDEK-specific capability beyond the carrier-agnostic
        ``IDocumentProvider.get_label`` port — reached by the CDEK admin
        layer, which resolves the concrete provider from the registry.
        """
        pdf_bytes = await self._client.get_barcode_pdf_with_polling(
            provider_shipment_id,
        )
        return DocumentResult(
            document_bytes=pdf_bytes,
            content_type="application/pdf",
        )
