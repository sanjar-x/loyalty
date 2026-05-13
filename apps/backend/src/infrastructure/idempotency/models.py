"""Shared SQLAlchemy ORM models for idempotency keys and consumer inbox.

Both tables are framework-shared (not module-owned) so every bounded
context uses the same schema, the same Alembic migration, the same
janitor task, and the same observability dashboards. Per-module
discrimination is achieved through the ``scope`` column on
``idempotency_keys`` and the ``consumer`` column on
``consumer_inbox`` — both are free-form strings owned by the module
that performs the reservation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class IdempotencyKeyModel(Base):
    """Reservation row for a single ``(scope, key)`` write idempotency token.

    The unique index on ``(scope, key)`` is what makes ``reserve``
    atomic — a duplicate insert raises ``IntegrityError`` and the
    repository turns that into a ``False`` return.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        Index(
            "uq_idempotency_keys_scope_key",
            "scope",
            "key",
            unique=True,
        ),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
        {"comment": "Per-request write-idempotency reservations (TTL-bounded)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class ConsumerInboxModel(Base):
    """Event inbox row — UNIQUE ``(event_id, consumer)`` deduplication.

    Each row records that a specific consumer has already processed a
    specific outbox event. Subsequent redeliveries observe the
    uniqueness constraint and short-circuit.
    """

    __tablename__ = "consumer_inbox"
    __table_args__ = (
        Index(
            "uq_consumer_inbox_event_consumer",
            "event_id",
            "consumer",
            unique=True,
        ),
        {"comment": "Idempotent consumer dedup (event_id + consumer)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    consumer: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
