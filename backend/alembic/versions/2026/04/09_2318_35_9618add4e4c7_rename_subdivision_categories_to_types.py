"""rename subdivision categories to types

Revision ID: 9618add4e4c7
Revises: 9c626f590d95
Create Date: 2026-04-09 23:18:35.158874

"""

from collections.abc import Sequence

from sqlalchemy import MetaData  # noqa: F401

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9618add4e4c7"
down_revision: str | Sequence[str] | None = "9c626f590d95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename subdivision_categories → subdivision_types (data-safe)."""

    # 1. Drop FK from subdivisions → subdivision_categories
    op.drop_constraint(
        "fk_subdivisions_category_code_subdivision_categories",
        "subdivisions",
        type_="foreignkey",
    )

    # 2. Drop FK from subdivision_category_translations → subdivision_categories
    op.drop_constraint(
        "fk_subdivision_category_translations_category_code_subd_1876",
        "subdivision_category_translations",
        type_="foreignkey",
    )

    # 2b. Drop FK from subdivision_category_translations → languages (rename later)
    op.drop_constraint(
        "fk_subdivision_category_translations_lang_code_languages",
        "subdivision_category_translations",
        type_="foreignkey",
    )

    # 3. Rename tables
    op.rename_table("subdivision_categories", "subdivision_types")
    op.rename_table(
        "subdivision_category_translations", "subdivision_type_translations"
    )

    # 4. Rename columns
    op.alter_column(
        "subdivision_type_translations",
        "category_code",
        new_column_name="type_code",
        comment="FK -> subdivision_types.code",
    )
    op.alter_column(
        "subdivisions",
        "category_code",
        new_column_name="type_code",
        comment="FK -> subdivision_types.code",
    )

    # 5. Rename PK constraints
    op.execute(
        "ALTER TABLE subdivision_types "
        "RENAME CONSTRAINT pk_subdivision_categories TO pk_subdivision_types"
    )
    op.execute(
        "ALTER TABLE subdivision_type_translations "
        "RENAME CONSTRAINT pk_subdivision_category_translations "
        "TO pk_subdivision_type_translations"
    )

    # 6. Rename unique constraint
    op.execute(
        "ALTER TABLE subdivision_type_translations "
        "RENAME CONSTRAINT uq_sub_category_lang TO uq_sub_type_lang"
    )

    # 7. Rename indexes
    op.execute("ALTER INDEX ix_sub_cat_tr_lang RENAME TO ix_sub_type_tr_lang")
    op.execute("ALTER INDEX ix_subdivisions_category RENAME TO ix_subdivisions_type")

    # 8. Recreate FK constraints with new names / targets
    op.create_foreign_key(
        op.f("fk_subdivision_type_translations_type_code_subdivision_types"),
        "subdivision_type_translations",
        "subdivision_types",
        ["type_code"],
        ["code"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_subdivision_type_translations_lang_code_languages"),
        "subdivision_type_translations",
        "languages",
        ["lang_code"],
        ["code"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_subdivisions_type_code_subdivision_types"),
        "subdivisions",
        "subdivision_types",
        ["type_code"],
        ["code"],
        ondelete="RESTRICT",
    )

    # 9. Update column comments
    op.alter_column(
        "subdivision_types",
        "code",
        comment="ISO type token (e.g. PROVINCE, EMIRATE)",
    )
    op.alter_column(
        "subdivision_types",
        "sort_order",
        comment="Display order in type filters",
    )


def downgrade() -> None:
    """Revert subdivision_types → subdivision_categories."""

    # 1. Drop new FK constraints
    op.drop_constraint(
        op.f("fk_subdivisions_type_code_subdivision_types"),
        "subdivisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_subdivision_type_translations_type_code_subdivision_types"),
        "subdivision_type_translations",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_subdivision_type_translations_lang_code_languages"),
        "subdivision_type_translations",
        type_="foreignkey",
    )

    # 2. Rename indexes back
    op.execute("ALTER INDEX ix_subdivisions_type RENAME TO ix_subdivisions_category")
    op.execute("ALTER INDEX ix_sub_type_tr_lang RENAME TO ix_sub_cat_tr_lang")

    # 3. Rename unique constraint back
    op.execute(
        "ALTER TABLE subdivision_type_translations "
        "RENAME CONSTRAINT uq_sub_type_lang TO uq_sub_category_lang"
    )

    # 4. Rename PK constraints back
    op.execute(
        "ALTER TABLE subdivision_type_translations "
        "RENAME CONSTRAINT pk_subdivision_type_translations "
        "TO pk_subdivision_category_translations"
    )
    op.execute(
        "ALTER TABLE subdivision_types "
        "RENAME CONSTRAINT pk_subdivision_types TO pk_subdivision_categories"
    )

    # 5. Rename columns back
    op.alter_column(
        "subdivisions",
        "type_code",
        new_column_name="category_code",
        comment="FK -> subdivision_categories.code",
    )
    op.alter_column(
        "subdivision_type_translations",
        "type_code",
        new_column_name="category_code",
        comment="FK -> subdivision_categories.code",
    )

    # 6. Rename tables back
    op.rename_table(
        "subdivision_type_translations", "subdivision_category_translations"
    )
    op.rename_table("subdivision_types", "subdivision_categories")

    # 7. Recreate old FK constraints
    op.create_foreign_key(
        "fk_subdivision_category_translations_category_code_subd_1876",
        "subdivision_category_translations",
        "subdivision_categories",
        ["category_code"],
        ["code"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_subdivision_category_translations_lang_code_languages",
        "subdivision_category_translations",
        "languages",
        ["lang_code"],
        ["code"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_subdivisions_category_code_subdivision_categories",
        "subdivisions",
        "subdivision_categories",
        ["category_code"],
        ["code"],
        ondelete="RESTRICT",
    )

    # 8. Restore column comments
    op.alter_column(
        "subdivision_categories",
        "code",
        comment="ISO category token (e.g. PROVINCE, EMIRATE)",
    )
    op.alter_column(
        "subdivision_categories",
        "sort_order",
        comment="Display order in category filters",
    )
