"""ORM model for the Recipient module.

Post-Sprint-1.5 Part 2: customs PII (passport_serial/number/issue_date,
birth_date, inn, validation_status) moved into the ``passports`` table
under the new ``passport`` bounded context. RecipientModel now holds
shipping coordinates only. The Alembic migration handles backfill +
column drops.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class RecipientModel(Base):
    __tablename__ = "recipients"
    __table_args__ = (
        Index("ix_recipients_identity", "identity_id", "is_archived"),
        {
            "comment": "Customer-owned shipping recipients (post-Sprint-1.5: no customs PII)"
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    full_name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_lat: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
