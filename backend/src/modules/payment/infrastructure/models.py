"""ORM models for the Payment bounded context."""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PaymentIntentModel(Base):
    __tablename__ = "payment_intents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('initiated','authorized','captured','refunded','cancelled','failed')",
            name="ck_payment_intents_valid_status",
        ),
        CheckConstraint("amount > 0", name="ck_payment_intents_amount_positive"),
        Index(
            "uix_payment_intents_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
        Index("ix_payment_intents_order", "order_id"),
        Index("ix_payment_intents_status", "status"),
        {"comment": "Payment intents owning a full PSP attempt lifecycle"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="initiated")
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
