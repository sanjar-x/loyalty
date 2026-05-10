"""Activity enrichment from favorites events (T-3 / D3.2).

Bridges ``FavoriteItemAddedEvent`` into the activity tracker's
``track_favorite_added`` so the co-view matrix and trending signals
include a strong "interest" indicator beyond passing PDP views.

Brand favorites are filtered out — they go through a separate
brand-affinity pipeline and don't drive product co-view scores.
``FavoriteItemRemovedEvent`` is intentionally NOT consumed: removal
is a weak signal (changed mind, accidental) without actionable
co-view value.
"""

from __future__ import annotations

import uuid

from src.shared.interfaces.activity import IActivityTracker
from src.shared.interfaces.logger import ILogger


class FavoritesActivityEnricher:
    """Outbox-consumer body that translates favorites → activity events."""

    def __init__(self, tracker: IActivityTracker, logger: ILogger) -> None:
        self._tracker = tracker
        self._logger = logger.bind(consumer="FavoritesActivityEnricher")

    async def on_favorite_item_added(self, payload: dict) -> None:
        target_type = payload.get("target_type")
        if target_type != "product":
            # Brand favorites: not a product co-view signal.
            self._logger.debug(
                "favorites_activity.skip",
                reason="non_product_target",
                target_type=target_type,
            )
            return

        actor_raw = payload.get("identity_id")
        product_raw = payload.get("target_id")
        list_raw = payload.get("list_id")

        if actor_raw is None or product_raw is None:
            self._logger.warning(
                "favorites_activity.skip", reason="missing_required_field"
            )
            return

        try:
            actor_id = uuid.UUID(str(actor_raw))
            product_id = uuid.UUID(str(product_raw))
            list_id = uuid.UUID(str(list_raw)) if list_raw is not None else None
        except TypeError, ValueError:
            self._logger.warning(
                "favorites_activity.skip",
                reason="bad_uuid",
                actor_id=str(actor_raw),
                product_id=str(product_raw),
            )
            return

        await self._tracker.track_favorite_added(
            product_id=product_id,
            actor_id=actor_id,
            list_id=list_id,
        )
