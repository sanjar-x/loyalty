"""Refactor countries table: numeric to String(3), drop name column, drop redundant indexes.

- Country.numeric: SmallInteger → String(3) for zero-padded ISO codes
- Country.name: removed (English name comes from country_translations)
- Drop redundant indexes on translation tables (covered by unique constraints)

Revision ID: 22_0003
Revises: 22_0002
Create Date: 2026-03-22
"""

import sqlalchemy as sa

from alembic import op

revision = "22_0003"
down_revision = "22_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply schema refactoring."""
    # 1. Convert countries.numeric from SmallInteger to String(3)
    #    First cast existing values to zero-padded strings
    op.execute(
        "ALTER TABLE countries "
        "ALTER COLUMN numeric TYPE VARCHAR(3) "
        "USING LPAD(numeric::text, 3, '0')"
    )

    # 2. Drop countries.name column (English name from country_translations)
    op.drop_index("ix_countries_name", table_name="countries")
    op.drop_column("countries", "name")

    # 3. Drop redundant indexes on translation tables
    #    (first column of unique constraint already indexed by PG)
    op.drop_index("ix_country_tr_country", table_name="country_translations")
    op.drop_index("ix_currency_tr_currency", table_name="currency_translations")
    # Note: subdivision_category_translations and subdivision_translations
    # redundant indexes are only in ORM model, not yet in DB migrations.
    # They will be handled when subdivision migrations are created.


def downgrade() -> None:
    """Revert schema refactoring."""
    # 3. Recreate redundant indexes
    op.create_index("ix_currency_tr_currency", "currency_translations", ["currency_code"])
    op.create_index("ix_country_tr_country", "country_translations", ["country_code"])

    # 2. Re-add countries.name column
    op.add_column(
        "countries",
        sa.Column("name", sa.String(100), nullable=True),
    )
    # Populate name from English translations
    op.execute(
        "UPDATE countries c SET name = ct.name "
        "FROM country_translations ct "
        "WHERE ct.country_code = c.alpha2 AND ct.lang_code = 'en'"
    )
    op.alter_column("countries", "name", nullable=False)
    op.create_index("ix_countries_name", "countries", ["name"])

    # 1. Convert countries.numeric back to SmallInteger
    op.execute(
        "ALTER TABLE countries "
        "ALTER COLUMN numeric TYPE SMALLINT "
        "USING numeric::integer"
    )
