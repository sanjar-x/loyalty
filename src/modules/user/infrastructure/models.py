# src/modules/user/infrastructure/models.py
import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class UserModel(Base):
    """User profile (PII). Shared PK 1:1 with identities."""

    __tablename__ = "users"
    __table_args__ = ({"comment": "User PII (GDPR-isolated from auth data)"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        primary_key=True,
        comment="PK + FK → identities (Shared PK 1:1)",
    )
    profile_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment="Display email (may differ from login email in local_credentials)",
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        server_default="",
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        server_default="",
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
