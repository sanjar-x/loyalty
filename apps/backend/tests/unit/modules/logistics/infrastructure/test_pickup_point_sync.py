"""Unit tests for ``sync_all_pickup_points``.

Covers the fan-out, error-isolation and dedup behaviour without
requiring a Postgres instance — the snapshot repository is faked.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from src.modules.logistics.domain.interfaces import (
    IPickupPointSnapshotRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PROVIDER_YANDEX_DELIVERY,
    Address,
    PickupPoint,
    PickupPointQuery,
    PickupPointType,
    ProviderCode,
)
from src.modules.logistics.infrastructure.services.pickup_point_sync import (
    sync_all_pickup_points,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

pytestmark = pytest.mark.unit


class _NoopLogger:
    def bind(self, **kwargs: Any) -> _NoopLogger:
        return self

    def debug(self, event: str, **kwargs: Any) -> None: ...
    def info(self, event: str, **kwargs: Any) -> None: ...
    def warning(self, event: str, **kwargs: Any) -> None: ...
    def error(self, event: str, **kwargs: Any) -> None: ...
    def critical(self, event: str, **kwargs: Any) -> None: ...
    def exception(self, event: str, **kwargs: Any) -> None: ...


class _StubUoW:
    """No-op IUnitOfWork: just runs the body inside ``async with`` blocks."""

    async def __aenter__(self) -> _StubUoW:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def register_aggregate(self, *_: Any) -> None:
        return None


class _FakeProvider:
    def __init__(
        self,
        code: ProviderCode,
        *,
        points: list[PickupPoint] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._code = code
        self._points = points or []
        self._raises = raises
        self.list_calls: list[PickupPointQuery] = []

    def provider_code(self) -> ProviderCode:
        return self._code

    async def list_pickup_points(self, query: PickupPointQuery) -> list[PickupPoint]:
        self.list_calls.append(query)
        if self._raises is not None:
            raise self._raises
        return list(self._points)


class _FakeRegistry:
    def __init__(self, providers: list[_FakeProvider]) -> None:
        self._providers = providers

    def list_pickup_point_providers(self) -> list[_FakeProvider]:
        return list(self._providers)

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"unexpected registry call in sync test: {name!r}")


class _FakeSnapshotRepo:
    def __init__(
        self,
        *,
        upsert_returns: tuple[int, int] = (0, 0),
        tombstone_returns: int = 0,
        upsert_raises: Exception | None = None,
    ) -> None:
        self._upsert_returns = upsert_returns
        self._tombstone_returns = tombstone_returns
        self._upsert_raises = upsert_raises
        self.upsert_calls: list[tuple[ProviderCode, list[PickupPoint]]] = []
        self.tombstone_calls: list[tuple[ProviderCode, set[str]]] = []

    async def find_one(self, *_: Any) -> None:
        return None

    async def search(self, *_: Any) -> list[PickupPoint]:
        return []

    async def upsert_batch(
        self,
        provider_code: ProviderCode,
        points: list[PickupPoint],
        synced_at: Any,
    ) -> tuple[int, int]:
        self.upsert_calls.append((provider_code, list(points)))
        if self._upsert_raises is not None:
            raise self._upsert_raises
        return self._upsert_returns

    async def mark_deleted_except(
        self,
        provider_code: ProviderCode,
        kept_external_ids: set[str],
        synced_at: Any,
    ) -> int:
        self.tombstone_calls.append((provider_code, set(kept_external_ids)))
        return self._tombstone_returns


def _point(provider: ProviderCode, external_id: str) -> PickupPoint:
    return PickupPoint(
        provider_code=provider,
        external_id=external_id,
        name=external_id,
        pickup_point_type=PickupPointType.PVZ,
        address=Address(
            country_code="RU",
            city="Москва",
            latitude=55.75,
            longitude=37.62,
        ),
    )


def _call(registry: _FakeRegistry, repo: _FakeSnapshotRepo):
    return sync_all_pickup_points(
        registry=cast(IShippingProviderRegistry, registry),
        snapshot_repo=cast(IPickupPointSnapshotRepository, repo),
        uow=cast(IUnitOfWork, _StubUoW()),
        logger=cast(ILogger, _NoopLogger()),
    )


async def test_per_provider_failure_does_not_block_siblings() -> None:
    cdek = _FakeProvider(PROVIDER_CDEK, raises=RuntimeError("carrier down"))
    yandex = _FakeProvider(
        PROVIDER_YANDEX_DELIVERY,
        points=[_point(PROVIDER_YANDEX_DELIVERY, "y-1")],
    )
    repo = _FakeSnapshotRepo(upsert_returns=(1, 0), tombstone_returns=3)

    summary = await _call(_FakeRegistry([cdek, yandex]), repo)

    by_code = {r.provider_code: r for r in summary.per_provider}
    assert by_code[PROVIDER_CDEK].error is not None
    assert by_code[PROVIDER_CDEK].fetched == 0
    assert by_code[PROVIDER_YANDEX_DELIVERY].ok
    assert by_code[PROVIDER_YANDEX_DELIVERY].inserted == 1
    assert by_code[PROVIDER_YANDEX_DELIVERY].tombstoned == 3


async def test_empty_provider_response_skips_tombstone() -> None:
    """Yandex returns 0 on the unbounded query — skip, don't wipe the table."""
    yandex = _FakeProvider(PROVIDER_YANDEX_DELIVERY, points=[])
    repo = _FakeSnapshotRepo()

    summary = await _call(_FakeRegistry([yandex]), repo)

    [result] = summary.per_provider
    assert result.ok
    assert result.fetched == 0
    assert result.tombstoned == 0
    assert repo.upsert_calls == []
    assert repo.tombstone_calls == []


async def test_carrier_duplicates_collapsed_before_upsert() -> None:
    """Duplicate external_id within the same batch is last-write-wins."""
    cdek = _FakeProvider(
        PROVIDER_CDEK,
        points=[
            _point(PROVIDER_CDEK, "pvz-1"),
            _point(PROVIDER_CDEK, "pvz-2"),
            _point(PROVIDER_CDEK, "pvz-1"),  # duplicate — must be dropped
        ],
    )
    repo = _FakeSnapshotRepo(upsert_returns=(2, 0))

    summary = await _call(_FakeRegistry([cdek]), repo)

    [result] = summary.per_provider
    assert result.fetched == 2  # deduped
    assert repo.upsert_calls[0][0] == PROVIDER_CDEK
    ids = [p.external_id for p in repo.upsert_calls[0][1]]
    assert sorted(ids) == ["pvz-1", "pvz-2"]
    assert repo.tombstone_calls[0][1] == {"pvz-1", "pvz-2"}


async def test_persist_failure_recorded_per_provider() -> None:
    cdek = _FakeProvider(PROVIDER_CDEK, points=[_point(PROVIDER_CDEK, "pvz-1")])
    repo = _FakeSnapshotRepo(upsert_raises=RuntimeError("constraint violation"))

    summary = await _call(_FakeRegistry([cdek]), repo)

    [result] = summary.per_provider
    assert not result.ok
    assert "persist_failed" in (result.error or "")
    # The fetched count is preserved so dashboards see the carrier *was*
    # reachable even though we failed to persist.
    assert result.fetched == 1
    assert result.inserted == 0


async def test_no_providers_yields_empty_summary() -> None:
    summary = await _call(_FakeRegistry([]), _FakeSnapshotRepo())
    assert summary.per_provider == ()
    assert summary.total_fetched == 0
    assert summary.total_failed == 0
