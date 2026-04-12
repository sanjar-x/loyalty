"""
ORM models for the Cart bounded context.

Maps cart domain concepts to PostgreSQL tables. These models belong to the
infrastructure layer -- repositories translate between ORM and domain entities
using the Data Mapper pattern.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class CartModel(Base):
    """Shopping cart aggregate root."""

    __tablename__ = "carts"
    __table_args__ = (
        Index(
            "uix_carts_identity_active",
            "identity_id",
            unique=True,
            postgresql_where="status = 'active' AND identity_id IS NOT NULL",
        ),
        Index(
            "uix_carts_anonymous_active",
            "anonymous_token",
            unique=True,
            postgresql_where="status = 'active' AND anonymous_token IS NOT NULL",
        ),
        CheckConstraint(
            "status IN ('active', 'frozen', 'merged', 'ordered')",
            name="ck_carts_valid_status",
        ),
        CheckConstraint(
            "(identity_id IS NOT NULL AND anonymous_token IS NULL) OR "
            "(identity_id IS NULL AND anonymous_token IS NOT NULL)",
            name="ck_carts_owner_xor",
        ),
        {"comment": "Shopping carts with lifecycle FSM"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    anonymous_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frozen_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_repriced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    items: Mapped[list[CartItemModel]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CartItemModel(Base):
    """Individual item within a cart."""

    __tablename__ = "cart_items"
    __table_args__ = (
        Index("uix_cart_items_cart_sku", "cart_id", "sku_id", unique=True),
        CheckConstraint(
            "quantity > 0 AND quantity <= 99", name="ck_cart_items_valid_quantity"
        ),
        {"comment": "Cart line items (one per SKU per cart)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    cart: Mapped[CartModel] = relationship(back_populates="items")


class CheckoutSnapshotModel(Base):
    """Immutable price snapshot created at checkout initiation."""

    __tablename__ = "checkout_snapshots"
    __table_args__ = ({"comment": "Frozen price snapshots for checkout validation"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    items_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="Serialized CheckoutItemSnapshot[]"
    )
    pickup_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class CheckoutAttemptModel(Base):
    """Checkout attempt (one active per cart at a time)."""

    __tablename__ = "checkout_attempts"
    __table_args__ = (
        Index(
            "uix_checkout_attempts_cart_pending",
            "cart_id",
            unique=True,
            postgresql_where="status = 'pending'",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'expired', 'failed')",
            name="ck_checkout_attempts_valid_attempt_status",
        ),
        {"comment": "Checkout attempts with at-most-one pending per cart"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checkout_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
