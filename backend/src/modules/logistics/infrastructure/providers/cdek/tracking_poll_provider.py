"""
CDEK tracking poll provider — implements ``ITrackingPollProvider``.

Batch-polls tracking status for multiple shipments as a reconciliation
mechanism.  Even though CDEK supports webhooks, a scheduled poller
ensures eventual consistency if webhooks are delayed or lost.
"""

import asyncio
import logging

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    parse_tracking_events,
)

logger = logging.getLogger(__name__)


class CdekTrackingPollProvider:
    """CDEK implementation of ``ITrackingPollProvider``.

    Polls ``GET /v2/orders/{uuid}`` for each shipment to extract
    tracking statuses.  Used by background reconciliation tasks.
    """

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def poll_tracking_batch(
        self, provider_shipment_ids: list[str]
    ) -> dict[str, list[TrackingEvent]]:
        result: dict[str, list[TrackingEvent]] = {}
        async with self._client:
            tasks = [self._poll_single(sid) for sid in provider_shipment_ids]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        for sid, resp in zip(provider_shipment_ids, responses, strict=False):
            if isinstance(resp, BaseException):
                logger.warning("Failed to poll CDEK tracking for %s: %s", sid, resp)
                result[sid] = []
            else:
                result[sid] = resp

        return result

    async def _poll_single(self, provider_shipment_id: str) -> list[TrackingEvent]:
        data = await self._client.get_order(provider_shipment_id)
        entity = data.get("entity", data)
        statuses = entity.get("statuses", [])
        return parse_tracking_events(statuses)
