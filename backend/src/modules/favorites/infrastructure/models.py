"""ORM models for the Favorites bounded context.

Two tables:

* ``favorite_lists`` — user-owned collections (default + custom).
* ``favorite_items`` — (target_type, target_id) entries inside lists.

Repositories translate between these ORM models and domain entities
via the Data Mapper pattern.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class FavoriteListModel(Base):
    """A favorites collection owned by an Identity."""

    __tablename__ = "favorite_lists"
    __table_args__ = (
        Index(
            "uq_favorite_lists_identity_id_name",
            "identity_id",
            "name",
            unique=True,
        ),
        Index(
            "uq_favorite_lists_identity_id_default",
            "identity_id",
            unique=True,
            postgresql_where=text("is_default IS TRUE"),
        ),
        Index("ix_favorite_lists_identity_id", "identity_id"),
        CheckConstraint(
            "char_length(trim(name)) > 0",
            name="ck_favorite_lists_name_non_empty",
        ),
        {"comment": "User-owned favorite lists (default + custom)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list[FavoriteItemModel]] = relationship(
        back_populates="favorite_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class FavoriteItemModel(Base):
    """An individual (target_type, target_id) entry inside a list."""

    __tablename__ = "favorite_items"
    __table_args__ = (
        Index(
            "uq_favorite_items_list_target",
            "list_id",
            "target_type",
            "target_id",
            unique=True,
        ),
        Index(
            "ix_favorite_items_target",
            "target_type",
            "target_id",
        ),
        CheckConstraint(
            "target_type IN ('product', 'brand')",
            name="ck_favorite_items_valid_target_type",
        ),
        {"comment": "Favorite items (products / brands) inside a list"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("favorite_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )

    favorite_list: Mapped[FavoriteListModel] = relationship(back_populates="items")
