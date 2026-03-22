"""Add missing uz-Cyrl country translations.

6 countries were missing Cyrillic Uzbek translations:
Tajikistan, Turkmenistan, Ukraine, Georgia, Japan, UAE.

Revision ID: 22_0004
Revises: 22_0003
Create Date: 2026-03-22
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "22_0004"
down_revision = "22_0003"
branch_labels = None
depends_on = None

# fmt: off
# (country_code, lang_code, name, official_name)
MISSING_TRANSLATIONS = [
    ("TJ", "uz-Cyrl", "Тожикистон",    "Тожикистон Республикаси"),
    ("TM", "uz-Cyrl", "Туркманистон",   None),
    ("UA", "uz-Cyrl", "Украина",         None),
    ("GE", "uz-Cyrl", "Грузия",          None),
    ("JP", "uz-Cyrl", "Япония",          None),
    ("AE", "uz-Cyrl", "БАА",             "Бирлашган Араб Амирликлари"),
]
# fmt: on


def upgrade() -> None:
    """Insert missing uz-Cyrl country translations."""
    tr_t = sa.table(
        "country_translations",
        sa.column("id", sa.UUID),
        sa.column("country_code", sa.String),
        sa.column("lang_code", sa.String),
        sa.column("name", sa.String),
        sa.column("official_name", sa.String),
    )

    for country_code, lang_code, name, official_name in MISSING_TRANSLATIONS:
        tr_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"country_tr.{country_code}.{lang_code}",
        )
        op.execute(
            tr_t.insert().values(
                id=tr_id,
                country_code=country_code,
                lang_code=lang_code,
                name=name,
                official_name=official_name,
            )
        )


def downgrade() -> None:
    """Remove the 6 added uz-Cyrl translations."""
    for country_code, lang_code, _, _ in MISSING_TRANSLATIONS:
        op.execute(
            sa.text(
                "DELETE FROM country_translations "
                "WHERE country_code = :cc AND lang_code = :lc"
            ).bindparams(cc=country_code, lc=lang_code)
        )
