"""add_sku_purchase_price_and_pricing_fsm

Revision ID: a91c4f2d8e51
Revises: b7e4a9d2c318
Create Date: 2026-04-25 17:00:00.000000

ADR-005 — SKU‑Level Autonomous Pricing Recompute.

Adds purchase price + pricing FSM provenance fields on ``skus``:

* ``purchase_price`` / ``purchase_currency`` — the wholesale cost the
  pricing engine consumes as input.
* ``selling_price`` / ``selling_currency`` — output written back by the
  pricing recompute service.
* ``pricing_status`` — FSM (``legacy`` / ``pending`` / ``priced`` /
  ``stale_fx`` / ``missing_purchase_price`` / ``formula_error``).
* ``priced_at`` / ``priced_with_formula_version_id`` /
  ``priced_inputs_hash`` / ``priced_failure_reason`` — provenance and
  idempotency support.

Existing SKUs are backfilled to ``pricing_status='legacy'`` so the
storefront keeps showing them via the legacy ``price`` fallback until
admins record a ``purchase_price`` and a recompute lands. The migration
is fully reversible — ``downgrade()`` drops every new column without
touching existing data.

Constraints:

* CHECK ``purchase_price`` and ``purchase_currency`` are NULL together.
* CHECK ``pricing_status='priced'`` ⇒ ``selling_price IS NOT NULL`` AND
  ``priced_inputs_hash IS NOT NULL``.
* CHECK failure statuses ⇒ ``priced_failure_reason IS NOT NULL``.

Indexes:

* ``ix_skus_pricing_status_active`` — partial index over
  ``(pricing_status, deleted_at)`` for storefront filtering.
* ``ix_skus_priced_inputs_hash`` — partial unique-style lookup for
  recompute idempotency short‑circuit.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a91c4f2d8e51"
down_revision: str | Sequence[str] | None = "b7e4a9d2c318"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PRICING_STATUS_ENUM = sa.Enum(
    "legacy",
    "pending",
    "priced",
    "stale_fx",
    "missing_purchase_price",
    "formula_error",
    name="sku_pricing_status",
)

_PURCHASE_CURRENCY_VALUES = ("RUB", "CNY")


def upgrade() -> None:
    bind = op.get_bind()
    _PRICING_STATUS_ENUM.create(bind, checkfirst=True)

    op.add_column(
        "skus",
        sa.Column(
            "purchase_price",
            sa.Integer(),
            nullable=True,
            comment=(
                "Wholesale cost in smallest currency units of "
                "``purchase_currency`` (ADR-005)"
            ),
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "purchase_currency",
            sa.String(length=3),
            nullable=True,
            comment="ISO 4217 code of the purchase price currency (RUB or CNY)",
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "selling_price",
            sa.Integer(),
            nullable=True,
            comment=(
                "Output of the most recent successful pricing recompute, "
                "in smallest currency units of ``selling_currency``"
            ),
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "selling_currency",
            sa.String(length=3),
            nullable=True,
            comment="ISO 4217 code of the selling price (typically RUB)",
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "pricing_status",
            _PRICING_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'legacy'::sku_pricing_status"),
            comment="ADR-005 pricing FSM (see :class:`SkuPricingStatus`)",
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "priced_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="UTC timestamp of the last successful selling-price recompute",
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "priced_with_formula_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FormulaVersion that produced the current selling_price",
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "priced_inputs_hash",
            sa.String(length=64),
            nullable=True,
            comment=(
                "SHA-256 of the canonical recompute inputs; recompute "
                "short-circuits when the new digest equals this value"
            ),
        ),
    )
    op.add_column(
        "skus",
        sa.Column(
            "priced_failure_reason",
            sa.String(length=500),
            nullable=True,
            comment="Admin-readable error from the last recompute attempt",
        ),
    )

    op.create_foreign_key(
        constraint_name="fk_skus_purchase_currency",
        source_table="skus",
        referent_table="currencies",
        local_cols=["purchase_currency"],
        remote_cols=["code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        constraint_name="fk_skus_selling_currency",
        source_table="skus",
        referent_table="currencies",
        local_cols=["selling_currency"],
        remote_cols=["code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        constraint_name="fk_skus_priced_with_formula_version",
        source_table="skus",
        referent_table="pricing_formula_versions",
        local_cols=["priced_with_formula_version_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    # purchase_currency must be in the closed enum — DB-level safety net
    # in case an out-of-band UPDATE bypasses the application layer.
    purchase_currency_values = ", ".join(f"'{c}'" for c in _PURCHASE_CURRENCY_VALUES)
    op.create_check_constraint(
        constraint_name="ck_skus_purchase_currency_enum",
        table_name="skus",
        condition=(
            f"purchase_currency IS NULL OR "
            f"purchase_currency IN ({purchase_currency_values})"
        ),
    )
    op.create_check_constraint(
        constraint_name="ck_skus_purchase_price_currency_pair",
        table_name="skus",
        condition=(
            "(purchase_price IS NULL AND purchase_currency IS NULL) OR "
            "(purchase_price IS NOT NULL AND purchase_currency IS NOT NULL "
            "AND purchase_price > 0)"
        ),
    )
    op.create_check_constraint(
        constraint_name="ck_skus_selling_price_currency_pair",
        table_name="skus",
        condition=(
            "(selling_price IS NULL AND selling_currency IS NULL) OR "
            "(selling_price IS NOT NULL AND selling_currency IS NOT NULL "
            "AND selling_price > 0)"
        ),
    )
    op.create_check_constraint(
        constraint_name="ck_skus_priced_status_consistency",
        table_name="skus",
        condition=(
            "(pricing_status <> 'priced') OR "
            "(selling_price IS NOT NULL AND priced_inputs_hash IS NOT NULL)"
        ),
    )
    op.create_check_constraint(
        constraint_name="ck_skus_failure_status_consistency",
        table_name="skus",
        condition=(
            "(pricing_status NOT IN ('stale_fx', 'missing_purchase_price', "
            "'formula_error')) OR (priced_failure_reason IS NOT NULL)"
        ),
    )

    op.create_index(
        "ix_skus_pricing_status_active",
        "skus",
        ["pricing_status", "deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_skus_priced_inputs_hash",
        "skus",
        ["priced_inputs_hash"],
        postgresql_where=sa.text("priced_inputs_hash IS NOT NULL"),
    )
    op.create_index(
        "ix_skus_priced_with_formula_version",
        "skus",
        ["priced_with_formula_version_id"],
        postgresql_where=sa.text("priced_with_formula_version_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_skus_priced_with_formula_version", table_name="skus")
    op.drop_index("ix_skus_priced_inputs_hash", table_name="skus")
    op.drop_index("ix_skus_pricing_status_active", table_name="skus")

    op.drop_constraint("ck_skus_failure_status_consistency", "skus", type_="check")
    op.drop_constraint("ck_skus_priced_status_consistency", "skus", type_="check")
    op.drop_constraint("ck_skus_selling_price_currency_pair", "skus", type_="check")
    op.drop_constraint("ck_skus_purchase_price_currency_pair", "skus", type_="check")
    op.drop_constraint("ck_skus_purchase_currency_enum", "skus", type_="check")

    op.drop_constraint(
        "fk_skus_priced_with_formula_version", "skus", type_="foreignkey"
    )
    op.drop_constraint("fk_skus_selling_currency", "skus", type_="foreignkey")
    op.drop_constraint("fk_skus_purchase_currency", "skus", type_="foreignkey")

    op.drop_column("skus", "priced_failure_reason")
    op.drop_column("skus", "priced_inputs_hash")
    op.drop_column("skus", "priced_with_formula_version_id")
    op.drop_column("skus", "priced_at")
    op.drop_column("skus", "pricing_status")
    op.drop_column("skus", "selling_currency")
    op.drop_column("skus", "selling_price")
    op.drop_column("skus", "purchase_currency")
    op.drop_column("skus", "purchase_price")

    bind = op.get_bind()
    _PRICING_STATUS_ENUM.drop(bind, checkfirst=True)
