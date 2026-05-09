"""add storage_object derivations (parent_storage_object_id, derivation_kind) — IMG-007

Background-removal (Bria RMBG-2.0 + future upscaling / watermark)
materialises a *new* StorageFile that points back to the original
upload. We add two columns + a ``DerivationKind`` enum + a partial
unique index that doubles as the idempotency anchor for
``IStorageRepository.find_derivation``.

Why the partial index:
- Predicate ``parent_storage_object_id IS NOT NULL AND is_latest = true``
  excludes both plain uploads (NULL parent) and soft-deleted derivations
  (``is_latest=false`` for previous bg-removed copies that have since
  been detached). Re-running background removal on an original whose
  prior derivation was deleted is allowed.
- ``UNIQUE`` enforces the one-derivation-per-(parent, kind) invariant
  at the DB level so a race between two concurrent
  ``POST .../remove-background`` requests fails one with an
  IntegrityError instead of producing two parallel S3 uploads.

Revision ID: e2f3a4b5c606
Revises: d1e2f3a4b505
Create Date: 2026-05-09 14:06:14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e2f3a4b5c606"
down_revision: str | Sequence[str] | None = "d1e2f3a4b505"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    derivation_kind_enum = postgresql.ENUM(
        "BG_REMOVED",
        name="derivation_kind_enum",
        create_type=False,
    )
    derivation_kind_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "storage_objects",
        sa.Column(
            "parent_storage_object_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "Parent storage object when this row is a derivation "
                "(IMG-007); NULL for plain uploads"
            ),
        ),
    )
    op.add_column(
        "storage_objects",
        sa.Column(
            "derivation_kind",
            derivation_kind_enum,
            nullable=True,
            comment=(
                "Discriminator for the kind of transformation when this "
                "row is a derivation (BG_REMOVED, future UPSCALED, ...)"
            ),
        ),
    )
    op.create_foreign_key(
        "fk_storage_objects_parent",
        "storage_objects",
        "storage_objects",
        ["parent_storage_object_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uix_storage_parent_derivation",
        "storage_objects",
        ["parent_storage_object_id", "derivation_kind"],
        unique=True,
        postgresql_where=sa.text(
            "parent_storage_object_id IS NOT NULL AND is_latest = true"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uix_storage_parent_derivation",
        table_name="storage_objects",
    )
    op.drop_constraint(
        "fk_storage_objects_parent",
        "storage_objects",
        type_="foreignkey",
    )
    op.drop_column("storage_objects", "derivation_kind")
    op.drop_column("storage_objects", "parent_storage_object_id")
    sa.Enum(name="derivation_kind_enum").drop(op.get_bind(), checkfirst=True)
