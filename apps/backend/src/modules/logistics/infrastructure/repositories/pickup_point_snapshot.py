"""PostgreSQL implementation of :class:`IPickupPointSnapshotRepository`.

Reads ``pickup_points`` (a local mirror of carrier pickup-point
catalogues) so the storefront map and quote handler never hit CDEK /
Yandex on the user-facing path. Writes come from
``sync_pickup_points_task`` and the matching management command.

Radius search uses PostGIS ``ST_DWithin(geom, ..., :radius_m)`` against
a partial GiST index — see migration ``a1b2c3d4e5f6``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.domain.interfaces import (
    IPickupPointSnapshotRepository,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    Dimensions,
    PickupPoint,
    PickupPointQuery,
    PickupPointServices,
    PickupPointType,
    ProviderCode,
)
from src.modules.logistics.infrastructure.models import PickupPointModel

# Default radius applied when the storefront supplied a centre point
# without an explicit ``radius_km``. Matches the frontend's default
# behaviour (``buildPickupPointsRequestBody`` falls back to 10 km).
_DEFAULT_RADIUS_KM = 10
# Hard ceiling on radius — the frontend already caps at 40 km, this
# is a server-side belt-and-braces guard for admin / debugging callers.
_MAX_RADIUS_KM = 100
# Upper bound on the number of points returned per query — even within
# a small radius the carrier catalogue can hold thousands of markers,
# and the storefront cluster collapses them anyway.
_SEARCH_LIMIT = 500


class PgPickupPointSnapshotRepository(IPickupPointSnapshotRepository):
    """Snapshot repository backed by the ``pickup_points`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_one(
        self, provider_code: ProviderCode, external_id: str
    ) -> PickupPoint | None:
        stmt = select(PickupPointModel).where(
            PickupPointModel.provider_code == provider_code,
            PickupPointModel.external_id == external_id,
            PickupPointModel.deleted_at.is_(None),
        )
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        if orm is None:
            return None
        return _to_domain(orm)

    async def search(self, query: PickupPointQuery) -> list[PickupPoint]:
        conditions: list[Any] = [PickupPointModel.deleted_at.is_(None)]

        if query.provider_code:
            conditions.append(PickupPointModel.provider_code == query.provider_code)
        if query.delivery_type is not None:
            # ``delivery_type`` on the query is the requested *transport
            # category*. We match it against ``pickup_point_type`` because
            # the carrier catalogue does not separately surface a
            # delivery_type per point — type-and-transport correlate
            # 1:1 here (a PVZ is always pickup, a postamat is always
            # pickup, etc.). When a carrier later distinguishes them this
            # becomes a real WHERE; for now it's a no-op narrowing.
            pass

        has_geo = query.latitude is not None and query.longitude is not None
        if has_geo:
            radius_km = max(
                1,
                min(
                    _MAX_RADIUS_KM,
                    query.radius_km or _DEFAULT_RADIUS_KM,
                ),
            )
            # Geography type → ST_DWithin expects metres for the
            # distance argument. Casting through ST_MakePoint(lon, lat)
            # to geography(POINT, 4326) lets the planner pick the
            # partial GiST index ``ix_pickup_points_geom``.
            origin = func.ST_GeogFromText(
                f"SRID=4326;POINT({query.longitude} {query.latitude})"
            )
            conditions.append(
                func.ST_DWithin(PickupPointModel.geom, origin, radius_km * 1000)
            )
            # Closest first — better UX when the cluster collapses,
            # and the planner already touched the GiST index above.
            stmt = (
                select(PickupPointModel)
                .where(and_(*conditions))
                .order_by(PickupPointModel.geom.op("<->")(origin))
                .limit(_SEARCH_LIMIT)
            )
        elif query.city:
            conditions.append(
                func.lower(PickupPointModel.city) == query.city.strip().lower()
            )
            if query.country_code:
                conditions.append(
                    PickupPointModel.country_code == query.country_code.upper()
                )
            stmt = (
                select(PickupPointModel)
                .where(and_(*conditions))
                .order_by(PickupPointModel.name)
                .limit(_SEARCH_LIMIT)
            )
        else:
            # No bounded area — refuse to dump the whole table.
            return []

        result = await self._session.execute(stmt)
        return [_to_domain(orm) for orm in result.scalars().all()]

    # ------------------------------------------------------------------
    # Writes (sync path)
    # ------------------------------------------------------------------

    async def upsert_batch(
        self,
        provider_code: ProviderCode,
        points: list[PickupPoint],
        synced_at: datetime,
    ) -> tuple[int, int]:
        if not points:
            return (0, 0)

        # Count existing rows up-front so we can return (inserted, updated)
        # without round-tripping per row. ``deleted_at`` is intentionally
        # ignored — a revived (tombstoned) row counts as "updated".
        external_ids = [p.external_id for p in points]
        existing_q = select(PickupPointModel.external_id).where(
            PickupPointModel.provider_code == provider_code,
            PickupPointModel.external_id.in_(external_ids),
        )
        existing_ids: set[str] = set(
            (await self._session.execute(existing_q)).scalars().all()
        )

        rows = [_to_insert_row(provider_code, p, synced_at) for p in points]

        # ON CONFLICT (provider_code, external_id) DO UPDATE — also
        # clears ``deleted_at`` so a previously-tombstoned point comes
        # back to life atomically.
        stmt = pg_insert(PickupPointModel).values(rows)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in PickupPointModel.__table__.columns
            if col.name not in {"id", "provider_code", "external_id", "created_at"}
        }
        # ``deleted_at`` is unconditionally cleared on upsert.
        update_cols["deleted_at"] = None
        upsert = stmt.on_conflict_do_update(
            constraint="uq_pickup_points_provider_external_id",
            set_=update_cols,
        )
        await self._session.execute(upsert)
        await self._session.flush()

        inserted = sum(1 for p in points if p.external_id not in existing_ids)
        updated = len(points) - inserted
        return (inserted, updated)

    async def mark_deleted_except(
        self,
        provider_code: ProviderCode,
        kept_external_ids: set[str],
        synced_at: datetime,
    ) -> int:
        # Build the tombstone in two steps so the SET clause only fires
        # for rows that are actually changing. ``RETURNING`` would give
        # us a cheap count but SQLAlchemy's async UPDATE shape forces
        # a separate SELECT for the affected-rows case — and the count
        # itself is a cheap aggregate.
        targets_q = select(PickupPointModel.id).where(
            PickupPointModel.provider_code == provider_code,
            PickupPointModel.deleted_at.is_(None),
        )
        if kept_external_ids:
            targets_q = targets_q.where(
                PickupPointModel.external_id.notin_(kept_external_ids)
            )
        target_ids: list[Any] = list(
            (await self._session.execute(targets_q)).scalars().all()
        )
        if not target_ids:
            return 0

        from sqlalchemy import update as sa_update

        await self._session.execute(
            sa_update(PickupPointModel)
            .where(PickupPointModel.id.in_(target_ids))
            .values(deleted_at=synced_at, updated_at=synced_at)
        )
        await self._session.flush()
        return len(target_ids)


# ---------------------------------------------------------------------------
# Data mapper helpers
# ---------------------------------------------------------------------------


def _to_domain(orm: PickupPointModel) -> PickupPoint:
    return PickupPoint(
        provider_code=orm.provider_code,
        external_id=orm.external_id,
        name=orm.name,
        pickup_point_type=PickupPointType(orm.pickup_point_type),
        address=Address(
            country_code=orm.country_code,
            city=orm.city,
            region=orm.region,
            postal_code=orm.postal_code,
            street=orm.street,
            house=orm.house,
            apartment=orm.apartment,
            subdivision_code=orm.subdivision_code,
            latitude=orm.latitude,
            longitude=orm.longitude,
            raw_address=orm.raw_address,
            metadata=dict(orm.address_metadata_json or {}),
        ),
        work_schedule=orm.work_schedule,
        phone=orm.phone,
        is_cash_allowed=bool(orm.is_cash_allowed),
        is_card_allowed=bool(orm.is_card_allowed),
        weight_limit_grams=orm.weight_limit_grams,
        dimensions_limit=_dimensions_from_json(orm.dimensions_limit_json),
        services=_services_from_json(orm.services_json),
    )


def _to_insert_row(
    provider_code: ProviderCode,
    point: PickupPoint,
    synced_at: datetime,
) -> dict[str, Any]:
    # Build the geography literal only when both coordinates are known —
    # carriers occasionally return points without a precise location
    # (e.g. CDEK terminals inside large transport hubs). Such rows still
    # ship to the cache so the quote path can resolve them, they just
    # don't participate in the spatial index.
    row: dict[str, Any] = {
        "provider_code": provider_code,
        "external_id": point.external_id,
        "name": point.name,
        "pickup_point_type": point.pickup_point_type.value,
        "country_code": point.address.country_code,
        "city": point.address.city,
        "region": point.address.region,
        "postal_code": point.address.postal_code,
        "street": point.address.street,
        "house": point.address.house,
        "apartment": point.address.apartment,
        "subdivision_code": point.address.subdivision_code,
        "raw_address": point.address.raw_address,
        "latitude": point.address.latitude,
        "longitude": point.address.longitude,
        "work_schedule": point.work_schedule,
        "phone": point.phone,
        "is_cash_allowed": bool(point.is_cash_allowed),
        "is_card_allowed": bool(point.is_card_allowed),
        "weight_limit_grams": point.weight_limit_grams,
        "dimensions_limit_json": _dimensions_to_json(point.dimensions_limit),
        "services_json": _services_to_json(point.services),
        "address_metadata_json": dict(point.address.metadata or {}),
        "synced_at": synced_at,
    }
    if point.address.latitude is not None and point.address.longitude is not None:
        # ST_GeogFromText is the canonical WKT → geography conversion;
        # bind via SQLAlchemy func so the value is parameterised, not
        # string-interpolated.
        row["geom"] = func.ST_GeogFromText(
            f"SRID=4326;POINT({point.address.longitude} {point.address.latitude})"
        )
    else:
        row["geom"] = None
    return row


def _dimensions_from_json(payload: dict | None) -> Dimensions | None:
    if not payload:
        return None
    try:
        return Dimensions(
            length_cm=int(payload["length_cm"]),
            width_cm=int(payload["width_cm"]),
            height_cm=int(payload["height_cm"]),
        )
    except KeyError, TypeError, ValueError:
        return None


def _dimensions_to_json(dims: Dimensions | None) -> dict | None:
    if dims is None:
        return None
    return {
        "length_cm": dims.length_cm,
        "width_cm": dims.width_cm,
        "height_cm": dims.height_cm,
    }


def _services_from_json(payload: dict | None) -> PickupPointServices | None:
    if not payload:
        return None
    return PickupPointServices(
        is_fitting_allowed=bool(payload.get("is_fitting_allowed", False)),
        is_partial_refuse_allowed=bool(payload.get("is_partial_refuse_allowed", False)),
        is_paperless_pickup_allowed=bool(
            payload.get("is_paperless_pickup_allowed", False)
        ),
        is_unboxing_allowed=bool(payload.get("is_unboxing_allowed", False)),
    )


def _services_to_json(services: PickupPointServices | None) -> dict | None:
    if services is None:
        return None
    return {
        "is_fitting_allowed": services.is_fitting_allowed,
        "is_partial_refuse_allowed": services.is_partial_refuse_allowed,
        "is_paperless_pickup_allowed": services.is_paperless_pickup_allowed,
        "is_unboxing_allowed": services.is_unboxing_allowed,
    }


__all__ = ["PgPickupPointSnapshotRepository"]
