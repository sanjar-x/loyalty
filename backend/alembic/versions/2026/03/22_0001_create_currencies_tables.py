"""Create currencies, currency_translations, and country_currencies tables.

Revision ID: 22_0001
Revises: 21_0004
Create Date: 2026-03-22
"""

import sqlalchemy as sa

from alembic import op

revision = "22_0001"
down_revision = "21_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create currency reference tables."""
    # -- currencies (ISO 4217) ----------------------------------------- #
    op.create_table(
        "currencies",
        sa.Column(
            "code",
            sa.String(3),
            primary_key=True,
            comment="ISO 4217 alpha-3 code (e.g. UZS, USD, EUR)",
        ),
        sa.Column(
            "numeric",
            sa.String(3),
            nullable=False,
            unique=True,
            comment="ISO 4217 numeric code, zero-padded (e.g. 840, 978)",
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Common English name (e.g. US Dollar)",
        ),
        sa.Column(
            "minor_unit",
            sa.SmallInteger,
            nullable=True,
            comment="Decimal places (2 for USD, 0 for JPY, 3 for BHD, NULL for XXX)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default="true",
            comment="Available for selection in UI / API",
        ),
        sa.Column(
            "sort_order",
            sa.SmallInteger,
            nullable=False,
            server_default="0",
            comment="Display order in currency pickers",
        ),
    )
    op.create_index("ix_currencies_numeric", "currencies", ["numeric"])
    op.create_index("ix_currencies_active", "currencies", ["is_active"])
    op.create_index("ix_currencies_name", "currencies", ["name"])

    # -- currency_translations ----------------------------------------- #
    op.create_table(
        "currency_translations",
        sa.Column(
            "id",
            sa.UUID,
            primary_key=True,
            comment="Surrogate primary key",
        ),
        sa.Column(
            "currency_code",
            sa.String(3),
            nullable=False,
            comment="FK -> currencies.code",
        ),
        sa.Column(
            "lang_code",
            sa.String(12),
            nullable=False,
            comment="FK -> languages.code (IETF BCP 47)",
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Translated currency name (e.g. Доллар США)",
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["currencies.code"],
            name="fk_currency_translations_currency_code_currencies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lang_code"],
            ["languages.code"],
            name="fk_currency_translations_lang_code_languages",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "currency_code",
            "lang_code",
            name="uq_currency_lang",
        ),
    )
    op.create_index(
        "ix_currency_tr_currency", "currency_translations", ["currency_code"]
    )
    op.create_index("ix_currency_tr_lang", "currency_translations", ["lang_code"])
    op.create_index("ix_currency_tr_name", "currency_translations", ["name"])

    # -- country_currencies (M:N bridge) ------------------------------- #
    op.create_table(
        "country_currencies",
        sa.Column(
            "country_code",
            sa.String(2),
            nullable=False,
            comment="FK -> countries.alpha2 (ISO 3166-1)",
        ),
        sa.Column(
            "currency_code",
            sa.String(3),
            nullable=False,
            comment="FK -> currencies.code (ISO 4217)",
        ),
        sa.Column(
            "is_primary",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="Whether this is the country's primary/official currency",
        ),
        sa.PrimaryKeyConstraint("country_code", "currency_code"),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["countries.alpha2"],
            name="fk_country_currencies_country_code_countries",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["currencies.code"],
            name="fk_country_currencies_currency_code_currencies",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_country_currencies_currency_code",
        "country_currencies",
        ["currency_code"],
    )


def downgrade() -> None:
    """Drop currency tables in reverse order."""
    op.drop_table("country_currencies")
    op.drop_table("currency_translations")
    op.drop_table("currencies")
