"""
CDEK document provider — implements ``IDocumentProvider``.

Handles the async waybill generation pattern:
POST /v2/print/orders → poll GET → download PDF.
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
        async with self._client:
            pdf_bytes = await self._client.get_waybill_pdf_with_polling(
                provider_shipment_id,
            )
        return DocumentResult(
            document_bytes=pdf_bytes,
            content_type="application/pdf",
        )
