"""Bulk-indexing helpers built on top of ``elasticsearch.helpers.async_bulk``.

The shipped ``async_bulk`` returns a 2-tuple ``(success_count, errors)``
where ``errors`` is a heterogeneous list of dicts. This module wraps it
with:

* A typed :class:`BulkResult` so call sites get autocomplete instead of
  poking dict keys.
* Per-item structured logging so failed docs are individually visible
  in stdout / Grafana — single aggregate warning is unhelpful when 5 of
  500 docs fail and you need to know which.
* Translation of transport-level failures to :class:`SearchBackendError`
  via :func:`translate`, so callers handle one exception type.

Indexers (TaskIQ consumers) and the initial-reindex CLI both go through
this helper to keep observability uniform.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

import structlog
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from src.infrastructure.elasticsearch.exceptions import translate

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BulkResult:
    """Outcome of a single :func:`bulk_index` invocation."""

    success_count: int
    error_count: int
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0


async def bulk_index(
    es: AsyncElasticsearch,
    *,
    index: str,
    docs: Iterable[Mapping[str, Any]] | AsyncIterator[Mapping[str, Any]],
    chunk_size: int = 500,
    max_chunk_bytes: int = 100 * 1024 * 1024,
    raise_on_error: bool = False,
    refresh: bool = False,
) -> BulkResult:
    """Index ``docs`` into ``index`` via the ``_bulk`` API.

    Args:
        es: APP-scoped async client.
        index: Target index name. Caller is expected to pass the alias
            (``products``) in normal operation and the concrete name
            (``products_v2``) only during alias-swap reindex.
        docs: Iterable (or async iterable) of plain dicts. Each dict
            must contain an ``_id`` field — the rest is sent as
            ``_source``. The wrapping ``{"_op_type": "index", "_index":
            ..., "_id": ..., "_source": ...}`` shape is built here so
            call sites stay focused on payload.
        chunk_size: Documents per HTTP request. 500 is the ES default
            and the sweet spot for 1–10KB docs; lower for heavier
            payloads, higher for tiny telemetry-style records.
        max_chunk_bytes: Hard upper bound on a single batch payload.
            Prevents one outlier doc (e.g. 50MB description) from
            blowing up the request.
        raise_on_error: Propagate the first per-item failure via
            :func:`translate` instead of collecting them. Use ``True``
            in CLI/admin flows where a single failure is a fail-fast
            signal; keep ``False`` (default) in consumers — they log
            errors and move on so the queue does not stall.
        refresh: Force an index refresh after the batch (debug/test
            helper only; production indexers rely on the default
            ``refresh_interval`` to keep ingest throughput up).

    Returns:
        :class:`BulkResult` with success/error counts and the raw
        per-item error payloads for further triage.
    """

    actions = _as_actions(index=index, docs=docs)

    try:
        success, errors = await async_bulk(
            es,
            actions,
            chunk_size=chunk_size,
            max_chunk_bytes=max_chunk_bytes,
            raise_on_error=raise_on_error,
            refresh=refresh,
        )
    except Exception as exc:
        # Transport-level failure (ES down, auth refused, malformed
        # request). Translate once so callers handle a single typed
        # exception instead of mixing transport-specific classes.
        raise translate(exc, index=index) from exc

    # ``async_bulk`` returns ``(int, list)`` when ``raise_on_error=False``
    # and ``(int, int)`` with ``stats_only=True`` (we never pass it, but
    # the typeshed-style signature is a union, so narrow explicitly).
    error_list: list[dict[str, Any]] = (
        [cast(dict[str, Any], e) for e in errors] if isinstance(errors, list) else []
    )
    for err in error_list:
        # async_bulk error payload: {"index": {"_id": ..., "status":
        # 4xx, "error": {"type": ..., "reason": ...}}, ...}
        op = _first_op_payload(err)
        err_meta = op.get("error") or {}
        logger.warning(
            "elasticsearch.bulk.item_failed",
            index=index,
            doc_id=op.get("_id"),
            status=op.get("status"),
            error_type=err_meta.get("type") if isinstance(err_meta, Mapping) else None,
            reason=err_meta.get("reason") if isinstance(err_meta, Mapping) else None,
        )

    logger.info(
        "elasticsearch.bulk.done",
        index=index,
        success=success,
        errors=len(error_list),
    )
    return BulkResult(
        success_count=success,
        error_count=len(error_list),
        errors=error_list,
    )


def _first_op_payload(err: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the inner op dict from an async_bulk error envelope.

    Shape: ``{"index": {"_id": ..., "status": ..., "error": {...}}}``.
    Returns an empty dict if the envelope is malformed so callers can
    keep using ``.get(...)`` without isinstance dance at the call site.
    """
    for value in err.values():
        if isinstance(value, Mapping):
            return dict(value)
        return {}
    return {}


def _as_actions(
    *,
    index: str,
    docs: Iterable[Mapping[str, Any]] | AsyncIterator[Mapping[str, Any]],
) -> Iterable[dict[str, Any]] | AsyncIterator[dict[str, Any]]:
    """Wrap raw ``{"_id": ..., **fields}`` dicts into the ``_bulk`` action shape.

    Branches on ``__aiter__`` presence to support both sync and async
    sources (CLI reads from SQLAlchemy scroll = sync; outbox consumer
    receives `AsyncIterator` from upstream). ``cast`` is used because
    the static type checker cannot narrow a union by ``hasattr`` alone.
    """
    if hasattr(docs, "__aiter__"):
        async_docs = cast(AsyncIterator[Mapping[str, Any]], docs)

        async def _async_gen() -> AsyncIterator[dict[str, Any]]:
            async for doc in async_docs:
                yield _wrap(index=index, doc=doc)

        return _async_gen()

    sync_docs = cast(Iterable[Mapping[str, Any]], docs)

    def _sync_gen() -> Iterable[dict[str, Any]]:
        for doc in sync_docs:
            yield _wrap(index=index, doc=doc)

    return _sync_gen()


def _wrap(*, index: str, doc: Mapping[str, Any]) -> dict[str, Any]:
    doc_id = doc.get("_id")
    if doc_id is None:
        raise ValueError("bulk_index document missing required '_id' field")
    source = {k: v for k, v in doc.items() if k != "_id"}
    return {
        "_op_type": "index",
        "_index": index,
        "_id": str(doc_id),
        "_source": source,
    }
