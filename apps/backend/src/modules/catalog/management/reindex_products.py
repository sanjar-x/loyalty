"""Initial / full reindex of products into Elasticsearch.

Usage::

    # Reindex into the index currently bound to the ``products`` alias.
    uv run python -m src.modules.catalog.management.reindex_products

    # Reindex into a fresh index, then atomically swap the alias.
    # Operator must have already created ``products_v2`` with the
    # target mapping (see SPEC - Elasticsearch Product Search §4.1).
    uv run python -m src.modules.catalog.management.reindex_products \\
        --target-index products_v2 --swap-alias

    # Bigger batches for high-CPU bulk windows.
    uv run python -m src.modules.catalog.management.reindex_products \\
        --batch-size 1000

The script reuses the same dependencies as the runtime indexer
(:class:`ProductHydrationAdapter` + :func:`bulk_index` from the shared
ES infra) by resolving them through the live Dishka container. There
is no second wiring path — what runs in the CLI is what runs in the
TaskIQ consumer.

Index lifecycle (create + mapping + alias attach/detach) stays out of
this script intentionally — operators do it through ``curl``/``_aliases``
with the mapping JSON from the SPEC, so the mapping has a single
source of truth (the doc) and the CLI cannot accidentally diverge.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import AsyncIterator
from typing import Any

import structlog
from elasticsearch import AsyncElasticsearch
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import Settings
from src.bootstrap.container import create_container
from src.bootstrap.logger import setup_logging
from src.infrastructure.elasticsearch import (
    alias_swap,
    bulk_index,
    current_alias_target,
)
from src.modules.catalog.application.ports import IProductHydrationReader

logger = structlog.get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reindex_products",
        description=(
            "Stream all non-deleted products from PostgreSQL into "
            "Elasticsearch via the shared bulk helper."
        ),
    )
    parser.add_argument(
        "--target-index",
        default=None,
        help=(
            "Concrete index name to write into. Defaults to the index "
            "the ``products`` alias currently resolves to."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Hydration + bulk batch size (default: 500).",
    )
    parser.add_argument(
        "--swap-alias",
        action="store_true",
        help=(
            "After successful reindex, atomically swap the "
            "ELASTICSEARCH_INDEX_ALIAS alias to point at "
            "--target-index. Required for zero-downtime mapping upgrades."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N products (smoke / staging). Unlimited by default.",
    )
    return parser


async def _resolve_target_index(
    es: AsyncElasticsearch, *, alias: str, override: str | None
) -> str:
    """Decide where to write.

    Explicit ``--target-index`` wins. Otherwise resolve the live
    alias; bail out if the alias doesn't exist yet (operator forgot
    to provision it).
    """
    if override:
        return override
    current = await current_alias_target(es, alias=alias)
    if current is None:
        raise SystemExit(
            f"Alias {alias!r} is not attached to any index. Either "
            "create the alias first or pass --target-index explicitly."
        )
    return current


async def _batched(
    source: AsyncIterator[Any], *, size: int
) -> AsyncIterator[list[dict[str, Any]]]:
    """Group an async stream of ``ProductIndexDoc`` into bulk-sized chunks."""
    buf: list[dict[str, Any]] = []
    async for doc in source:
        buf.append(doc.to_es_source())
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


async def _run(args: argparse.Namespace) -> int:
    container = create_container()
    try:
        settings = await container.get(Settings)
        es = await container.get(AsyncElasticsearch)

        target = await _resolve_target_index(
            es, alias=settings.ELASTICSEARCH_INDEX_ALIAS, override=args.target_index
        )
        logger.info(
            "reindex.start",
            target_index=target,
            alias=settings.ELASTICSEARCH_INDEX_ALIAS,
            batch_size=args.batch_size,
            limit=args.limit,
        )
        start = time.monotonic()

        total_success = 0
        total_errors = 0
        async with container() as request:
            session = await request.get(AsyncSession)
            hydration = await request.get(IProductHydrationReader)
            stream = hydration.iter_indexable(batch_size=args.batch_size)

            limit_remaining = args.limit
            async for batch in _batched(stream, size=args.batch_size):
                if limit_remaining is not None:
                    batch = batch[:limit_remaining]
                    limit_remaining -= len(batch)

                result = await bulk_index(
                    es,
                    index=target,
                    docs=batch,
                    chunk_size=args.batch_size,
                )
                total_success += result.success_count
                total_errors += result.error_count
                logger.info(
                    "reindex.batch",
                    target_index=target,
                    success=result.success_count,
                    errors=result.error_count,
                    cumulative_success=total_success,
                    cumulative_errors=total_errors,
                )

                if limit_remaining is not None and limit_remaining <= 0:
                    logger.info("reindex.limit_reached", limit=args.limit)
                    break

            await session.commit()

        elapsed = time.monotonic() - start
        logger.info(
            "reindex.done",
            target_index=target,
            success=total_success,
            errors=total_errors,
            elapsed_seconds=round(elapsed, 2),
            docs_per_sec=round(total_success / elapsed, 1) if elapsed > 0 else None,
        )

        if args.swap_alias:
            if args.target_index is None:
                raise SystemExit(
                    "--swap-alias requires --target-index (you have to "
                    "name the index you want to swap to)."
                )
            # H4 (Deep Review fix #1): refuse to swap a partially-failed
            # reindex live — storefront search would silently lose
            # whichever products bounced off ``bulk_index``. Operator
            # must fix the underlying error and re-run.
            if total_errors > 0:
                raise SystemExit(
                    f"--swap-alias refused: reindex finished with "
                    f"{total_errors} per-item failures (success={total_success}). "
                    f"Fix the source data / mapping and re-run before swapping."
                )
            # H4 (Deep Review fix #2): refuse to swap onto an empty
            # index (--limit 0, upstream filter bug, schema drift that
            # made every product skip indexing). An empty alias means
            # zero search results live-on-prod. Pull the actual
            # post-flush count from ES so we don't rely on local
            # counters that may not have observed every batch.
            await es.indices.refresh(index=target)
            count_resp = await es.count(index=target)
            doc_count = int(count_resp.get("count", 0))
            if doc_count == 0:
                raise SystemExit(
                    f"--swap-alias refused: target index {target!r} contains "
                    f"0 documents. Refusing to swap onto an empty index — "
                    f"storefront search would go dark immediately."
                )

            current = await current_alias_target(
                es, alias=settings.ELASTICSEARCH_INDEX_ALIAS
            )
            await alias_swap(
                es,
                alias=settings.ELASTICSEARCH_INDEX_ALIAS,
                from_index=current,
                to_index=target,
            )
            logger.info(
                "reindex.alias_swapped",
                alias=settings.ELASTICSEARCH_INDEX_ALIAS,
                from_index=current,
                to_index=target,
                target_doc_count=doc_count,
            )

        return 0 if total_errors == 0 else 2
    finally:
        await container.close()


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = _build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
