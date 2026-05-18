"""Unit tests for ``ListPickupPointsHandler`` (snapshot-backed)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from src.modules.logistics.application.queries.list_pickup_points import (
    ListPickupPointsHandler,
    ListPickupPointsQuery,
)
from src.modules.logistics.domain.interfaces import (
    IPickupPointSnapshotRepository,
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


class _FakeSnapshotRepo:
    """Tiny in-memory snapshot — only exercises the handler's expectations."""

    def __init__(
        self,
        *,
        search_returns: list[PickupPoint] | None = None,
        find_one_returns: PickupPoint | None = None,
    ) -> None:
        self._search_returns = search_returns or []
        self._find_one_returns = find_one_returns
        self.search_calls: list[PickupPointQuery] = []
        self.find_one_calls: list[tuple[ProviderCode, str]] = []

    async def find_one(
        self, provider_code: ProviderCode, external_id: str
    ) -> PickupPoint | None:
        self.find_one_calls.append((provider_code, external_id))
        return self._find_one_returns

    async def search(self, query: PickupPointQuery) -> list[PickupPoint]:
        self.search_calls.append(query)
        return list(self._search_returns)

    async def upsert_batch(self, *_args: Any, **_kwargs: Any) -> tuple[int, int]:
        return (0, 0)

    async def mark_deleted_except(self, *_args: Any, **_kwargs: Any) -> int:
        return 0


def _make_query(**overrides: Any) -> PickupPointQuery:
    return PickupPointQuery(
        country_code=overrides.get("country_code", "RU"),
        city=overrides.get("city"),
        postal_code=overrides.get("postal_code"),
        latitude=overrides.get("latitude", 55.75),
        longitude=overrides.get("longitude", 37.62),
        radius_km=overrides.get("radius_km", 20),
        provider_code=overrides.get("provider_code"),
        delivery_type=overrides.get("delivery_type"),
    )


def _make_point(provider: ProviderCode, external_id: str = "pvz-1") -> PickupPoint:
    return PickupPoint(
        provider_code=provider,
        external_id=external_id,
        name=f"{provider} {external_id}",
        pickup_point_type=PickupPointType.PVZ,
        address=Address(
            country_code="RU",
            city="Москва",
            latitude=55.75,
            longitude=37.62,
        ),
    )


def _handler(repo: _FakeSnapshotRepo) -> ListPickupPointsHandler:
    return ListPickupPointsHandler(
        snapshot_repo=cast(IPickupPointSnapshotRepository, repo),
        logger=_NoopLogger(),
    )


async def test_returns_snapshot_results() -> None:
    points = [_make_point(PROVIDER_CDEK), _make_point(PROVIDER_YANDEX_DELIVERY)]
    repo = _FakeSnapshotRepo(search_returns=points)
    handler = _handler(repo)

    result = await handler.handle(ListPickupPointsQuery(query=_make_query()))

    assert [p.external_id for p in result.points] == ["pvz-1", "pvz-1"]
    assert result.errors == {}
    assert len(repo.search_calls) == 1
    # When the request-level provider filter is absent, the search query
    # carries no provider_code — repo sees the original PickupPointQuery.
    assert repo.search_calls[0].provider_code is None


async def test_provider_filter_is_pushed_into_search_query() -> None:
    repo = _FakeSnapshotRepo(search_returns=[_make_point(PROVIDER_CDEK)])
    handler = _handler(repo)

    await handler.handle(
        ListPickupPointsQuery(query=_make_query(), provider_code=PROVIDER_CDEK)
    )

    assert repo.search_calls[0].provider_code == PROVIDER_CDEK
    # Other fields survive the copy.
    assert repo.search_calls[0].latitude == 55.75
    assert repo.search_calls[0].radius_km == 20


async def test_empty_snapshot_returns_empty_result_without_errors() -> None:
    """Cold table on first deploy must not raise — operator hasn't seeded yet."""
    repo = _FakeSnapshotRepo(search_returns=[])
    handler = _handler(repo)

    result = await handler.handle(ListPickupPointsQuery(query=_make_query()))

    assert result.points == []
    assert result.errors == {}


async def test_city_query_passes_through_unchanged() -> None:
    repo = _FakeSnapshotRepo(search_returns=[])
    handler = _handler(repo)

    await handler.handle(
        ListPickupPointsQuery(query=PickupPointQuery(country_code="RU", city="Москва"))
    )

    assert repo.search_calls[0].city == "Москва"
    assert repo.search_calls[0].country_code == "RU"
