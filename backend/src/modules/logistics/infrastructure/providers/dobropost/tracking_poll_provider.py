"""DobroPost tracking-poll provider — implements ``ITrackingPollProvider``.

Polls ``GET /api/shipment`` to backfill webhook gaps.  DobroPost does
**not** expose a per-shipment status-history endpoint; the list
endpoint returns *current* state only. Each poll therefore
materialises a single ``TrackingEvent`` per shipment representing the
latest known state.

The poller paginates the queue using only the ``offset`` query
parameter (DobroPost openapi exposes both ``page`` and ``offset`` —
sending both is undefined behaviour and risks double-skip on backends
that sum them). It intersects each page with the requested set and
exits as soon as everything is matched (or the configured ceiling is
reached). Shipments not present after the ceiling are simply absent
from the result — they will be re-attempted on the next polling
cycle, and the webhook path remains the primary update channel.
"""

from __future__ import annotations

import logging

from src.modules.logistics.domain.value_objects import (
    PROVIDER_DOBROPOST,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.dobropost.client import (
    DobroPostClient,
)
from src.modules.logistics.infrastructure.providers.dobropost.mappers import (
    parse_list_shipment_response,
)

logger = logging.getLogger(__name__)

# DobroPost ``GET /api/shipment`` paging — keep modest to fit the
# ``logistics_tracking_poll`` task's 4-min timeout for ~200 shipments.
_DEFAULT_PAGE_SIZE = 100
# Hard ceiling on pagination passes per call — guards against runaway
# scans when DobroPost's queue is much larger than the wanted set.
_DEFAULT_MAX_PAGES = 20


class DobroPostTrackingPollProvider:
    """DobroPost implementation of ``ITrackingPollProvider``."""

    def __init__(
        self,
        client: DobroPostClient,
        *,
        page_size: int = _DEFAULT_PAGE_SIZE,
        max_pages: int = _DEFAULT_MAX_PAGES,
    ) -> None:
        self._client = client
        self._page_size = page_size
        self._max_pages = max_pages

    def provider_code(self) -> ProviderCode:
        return PROVIDER_DOBROPOST

    async def poll_tracking_batch(
        self, provider_shipment_ids: list[str]
    ) -> dict[str, list[TrackingEvent]]:
        """Return current state for every shipment in ``provider_shipment_ids``.

        Iterates pages with ``offset`` (NOT ``page`` — undefined to send
        both per openapi spec). Stops as soon as the wanted set is
        emptied or ``max_pages`` is exhausted; missing shipments are
        backfilled by the next polling cycle or the webhook path.
        """
        wanted: set[str] = set(provider_shipment_ids)
        if not wanted:
            return {}
        result: dict[str, list[TrackingEvent]] = {}

        for page in range(self._max_pages):
            offset = page * self._page_size
            try:
                data = await self._client.list_shipments({"offset": offset})
            except Exception as exc:
                logger.warning("DobroPost poll offset=%d failed: %s", offset, exc)
                break

            page_events = parse_list_shipment_response(data)
            for dp_id, events in page_events.items():
                if dp_id in wanted:
                    result[dp_id] = events
                    wanted.discard(dp_id)
            if not wanted:
                break

            content = data.get("content") or []
            if len(content) < self._page_size:
                # Reached the tail of the queue — no point paginating further.
                break
        else:
            # for-else: max_pages exhausted before wanted was empty.
            if wanted:
                logger.warning(
                    "DobroPost poll: max_pages=%d reached with %d shipments unmatched",
                    self._max_pages,
                    len(wanted),
                )

        if wanted:
            logger.debug(
                "DobroPost poll: %d shipments not found in queue (likely terminal)",
                len(wanted),
            )

        return result
