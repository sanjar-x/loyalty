"""extend_pricing_variable_scope_with_sku_input

Revision ID: e8b3c721d49a
Revises: 636505b0c13a
Create Date: 2026-04-25 17:45:00.000000

ADR-005 — extends ``ck_pricing_variables_valid_scope`` to allow
``sku_input``, the new ``VariableScope`` member that routes purchase
prices through the catalog SKU row instead of ``ProductPricingProfile``.

Threaded off the ``636505b0c13a`` merge node so this branch is part of
the consolidated chain that ``alembic upgrade head`` walks; threading
directly off ``d4f7e2a91c83`` (the original Pass-2 parent) would
orphan it past the merge.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e8b3c721d49a"
# Re-targeted to the merge node that consolidates the
# ``pricing_context_set_at`` and ``shipment_edit_intake_return`` heads;
# threading directly off ``d4f7e2a91c83`` would leave this branch
# orphaned of the merge so ``alembic upgrade head`` would skip it.
down_revision: str | Sequence[str] | None = "636505b0c13a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_pricing_variables_valid_scope",
        "pricing_variables",
        type_="check",
    )
    op.create_check_constraint(
        constraint_name="ck_pricing_variables_valid_scope",
        table_name="pricing_variables",
        condition=(
            "scope IN ('global', 'supplier', 'category', 'range', "
            "'product_input', 'sku_input')"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_pricing_variables_valid_scope",
        "pricing_variables",
        type_="check",
    )
    op.create_check_constraint(
        constraint_name="ck_pricing_variables_valid_scope",
        table_name="pricing_variables",
        condition=(
            "scope IN ('global', 'supplier', 'category', 'range', 'product_input')"
        ),
    )
