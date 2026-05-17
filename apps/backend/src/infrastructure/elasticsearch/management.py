"""Index lifecycle primitives for admin/CLI tooling.

These helpers wrap the ES indices/aliases APIs with the same translate
+ logging conventions as :mod:`bulk` and :mod:`health`. Consumers:

* :mod:`src.modules.catalog.management.reindex_products` — initial bulk
  reindex CLI; uses :func:`create_index`, :func:`alias_swap`,
  :func:`delete_index`.
* Smoke / integration tests that need to spin a fresh index per
  scenario.

We deliberately do *not* expose every indices/aliases endpoint — only
the subset that the alias-swap pattern from
``SPEC - Elasticsearch Product Search.md`` §5.4 actually requires.
Anything else goes through the raw client.
"""

from __future__ import annotations

from typing import Any

import structlog
from elasticsearch import AsyncElasticsearch

from src.infrastructure.elasticsearch.exceptions import translate

logger = structlog.get_logger(__name__)


async def index_exists(es: AsyncElasticsearch, *, name: str) -> bool:
    """Return whether the concrete index (not alias) exists.

    ``indices.exists`` returns ``HeadApiResponse`` which is a thin
    wrapper around the HTTP status — bool-cast captures the
    200/404 boolean intent without leaking the transport type.
    """
    try:
        return bool(await es.indices.exists(index=name))
    except Exception as exc:
        raise translate(exc, index=name) from exc


async def create_index(
    es: AsyncElasticsearch,
    *,
    name: str,
    settings: dict[str, Any] | None = None,
    mappings: dict[str, Any] | None = None,
    aliases: dict[str, Any] | None = None,
) -> None:
    """Create a fresh index.

    Idempotent guard at call sites: if the index already exists this
    raises a translated ``SearchConflictError`` (ES returns 400 with
    ``resource_already_exists_exception``). Callers that want
    create-or-skip semantics should ``await index_exists(...)`` first.
    """
    try:
        await es.indices.create(
            index=name,
            settings=settings or {},
            mappings=mappings or {},
            aliases=aliases or {},
        )
    except Exception as exc:
        raise translate(exc, index=name) from exc
    logger.info("elasticsearch.index.created", index=name)


async def delete_index(es: AsyncElasticsearch, *, name: str) -> None:
    """Drop an index. No-op if it does not exist."""
    try:
        await es.indices.delete(index=name, ignore_unavailable=True)
    except Exception as exc:
        raise translate(exc, index=name) from exc
    logger.info("elasticsearch.index.deleted", index=name)


async def current_alias_target(es: AsyncElasticsearch, *, alias: str) -> str | None:
    """Return the index name currently bound to ``alias``, or ``None``.

    When multiple indices are pointed at the same alias (legal but rare
    — typically only mid-swap) the lexicographically first is returned.
    Callers must not rely on the choice in that ambiguous window — use
    :func:`alias_swap` instead of manual remove/add.
    """
    try:
        resp = await es.indices.get_alias(name=alias, ignore_unavailable=True)
    except Exception as exc:
        raise translate(exc, index=alias) from exc

    # resp shape: {"products_v2": {"aliases": {"products": {}}}}
    indices = sorted(resp.keys())
    return indices[0] if indices else None


async def alias_swap(
    es: AsyncElasticsearch,
    *,
    alias: str,
    from_index: str | None,
    to_index: str,
) -> None:
    """Atomically point ``alias`` from ``from_index`` to ``to_index``.

    The two operations (remove + add) ship in a single ``_aliases``
    request — ES processes the actions transactionally so search
    traffic never sees a gap. ``from_index`` may be ``None`` for the
    first attach (no removal needed).
    """
    actions: list[dict[str, Any]] = []
    if from_index is not None:
        actions.append({"remove": {"index": from_index, "alias": alias}})
    actions.append({"add": {"index": to_index, "alias": alias}})

    try:
        await es.indices.update_aliases(actions=actions)
    except Exception as exc:
        raise translate(exc, index=to_index) from exc

    logger.info(
        "elasticsearch.alias.swapped",
        alias=alias,
        from_index=from_index,
        to_index=to_index,
    )


async def refresh(es: AsyncElasticsearch, *, index: str) -> None:
    """Force-refresh ``index`` so newly indexed docs become searchable.

    Production code should rely on ``refresh_interval`` for throughput;
    this helper is for tests and the post-reindex CLI step that wants
    to validate hit counts before alias swap.
    """
    try:
        await es.indices.refresh(index=index)
    except Exception as exc:
        raise translate(exc, index=index) from exc
