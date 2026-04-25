"""
ORM models for the Logistics bounded context.

Maps domain concepts to PostgreSQL tables via SQLAlchemy declarative mappings.
Infrastructure layer — never imported by domain or application layers.
Repositories translate between ORM and domain entities (Data Mapper pattern).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Enum,
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
        {"comment": "Server-side delivery quotes for price integrity"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Quote identifier (returned to client)",
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
