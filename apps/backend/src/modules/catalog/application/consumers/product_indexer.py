"""Outbox-driven Elasticsearch indexer for the Product aggregate.

Listens for Product lifecycle events on the outbox, rehydrates the
target product from PostgreSQL (with all denormalised fields the ES
mapping needs), and pushes it to the configured ES alias via
:func:`bulk_index`. Hard-deleted products (the row vanishes from PG)
are removed from ES by id; soft-deleted ones are re-indexed with
``deleted=true`` so admin search keeps finding them while public
filters (``deleted=false``) hide them.

Wired in by :class:`StorefrontCatalogProvider`; the bridges below run
at import time and register the consumer against the four
Product-level event types declared in :mod:`catalog.domain.events`.

What this consumer does NOT cover (future scope, SPEC §5.1):

* SKU price / status change events — reindex parent product when
  ``effective_price`` / ``in_stock`` flip. Currently those reach ES
  only via the next ``ProductUpdatedEvent`` (e.g. after manual edit)
  or on the nightly full reindex.
* Brand / category rename fan-out — products denormalise
  ``brand_name`` / ``category_full_slug`` so a rename should refresh
  the whole set. Add a bulk reindex bridge when needed.
* Media attach / detach events — covered indirectly by
  ``ProductUpdatedEvent`` today; promote to direct bridges when
  visible-only changes become common.
"""

from __future__ import annotations

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from elasticsearch import AsyncElasticsearch
from elasticsearch import NotFoundError as ESNotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.broker import broker
from src.bootstrap.config import Settings
from src.infrastructure.elasticsearch import bulk_index, translate
from src.infrastructure.idempotency import run_inbox_idempotent
from src.infrastructure.outbox.relay import register_event_handler
from src.modules.catalog.application.ports import IProductHydrationReader
from src.shared.interfaces.idempotency import IInboxStore

logger = structlog.get_logger(__name__)


class ProductIndexer:
    """Hydrate one product from PG and push it to Elasticsearch.

    Stateless — the dependencies (hydration reader, ES client, alias
    name, inbox guard) come from Dishka REQUEST scope per TaskIQ
    invocation.
    """

    def __init__(
        self,
        hydration: IProductHydrationReader,
        es: AsyncElasticsearch,
        index_alias: str,
    ) -> None:
        self._hydration = hydration
        self._es = es
        self._index = index_alias
        self._logger = logger.bind(consumer="ProductIndexer", index=index_alias)

    async def handle(self, payload: dict) -> None:
        raw = payload.get("product_id")
        if raw is None:
            self._logger.warning("product_indexer.skip", reason="missing_product_id")
            return
        try:
            product_id = uuid.UUID(str(raw))
        except TypeError, ValueError:
            self._logger.warning(
                "product_indexer.skip", reason="bad_product_id", raw=str(raw)
            )
            return

        doc = await self._hydration.get(product_id)
        if doc is None:
            await self._remove(product_id)
            return

        result = await bulk_index(
            self._es,
            index=self._index,
            docs=[doc.to_es_source()],
        )
        self._logger.info(
            "product_indexer.upsert",
            product_id=str(product_id),
            status=doc.status,
            visible=doc.is_visible,
            deleted=doc.deleted,
            es_success=result.success_count,
            es_errors=result.error_count,
        )

    async def _remove(self, product_id: uuid.UUID) -> None:
        try:
            await self._es.delete(index=self._index, id=str(product_id))
        except ESNotFoundError:
            self._logger.info(
                "product_indexer.delete.noop",
                product_id=str(product_id),
                reason="not_in_index",
            )
            return
        except Exception as exc:
            raise translate(exc, index=self._index, doc_id=str(product_id)) from exc
        self._logger.info("product_indexer.deleted", product_id=str(product_id))


# ---------------------------------------------------------------------------
# TaskIQ task — idempotent consumer body
# ---------------------------------------------------------------------------


@broker.task(
    queue="catalog_indexer",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.product.index",
    max_retries=5,
    retry_on_error=True,
    timeout=60,
)
@inject
async def index_product_task(
    payload: dict,
    *,
    settings: FromDishka[Settings],
    hydration: FromDishka[IProductHydrationReader],
    es: FromDishka[AsyncElasticsearch],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    """Idempotent reindex of a single product.

    The actual work is delegated to a freshly-constructed
    :class:`ProductIndexer` so the same task can switch backends (e.g.
    routing-key-based sharding) without re-wiring DI.
    """
    indexer = ProductIndexer(
        hydration=hydration,
        es=es,
        index_alias=settings.ELASTICSEARCH_INDEX_ALIAS,
    )
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="catalog.ProductIndexer",
        inbox=inbox,
        session=session,
        body=lambda: indexer.handle(payload),
    )


# ---------------------------------------------------------------------------
# Outbox handler registration
# ---------------------------------------------------------------------------


def _labels(correlation_id: str | None) -> dict[str, str]:
    return {"correlation_id": correlation_id} if correlation_id else {}


async def _on_product_event(payload: dict, correlation_id: str | None = None) -> None:
    """Bridge any Product-level event onto the indexer task.

    All four events (``ProductCreatedEvent`` / ``ProductStatusChangedEvent`` /
    ``ProductUpdatedEvent`` / ``ProductDeletedEvent``) carry a
    ``product_id`` and trigger the exact same reindex flow — the
    indexer derives the operation type from the live PG state, not the
    event class. This keeps the bridge layer trivial and avoids a
    handful of near-identical functions.
    """
    await (
        index_product_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


register_event_handler("ProductCreatedEvent", _on_product_event)
register_event_handler("ProductStatusChangedEvent", _on_product_event)
register_event_handler("ProductUpdatedEvent", _on_product_event)
register_event_handler("ProductDeletedEvent", _on_product_event)
