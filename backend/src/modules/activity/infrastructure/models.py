"""
ORM model for the activity tracking bounded context.

The ``user_activity_events`` table is a **partitioned append-only log**
(RANGE on ``created_at``), intended to scale to millions of rows while
still supporting time-bounded analytical queries cheaply via a BRIN
index.  Partitions are provisioned monthly.

Design decisions (see Research - Activity Tracking (2) PostgreSQL Analytics Design):
- Monthly RANGE partitions — best fit for current volume (10-50k/day).
- BRIN on ``created_at`` — tiny (<1 MB) and ideal for append-only.
- Partial B-tree on ``actor_id`` / ``product_id`` — skips anonymous rows.
- GIN (``jsonb_path_ops``) on ``payload`` — fast containment lookups.
- Primary key ``(id, created_at)`` — required by RANGE partitioning.

The ORM model itself is *declarative-only* — partition DDL (the parent
table declaration, the monthly children, and all indexes) is managed by
the Alembic migration and by the ``ensure_activity_partitions`` task.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class UserActivityEventModel(Base):
    """ORM mapping for ``user_activity_events`` (partitioned parent table).

    Note: the parent table is declared by the Alembic migration with
    ``PARTITION BY RANGE (created_at)``; SQLAlchemy only needs to know its
    columns for autogenerate diffing and for the INSERT path — it never
    issues plain ``CREATE TABLE`` for this model at runtime.
    """

    __tablename__ = "user_activity_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    search_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        primary_key=True,
        server_default=func.now(),
    )

    __table_args__ = (
        # BRIN index on created_at — tiny, perfect for append-only scans.
        Index(
            "ix_user_activity_events_created_brin",
            "created_at",
            postgresql_using="brin",
        ),
        # Hot path: "events for user X in the last N days".
        Index(
            "ix_user_activity_events_actor_created",
            "actor_id",
            "created_at",
            postgresql_where="actor_id IS NOT NULL",
        ),
        # Hot path: "views for product X grouped by type".
        Index(
            "ix_user_activity_events_product_type",
            "product_id",
            "event_type",
            postgresql_where="product_id IS NOT NULL",
        ),
        # JSONB containment queries (e.g. payload @> '{"source": "search"}').
        Index(
            "ix_user_activity_events_payload_gin",
            "payload",
            postgresql_using="gin",
            postgresql_ops={"payload": "jsonb_path_ops"},
        ),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )
