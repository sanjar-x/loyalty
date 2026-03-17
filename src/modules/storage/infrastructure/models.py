"""Storage ORM models.

Defines the SQLAlchemy ORM model for the ``storage_objects`` table, which
serves as a centralized registry of all files in the system. Metadata is
kept in sync with the S3-compatible object storage.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StorageObject(Base):
    """ORM model for the centralized file metadata registry.

    Each row represents one version of an object stored in an
    S3-compatible bucket. A partial unique index ensures that only
    one active (``is_latest=True``) record exists per bucket/key pair.
    """

    __tablename__ = "storage_objects"

    # -- Identification --

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        comment="Internal object ID in the database",
    )
    bucket_name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="S3 bucket name",
    )
    object_key: Mapped[str] = mapped_column(
        String(1024),
        comment="Full path to the file within the bucket (e.g. 'brands/123/logo.webp')",
    )

    # -- Versioning (when bucket versioning is enabled) --

    version_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="S3 object version ID"
    )
    is_latest: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        comment="Whether this version is the current active one",
    )

    # -- Physical characteristics --

    size_bytes: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), comment="File size in bytes"
    )
    etag: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="MD5 hash returned by S3 (useful for integrity checks)",
    )

    # -- Content metadata (HTTP headers) --

    content_type: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="MIME type (e.g. 'image/jpeg', 'application/pdf')",
    )
    content_encoding: Mapped[str | None] = mapped_column(String(255))
    cache_control: Mapped[str | None] = mapped_column(String(255))

    # -- System fields --

    owner_module: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        comment="Owning module name (e.g. 'catalog', 'users') for auditing",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    last_modified_in_s3: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        comment="Last modification timestamp on the S3 side (updated when ETag changes)",
    )

    __table_args__ = (
        Index(
            "uix_storage_active_object",
            "bucket_name",
            "object_key",
            unique=True,
            postgresql_where=text("is_latest = true"),
        ),
    )
