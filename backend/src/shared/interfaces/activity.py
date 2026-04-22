"""
Activity tracker port (Hexagonal Architecture).

Defines the ``IActivityTracker`` protocol used by storefront query handlers
to record user activity (product views, search queries, listing views).

Implementations live in ``src.modules.activity.infrastructure`` and must be
**fire-and-forget**: they never raise, so callers do not need a ``try``
block around tracking calls — analytics failures must not affect user
requests.

Typical usage::

    class GetStorefrontProductHandler:
        def __init__(self, tracker: IActivityTracker) -> None:
            self._tracker = tracker

        async def handle(self, query):
            ...
            await self._tracker.track_product_view(
                product_id=product.id,
                category_id=product.primary_category_id,
                actor_id=query.actor_id,
                session_id=query.session_id,
            )
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol


class IActivityTracker(Protocol):
    """Contract for recording user activity events."""

    async def track_product_view(
        self,
        *,
        product_id: uuid.UUID,
        category_id: uuid.UUID | None,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Record a product detail page view.

        Must never raise — failures are logged and swallowed.
        """
        ...

    async def track_product_list_view(
        self,
        *,
        category_id: uuid.UUID | None,
        result_count: int,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Record a product listing (PLP) view.

        Must never raise.
        """
        ...

    async def track_search(
        self,
        *,
        query: str,
        result_count: int,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Record a search query execution.

        Must never raise.
        """
        ...


@dataclass(frozen=True)
class CategoryAffinity:
    """User's affinity score towards a category.

    ``weight`` reflects recency-decayed view count within the lookback
    window.  Higher means the user viewed products in that category more
    frequently / more recently.
    """

    category_id: uuid.UUID
    weight: float


class IUserActivityReader(Protocol):
    """Read-side contract for per-user activity history.

    Powers personalized recommendation handlers (e.g. the homepage
    «Для вас» feed).  Implementations read from ``user_activity_events``
    directly — the partitioned index on ``(actor_id, created_at)`` keeps
    these queries cheap.

    All methods must degrade gracefully: on DB failure they should return
    empty results so recommendation endpoints can still serve a cold-start
    response.
    """

    async def get_category_affinities(
        self,
        *,
        user_id: uuid.UUID,
        lookback_days: int = 30,
        limit: int = 5,
    ) -> list[CategoryAffinity]:
        """Return top-N categories the user has viewed, ordered by weight.

        Only ``product_view`` events with a non-NULL ``category_id`` are
        counted.  ``weight`` is a simple count within the window; callers
        normalise or decay as needed.
        """
        ...

    async def get_recently_viewed_product_ids(
        self,
        *,
        user_id: uuid.UUID,
        lookback_days: int = 30,
        limit: int = 100,
    ) -> list[uuid.UUID]:
        """Return IDs of products this user most recently viewed.

        Useful for deduping recommendations against items the user has
        already seen.  Ordered by ``created_at`` DESC.
        """
        ...

    async def get_activity_event_count(
        self,
        *,
        user_id: uuid.UUID,
        lookback_days: int = 30,
    ) -> int:
        """Return total activity events in the window — used to classify
        cold vs. warm users.
        """
        ...


@dataclass(frozen=True)
class CoViewScore:
    """Single "viewed-together" pair score.

    Returned by :class:`ICoViewReader`.  ``score`` is a non-negative integer
    count of distinct users/sessions that viewed both products within the
    co-view window during the refresh lookback period.
    """

    product_id: uuid.UUID
    score: int


class ICoViewReader(Protocol):
    """Read-side contract for the pairwise co-view matrix.

    Implementations back the storefront "также смотрят" endpoint and the
    Phase B+ personalization boost.  The matrix is refreshed periodically
    by a TaskIQ job — readers never compute on demand.

    Implementations must degrade gracefully: on DB failure return an empty
    list so callers can fall back to content similarity.
    """

    async def get_also_viewed(
        self,
        *,
        product_id: uuid.UUID,
        limit: int = 12,
    ) -> list[CoViewScore]:
        """Return top-N co-viewed products, ordered by score DESC.

        The source ``product_id`` is never included in the result.
        """
        ...


@dataclass(frozen=True)
class RankedEntity:
    """Ranked entry returned by the activity query service.

    ``entity_id`` is the application-level identifier (UUID string for
    products, normalised query text for searches).  ``score`` is the
    Redis ZSCORE value — interpretation depends on the window.
    """

    entity_id: str
    score: float


class IActivityQueryService(Protocol):
    """Read-side contract for activity analytics.

    Exposes top-N queries against Redis sorted sets populated by
    :class:`IActivityTracker`.  All methods must return an empty list when
    Redis is unreachable (graceful degradation — analytics are
    non-critical for request handling).
    """

    async def get_trending_products(
        self,
        *,
        limit: int = 20,
        window: str = "weekly",
        category_id: uuid.UUID | None = None,
    ) -> list[RankedEntity]:
        """Return top-N trending product IDs with view scores.

        ``window`` is one of ``"daily"`` (today's ZSET) or ``"weekly"``
        (rolling weekly ZSET).  When ``category_id`` is provided, the
        per-category ZSET is used and ``window`` is ignored.
        """
        ...

    async def get_popular_search_queries(
        self, *, limit: int = 20
    ) -> list[RankedEntity]:
        """Return top search terms ranked by execution count."""
        ...

    async def get_zero_result_queries(self, *, limit: int = 20) -> list[RankedEntity]:
        """Return searches that produced zero results."""
        ...
