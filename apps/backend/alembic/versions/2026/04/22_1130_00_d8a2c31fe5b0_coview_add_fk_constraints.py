"""coview_add_fk_constraints

Revision ID: d8a2c31fe5b0
Revises: c9f1d2a3b7e4
Create Date: 2026-04-22 11:30:00.000000

Adds ``ON DELETE CASCADE`` FK constraints to ``product_co_view_scores`` so
that deleting a product (hard delete; soft deletes leave the row) cannot
leave orphaned neighbour rows that the cards handler would have to filter
at read time.

Also pre-cleans any rows whose referenced products no longer exist — the
constraint would otherwise fail to validate.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a2c31fe5b0"
down_revision: str | Sequence[str] | None = "c9f1d2a3b7e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop orphans left by earlier refreshes that ran before FK existed.
    op.execute(
        """
        DELETE FROM product_co_view_scores s
         WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.id = s.product_id)
            OR NOT EXISTS (SELECT 1 FROM products p WHERE p.id = s.co_product_id)
        """
    )
    op.execute(
        """
        ALTER TABLE product_co_view_scores
            ADD CONSTRAINT fk_product_co_view_scores_product
                FOREIGN KEY (product_id) REFERENCES products (id)
                ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE product_co_view_scores
            ADD CONSTRAINT fk_product_co_view_scores_co_product
                FOREIGN KEY (co_product_id) REFERENCES products (id)
                ON DELETE CASCADE
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE product_co_view_scores "
        "DROP CONSTRAINT IF EXISTS fk_product_co_view_scores_co_product"
    )
    op.execute(
        "ALTER TABLE product_co_view_scores "
        "DROP CONSTRAINT IF EXISTS fk_product_co_view_scores_product"
    )
