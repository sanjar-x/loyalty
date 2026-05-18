"""Initial / full sync of carrier pickup-point catalogues into ``pickup_points``.

Usage::

    # First seed after deployment (or after rotating PostGIS data).
    uv run python -m src.modules.logistics.management.sync_pickup_points

    # Force a one-off refresh of just one provider while debugging.
    uv run python -m src.modules.logistics.management.sync_pickup_points \\
        --provider cdek

The cron task ``sync_pickup_points_task`` (every 6 h) keeps the table
fresh in production; this command exists for the bootstrap path (empty
table on first deploy) and for operators who need an out-of-band
refresh, e.g. after a carrier emergency catalogue dump.

Same wiring as the cron task — resolves ``IShippingProviderRegistry``,
``IPickupPointSnapshotRepository`` and ``IUnitOfWork`` from the live
Dishka container so there is no second code path that could drift.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import cast

import structlog

from src.bootstrap.container import create_container
from src.bootstrap.logger import setup_logging
from src.modules.logistics.domain.interfaces import (
    IPickupPointSnapshotRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.infrastructure.services.pickup_point_sync import (
    ProviderSyncResult,
    sync_all_pickup_points,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync_pickup_points",
        description=(
            "Pull every carrier's pickup-point catalogue and upsert into "
            "the local ``pickup_points`` snapshot. Tombstones rows the "
            "carrier no longer reports."
        ),
    )
    parser.add_argument(
        "--provider",
        default=None,
        help=(
            "If set, sync only this provider (e.g. 'cdek'). Default: "
            "every registered pickup-point provider."
        ),
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    container = create_container()
    exit_code = 0
    try:
        async with container() as request:
            registry = await request.get(IShippingProviderRegistry)
            snapshot_repo = await request.get(IPickupPointSnapshotRepository)
            uow = await request.get(IUnitOfWork)
            structured_logger = await request.get(ILogger)

            if args.provider is not None:
                # Filter the registry to a single provider so the shared
                # ``sync_all_pickup_points`` helper does the same work
                # one item at a time. We rebuild a one-shot wrapper
                # instead of cloning the registry — registry has app
                # scope and mutating it would affect concurrent requests.
                providers = registry.list_pickup_point_providers()
                target = next(
                    (p for p in providers if p.provider_code() == args.provider),
                    None,
                )
                if target is None:
                    logger.error(
                        "sync_pickup_points.unknown_provider",
                        provider=args.provider,
                        available=[p.provider_code() for p in providers],
                    )
                    return 2
                # The facade is a Liskov-substitutable wrapper that only
                # narrows ``list_pickup_point_providers``; cast is safe
                # and keeps the protocol contract intact for ty.
                registry = cast(
                    IShippingProviderRegistry,
                    _SingleProviderRegistryFacade(registry, target),
                )

            summary = await sync_all_pickup_points(
                registry=registry,
                snapshot_repo=snapshot_repo,
                uow=uow,
                logger=structured_logger,
            )

        _print_summary(summary.per_provider)
        if summary.total_failed:
            exit_code = 1
    finally:
        await container.close()
    return exit_code


class _SingleProviderRegistryFacade:
    """Wraps a real ``IShippingProviderRegistry`` to surface one provider.

    Only ``list_pickup_point_providers`` is used by the sync helper, but
    the wrapper passes through every other call so it stays a drop-in
    replacement if the helper evolves.
    """

    def __init__(self, inner: IShippingProviderRegistry, only) -> None:
        self._inner = inner
        self._only = only

    def list_pickup_point_providers(self):
        return [self._only]

    def __getattr__(self, name: str):
        return getattr(self._inner, name)


def _print_summary(results: tuple[ProviderSyncResult, ...]) -> None:
    if not results:
        print("No pickup-point providers registered.")
        return
    print(
        f"{'provider':<20} {'fetched':>8} {'inserted':>9} "
        f"{'updated':>8} {'tombstoned':>11} status"
    )
    for r in results:
        status = "OK" if r.ok else f"FAIL ({r.error})"
        print(
            f"{r.provider_code:<20} {r.fetched:>8} {r.inserted:>9} "
            f"{r.updated:>8} {r.tombstoned:>11} {status}"
        )


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = _build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
