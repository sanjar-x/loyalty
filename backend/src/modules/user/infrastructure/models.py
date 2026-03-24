"""SQLAlchemy ORM models for the User module."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CustomerModel(Base):
    """ORM model for the ``customers`` table (customer profiles)."""

    __tablename__ = "customers"
    __table_args__ = ({"comment": "Customer profiles with referral data (GDPR-isolated)"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    profile_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), server_default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), server_default="", nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    referral_code: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class StaffMemberModel(Base):
    """ORM model for the ``staff_members`` table (staff profiles)."""

    __tablename__ = "staff_members"
    __table_args__ = ({"comment": "Staff member profiles"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), server_default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), server_default="", nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identities.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
