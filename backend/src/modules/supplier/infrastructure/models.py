"""Supplier ORM model (Data Mapper pattern)."""

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.modules.supplier.domain.value_objects import SupplierType


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[SupplierType] = mapped_column(
        Enum(SupplierType, name="supplier_type_enum", create_type=False)
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        ForeignKey("countries.alpha2", ondelete="RESTRICT"),
        nullable=False,
        comment="ISO 3166-1 alpha-2 country code",
    )
    subdivision_code: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("subdivisions.code", ondelete="SET NULL"),
        nullable=True,
        comment="ISO 3166-2 subdivision code (optional)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    version: Mapped[int] = mapped_column(
        Integer, server_default=text("1"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[list] = relationship(
        "src.modules.catalog.infrastructure.models.Product",
        back_populates="supplier",
    )

    __table_args__ = (Index("ix_suppliers_country_code", "country_code"),)

    __mapper_args__: ClassVar[dict[str, Any]] = {
        "version_id_col": version,
    }
