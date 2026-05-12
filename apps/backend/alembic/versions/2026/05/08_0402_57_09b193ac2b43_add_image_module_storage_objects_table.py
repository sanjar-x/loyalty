"""add image module storage_objects table

Revision ID: 09b193ac2b43
Revises: c9e4d3f7b502
Create Date: 2026-05-08 04:02:57.382156

Adds the storage_objects table that backs the new image module
(consolidated from the standalone image_backend microservice per CEO
directive 2026-05-08, β: hard cutover).

The auto-generated migration was trimmed to ONLY image-related
changes — alembic's autogenerate also surfaced pre-existing schema
drift on activity / orders / payment_intents / pricing_contexts /
recipients / shipments / skus / user_activity_events that is unrelated
to this PR's scope and is tracked separately in REC-005's audit
backlog.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "09b193ac2b43"
down_revision: str | Sequence[str] | None = "c9e4d3f7b502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create storage_objects table + indexes."""
    op.create_table(
        "storage_objects",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            comment="Internal object ID in the database",
        ),
        sa.Column(
            "bucket_name",
            sa.String(length=255),
            nullable=False,
            comment="S3 bucket name",
        ),
        sa.Column(
            "object_key",
            sa.String(length=1024),
            nullable=False,
            comment="Full path to the file within the bucket (e.g. 'brands/123/logo.webp')",
        ),
        sa.Column(
            "version_id",
            sa.String(length=255),
            nullable=True,
            comment="S3 object version ID",
        ),
        sa.Column(
            "is_latest",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether this version is the current active one",
        ),
        sa.Column(
            "size_bytes",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="File size in bytes",
        ),
        sa.Column(
            "etag",
            sa.String(length=64),
            nullable=True,
            comment="MD5 hash returned by S3 (useful for integrity checks)",
        ),
        sa.Column(
            "content_type",
            sa.String(length=255),
            nullable=False,
            comment="MIME type (e.g. 'image/jpeg', 'application/pdf')",
        ),
        sa.Column("content_encoding", sa.String(length=255), nullable=True),
        sa.Column("cache_control", sa.String(length=255), nullable=True),
        sa.Column(
            "owner_module",
            sa.String(length=100),
            nullable=True,
            comment="Owning module name (e.g. 'catalog', 'users') for auditing",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_UPLOAD",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                name="storage_status_enum",
                create_type=True,
            ),
            server_default="PENDING_UPLOAD",
            nullable=False,
        ),
        sa.Column(
            "url",
            sa.String(length=1024),
            nullable=True,
            comment="Public CDN URL after processing",
        ),
        sa.Column(
            "image_variants",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Processed size variants: [{size, width, height, url}]",
        ),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=True,
            comment="Original upload filename",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_modified_in_s3",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Last modification timestamp on the S3 side (updated when ETag changes)",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_storage_objects")),
    )
    op.create_index(
        op.f("ix_storage_objects_bucket_name"),
        "storage_objects",
        ["bucket_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storage_objects_content_type"),
        "storage_objects",
        ["content_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storage_objects_owner_module"),
        "storage_objects",
        ["owner_module"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storage_objects_status"),
        "storage_objects",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uix_storage_active_object",
        "storage_objects",
        ["bucket_name", "object_key"],
        unique=True,
        postgresql_where=sa.text("is_latest = true"),
    )


def downgrade() -> None:
    """Downgrade schema: drop storage_objects table + enum."""
    op.drop_index(
        "uix_storage_active_object",
        table_name="storage_objects",
        postgresql_where=sa.text("is_latest = true"),
    )
    op.drop_index(op.f("ix_storage_objects_status"), table_name="storage_objects")
    op.drop_index(op.f("ix_storage_objects_owner_module"), table_name="storage_objects")
    op.drop_index(op.f("ix_storage_objects_content_type"), table_name="storage_objects")
    op.drop_index(op.f("ix_storage_objects_bucket_name"), table_name="storage_objects")
    op.drop_table("storage_objects")
    sa.Enum(name="storage_status_enum").drop(op.get_bind(), checkfirst=True)
