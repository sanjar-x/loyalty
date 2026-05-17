"""Health-probe helpers for Elasticsearch.

Used by the optional ``/health/elasticsearch`` endpoint and by the
``ping_at_startup`` hook in the provider. Returns a small structured
DTO instead of leaking the raw ``info()`` / ``cluster.health()``
payloads so the public health contract is stable across ES upgrades.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from elasticsearch import AsyncElasticsearch

from src.infrastructure.elasticsearch.exceptions import translate

ClusterStatus = Literal["green", "yellow", "red", "unknown"]


@dataclass(frozen=True)
class ElasticsearchHealth:
    """Stable DTO returned by :func:`check_health`."""

    reachable: bool
    status: ClusterStatus = "unknown"
    version: str | None = None
    cluster_name: str | None = None
    number_of_nodes: int | None = None
    active_shards: int | None = None
    error: str | None = None


async def check_health(es: AsyncElasticsearch) -> ElasticsearchHealth:
    """Probe cluster reachability and basic stats.

    Never raises — wraps ES-side errors into ``ElasticsearchHealth(reachable=False)``
    so the /health endpoint can render a 200 with a payload instead of
    falling back to the generic 500 handler.
    """
    try:
        info = await es.info()
        health = await es.cluster.health()
    except Exception as exc:
        translated = translate(exc)
        return ElasticsearchHealth(reachable=False, error=str(translated.message))

    raw_status = str(health.get("status", "")).lower()
    status: ClusterStatus = cast(
        ClusterStatus,
        raw_status if raw_status in ("green", "yellow", "red") else "unknown",
    )

    return ElasticsearchHealth(
        reachable=True,
        status=status,
        version=info.get("version", {}).get("number"),
        cluster_name=info.get("cluster_name"),
        number_of_nodes=health.get("number_of_nodes"),
        active_shards=health.get("active_shards"),
    )


async def ping(es: AsyncElasticsearch) -> bool:
    """Minimal liveness probe — ``True`` when ES responds, ``False`` otherwise.

    Cheap enough to call from request-path circuit-breakers; the
    structured stats from :func:`check_health` are reserved for the
    admin/monitoring endpoint.
    """
    try:
        return await es.ping()
    except Exception:
        return False
