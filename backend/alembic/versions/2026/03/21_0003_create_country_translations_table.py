"""Create country_translations table.

Revision ID: 21_0003
Revises: 21_0002
Create Date: 2026-03-21
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "21_0003"
down_revision = "21_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "country_translations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, comment="Surrogate primary key"),
        sa.Column(
            "country_code",
            sa.String(2),
            sa.ForeignKey("countries.alpha2", ondelete="CASCADE"),
            nullable=False,
            comment="FK → countries.alpha2",
        ),
        sa.Column(
            "lang_code",
            sa.String(12),
            sa.ForeignKey("languages.code", ondelete="CASCADE"),
            nullable=False,
            comment="FK → languages.code (IETF BCP 47)",
        ),
        sa.Column("name", sa.String(255), nullable=False, comment="Translated short name (e.g. Россия)"),
        sa.Column("official_name", sa.String(255), nullable=True, comment="Official name (e.g. Российская Федерация)"),
    )
    op.create_unique_constraint("uq_country_lang", "country_translations", ["country_code", "lang_code"])
    op.create_index("ix_country_tr_country", "country_translations", ["country_code"])
    op.create_index("ix_country_tr_lang", "country_translations", ["lang_code"])
    op.create_index("ix_country_tr_name", "country_translations", ["name"])


def downgrade() -> None:
    op.drop_index("ix_country_tr_name", table_name="country_translations")
    op.drop_index("ix_country_tr_lang", table_name="country_translations")
    op.drop_index("ix_country_tr_country", table_name="country_translations")
    op.drop_constraint("uq_country_lang", "country_translations", type_="unique")
    op.drop_table("country_translations")
