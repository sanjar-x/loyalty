"""add_product_variants

Revision ID: 7406c4bd5771
Revises: 3c5e991dde6c
Create Date: 2026-03-23 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7406c4bd5771"
down_revision: str | Sequence[str] | None = "3c5e991dde6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create product_variants table
    op.create_table(
        "product_variants",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "product_id",
            sa.UUID(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "name_i18n",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("description_i18n", postgresql.JSONB(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("default_price", sa.Integer(), nullable=True),
        sa.Column(
            "default_currency",
            sa.String(3),
            sa.ForeignKey("currencies.code", ondelete="RESTRICT"),
            server_default=sa.text("'RUB'"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    # 2. Backfill: create 1 default variant per existing product
    # NOTE: Uses UUIDv4 (gen_random_uuid) for backfill. Production IDs use UUIDv7 via application layer.
    op.execute(
        """
        INSERT INTO product_variants (id, product_id, name_i18n, sort_order, default_currency, created_at, updated_at)
        SELECT gen_random_uuid(), id, title_i18n, 0, 'RUB', now(), now()
        FROM products
    """
    )

    # 3. Add variant_id column to skus (nullable first)
    op.add_column("skus", sa.Column("variant_id", sa.UUID(), nullable=True))

    # 4. Backfill SKU variant_id
    op.execute(
        """
        UPDATE skus SET variant_id = (
            SELECT pv.id FROM product_variants pv WHERE pv.product_id = skus.product_id LIMIT 1
        )
    """
    )

    # 5. Make variant_id NOT NULL and add FK + index
    op.alter_column("skus", "variant_id", nullable=False)
    op.create_foreign_key(
        "fk_skus_variant_id",
        "skus",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_skus_variant_id", "skus", ["variant_id"])

    # 6. Make price nullable (remove server_default, allow NULL)
    op.alter_column("skus", "price", server_default=None, nullable=True)

    # 7. Add variant_id column to media_assets (nullable)
    op.add_column("media_assets", sa.Column("variant_id", sa.UUID(), nullable=True))

    # 8. Backfill media variant_id for non-null attribute_value_id rows
    op.execute(
        """
        UPDATE media_assets SET variant_id = (
            SELECT pv.id FROM product_variants pv WHERE pv.product_id = media_assets.product_id LIMIT 1
        ) WHERE attribute_value_id IS NOT NULL
    """
    )

    # 9. Add FK for media_assets.variant_id
    op.create_foreign_key(
        "fk_media_assets_variant_id",
        "media_assets",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_media_assets_variant_id", "media_assets", ["variant_id"])

    # 10. Drop old attribute_value_id column and its index
    op.drop_index("ix_media_assets_product_attr", table_name="media_assets")
    op.drop_index("uix_media_single_main_per_color", table_name="media_assets")
    op.drop_constraint("media_assets_attribute_value_id_fkey", "media_assets", type_="foreignkey")
    op.drop_column("media_assets", "attribute_value_id")

    # 11. Create new variant-based unique index for main media
    op.create_index(
        "uix_media_single_main_per_variant",
        "media_assets",
        ["product_id", "variant_id"],
        unique=True,
        postgresql_where=sa.text("role = 'main'"),
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    # Reverse operations (not detailed — pre-production)
    # NOTE: Pre-production migration. Original indexes (ix_media_assets_product_attr, uix_media_single_main_per_color) not restored in downgrade.
    op.drop_index("uix_media_single_main_per_variant", table_name="media_assets")
    op.add_column("media_assets", sa.Column("attribute_value_id", sa.UUID(), nullable=True))
    op.drop_index("ix_media_assets_variant_id", table_name="media_assets")
    op.drop_constraint("fk_media_assets_variant_id", "media_assets", type_="foreignkey")
    op.drop_column("media_assets", "variant_id")
    op.alter_column("skus", "price", server_default=sa.text("0"), nullable=False)
    op.drop_index("ix_skus_variant_id", table_name="skus")
    op.drop_constraint("fk_skus_variant_id", "skus", type_="foreignkey")
    op.drop_column("skus", "variant_id")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
