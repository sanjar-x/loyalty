"""fix_media_main_index_case

Fix the WHERE clause on uix_media_single_main_per_color: the original
migration used role = 'MAIN' (uppercase) but the ORM model defines
role = 'main' (lowercase).  Re-create the index with the correct case.

Revision ID: 3c5e991dde6c
Revises: 43de4d0e8914
Create Date: 2026-03-22 19:25:20.475884

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c5e991dde6c"
down_revision: str | Sequence[str] | None = "43de4d0e8914"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        "uix_media_single_main_per_color",
        table_name="media_assets",
        postgresql_where=sa.text("role = 'MAIN'"),
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "uix_media_single_main_per_color",
        "media_assets",
        ["product_id", "attribute_value_id"],
        unique=True,
        postgresql_where=sa.text("role = 'main'"),
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uix_media_single_main_per_color",
        table_name="media_assets",
        postgresql_where=sa.text("role = 'main'"),
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "uix_media_single_main_per_color",
        "media_assets",
        ["product_id", "attribute_value_id"],
        unique=True,
        postgresql_where=sa.text("role = 'MAIN'"),
        postgresql_nulls_not_distinct=True,
    )
