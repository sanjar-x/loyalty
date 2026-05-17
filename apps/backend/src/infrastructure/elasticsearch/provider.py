"""Dishka dependency provider for the Elasticsearch client.

Manages the :class:`AsyncElasticsearch` lifecycle as an APP-scoped
resource — the client owns an aiohttp connection pool that must NOT
be recreated per request (each new instance leaks sockets until GC).
Modelled on :class:`CacheProvider` (Redis) and the DobroPost HTTP
client provider in the order module.
"""

from __future__ import annotations

from collections.abc import AsyncIterable

import structlog
from dishka import Provider, Scope, provide
from elastic_transport import ConnectionError as ESConnectionError
from elasticsearch import AsyncElasticsearch

from src.bootstrap.config import Settings

logger = structlog.get_logger(__name__)


class ElasticsearchProvider(Provider):
    """Dishka provider that supplies the async Elasticsearch client.

    The client is APP-scoped: created once on application startup, kept
    alive across all requests, and closed on shutdown. ``setup_dishka``
    in :mod:`src.bootstrap.web` triggers the generator's cleanup branch
    via container.close().
    """

    @provide(scope=Scope.APP)
    async def es_client(self, settings: Settings) -> AsyncIterable[AsyncElasticsearch]:
        """Yield a ready-to-use ``AsyncElasticsearch`` instance.

        Boot-time behaviour:

        * If ``elasticsearch_resolved_url`` is empty, the client is
          still constructed against ``http://localhost:9200`` so unit
          tests / smoke imports do not blow up on a missing env var.
          Real cluster calls will fail loudly with a connection error
          — which is the correct signal (search is unconfigured).
        * Otherwise the client connects to the resolved URL, performs
          a ping, and logs the cluster version. A ping failure is
          logged as a warning but does NOT abort startup: the API can
          still serve non-search traffic while the operator fixes the
          deployment.
        """
        url = settings.elasticsearch_resolved_url or "http://localhost:9200"
        username = settings.ELASTICSEARCH_USERNAME
        password = settings.ELASTICSEARCH_PASSWORD.get_secret_value()
        basic_auth = (username, password) if username and password else None

        client = AsyncElasticsearch(
            hosts=[url],
            basic_auth=basic_auth,
            request_timeout=settings.ELASTICSEARCH_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.ELASTICSEARCH_MAX_RETRIES,
            retry_on_timeout=True,
            verify_certs=True,
        )

        await _ping_at_startup(client, url=url)

        try:
            yield client
        finally:
            logger.info("elasticsearch.client.closing", url=url)
            await client.close()


async def _ping_at_startup(client: AsyncElasticsearch, *, url: str) -> None:
    """Best-effort health probe so connection issues surface immediately.

    A failed ping is *not* a deploy-breaking error: a fresh Railway
    redeploy may take a few seconds before ES accepts traffic, and the
    customer-facing search endpoint already degrades gracefully via the
    feature-flag fallback (``SEARCH_PROVIDER=postgres``). Logging a
    warning keeps the failure observable without false-positive crashes
    on rolling restarts.
    """
    try:
        info = await client.info()
        logger.info(
            "elasticsearch.client.connected",
            url=url,
            version=info["version"]["number"],
            cluster_name=info["cluster_name"],
        )
    except ESConnectionError as exc:
        logger.warning(
            "elasticsearch.client.connect_failed",
            url=url,
            error=str(exc),
        )
    except Exception as exc:
        logger.warning(
            "elasticsearch.client.ping_failed",
            url=url,
            error=str(exc),
            error_type=exc.__class__.__name__,
        )
