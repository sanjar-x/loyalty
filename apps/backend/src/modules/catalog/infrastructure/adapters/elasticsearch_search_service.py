"""Elasticsearch implementation of :class:`IProductSearchService`.

Phase 2 SPEC skeleton — feature-parity wire shape with the existing
PG-backed handler (same criteria DTO in, same ``CursorPage`` /
``SearchSuggestionReadModel`` out). The query DSL stays deliberately
small: ``multi_match`` over ``all_text_ru`` / ``all_text_en`` (the
combined ``copy_to`` fields built by the mapping in v1) plus a
``bool.filter`` block for status / visibility / category / brand /
price / stock / nested attribute_values. Ranking by ``_score`` for the
default ``relevant`` sort, otherwise by the doc field.

Anti-corruption rules:
* The adapter owns the entire ES <-> read-model mapping. Application
  layer never sees ES documents.
* All transport errors funnel through ``translate(...)`` from the
  shared ES infrastructure so the global error handler emits the same
  envelope as for SQL / Redis failures.
* Cursor encoding piggybacks on :func:`src.shared.pagination.encode_cursor`
  for wire compatibility with the PG-backed handler.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

import structlog
from elasticsearch import AsyncElasticsearch

from src.infrastructure.elasticsearch import translate
from src.modules.catalog.application.ports import (
    IProductSearchService,
    SearchProductsCriteria,
    SearchSuggestCriteria,
)
from src.modules.catalog.application.queries.read_models import (
    SearchSuggestionReadModel,
    StorefrontBrandReadModel,
    StorefrontImageReadModel,
    StorefrontMoneyReadModel,
    StorefrontProductCardReadModel,
    StorefrontSupplierReadModel,
)
from src.shared.pagination import CursorPage, decode_cursor, encode_cursor

logger = structlog.get_logger(__name__)


class ElasticsearchProductSearchService(IProductSearchService):
    """Elasticsearch-backed search adapter.

    Provider-side wiring in :class:`StorefrontCatalogProvider` selects
    this implementation when ``settings.SEARCH_PROVIDER == "elasticsearch"``;
    until then it sits dormant in the container — instantiable for
    smoke / integration tests but not on the request path.
    """

    def __init__(self, es: AsyncElasticsearch, index_alias: str) -> None:
        self._es = es
        self._index = index_alias
        self._logger = logger.bind(
            adapter="ElasticsearchProductSearchService", index=index_alias
        )

    # ------------------------------------------------------------------
    # IProductSearchService
    # ------------------------------------------------------------------

    async def search(
        self, criteria: SearchProductsCriteria
    ) -> CursorPage[StorefrontProductCardReadModel]:
        body = self._build_search_body(criteria)
        try:
            resp = await self._es.search(
                index=self._index, body=body, size=criteria.limit + 1
            )
        except Exception as exc:
            raise translate(exc, index=self._index) from exc

        hits = list(resp.get("hits", {}).get("hits", []))
        has_next = len(hits) > criteria.limit
        page_hits = hits[: criteria.limit]
        items = [self._hit_to_card(h) for h in page_hits]

        next_cursor: str | None = None
        if has_next and items:
            sort_val = self._extract_sort_value(page_hits[-1], criteria.sort)
            next_cursor = encode_cursor(sort_val, items[-1].id)

        total: int | None = None
        if criteria.include_total:
            raw_total = resp.get("hits", {}).get("total", {})
            if isinstance(raw_total, dict):
                total = raw_total.get("value")

        return CursorPage(
            items=items, has_next=has_next, next_cursor=next_cursor, total=total
        )

    async def suggest(
        self, criteria: SearchSuggestCriteria
    ) -> list[SearchSuggestionReadModel]:
        prefix = criteria.q.strip()
        if len(prefix) < 2:
            return []

        body = {
            "query": {
                "multi_match": {
                    "query": prefix,
                    "type": "bool_prefix",
                    "fields": [
                        "title_ru.suggest",
                        "title_ru.suggest._2gram",
                        "title_ru.suggest._3gram",
                        "title_en.suggest",
                        "title_en.suggest._2gram",
                        "brand_name.suggest",
                        "brand_name.suggest._2gram",
                    ],
                }
            },
            "_source": ["product_id", "slug", "title_ru", "title_en", "brand_name"],
            "size": max(1, min(criteria.limit, 10)),
        }
        try:
            resp = await self._es.search(index=self._index, body=body)
        except Exception as exc:
            raise translate(exc, index=self._index) from exc

        out: list[SearchSuggestionReadModel] = []
        for hit in resp.get("hits", {}).get("hits", []):
            src = cast(dict[str, Any], hit.get("_source", {}))
            title = self._pick_locale(src, criteria.lang)
            if not title:
                continue
            out.append(
                SearchSuggestionReadModel(
                    type="product",
                    text=title,
                    slug=str(src.get("slug", "")),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Body builders
    # ------------------------------------------------------------------

    def _build_search_body(self, criteria: SearchProductsCriteria) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        q = criteria.q.strip()
        if q:
            must.append(
                {
                    "multi_match": {
                        "query": q,
                        "fields": [
                            "title_ru^3",
                            "title_en^3",
                            "brand_name^2",
                            "tags_text^1.5",
                            "all_text_ru",
                            "all_text_en",
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                        "operator": "and",
                    }
                }
            )
        else:
            must.append({"match_all": {}})

        filters: list[dict[str, Any]] = [
            {"term": {"status": "published"}},
            {"term": {"is_visible": True}},
            {"term": {"deleted": False}},
        ]
        if criteria.category_id is not None:
            filters.append({"term": {"category_ids": str(criteria.category_id)}})
        if criteria.brand_ids:
            filters.append(
                {"terms": {"brand_id": [str(b) for b in criteria.brand_ids]}}
            )
        if criteria.price_min is not None or criteria.price_max is not None:
            rng: dict[str, Any] = {}
            if criteria.price_min is not None:
                rng["gte"] = criteria.price_min
            if criteria.price_max is not None:
                rng["lte"] = criteria.price_max
            filters.append({"range": {"effective_price": rng}})
        if criteria.in_stock:
            filters.append({"term": {"in_stock": True}})
        for code, slugs in criteria.attribute_filters.items():
            if not slugs:
                continue
            filters.append(
                {
                    "nested": {
                        "path": "attribute_values",
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"attribute_values.attribute_code": code}},
                                    {
                                        "terms": {
                                            "attribute_values.value_slug": list(slugs)
                                        }
                                    },
                                ]
                            }
                        },
                    }
                }
            )

        body: dict[str, Any] = {
            "query": {"bool": {"must": must, "filter": filters}},
            "sort": self._build_sort(criteria.sort),
            "track_total_hits": bool(criteria.include_total),
        }

        if criteria.cursor:
            cursor_sort, cursor_id = decode_cursor(criteria.cursor)
            body["search_after"] = [cursor_sort, str(cursor_id)]

        return body

    # ------------------------------------------------------------------
    # Sort / cursor helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_sort(sort: str) -> list[dict[str, Any]]:
        # ``product_id`` tiebreaker keeps cursor pagination stable when
        # the primary sort value collides on multiple docs.
        if sort == "newest":
            return [
                {"published_at": {"order": "desc", "missing": "_last"}},
                {"product_id": "desc"},
            ]
        if sort == "price_asc":
            return [
                {"effective_price": {"order": "asc", "missing": "_last"}},
                {"product_id": "desc"},
            ]
        if sort == "price_desc":
            return [
                {"effective_price": {"order": "desc", "missing": "_last"}},
                {"product_id": "desc"},
            ]
        if sort == "popular":
            return [
                {"popularity_score": {"order": "desc", "missing": "_last"}},
                {"product_id": "desc"},
            ]
        # Default: relevance (FTS rank).
        return [{"_score": "desc"}, {"product_id": "desc"}]

    @staticmethod
    def _extract_sort_value(hit: dict[str, Any], sort: str) -> Any:
        src = cast(dict[str, Any], hit.get("_source", {}))
        if sort == "newest":
            return src.get("published_at")
        if sort in ("price_asc", "price_desc"):
            return src.get("effective_price")
        if sort == "popular":
            return src.get("popularity_score")
        score = hit.get("_score")
        return float(score) if score is not None else 0.0

    # ------------------------------------------------------------------
    # Hit → ReadModel mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _hit_to_card(hit: dict[str, Any]) -> StorefrontProductCardReadModel:
        src = cast(dict[str, Any], hit.get("_source", {}))

        image: StorefrontImageReadModel | None = None
        if src.get("image_url"):
            image = StorefrontImageReadModel(
                url=str(src["image_url"]),
                image_variants=src.get("image_variants"),
            )

        price: StorefrontMoneyReadModel | None = None
        if src.get("effective_price") is not None:
            price = StorefrontMoneyReadModel(
                amount=int(src["effective_price"]),
                currency=str(src.get("currency") or "RUB"),
                compare_at=src.get("compare_at_price"),
            )

        brand: StorefrontBrandReadModel | None = None
        if src.get("brand_name"):
            brand_id = src.get("brand_id")
            brand = StorefrontBrandReadModel(
                id=uuid.UUID(str(brand_id)) if brand_id else uuid.UUID(int=0),
                name=str(src["brand_name"]),
                slug=str(src.get("brand_slug") or ""),
                logo_url=src.get("brand_logo_url"),
            )

        supplier: StorefrontSupplierReadModel | None = None
        if src.get("supplier_type"):
            supplier = StorefrontSupplierReadModel(type=str(src["supplier_type"]))

        title_i18n: dict[str, str] = {}
        if src.get("title_ru"):
            title_i18n["ru"] = str(src["title_ru"])
        if src.get("title_en"):
            title_i18n["en"] = str(src["title_en"])

        published_at = src.get("published_at")
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
            except ValueError:
                published_at = None

        return StorefrontProductCardReadModel(
            id=uuid.UUID(str(src["product_id"])),
            slug=str(src.get("slug") or ""),
            title_i18n=title_i18n,
            image=image,
            price=price,
            brand=brand,
            supplier=supplier,
            popularity_score=int(src.get("popularity_score") or 0),
            published_at=published_at,
            variant_count=int(src.get("variant_count") or 0),
            in_stock=bool(src.get("in_stock")),
        )

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_locale(src: dict[str, Any], lang: str | None) -> str:
        if lang == "en" and src.get("title_en"):
            return str(src["title_en"])
        if src.get("title_ru"):
            return str(src["title_ru"])
        if src.get("title_en"):
            return str(src["title_en"])
        if src.get("brand_name"):
            return str(src["brand_name"])
        return ""
