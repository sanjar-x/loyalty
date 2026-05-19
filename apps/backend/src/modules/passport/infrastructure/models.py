"""Passport ORM model.

Mirrors the customs subset of the legacy ``recipients`` table (pre
Sprint 1.5 Part 2). Migration 2026-05-19 extracts these rows out of
``recipients`` into the new ``passports`` table; recipient is left
with the shipping-coordinate slice only.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PassportModel(Base):
    __tablename__ = "passports"
    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('pending','verified','invalid')",
            name="ck_passports_valid_status",
        ),
        CheckConstraint(
            "char_length(passport_serial) = 4",
            name="ck_passports_passport_serial_len",
        ),
        CheckConstraint(
            "char_length(passport_number) = 6",
            name="ck_passports_passport_number_len",
        ),
        CheckConstraint("char_length(inn) = 12", name="ck_passports_inn_len"),
        Index("ix_passports_identity", "identity_id", "is_archived"),
        Index("ix_passports_inn", "inn"),
        {
            "comment": "Customer-owned customs passports (PII; extracted from recipients)"
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    full_name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_lat: Mapped[str] = mapped_column(String(255), nullable=False)
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
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
