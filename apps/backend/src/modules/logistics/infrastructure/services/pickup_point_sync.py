"""Sync logic for the local pickup-point snapshot.

Single entry point used by both the cron task
(``sync_pickup_points_task`` in ``infrastructure/tasks.py``) and the
``python -m src.modules.logistics.management.sync_pickup_points``
management command.

Per provider: pull the full unbounded catalogue → upsert into
``pickup_points`` → tombstone rows the carrier no longer reports.
Failures on one provider don't block the others.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.logistics.domain.interfaces import (
    IPickupPointProvider,
    IPickupPointSnapshotRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

# Unbounded query — the snapshot mirrors the *entire* carrier catalogue.
# Providers that require a bounded query (Yandex needs a ``geo_id``) skip
# straight to the ``"unbounded_unsupported"`` branch below and we leave
# their rows untouched. They get filled from the per-region adapters as
# the storefront map asks for them on cache miss.
_UNBOUNDED_QUERY = PickupPointQuery()


@dataclass(frozen=True)
class ProviderSyncResult:
    """Outcome of a single provider sync run."""

    provider_code: ProviderCode
    fetched: int
    inserted: int
    updated: int
    tombstoned: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class SyncSummary:
    """Aggregate outcome of a sync round across every provider."""

    started_at: datetime
    finished_at: datetime
    per_provider: tuple[ProviderSyncResult, ...]

    @property
    def total_fetched(self) -> int:
        return sum(r.fetched for r in self.per_provider)

    @property
    def total_failed(self) -> int:
        return sum(1 for r in self.per_provider if not r.ok)


async def sync_all_pickup_points(
    *,
    registry: IShippingProviderRegistry,
    snapshot_repo: IPickupPointSnapshotRepository,
    uow: IUnitOfWork,
    logger: ILogger,
) -> SyncSummary:
    """Run a snapshot sync for every registered pickup-point provider.

    Each provider runs in its own ``uow`` commit so a transient failure
    on one carrier never rolls back the others.
    """
    log = logger.bind(task="pickup_point_sync")
    started_at = datetime.now(UTC)

    providers = registry.list_pickup_point_providers()
    if not providers:
        log.info("pickup_point_sync.skip", reason="no_providers")
        return SyncSummary(
            started_at=started_at,
            finished_at=datetime.now(UTC),
            per_provider=(),
        )

    results: list[ProviderSyncResult] = []
    for provider in providers:
        result = await _sync_single_provider(
            provider=provider,
            snapshot_repo=snapshot_repo,
            uow=uow,
            logger=log,
        )
        results.append(result)

    summary = SyncSummary(
        started_at=started_at,
        finished_at=datetime.now(UTC),
        per_provider=tuple(results),
    )
    log.info(
        "pickup_point_sync.done",
        providers=len(results),
        failed=summary.total_failed,
        total_fetched=summary.total_fetched,
        duration_seconds=(summary.finished_at - summary.started_at).total_seconds(),
    )
    return summary


async def _sync_single_provider(
    *,
    provider: IPickupPointProvider,
    snapshot_repo: IPickupPointSnapshotRepository,
    uow: IUnitOfWork,
    logger: ILogger,
) -> ProviderSyncResult:
    code: ProviderCode = provider.provider_code()
    provider_log = logger.bind(provider_code=code)

    try:
        points = await provider.list_pickup_points(_UNBOUNDED_QUERY)
    except Exception as exc:  # carrier failure isolates per-provider
        provider_log.warning("pickup_point_sync.fetch_failed", error=str(exc))
        return ProviderSyncResult(
            provider_code=code,
            fetched=0,
            inserted=0,
            updated=0,
            tombstoned=0,
            error=f"fetch_failed: {exc}",
        )

    if not points:
        # Empty result on an unbounded query — almost certainly a
        # provider that doesn't support catalogue dumps (Yandex needs
        # a ``geo_id``). Don't tombstone anything; just record it and
        # move on.
        provider_log.info("pickup_point_sync.skip", reason="unbounded_unsupported")
        return ProviderSyncResult(
            provider_code=code,
            fetched=0,
            inserted=0,
            updated=0,
            tombstoned=0,
        )

    synced_at = datetime.now(UTC)
    deduped = _deduplicate_by_external_id(points)

    try:
        async with uow:
            inserted, updated = await snapshot_repo.upsert_batch(
                code, deduped, synced_at
            )
            tombstoned = await snapshot_repo.mark_deleted_except(
                code,
                {p.external_id for p in deduped},
                synced_at,
            )
            await uow.commit()
    except Exception as exc:
        provider_log.exception("pickup_point_sync.persist_failed")
        return ProviderSyncResult(
            provider_code=code,
            fetched=len(deduped),
            inserted=0,
            updated=0,
            tombstoned=0,
            error=f"persist_failed: {exc}",
        )

    provider_log.info(
        "pickup_point_sync.provider_done",
        fetched=len(deduped),
        inserted=inserted,
        updated=updated,
        tombstoned=tombstoned,
    )
    return ProviderSyncResult(
        provider_code=code,
        fetched=len(deduped),
        inserted=inserted,
        updated=updated,
        tombstoned=tombstoned,
    )


def _deduplicate_by_external_id(
    points: Iterable[PickupPoint],
) -> list[PickupPoint]:
    """Last-write-wins dedup against ``external_id``.

    Carriers occasionally emit duplicates across paginated responses;
    upsert would happily process them but the ``ON CONFLICT`` clause
    fires per row in the same batch and Postgres refuses to update the
    same row twice in one ``INSERT ... ON CONFLICT``. Dedup beforehand
    keeps the batch atomic.
    """
    by_id: dict[str, PickupPoint] = {}
    for point in points:
        if not point.external_id:
            continue
        by_id[point.external_id] = point
    return list(by_id.values())
