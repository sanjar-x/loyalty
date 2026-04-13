"""
Yandex Delivery document provider — implements ``IDocumentProvider``.

Generates shipping labels via POST /generate-labels (returns PDF directly).
"""

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    DocumentResult,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)


class YandexDeliveryDocumentProvider:
    """Yandex Delivery implementation of ``IDocumentProvider``."""

    def __init__(self, client: YandexDeliveryClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    async def get_label(self, provider_shipment_id: str) -> DocumentResult:
        async with self._client:
            pdf_bytes = await self._client.generate_labels([provider_shipment_id])
        return DocumentResult(
            document_bytes=pdf_bytes,
            content_type="application/pdf",
        )
