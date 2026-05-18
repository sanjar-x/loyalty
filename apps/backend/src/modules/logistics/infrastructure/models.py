"""
ORM models for the Logistics bounded context.

Maps domain concepts to PostgreSQL tables via SQLAlchemy declarative mappings.
Infrastructure layer — never imported by domain or application layers.
Repositories translate between ORM and domain entities (Data Mapper pattern).
"""

import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.modules.logistics.domain.value_objects import (
    DeliveryType,
    ShipmentStatus,
    TrackingStatus,
)

# ---------------------------------------------------------------------------
# Shipment
# ---------------------------------------------------------------------------


class ShipmentModel(Base):
    """Shipment aggregate ORM model."""

    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipments_order_id", "order_id"),
        Index(
            "ix_shipments_provider_shipment",
            "provider_code",
            "provider_shipment_id",
            unique=True,
            postgresql_where="provider_shipment_id IS NOT NULL",
        ),
        Index("ix_shipments_tracking_number", "tracking_number"),
        Index("ix_shipments_status", "status"),
        # "Stuck cross-border" detection — nightly job finds DobroPost
        # shipments booked > 14 days ago that never reported 648/649.
        # See docs/dobropost_shipment_api/integration.md edge-case 2.
        Index(
            "ix_shipments_stuck_cross_border",
            "booked_at",
            postgresql_where=(
                "cross_border_arrived_at IS NULL "
                "AND provider_code = 'dobropost' "
                "AND status = 'booked'"
            ),
        ),
        {"comment": "Shipment lifecycle tracking for logistics integrations"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key",
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Link to order/checkout that triggered this shipment",
    )

    provider_code: Mapped[str] = mapped_column(
        String(50),
        comment="Logistics provider identifier (open string, e.g. 'cdek')",
    )
    service_code: Mapped[str] = mapped_column(
        String(100), comment="Provider-specific tariff/service code"
    )
    delivery_type: Mapped[str] = mapped_column(
        Enum(DeliveryType, name="delivery_type_enum", create_constraint=False),
        comment="Courier, pickup point, or post office",
    )
    status: Mapped[str] = mapped_column(
        Enum(ShipmentStatus, name="shipment_status_enum", create_constraint=False),
        default=ShipmentStatus.DRAFT,
        comment="Local integration lifecycle status",
    )

    # Addresses and contacts stored as JSON (composite value objects)
    origin_json: Mapped[dict] = mapped_column(JSONB, comment="Sender address as JSON")
    destination_json: Mapped[dict] = mapped_column(
        JSONB, comment="Recipient address as JSON"
    )
    recipient_json: Mapped[dict] = mapped_column(
        JSONB, comment="Recipient contact info as JSON"
    )
    sender_json: Mapped[dict] = mapped_column(
        JSONB, comment="Sender contact info as JSON"
    )
    parcels_json: Mapped[list] = mapped_column(JSONB, comment="List of parcels as JSON")

    # Cost
    quoted_cost_amount: Mapped[int] = mapped_column(
        Integer, comment="Quoted cost in smallest currency unit"
    )
    quoted_cost_currency: Mapped[str] = mapped_column(
        String(3), comment="ISO 4217 currency code"
    )
    cod_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Cash-on-delivery config as JSON"
    )

    # Provider-assigned identifiers
    provider_shipment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Provider's shipment/order ID"
    )
    tracking_number: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Provider's tracking number"
    )
    provider_payload: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Opaque provider data (JSON) from quote"
    )

    # Denormalized tracking
    latest_tracking_status: Mapped[str | None] = mapped_column(
        Enum(TrackingStatus, name="tracking_status_enum", create_constraint=False),
        nullable=True,
        comment="Latest carrier tracking status",
    )

    # Failure / delivery metadata
    failure_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Reason for booking/cancellation failure"
    )
    estimated_delivery_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Estimated delivery window as JSON"
    )

    # Outstanding async edit tasks (Yandex 3.06 / 3.12 / 3.14 / 3.15).
    pending_edit_tasks_json: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="In-flight edit tasks: [{task_id, kind, submitted_at, initial_status}]",
    )
    # Currently active courier intake (CDEK).
    scheduled_intake_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Active intake: {provider_intake_id, status, scheduled_at}",
    )
    # Append-only audit of returns / refusals registered with the carrier.
    registered_returns_json: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="Returns: [{kind, provider_return_id, reason, registered_at}]",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Record creation time",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification time",
    )
    booked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When provider confirmed booking",
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When cancellation was confirmed",
    )
    cross_border_arrived_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment=(
            "First moment a cross-border shipment reported 'arrived in destination "
            "country' (DobroPost status_id ∈ {648, 649}). Idempotency anchor for "
            "CrossBorderArrivedEvent emission."
        ),
    )

    # Optimistic locking
    version: Mapped[int] = mapped_column(
        Integer, default=1, comment="Optimistic locking counter"
    )

    # SQLAlchemy uses ``version`` as the optimistic-lock token: every
    # UPDATE adds ``WHERE version = :prev_version`` and bumps the column
    # itself. Concurrent writers see ``StaleDataError`` instead of
    # last-write-wins. The repository constructs domain entities with
    # the version it just observed and feeds it back here unchanged —
    # SQLAlchemy increments by 1 server-side, which the repo reads back
    # via ``RETURNING`` (autoflush).
    __mapper_args__ = {  # noqa: RUF012  (SQLAlchemy expects a plain dict)
        "version_id_col": version,
        "version_id_generator": False,
    }

    # Relationships
    tracking_events: Mapped[list[ShipmentTrackingEventModel]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentTrackingEventModel.timestamp",
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Shipment Tracking Events
# ---------------------------------------------------------------------------


class ShipmentTrackingEventModel(Base):
    """Append-only carrier tracking events."""

    __tablename__ = "shipment_tracking_events"
    __table_args__ = (
        UniqueConstraint(
            "shipment_id",
            "timestamp",
            "status",
            name="uq_tracking_events_shipment_ts_status",
        ),
        Index("ix_tracking_events_shipment_id", "shipment_id"),
        Index("ix_tracking_events_timestamp", "timestamp"),
        {
            "comment": "Carrier tracking event history (append-only)",
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key",
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        comment="Parent shipment",
    )

    status: Mapped[str] = mapped_column(
        Enum(TrackingStatus, name="tracking_status_enum", create_constraint=False),
        comment="Unified tracking status",
    )
    provider_status_code: Mapped[str] = mapped_column(
        String(100), comment="Original provider status code"
    )
    provider_status_name: Mapped[str] = mapped_column(
        String(500), comment="Original provider status description"
    )
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), comment="When this event occurred at the carrier"
    )
    location: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Location where the event occurred"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional event details"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="When this record was ingested",
    )

    # Relationships
    shipment: Mapped[ShipmentModel] = relationship(
        back_populates="tracking_events",
    )


# ---------------------------------------------------------------------------
# Provider Accounts
# ---------------------------------------------------------------------------


class ProviderAccountModel(Base):
    """Logistics provider account credentials and configuration."""

    __tablename__ = "provider_accounts"
    __table_args__ = (
        Index("ix_provider_accounts_code", "provider_code"),
        # Partial unique index: only one ACTIVE row per provider_code.
        # ``bootstrap_registry`` takes the first active row and warns-and-skips
        # the rest; the constraint makes the application-layer guard in
        # ``manage_provider_accounts`` a true invariant rather than a TOCTOU race.
        Index(
            "uq_provider_accounts_active_code",
            "provider_code",
            unique=True,
            postgresql_where="is_active = true",
        ),
        {"comment": "Provider account credentials and configuration"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key",
    )
    provider_code: Mapped[str] = mapped_column(
        String(50),
        comment="Logistics provider identifier (open string)",
    )
    name: Mapped[str] = mapped_column(
        String(255), comment="Human-readable account name"
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, comment="Whether this account is active"
    )
    credentials_json: Mapped[dict] = mapped_column(
        JSONB, comment="Encrypted credentials (JSON)"
    )
    config_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Provider-specific configuration"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# ---------------------------------------------------------------------------
# Delivery Quotes (server-side storage for price integrity)
# ---------------------------------------------------------------------------


class DeliveryQuoteModel(Base):
    """Server-side persisted delivery quote.

    Quotes are created during rate calculation and looked up when
    creating a shipment to prevent client-side price tampering.
    """

    __tablename__ = "delivery_quotes"
    __table_args__ = (
        Index("ix_delivery_quotes_expires_at", "expires_at"),
        Index("ix_delivery_quotes_identity", "identity_id"),
        {"comment": "Server-side delivery quotes for price integrity"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Quote identifier (returned to client)",
    )
    # Owner of the quote — populated by the customer-facing checkout
    # endpoint so order creation can refuse a quote that belongs to a
    # different customer (CR-2). Nullable for backward compat with
    # legacy quotes (rows pre-dating REC-041) and for the admin
    # ``/admin/logistics/rates/quote`` flow where the operator quotes
    # on behalf of a not-yet-known buyer.
    identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Customer identity that requested the quote; NULL for admin or legacy",
    )

    provider_code: Mapped[str] = mapped_column(
        String(50), comment="Logistics provider identifier"
    )
    service_code: Mapped[str] = mapped_column(
        String(100), comment="Provider-specific tariff/service code"
    )
    service_name: Mapped[str] = mapped_column(
        String(500), comment="Human-readable tariff name"
    )
    delivery_type: Mapped[str] = mapped_column(
        Enum(DeliveryType, name="delivery_type_enum", create_constraint=False),
        comment="Courier, pickup point, or post office",
    )

    # Cost breakdown
    total_cost_amount: Mapped[int] = mapped_column(
        Integer, comment="Total cost in smallest currency unit"
    )
    total_cost_currency: Mapped[str] = mapped_column(
        String(3), comment="ISO 4217 currency code"
    )
    base_cost_amount: Mapped[int] = mapped_column(
        Integer, comment="Base cost in smallest currency unit"
    )
    base_cost_currency: Mapped[str] = mapped_column(
        String(3), comment="ISO 4217 currency code"
    )
    insurance_cost_amount: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Insurance cost"
    )
    insurance_cost_currency: Mapped[str | None] = mapped_column(
        String(3), nullable=True, comment="Insurance currency"
    )

    # Delivery estimate
    delivery_days_min: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Minimum delivery days"
    )
    delivery_days_max: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Maximum delivery days"
    )

    # Opaque provider data
    provider_payload: Mapped[str] = mapped_column(
        Text, default="", comment="JSON-serialised opaque provider data"
    )

    # Lifecycle
    quoted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), comment="When quote was generated"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When quote expires (e.g. Yandex 10-min offer timeout)",
    )

    # Route context (for audit / debugging)
    origin_json: Mapped[dict] = mapped_column(JSONB, comment="Origin address snapshot")
    destination_json: Mapped[dict] = mapped_column(
        JSONB, comment="Destination address snapshot"
    )
    parcels_json: Mapped[list] = mapped_column(JSONB, comment="Parcels snapshot")


# ---------------------------------------------------------------------------
# PickupPoint snapshot (local mirror of CDEK / Yandex pickup-point catalogue)
# ---------------------------------------------------------------------------


class PickupPointModel(Base):
    """Local snapshot of every pickup / delivery point known to a provider.

    Populated by ``sync_pickup_points_task`` (TaskIQ cron, every 6 h) so
    the storefront map reads from PostgreSQL with a GiST radius index
    instead of paginating CDEK on every pan/zoom. ``QuoteForPickupPointHandler``
    resolves a clicked marker against the same table.

    Soft-delete via ``deleted_at``: when a sync run no longer sees a
    given ``external_id``, the row is tombstoned rather than dropped so
    references from booked orders remain queryable for audit.
    """

    __tablename__ = "pickup_points"
    __table_args__ = (
        UniqueConstraint(
            "provider_code",
            "external_id",
            name="uq_pickup_points_provider_external_id",
        ),
        # All three supporting indexes (partial GiST on geom, partial
        # B-tree on (provider_code, lower(city)), partial B-tree on
        # provider_code) are declared as raw SQL inside the alembic
        # migration ``a1b2c3d4e5f6`` because alembic autogenerate does
        # not faithfully render partial expression indexes. Keep them
        # out of __table_args__ to avoid duplicate-index drift.
        {"comment": "Local snapshot of carrier pickup-point catalogues"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Internal PK; carrier identity is (provider_code, external_id)",
    )

    provider_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Carrier code: 'cdek' / 'yandex_delivery' / ...",
    )
    external_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Carrier-side ID (CDEK PVZ code, Yandex platform_station_id)",
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_point_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="pvz | postamat | post_office | terminal",
    )

    # --- Address (flattened so simple WHERE clauses still index) -----------
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    street: Mapped[str | None] = mapped_column(Text, nullable=True)
    house: Mapped[str | None] = mapped_column(Text, nullable=True)
    apartment: Mapped[str | None] = mapped_column(Text, nullable=True)
    subdivision_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Geo ---------------------------------------------------------------
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # geography(POINT, 4326) — WGS84 lat/lon. ``spatial_index=False``
    # because we declare the GiST index by hand in __table_args__ (so the
    # partial-WHERE clause is preserved across alembic autogenerates).
    geom: Mapped[object | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=True,
        comment="PostGIS WGS84 point built from (latitude, longitude)",
    )

    # --- Capabilities ------------------------------------------------------
    work_schedule: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_cash_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_card_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    weight_limit_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions_limit_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="{length_cm, width_cm, height_cm} or NULL",
    )
    services_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="PickupPointServices flags (fitting / partial refuse / ...)",
    )

    # --- Provider-specific metadata (CDEK city_code, Yandex station_id) ---
    address_metadata_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Carrier-specific Address.metadata payload",
    )

    # --- Lifecycle ---------------------------------------------------------
    synced_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="Last time a sync run saw this row from the carrier",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Tombstone — set when a sync no longer sees this external_id",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
