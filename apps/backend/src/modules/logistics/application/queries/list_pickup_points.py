"""
Query handler: list pickup / delivery points from the local snapshot.

CQRS read side — backed by ``pickup_points`` PostgreSQL table that
``sync_pickup_points_task`` refreshes every 6 hours from every carrier
catalogue. The user-facing path no longer touches CDEK / Yandex; the
storefront map reads from a partial GiST radius index.

``provider_code``, when set on the input query, narrows the result to
one carrier; otherwise every active row across all providers comes
back in a single response.
"""

from dataclasses import dataclass

from src.modules.logistics.domain.interfaces import (
    IPickupPointSnapshotRepository,
)
from src.modules.logistics.domain.value_objects import (
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListPickupPointsQuery:
    """Input for listing pickup points.

    Attributes:
        query: Search criteria (location, filters, etc.).
        provider_code: If set, narrow the snapshot search to this
            carrier; else return points from every provider.
    """

    query: PickupPointQuery
    provider_code: ProviderCode | None = None


@dataclass(frozen=True)
class ListPickupPointsResult:
    """Output of pickup points listing.

    Attributes:
        points: All matching pickup points from the snapshot.
        errors: Per-provider error map — always empty on the snapshot
            path; preserved for wire-shape compatibility with the
            previous live-fan-out implementation, so the frontend's
            ``errors`` rendering keeps compiling unchanged.
    """

    points: list[PickupPoint]
    errors: dict[str, str]


class ListPickupPointsHandler:
    """List pickup/delivery points from the local snapshot.

    No carrier calls, no per-provider timeouts, no fan-out aggregation:
    a single indexed PostgreSQL query (``ST_DWithin`` for radius search
    or ``lower(city)`` for city search) returns the union.

    The snapshot is refreshed by ``sync_pickup_points_task`` and seeded
    by the matching management command. When the table is empty on a
    fresh deploy this handler returns an empty list — operators MUST
    run the seed command before flipping the storefront over.
    """

    def __init__(
        self,
        snapshot_repo: IPickupPointSnapshotRepository,
        logger: ILogger,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._logger = logger.bind(handler="ListPickupPointsHandler")

    async def handle(self, query: ListPickupPointsQuery) -> ListPickupPointsResult:
        # Push the provider filter into the search query — the snapshot
        # repository expects it on ``PickupPointQuery.provider_code``,
        # and applying it at the SQL level lets the partial index do
        # the work instead of a Python-side filter.
        effective_query = query.query
        if query.provider_code is not None:
            effective_query = _with_provider(effective_query, query.provider_code)

        points = await self._snapshot_repo.search(effective_query)
        if not points:
            self._logger.info(
                "pickup_points.empty_result",
                provider_code=query.provider_code,
                city=effective_query.city,
                has_geo=(
                    effective_query.latitude is not None
                    and effective_query.longitude is not None
                ),
            )
        return ListPickupPointsResult(points=points, errors={})


def _with_provider(
    query: PickupPointQuery, provider_code: ProviderCode
) -> PickupPointQuery:
    """Return a copy of ``query`` with ``provider_code`` forced.

    Centralised so the handler doesn't reach into the dataclass shape;
    if ``PickupPointQuery`` gains more fields tomorrow only this helper
    has to grow.
    """
    return PickupPointQuery(
        country_code=query.country_code,
        city=query.city,
        postal_code=query.postal_code,
        latitude=query.latitude,
        longitude=query.longitude,
        radius_km=query.radius_km,
        provider_code=provider_code,
        delivery_type=query.delivery_type,
    )
