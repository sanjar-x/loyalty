"""Transactional Outbox ORM model for reliable domain event delivery.

Each row represents a domain event that must be published to the
message broker. The relay worker polls for unprocessed rows and
dispatches them, guaranteeing at-least-once delivery.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OutboxMessage(Base):
    """ORM model for the transactional outbox pattern.

    Written atomically in the same transaction as business data.
    The relay worker reads unprocessed rows and publishes them
    to the message broker (RabbitMQ).

    Attributes:
        id: Primary key (UUID, sortable by creation time).
        aggregate_type: Source aggregate type (e.g., Brand, Order).
        aggregate_id: Source aggregate identifier.
        event_type: Domain event name (e.g., BrandLogoConfirmedEvent).
        payload: Serialized event body as JSON.
        created_at: Timestamp when the event was written to the outbox.
        processed_at: Timestamp of successful publication (NULL = pending).
        correlation_id: Trace correlation ID (HTTP request_id -> Outbox -> TaskIQ).
    """

    __tablename__ = "outbox_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key (UUIDv7 for time-based sorting)",
    )
    aggregate_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Source aggregate type (Brand, Order, ...)",
    )
    aggregate_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Source aggregate ID",
    )

    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Domain event name (BrandLogoConfirmedEvent, ...)",
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Serialized event body",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the event was written to the outbox",
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp of successful broker publication (NULL = pending)",
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="Trace correlation ID (HTTP request_id -> Outbox -> TaskIQ)",
    )

    __table_args__ = (
        Index(
            "ix_outbox_processed_created",
            "processed_at",
            "created_at",
        ),
    )
