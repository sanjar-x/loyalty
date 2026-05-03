"""ORM models for the Recipient module.

PII columns (passport_*, inn, birth_date) are currently stored **plain**.
TODO before prod rollout: encrypt at rest (pgcrypto / Fernet) — the
column types stay String/Date so the migration is purely operational.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Date,
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
        CheckConstraint(
            "validation_status IN ('pending','verified','invalid')",
            name="ck_recipients_valid_status",
        ),
        CheckConstraint(
            "char_length(passport_serial) = 4",
            name="ck_recipients_passport_serial_len",
        ),
        CheckConstraint(
            "char_length(passport_number) = 6",
            name="ck_recipients_passport_number_len",
        ),
        CheckConstraint("char_length(inn) = 12", name="ck_recipients_inn_len"),
        Index("ix_recipients_identity", "identity_id", "is_archived"),
        Index("ix_recipients_inn", "inn"),
        {"comment": "Customer-owned recipients with customs PII"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    full_name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_lat: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    passport_serial: Mapped[str] = mapped_column(String(4), nullable=False)
    passport_number: Mapped[str] = mapped_column(String(6), nullable=False)
    passport_issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    validation_failed_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
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
