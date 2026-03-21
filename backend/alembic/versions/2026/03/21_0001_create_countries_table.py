"""Create countries reference table (ISO 3166-1).

Revision ID: 21_0001
Revises: 20_0003
Create Date: 2026-03-21
"""

import sqlalchemy as sa

from alembic import op

revision = "21_0001"
down_revision = "20_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("alpha2", sa.String(2), primary_key=True, comment="ISO 3166-1 Alpha-2 code (e.g. KZ)"),
        sa.Column("alpha3", sa.String(3), nullable=False, unique=True, comment="ISO 3166-1 Alpha-3 code (e.g. KAZ)"),
        sa.Column("numeric", sa.SmallInteger(), nullable=False, unique=True, comment="ISO 3166-1 Numeric code (e.g. 398)"),
        sa.Column("name", sa.String(100), nullable=False, comment="Common English short name"),
    )
    op.create_index("ix_countries_name", "countries", ["name"])


def downgrade() -> None:
    op.drop_index("ix_countries_name", table_name="countries")
    op.drop_table("countries")
