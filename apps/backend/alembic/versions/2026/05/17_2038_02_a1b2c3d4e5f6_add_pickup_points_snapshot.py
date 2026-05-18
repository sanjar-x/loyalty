"""add_pickup_points_snapshot

Revision ID: a1b2c3d4e5f6
Revises: c4d8e2f9a317
Create Date: 2026-05-17 20:38:02

Adds the local snapshot of carrier pickup-point catalogues so the
storefront map (``POST /storefront/logistics/pickup-points``) reads
from a GiST-indexed PostgreSQL table instead of paginating CDEK /
Yandex on every viewport change.

* PostGIS extension — required for ``geography(POINT, 4326)`` and the
  ``ST_DWithin`` radius search the snapshot repository runs.
* ``pickup_points`` table — see ``logistics.infrastructure.models.PickupPointModel``
  for column rationale.
* Partial GiST index on ``geom`` (active rows only) — the primary index
  used by ``ST_DWithin``.
* Partial B-tree on ``(provider_code, lower(city))`` for the city
  fallback path when the frontend has no lat/lng box.
* Partial B-tree on ``provider_code`` for the sync upsert / cleanup
  scans run by ``sync_pickup_points_task``.

The table is empty after migration; the operator runs the management
command ``python -m src.modules.logistics.management.sync_pickup_points``
to seed it before the storefront switches over. After that
``sync_pickup_points_task`` keeps it fresh every six hours.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "c4d8e2f9a317"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable PostGIS. Idempotent — safe to re-run.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Snapshot table.
    op.create_table(
        "pickup_points",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Internal PK; carrier identity is (provider_code, external_id)",
        ),
        sa.Column(
            "provider_code",
            sa.String(length=32),
            nullable=False,
            comment="Carrier code: 'cdek' / 'yandex_delivery' / ...",
        ),
        sa.Column(
            "external_id",
            sa.String(length=128),
            nullable=False,
            comment="Carrier-side ID (CDEK PVZ code, Yandex platform_station_id)",
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "pickup_point_type",
            sa.String(length=32),
            nullable=False,
            comment="pvz | postamat | post_office | terminal",
        ),
        # Address (flattened)
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("street", sa.Text(), nullable=True),
        sa.Column("house", sa.Text(), nullable=True),
        sa.Column("apartment", sa.Text(), nullable=True),
        sa.Column("subdivision_code", sa.String(length=16), nullable=True),
        sa.Column("raw_address", sa.Text(), nullable=True),
        # Geo — geoalchemy2 emits ``geography(POINT, 4326)``. The
        # ``spatial_index=False`` flag prevents alembic from creating
        # a default non-partial index — we declare the partial GiST
        # below by hand so it ignores soft-deleted rows.
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
            comment="PostGIS WGS84 point built from (latitude, longitude)",
        ),
        # Capabilities
        sa.Column("work_schedule", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column(
            "is_cash_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_card_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("weight_limit_grams", sa.Integer(), nullable=True),
        sa.Column("dimensions_limit_json", postgresql.JSONB(), nullable=True),
        sa.Column("services_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "address_metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Lifecycle
        sa.Column(
            "synced_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pickup_points"),
        sa.UniqueConstraint(
            "provider_code",
            "external_id",
            name="uq_pickup_points_provider_external_id",
        ),
        comment="Local snapshot of carrier pickup-point catalogues",
    )

    # 3. Primary spatial index — partial, active rows only. This is the
    #    index ``ST_DWithin(geom, ..., :radius_m)`` planner picks.
    op.execute(
        "CREATE INDEX ix_pickup_points_geom "
        "ON pickup_points USING GIST (geom) "
        "WHERE deleted_at IS NULL;"
    )

    # 4. City-fallback index — case-insensitive, partial.
    op.execute(
        "CREATE INDEX ix_pickup_points_provider_city_lower "
        "ON pickup_points (provider_code, lower(city)) "
        "WHERE deleted_at IS NULL;"
    )

    # 5. Per-provider active-rows scan (sync upsert / tombstone path).
    op.execute(
        "CREATE INDEX ix_pickup_points_provider_active "
        "ON pickup_points (provider_code) "
        "WHERE deleted_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pickup_points_provider_active;")
    op.execute("DROP INDEX IF EXISTS ix_pickup_points_provider_city_lower;")
    op.execute("DROP INDEX IF EXISTS ix_pickup_points_geom;")
    op.drop_table("pickup_points")
    # PostGIS extension intentionally not dropped — other features may
    # adopt it (catalog delivery zones, supplier coverage maps).
