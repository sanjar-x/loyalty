"""add_fts_search_vector

Revision ID: 58c349468552
Revises: 31e789139629
Create Date: 2026-04-10 22:39:19.739192

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58c349468552"
down_revision: str | Sequence[str] | None = "31e789139629"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add full-text search infrastructure for the storefront catalog."""

    # 1. Helper function: builds a weighted tsvector from product i18n fields.
    #    Marked IMMUTABLE so PostgreSQL can use it in an expression GIN index.
    #    Uses 'russian' / 'english' configs for proper stemming, 'simple' for tags.
    op.execute("""
        CREATE OR REPLACE FUNCTION catalog_product_search_vector(
            title_i18n  jsonb,
            descr_i18n  jsonb,
            tags        text[]
        ) RETURNS tsvector
        LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
            SELECT
                setweight(to_tsvector('russian',  coalesce(title_i18n  ->> 'ru', '')), 'A') ||
                setweight(to_tsvector('english',  coalesce(title_i18n  ->> 'en', '')), 'A') ||
                setweight(to_tsvector('russian',  coalesce(descr_i18n  ->> 'ru', '')), 'B') ||
                setweight(to_tsvector('english',  coalesce(descr_i18n  ->> 'en', '')), 'B') ||
                setweight(to_tsvector('simple',   coalesce(array_to_string(tags, ' '), '')), 'C')
        $$;
    """)

    # 2. GIN index on the computed tsvector (partial: non-deleted products only).
    op.execute("""
        CREATE INDEX ix_products_fts
            ON products
         USING GIN (catalog_product_search_vector(title_i18n, description_i18n, tags))
         WHERE deleted_at IS NULL;
    """)

    # 3. Expression B-tree indexes for autocomplete LIKE 'prefix%' queries.
    op.execute("""
        CREATE INDEX ix_products_title_ru_lower
            ON products (lower(title_i18n ->> 'ru') text_pattern_ops)
         WHERE deleted_at IS NULL
           AND status = 'PUBLISHED'
           AND is_visible = true;
    """)
    op.execute("""
        CREATE INDEX ix_products_title_en_lower
            ON products (lower(title_i18n ->> 'en') text_pattern_ops)
         WHERE deleted_at IS NULL
           AND status = 'PUBLISHED'
           AND is_visible = true;
    """)
    op.execute("""
        CREATE INDEX ix_categories_name_ru_lower
            ON categories (lower(name_i18n ->> 'ru') text_pattern_ops);
    """)
    op.execute("""
        CREATE INDEX ix_categories_name_en_lower
            ON categories (lower(name_i18n ->> 'en') text_pattern_ops);
    """)
    op.execute("""
        CREATE INDEX ix_brands_name_lower
            ON brands (lower(name) text_pattern_ops);
    """)


def downgrade() -> None:
    """Remove full-text search infrastructure."""
    op.execute("DROP INDEX IF EXISTS ix_brands_name_lower;")
    op.execute("DROP INDEX IF EXISTS ix_categories_name_en_lower;")
    op.execute("DROP INDEX IF EXISTS ix_categories_name_ru_lower;")
    op.execute("DROP INDEX IF EXISTS ix_products_title_en_lower;")
    op.execute("DROP INDEX IF EXISTS ix_products_title_ru_lower;")
    op.execute("DROP INDEX IF EXISTS ix_products_fts;")
    op.execute("DROP FUNCTION IF EXISTS catalog_product_search_vector;")
