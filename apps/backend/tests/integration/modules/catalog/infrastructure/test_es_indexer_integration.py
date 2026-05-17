"""Integration test for the ProductIndexer end-to-end against a real
Elasticsearch container.

Distinct from the rest of ``tests/integration/modules/catalog`` because
the session-level conftest stubs :class:`AsyncElasticsearch` with an
``AsyncMock`` to keep regular runs hermetic (REC-020 — testcontainers
ES adds ~30s per session). This test spins its own container, so it's
opt-in via ``@pytest.mark.es``:

    make test-es              # only this kind of test
    pytest -m es              # ditto, raw

Hydration is mocked — we're verifying the bulk_index + ES round-trip,
not the PG query layer (covered by unit tests on the adapter). The
flow under test:

    ProductIndexer.handle(payload)
      → IProductHydrationReader.get(...)            (mocked)
      → bulk_index(es, alias, [doc.to_es_source()]) (real ES)
      → es.search(...)                              (real ES, asserts hit)
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from elasticsearch import AsyncElasticsearch

from src.modules.catalog.application.consumers.product_indexer import ProductIndexer
from src.modules.catalog.application.ports import (
    IProductHydrationReader,
    ProductIndexDoc,
)

pytestmark = [pytest.mark.integration, pytest.mark.es]

# Minimal viable subset of the v1 mapping (SPEC §4.1) — only the fields
# the assertions touch. Full mapping stays in the SPEC doc as single
# source of truth; tests duplicate just enough to exercise the path.
_MINIMAL_INDEX_BODY: dict[str, Any] = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
        "dynamic": "true",
        "properties": {
            "product_id": {"type": "keyword"},
            "slug": {"type": "keyword"},
            "status": {"type": "keyword"},
            "is_visible": {"type": "boolean"},
            "deleted": {"type": "boolean"},
            "title_ru": {"type": "text"},
            "title_en": {"type": "text"},
            "effective_price": {"type": "long"},
            "currency": {"type": "keyword"},
            "in_stock": {"type": "boolean"},
        },
    },
}


@pytest.fixture(scope="session")
def es_container() -> Any:
    """Spin a one-off Elasticsearch container for this test module.

    Imported lazily so the optional ``testcontainers[elasticsearch]``
    dep doesn't break collection in environments without docker
    (regular ``make test-unit`` runs).
    """
    pytest.importorskip("testcontainers.elasticsearch")
    from testcontainers.elasticsearch import ElasticSearchContainer

    container = ElasticSearchContainer(
        "docker.elastic.co/elasticsearch/elasticsearch:8.19.10"
    )
    container.with_env("xpack.security.enabled", "false")
    container.with_env("discovery.type", "single-node")
    container.with_env("ES_JAVA_OPTS", "-Xms512m -Xmx512m")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture
async def es_client(es_container: Any) -> AsyncIterator[AsyncElasticsearch]:
    """Async ES client bound to the running container."""
    client = AsyncElasticsearch(
        hosts=[es_container.get_url()],
        request_timeout=15,
        max_retries=2,
        retry_on_timeout=True,
    )
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
async def fresh_index(es_client: AsyncElasticsearch) -> AsyncIterator[str]:
    """Per-test index — created from the minimal mapping, torn down after."""
    name = f"products_test_{uuid.uuid4().hex[:8]}"
    await es_client.indices.create(
        index=name,
        settings=_MINIMAL_INDEX_BODY["settings"],
        mappings=_MINIMAL_INDEX_BODY["mappings"],
    )
    try:
        yield name
    finally:
        await es_client.indices.delete(index=name, ignore_unavailable=True)


def _make_doc(*, product_id: uuid.UUID, **overrides: Any) -> ProductIndexDoc:
    defaults: dict[str, Any] = {
        "product_id": product_id,
        "slug": f"slug-{product_id.hex[:6]}",
        "status": "published",
        "is_visible": True,
        "deleted": False,
        "title_ru": "Кроссовки Nike Air Max",
        "title_en": "Nike Air Max Sneakers",
        "effective_price": 1599000,
        "currency": "RUB",
        "in_stock": True,
    }
    defaults.update(overrides)
    return ProductIndexDoc(**defaults)


@pytest.mark.asyncio
async def test_indexer_upserts_document_into_es(
    es_client: AsyncElasticsearch, fresh_index: str
) -> None:
    """Happy path: indexer hydrates → bulk_index → doc searchable."""
    product_id = uuid.uuid4()
    doc = _make_doc(product_id=product_id)

    hydration = AsyncMock(spec=IProductHydrationReader)
    hydration.get.return_value = doc

    indexer = ProductIndexer(hydration=hydration, es=es_client, index_alias=fresh_index)
    await indexer.handle({"product_id": str(product_id)})
    await es_client.indices.refresh(index=fresh_index)

    hits = await es_client.search(
        index=fresh_index,
        query={"term": {"product_id": str(product_id)}},
    )
    assert hits["hits"]["total"]["value"] == 1
    source = hits["hits"]["hits"][0]["_source"]
    assert source["title_ru"] == doc.title_ru
    assert source["effective_price"] == doc.effective_price
    assert source["status"] == "published"


@pytest.mark.asyncio
async def test_indexer_deletes_missing_product_from_es(
    es_client: AsyncElasticsearch, fresh_index: str
) -> None:
    """Hydration returns None ⇒ indexer issues an ES DELETE."""
    product_id = uuid.uuid4()

    # Seed a stale doc so we can observe the deletion.
    await es_client.index(
        index=fresh_index,
        id=str(product_id),
        document=_make_doc(product_id=product_id).to_es_source(),
        refresh=True,
    )

    hydration = AsyncMock(spec=IProductHydrationReader)
    hydration.get.return_value = None  # product gone

    indexer = ProductIndexer(hydration=hydration, es=es_client, index_alias=fresh_index)
    await indexer.handle({"product_id": str(product_id)})
    await es_client.indices.refresh(index=fresh_index)

    hits = await es_client.search(
        index=fresh_index,
        query={"term": {"product_id": str(product_id)}},
    )
    assert hits["hits"]["total"]["value"] == 0


@pytest.mark.asyncio
async def test_indexer_delete_is_idempotent_on_missing_es_doc(
    es_client: AsyncElasticsearch, fresh_index: str
) -> None:
    """Deleting a doc that was never indexed must NOT raise."""
    hydration = AsyncMock(spec=IProductHydrationReader)
    hydration.get.return_value = None

    indexer = ProductIndexer(hydration=hydration, es=es_client, index_alias=fresh_index)
    # Should silently no-op when ES returns NotFoundError.
    await indexer.handle({"product_id": str(uuid.uuid4())})


@pytest.mark.asyncio
async def test_indexer_skips_payload_without_product_id(
    es_client: AsyncElasticsearch, fresh_index: str
) -> None:
    """Defensive: malformed payload (no product_id) is a no-op."""
    hydration = AsyncMock(spec=IProductHydrationReader)
    indexer = ProductIndexer(hydration=hydration, es=es_client, index_alias=fresh_index)
    await indexer.handle({})
    hydration.get.assert_not_called()
