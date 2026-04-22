"""
Query handler: personalized «Для вас» (For You) homepage feed.

Strategy v1 (Phase A MVP)
-------------------------

Input signals:
* ``IUserActivityReader`` — top viewed categories + recently-viewed products
  for the authenticated user (last 30 days).
* ``IActivityQueryService.get_trending_products`` — global weekly trending
  from Redis (cold-start fallback + diversity).
* ``products.popularity_score`` — baseline ranking within a category.

Branching:

``warm`` user (>= ``WARM_THRESHOLD`` activity events) →
    * Pull top products from each affinity category (weighted by affinity).
    * Interleave round-robin so the feed does not start with a single
      category.
    * Dedupe against recently-viewed products.
    * Tail-append global trending for discovery (up to 20 % of candidates).

``cold`` user (anonymous or new) →
    * Global trending weekly (Redis).
    * Fall back to highest ``popularity_score`` if Redis is empty.

Candidate list (up to ``MAX_CANDIDATES`` product IDs) is stored in Redis
under ``for_you:candidates:{seed_id}`` with a 10-minute TTL.  The client
receives a cursor that points into this materialised list, guaranteeing
stable pagination across requests even if the underlying signals move.

All ranking logic is isolated here so a future ``strategy_version = "v2"``
can plug in co-occurrence / content-based signals without breaking the
presentation API.
"""

from __future__ import annotations

import base64
import json
import secrets
import uuid
from dataclasses import dataclass

import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.get_storefront_cards_by_ids import (
    GetStorefrontProductCardsByIdsHandler,
    GetStorefrontProductCardsByIdsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    StorefrontProductCardReadModel,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.shared.interfaces.activity import (
    CategoryAffinity,
    IActivityQueryService,
    ICoViewReader,
    IUserActivityReader,
)
from src.shared.interfaces.logger import ILogger

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

STRATEGY_VERSION = "v2"
WARM_THRESHOLD = 5  # minimum recent events to switch from cold to warm
LOOKBACK_DAYS = 30
MAX_CANDIDATES = 200  # upper bound on materialised list per seed
PER_CATEGORY_POOL = 40  # products fetched per affinity category
TRENDING_TAIL_RATIO = 0.2  # fraction of candidate list reserved for global trending
CANDIDATE_CACHE_TTL_SECONDS = 600  # 10 min
CO_VIEW_SEED_PRODUCTS = 5  # number of recently viewed products used as co-view seeds
CO_VIEW_NEIGHBOURS_PER_SEED = 10  # top neighbours fetched per seed product
CO_VIEW_HEAD_CAP = 40  # upper bound on co-view boost slot count in final list


def _candidate_cache_key(seed_id: str) -> str:
    return f"for_you:candidates:{seed_id}"


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ForYouCursor:
    strategy_version: str
    seed_id: str
    offset: int

    def encode(self) -> str:
        raw = json.dumps(
            {
                "v": self.strategy_version,
                "s": self.seed_id,
                "o": self.offset,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @classmethod
    def decode(cls, token: str) -> ForYouCursor | None:
        try:
            padded = token + "=" * (-len(token) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            data = json.loads(raw)
            return cls(
                strategy_version=str(data["v"]),
                seed_id=str(data["s"]),
                offset=int(data["o"]),
            )
        except ValueError, KeyError, TypeError, json.JSONDecodeError:
            return None


# ---------------------------------------------------------------------------
# Query / Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ForYouFeedQuery:
    """Parameters for :class:`ForYouFeedHandler`.

    * ``user_id`` — authenticated identity (``None`` → cold anonymous flow).
    * ``limit`` — page size (1..50).
    * ``cursor`` — opaque pagination token from a previous response.
    """

    user_id: uuid.UUID | None
    limit: int = 20
    cursor: str | None = None


@dataclass(frozen=True)
class ForYouFeedResult:
    items: list[StorefrontProductCardReadModel]
    next_cursor: str | None
    strategy_version: str
    is_personalized: bool


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class ForYouFeedHandler:
    """Assemble and paginate the homepage «Для вас» feed."""

    def __init__(
        self,
        session: AsyncSession,
        redis_client: redis.Redis,
        history_reader: IUserActivityReader,
        trending_service: IActivityQueryService,
        co_view_reader: ICoViewReader,
        cards_handler: GetStorefrontProductCardsByIdsHandler,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._redis = redis_client
        self._history = history_reader
        self._trending = trending_service
        self._co_view = co_view_reader
        self._cards = cards_handler
        self._logger = logger.bind(handler="ForYouFeedHandler")

    async def handle(self, query: ForYouFeedQuery) -> ForYouFeedResult:
        limit = max(1, min(int(query.limit), 50))

        cursor = ForYouCursor.decode(query.cursor) if query.cursor else None
        if cursor and cursor.strategy_version != STRATEGY_VERSION:
            # Strategy changed since the cursor was issued — start fresh.
            cursor = None

        (
            candidate_ids,
            is_personalized,
            seed_id,
            cursor_invalidated,
        ) = await self._get_or_build_candidates(
            user_id=query.user_id, existing_cursor=cursor
        )

        if not candidate_ids:
            return ForYouFeedResult(
                items=[],
                next_cursor=None,
                strategy_version=STRATEGY_VERSION,
                is_personalized=is_personalized,
            )

        # If the cached list was evicted, the offset from the old cursor is
        # meaningless against the new list — restart from zero.
        # Also clamp negative offsets (crafted / truncated cursors): Python
        # slicing with a negative start wraps around the list, which would
        # expose stale tail items and can produce an infinite next_cursor
        # loop (``new_offset < len(candidate_ids)`` stays true forever).
        raw_offset = cursor.offset if cursor is not None and not cursor_invalidated else 0
        offset = max(0, raw_offset)
        window_ids = candidate_ids[offset : offset + limit]

        cards = (
            await self._cards.handle(
                GetStorefrontProductCardsByIdsQuery(product_ids=window_ids)
            )
            if window_ids
            else []
        )

        new_offset = offset + len(window_ids)
        has_more = new_offset < len(candidate_ids)
        next_cursor: str | None = None
        if has_more:
            next_cursor = ForYouCursor(
                strategy_version=STRATEGY_VERSION,
                seed_id=seed_id,
                offset=new_offset,
            ).encode()

        return ForYouFeedResult(
            items=cards,
            next_cursor=next_cursor,
            strategy_version=STRATEGY_VERSION,
            is_personalized=is_personalized,
        )

    # -----------------------------------------------------------------
    # Candidate generation
    # -----------------------------------------------------------------

    async def _get_or_build_candidates(
        self,
        *,
        user_id: uuid.UUID | None,
        existing_cursor: ForYouCursor | None,
    ) -> tuple[list[uuid.UUID], bool, str, bool]:
        """Return ``(candidate_ids, is_personalized, seed_id, cursor_invalidated)``.

        Using an explicit tuple instead of instance attributes keeps the
        handler instance stateless across concurrent calls — important
        because the DI container may reuse the handler if its scope ever
        gets promoted from REQUEST to APP.
        """
        cursor_invalidated = False
        if existing_cursor is not None:
            cached = await self._load_candidates(existing_cursor.seed_id)
            if cached:
                is_personalized = existing_cursor.seed_id.startswith("w:")
                return cached, is_personalized, existing_cursor.seed_id, False
            # Cache miss (TTL expired or evicted) — caller will restart from
            # offset 0 against a freshly materialised list.
            cursor_invalidated = True

        # Fresh first page — run the ranker.
        candidate_ids, is_personalized = await self._rank_candidates(user_id)

        seed_id = f"{'w' if is_personalized else 'c'}:{secrets.token_urlsafe(12)}"
        if candidate_ids:
            await self._store_candidates(seed_id, candidate_ids)
        return candidate_ids, is_personalized, seed_id, cursor_invalidated

    async def _rank_candidates(
        self, user_id: uuid.UUID | None
    ) -> tuple[list[uuid.UUID], bool]:
        # Cold path: no identity or warmth threshold not met.
        if user_id is None:
            return await self._cold_candidates(), False

        event_count = await self._history.get_activity_event_count(
            user_id=user_id, lookback_days=LOOKBACK_DAYS
        )
        if event_count < WARM_THRESHOLD:
            return await self._cold_candidates(), False

        affinities = await self._history.get_category_affinities(
            user_id=user_id, lookback_days=LOOKBACK_DAYS, limit=5
        )
        if not affinities:
            return await self._cold_candidates(), False

        viewed_list = await self._history.get_recently_viewed_product_ids(
            user_id=user_id, lookback_days=LOOKBACK_DAYS, limit=100
        )
        viewed = set(viewed_list)

        per_category_ids = await self._fetch_products_by_category(
            [a.category_id for a in affinities]
        )

        # Weight each category's queue by its affinity weight — a higher
        # affinity category drops more cards into the round-robin pool.
        weighted = self._weight_and_interleave(affinities, per_category_ids, viewed)

        # Co-view boost head: for each of the user's most recently viewed
        # products, pull top co-viewed neighbours from the precomputed matrix
        # (see ``refresh_co_view_scores_task``).  This is the signal that
        # surfaces «тоже смотрят» / «continue browsing» style suggestions on
        # the home feed.  If the matrix is empty (e.g. early in production),
        # head is empty and the feed gracefully falls back to v1 behaviour.
        co_view_head = await self._co_view_boost(
            seed_product_ids=viewed_list[:CO_VIEW_SEED_PRODUCTS],
            excluded=viewed | set(weighted),
        )

        # Add a trending tail for diversity.
        trending_tail = await self._trending_tail(
            excluded=set(co_view_head) | set(weighted) | viewed,
            slots=max(1, int(MAX_CANDIDATES * TRENDING_TAIL_RATIO)),
        )
        candidates = (co_view_head + weighted + trending_tail)[:MAX_CANDIDATES]
        return candidates, True

    async def _cold_candidates(self) -> list[uuid.UUID]:
        """Trending-first cold start with popularity_score fallback."""
        ranked = await self._trending.get_trending_products(
            limit=MAX_CANDIDATES, window="weekly"
        )
        ids: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        for entry in ranked:
            try:
                pid = uuid.UUID(entry.entity_id)
            except ValueError:
                continue
            if pid in seen:
                continue
            seen.add(pid)
            ids.append(pid)

        if len(ids) >= MAX_CANDIDATES:
            return ids

        # Supplement with highest popularity_score products for cold boot
        # (Redis may be empty early in production).
        remaining = MAX_CANDIDATES - len(ids)
        stmt = select(OrmProduct.id).where(
            OrmProduct.status == ProductStatus.PUBLISHED,
            OrmProduct.is_visible.is_(True),
            OrmProduct.deleted_at.is_(None),
        )
        if ids:
            stmt = stmt.where(OrmProduct.id.notin_(ids))
        stmt = stmt.order_by(
            OrmProduct.popularity_score.desc().nullslast(),
            OrmProduct.published_at.desc().nullslast(),
        ).limit(remaining)
        result = await self._session.execute(stmt)
        for pid in result.scalars():
            if pid not in seen:
                ids.append(pid)
                seen.add(pid)
        return ids

    async def _fetch_products_by_category(
        self, category_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        if not category_ids:
            return {}
        # One query per category keeps the SQL simple (5 queries × 40 rows = 200 rows).
        # Using a window-function ranking over the union could reduce roundtrips
        # but is overkill for Phase A.
        result: dict[uuid.UUID, list[uuid.UUID]] = {}
        for cid in category_ids:
            stmt = (
                select(OrmProduct.id)
                .where(
                    OrmProduct.primary_category_id == cid,
                    OrmProduct.status == ProductStatus.PUBLISHED,
                    OrmProduct.is_visible.is_(True),
                    OrmProduct.deleted_at.is_(None),
                )
                .order_by(
                    OrmProduct.popularity_score.desc().nullslast(),
                    func.coalesce(
                        OrmProduct.published_at, OrmProduct.created_at
                    ).desc(),
                )
                .limit(PER_CATEGORY_POOL)
            )
            rows = await self._session.execute(stmt)
            result[cid] = list(rows.scalars())
        return result

    @staticmethod
    def _weight_and_interleave(
        affinities: list[CategoryAffinity],
        per_category_ids: dict[uuid.UUID, list[uuid.UUID]],
        excluded: set[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Weighted round-robin merge preserving per-category ordering.

        Each category gets a virtual turn every ``stride`` merged items,
        where ``stride`` is inversely proportional to its affinity weight.
        """
        if not affinities:
            return []
        total_weight = sum(a.weight for a in affinities) or 1.0

        # Simple approach: normalize weights to [1.0 .. 1/N] and produce
        # output by repeatedly sampling the most-deserving pointer.
        queues: dict[uuid.UUID, list[uuid.UUID]] = {
            a.category_id: [p for p in per_category_ids.get(a.category_id, [])]
            for a in affinities
        }
        credit: dict[uuid.UUID, float] = {a.category_id: 0.0 for a in affinities}
        share: dict[uuid.UUID, float] = {
            a.category_id: a.weight / total_weight for a in affinities
        }

        merged: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set(excluded)
        while any(queues.values()):
            for cid in queues:
                credit[cid] += share[cid]
            # Pick the category with highest accumulated credit that still
            # has items.
            picked = max(
                (cid for cid in queues if queues[cid]),
                key=lambda c: credit[c],
                default=None,
            )
            if picked is None:
                break
            pid = queues[picked].pop(0)
            credit[picked] -= 1.0
            if pid in seen:
                continue
            seen.add(pid)
            merged.append(pid)
            if len(merged) >= MAX_CANDIDATES:
                break
        return merged

    async def _co_view_boost(
        self,
        *,
        seed_product_ids: list[uuid.UUID],
        excluded: set[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Merge top co-viewed neighbours of recent views into a boost list.

        For each seed product the caller supplied (most recently viewed
        items), fetch the top co-view neighbours from the precomputed
        matrix.  Results from different seeds are merged so the highest
        score across all seeds wins (a product that appears strongly
        co-viewed with multiple viewed items bubbles to the top).

        The reader degrades gracefully on DB failure: an empty matrix
        simply yields an empty list, letting the warm ranker fall back to
        v1 behaviour transparently.
        """
        if not seed_product_ids:
            return []
        aggregated: dict[uuid.UUID, int] = {}
        for seed_id in seed_product_ids:
            try:
                neighbours = await self._co_view.get_also_viewed(
                    product_id=seed_id, limit=CO_VIEW_NEIGHBOURS_PER_SEED
                )
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.warning(
                    "for_you.co_view.failed", error=str(exc), seed_id=str(seed_id)
                )
                continue
            for entry in neighbours:
                pid = entry.product_id
                if pid in excluded:
                    continue
                # Keep the max score seen across seeds.
                existing = aggregated.get(pid, 0)
                if entry.score > existing:
                    aggregated[pid] = entry.score
        if not aggregated:
            return []
        ranked = sorted(aggregated.items(), key=lambda kv: kv[1], reverse=True)
        return [pid for pid, _ in ranked[:CO_VIEW_HEAD_CAP]]

    async def _trending_tail(
        self, *, excluded: set[uuid.UUID], slots: int
    ) -> list[uuid.UUID]:
        ranked = await self._trending.get_trending_products(
            limit=slots * 3, window="weekly"
        )
        tail: list[uuid.UUID] = []
        for entry in ranked:
            try:
                pid = uuid.UUID(entry.entity_id)
            except ValueError:
                continue
            if pid in excluded:
                continue
            tail.append(pid)
            excluded.add(pid)
            if len(tail) >= slots:
                break
        return tail

    # -----------------------------------------------------------------
    # Redis candidate cache
    # -----------------------------------------------------------------

    async def _load_candidates(self, seed_id: str) -> list[uuid.UUID]:
        key = _candidate_cache_key(seed_id)
        try:
            raw = await self._redis.get(key)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("for_you.cache.get_failed", error=str(exc))
            return []
        if not raw:
            return []
        try:
            items = json.loads(raw)
            return [uuid.UUID(s) for s in items]
        except ValueError, TypeError, json.JSONDecodeError:
            self._logger.warning("for_you.cache.parse_failed", seed_id=seed_id)
            return []

    async def _store_candidates(
        self, seed_id: str, candidate_ids: list[uuid.UUID]
    ) -> None:
        key = _candidate_cache_key(seed_id)
        payload = json.dumps([str(pid) for pid in candidate_ids])
        try:
            await self._redis.set(key, payload, ex=CANDIDATE_CACHE_TTL_SECONDS)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("for_you.cache.set_failed", error=str(exc))


__all__ = [
    "STRATEGY_VERSION",
    "ForYouCursor",
    "ForYouFeedHandler",
    "ForYouFeedQuery",
    "ForYouFeedResult",
]
