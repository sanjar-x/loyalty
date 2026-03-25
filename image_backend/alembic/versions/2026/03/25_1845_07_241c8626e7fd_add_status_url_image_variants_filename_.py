"""add status url image_variants filename to storage_objects

Revision ID: 241c8626e7fd
Revises:
Create Date: 2026-03-25 18:45:07.795046

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "241c8626e7fd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add processing-lifecycle columns to storage_objects."""
    storage_status_enum = sa.Enum(
        "PENDING_UPLOAD",
        "PROCESSING",
        "COMPLETED",
        "FAILED",
        name="storage_status_enum",
    )
    storage_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "storage_objects",
        sa.Column(
            "status",
            storage_status_enum,
            server_default="PENDING_UPLOAD",
            nullable=False,
        ),
    )
    op.add_column(
        "storage_objects",
        sa.Column(
            "url",
            sa.String(length=1024),
            nullable=True,
            comment="Public CDN URL after processing",
        ),
    )
    op.add_column(
        "storage_objects",
        sa.Column(
            "image_variants",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Processed size variants: [{size, width, height, url}]",
        ),
    )
    op.add_column(
        "storage_objects",
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=True,
            comment="Original upload filename",
        ),
    )
    op.create_index(
        op.f("ix_storage_objects_status"),
        "storage_objects",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove processing-lifecycle columns from storage_objects."""
    op.drop_index(op.f("ix_storage_objects_status"), table_name="storage_objects")
    op.drop_column("storage_objects", "filename")
    op.drop_column("storage_objects", "image_variants")
    op.drop_column("storage_objects", "url")
    op.drop_column("storage_objects", "status")

    sa.Enum(name="storage_status_enum").drop(op.get_bind(), checkfirst=True)
