"""
Query handler: storefront search autocomplete / typeahead suggestions.

Returns mixed suggestions from products, categories, and brands that match
a user-typed prefix.  Results are language-aware and Redis-cached.

CQRS read side — queries ORM directly, returns read models.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import (
    STOREFRONT_SUGGEST_CACHE_TTL,
    storefront_suggest_cache_key,
)
from src.modules.catalog.application.queries.read_models import (
    SearchSuggestionReadModel,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger


def _escape_like(value: str) -> str:
    """Escape special LIKE pattern characters."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class SearchSuggestQuery:
    """Parameters for autocomplete suggestion request."""

    q: str  # prefix, min 2 chars enforced by router
    limit: int = 5  # max 10
    lang: str | None = None


class SearchSuggestHandler:
    """Autocomplete/typeahead suggestions for the storefront search bar."""

    def __init__(
        self,
        session: AsyncSession,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="SearchSuggestHandler")

    async def handle(
        self, query: SearchSuggestQuery
    ) -> list[SearchSuggestionReadModel]:
        cache_key = storefront_suggest_cache_key(self._query_hash(query))
        cached = await self._cache.get(cache_key)
        if cached:
            return self._deserialize_cache(cached)

        prefix = query.q.strip().lower()
        if len(prefix) < 2:
            return []

        escaped = _escape_like(prefix)
        like_pattern = f"{escaped}%"

        # Run queries sequentially (single AsyncSession cannot run concurrently).
        categories = await self._suggest_categories(like_pattern, query.lang, limit=3)
        brands = await self._suggest_brands(like_pattern, limit=3)
        products = await self._suggest_products(
            like_pattern, query.lang, limit=query.limit
        )

        # Merge: categories first (navigation), then brands, then products.
        results: list[SearchSuggestionReadModel] = []
        seen_slugs: set[tuple[str, str]] = set()

        for item in categories + brands + products:
            key = (item.type, item.slug)
            if key not in seen_slugs:
                seen_slugs.add(key)
                results.append(item)
            if len(results) >= query.limit:
                break

        await self._cache_result(cache_key, results)
        return results

    # ------------------------------------------------------------------
    # Individual suggestion queries
    # ------------------------------------------------------------------

    async def _suggest_categories(
        self, like_pattern: str, lang: str | None, limit: int
    ) -> list[SearchSuggestionReadModel]:
        """Prefix-match category names."""
        conditions = []
        if lang and lang in ("ru", "en"):
            conditions.append(
                func.lower(OrmCategory.name_i18n[lang].astext).like(like_pattern)
            )
        else:
            conditions.append(
                func.lower(OrmCategory.name_i18n["ru"].astext).like(like_pattern)
            )
            conditions.append(
                func.lower(OrmCategory.name_i18n["en"].astext).like(like_pattern)
            )

        from sqlalchemy import or_

        stmt = (
            select(
                OrmCategory.name_i18n,
                OrmCategory.slug,
                OrmCategory.full_slug,
            )
            .where(or_(*conditions))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        suggestions = []
        for row in rows:
            display = self._pick_locale(row.name_i18n, lang)
            if display:
                suggestions.append(
                    SearchSuggestionReadModel(
                        type="category",
                        text=display,
                        slug=row.slug,
                        extra={"full_slug": row.full_slug},
                    )
                )
        return suggestions

    async def _suggest_brands(
        self, like_pattern: str, limit: int
    ) -> list[SearchSuggestionReadModel]:
        """Prefix-match brand names."""
        stmt = (
            select(OrmBrand.name, OrmBrand.slug, OrmBrand.logo_url)
            .where(func.lower(OrmBrand.name).like(like_pattern))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            SearchSuggestionReadModel(
                type="brand",
                text=row.name,
                slug=row.slug,
                extra={"logo_url": row.logo_url} if row.logo_url else None,
            )
            for row in rows
        ]

    async def _suggest_products(
        self, like_pattern: str, lang: str | None, limit: int
    ) -> list[SearchSuggestionReadModel]:
        """Prefix-match product titles (published only)."""
        conditions = []
        if lang and lang in ("ru", "en"):
            conditions.append(
                func.lower(OrmProduct.title_i18n[lang].astext).like(like_pattern)
            )
        else:
            conditions.append(
                func.lower(OrmProduct.title_i18n["ru"].astext).like(like_pattern)
            )
            conditions.append(
                func.lower(OrmProduct.title_i18n["en"].astext).like(like_pattern)
            )

        from sqlalchemy import or_

        stmt = (
            select(
                OrmProduct.title_i18n,
                OrmProduct.slug,
            )
            .where(
                OrmProduct.status == ProductStatus.PUBLISHED,
                OrmProduct.is_visible.is_(True),
                OrmProduct.deleted_at.is_(None),
                or_(*conditions),
            )
            .order_by(OrmProduct.popularity_score.desc().nullslast())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        suggestions = []
        for row in rows:
            display = self._pick_locale(row.title_i18n, lang)
            if display:
                suggestions.append(
                    SearchSuggestionReadModel(
                        type="product",
                        text=display,
                        slug=row.slug,
                    )
                )
        return suggestions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_locale(i18n: dict[str, str] | None, lang: str | None) -> str:
        """Pick the best locale from an i18n dict."""
        if not i18n:
            return ""
        if lang and lang in i18n:
            return i18n[lang]
        # Fallback: first available
        return next(iter(i18n.values()), "")

    @staticmethod
    def _query_hash(query: SearchSuggestQuery) -> str:
        parts = {
            "q": query.q.strip().lower(),
            "l": query.limit,
            "lang": query.lang,
        }
        return hashlib.md5(
            json.dumps(parts, sort_keys=True).encode()
        ).hexdigest()[:12]

    async def _cache_result(
        self, key: str, results: list[SearchSuggestionReadModel]
    ) -> None:
        try:
            payload = json.dumps(
                [item.model_dump(mode="json") for item in results],
                default=str,
            )
            await self._cache.set(key, payload, ttl=STOREFRONT_SUGGEST_CACHE_TTL)
        except Exception:
            self._logger.warning("suggest_cache_write_failed", key=key)

    @staticmethod
    def _deserialize_cache(raw: str) -> list[SearchSuggestionReadModel]:
        data = json.loads(raw)
        return [SearchSuggestionReadModel.model_validate(i) for i in data]
