"""create initial tables (storage_objects + failed_tasks)

Revision ID: 000000000001
Revises:
Create Date: 2026-03-25 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create storage_objects and failed_tasks tables."""
    # -- storage_objects --
    op.create_table(
        "storage_objects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            comment="Internal object ID in the database",
        ),
        sa.Column(
            "bucket_name",
            sa.String(255),
            nullable=False,
            index=True,
            comment="S3 bucket name",
        ),
        sa.Column(
            "object_key",
            sa.String(1024),
            nullable=False,
            comment="Full path to the file within the bucket",
        ),
        sa.Column(
            "version_id",
            sa.String(255),
            nullable=True,
            comment="S3 object version ID",
        ),
        sa.Column(
            "is_latest",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether this version is the current active one",
        ),
        sa.Column(
            "size_bytes",
            sa.BigInteger,
            server_default=sa.text("0"),
            nullable=False,
            comment="File size in bytes",
        ),
        sa.Column(
            "etag",
            sa.String(64),
            nullable=True,
            comment="MD5 hash returned by S3",
        ),
        sa.Column(
            "content_type",
            sa.String(255),
            nullable=False,
            index=True,
            comment="MIME type",
        ),
        sa.Column("content_encoding", sa.String(255), nullable=True),
        sa.Column("cache_control", sa.String(255), nullable=True),
        sa.Column(
            "owner_module",
            sa.String(100),
            nullable=True,
            index=True,
            comment="Owning module name",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_modified_in_s3",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Last modification timestamp on the S3 side",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_storage_objects")),
    )

    # Partial unique index: only one active record per bucket/key pair
    op.create_index(
        "uix_storage_active_object",
        "storage_objects",
        ["bucket_name", "object_key"],
        unique=True,
        postgresql_where=sa.text("is_latest = true"),
    )

    # -- failed_tasks (DLQ) --
    op.create_table(
        "failed_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            comment="Primary key",
        ),
        sa.Column(
            "task_name",
            sa.String(255),
            nullable=False,
            comment="TaskIQ task name",
        ),
        sa.Column(
            "task_id",
            sa.String(255),
            nullable=False,
            comment="TaskIQ message ID",
        ),
        sa.Column(
            "args",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Task arguments",
        ),
        sa.Column(
            "labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Task labels",
        ),
        sa.Column(
            "error_message",
            sa.Text,
            nullable=False,
            comment="Error message text",
        ),
        sa.Column(
            "retry_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of retry attempts executed",
        ),
        sa.Column(
            "failed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp of the final failure",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_failed_tasks")),
    )


def downgrade() -> None:
    """Drop initial tables."""
    op.drop_table("failed_tasks")
    op.drop_index("uix_storage_active_object", table_name="storage_objects")
    op.drop_table("storage_objects")
