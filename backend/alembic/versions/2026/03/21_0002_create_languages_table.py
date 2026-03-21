"""Create languages reference table (ISO 639 + IETF BCP 47).

Revision ID: 21_0002
Revises: 21_0001
Create Date: 2026-03-21
"""

import sqlalchemy as sa

from alembic import op

revision = "21_0002"
down_revision = "21_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "languages",
        sa.Column("code", sa.String(12), primary_key=True, comment="IETF BCP 47 tag (e.g. uz-Latn, en, ru)"),
        sa.Column("iso639_1", sa.String(2), nullable=True, comment="ISO 639-1 alpha-2 (e.g. uz, ru, en)"),
        sa.Column("iso639_2", sa.String(3), nullable=True, comment="ISO 639-2/T alpha-3 (e.g. uzb, rus, eng)"),
        sa.Column("iso639_3", sa.String(3), nullable=True, comment="ISO 639-3 alpha-3 (e.g. uzb, kaa)"),
        sa.Column("script", sa.String(4), nullable=True, comment="ISO 15924 script code (e.g. Latn, Cyrl, Arab)"),
        sa.Column("name_en", sa.String(100), nullable=False, comment="English name (e.g. Uzbek (Latin))"),
        sa.Column("name_native", sa.String(100), nullable=False, comment="Endonym (e.g. Oʻzbekcha, Русский)"),
        sa.Column("direction", sa.String(3), nullable=False, server_default="ltr", comment="Text direction: ltr or rtl"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="Available for selection in UI"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false", comment="Default fallback language (exactly one True)"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0", comment="Display order in language pickers"),
    )
    op.create_index("ix_languages_iso639_1", "languages", ["iso639_1"])
    op.create_index("ix_languages_active", "languages", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_languages_active", table_name="languages")
    op.drop_index("ix_languages_iso639_1", table_name="languages")
    op.drop_table("languages")
