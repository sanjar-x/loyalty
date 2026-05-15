"""
CDEK webhook-subscription management.

CDEK delivers order-status / order-modified events to a client-owned
URL, registered via ``POST /v2/webhooks``. Two hard constraints from
the CDEK protocol shape this module:

* **A client may hold at most 2 active subscriptions.** Registering a
  third silently creates a duplicate of an existing type rather than
  failing — so blind re-registration on every boot would burn the cap.
* **CDEK never deduplicates.** ``POST /v2/webhooks`` with a type that is
  already subscribed creates *another* subscription.

:func:`ensure_webhook_subscriptions` is therefore idempotent: it lists
the current subscriptions, creates only the ``(type, url)`` pairs that
are genuinely missing, and never exceeds the 2-subscription cap. It is
safe to call on every registry bootstrap and from the admin sync
endpoint alike.
"""

from __future__ import annotations

import attrs
import structlog

from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_MAX_WEBHOOK_SUBSCRIPTIONS,
    CDEK_WEBHOOK_AUTO_SUBSCRIBE,
)

logger = structlog.get_logger(__name__)


@attrs.define(frozen=True)
class WebhookSyncResult:
    """Outcome of an idempotent webhook-subscription sync.

    Attributes:
        existing: Subscriptions CDEK reported *before* the sync.
        created: Webhook types newly registered by this call.
        already_present: Requested types already subscribed for the URL.
        not_created: Requested types skipped — registering them would
            exceed CDEK's 2-subscription cap. The operator must free a
            slot (delete an unused subscription) first.
    """

    existing: list[dict]
    created: tuple[str, ...]
    already_present: tuple[str, ...]
    not_created: tuple[str, ...]


async def list_subscriptions(client: CdekClient) -> list[dict]:
    """Return the current CDEK webhook subscriptions as a list of dicts.

    ``GET /v2/webhooks`` returns a bare JSON array of ``WebhookDto``;
    this normalises away the occasional non-list payload defensively.
    """
    raw = await client.list_webhooks()
    if isinstance(raw, list):
        return [w for w in raw if isinstance(w, dict)]
    return []


async def ensure_webhook_subscriptions(
    client: CdekClient,
    url: str,
    types: tuple[str, ...] = CDEK_WEBHOOK_AUTO_SUBSCRIBE,
) -> WebhookSyncResult:
    """Idempotently ensure ``types`` are subscribed for ``url``.

    Lists the current subscriptions, creates only the genuinely-missing
    ``(type, url)`` pairs, and stops at CDEK's 2-subscription cap —
    safe to call repeatedly (every boot, every operator sync).
    """
    existing = await list_subscriptions(client)
    present_pairs = {(w.get("type"), w.get("url")) for w in existing}

    created: list[str] = []
    already_present: list[str] = []
    not_created: list[str] = []
    free_slots = CDEK_MAX_WEBHOOK_SUBSCRIPTIONS - len(existing)

    for webhook_type in types:
        if (webhook_type, url) in present_pairs:
            already_present.append(webhook_type)
            continue
        if free_slots <= 0:
            not_created.append(webhook_type)
            continue
        await client.create_webhook(url, webhook_type)
        created.append(webhook_type)
        free_slots -= 1

    if created:
        logger.info(
            "cdek_webhook_subscriptions_created",
            url=url,
            created=created,
        )
    if not_created:
        logger.warning(
            "cdek_webhook_subscriptions_capacity_exhausted",
            url=url,
            not_created=not_created,
            cap=CDEK_MAX_WEBHOOK_SUBSCRIPTIONS,
        )

    return WebhookSyncResult(
        existing=existing,
        created=tuple(created),
        already_present=tuple(already_present),
        not_created=tuple(not_created),
    )
