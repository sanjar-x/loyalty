"""provider_accounts: unique active row per provider_code

Revision ID: a4f3c812d650
Revises: f2c93a8e54b1
Create Date: 2026-04-28 16:20:06.000000

Adds a partial unique index on ``provider_accounts.(provider_code)``
constrained to ``is_active = true``. ``bootstrap_registry`` only takes
the first active row per code, so any second active row would silently
shadow the first; without a DB constraint the application-layer
SELECT-then-INSERT/UPDATE check in ``manage_provider_accounts`` races
under concurrent admin requests. The partial unique index makes the
invariant a true constraint and surfaces violations as ``IntegrityError``
which the handlers translate to HTTP 409.

The migration is safe on existing data: deployed environments today have
at most one active CDEK row (single seed). If a duplicate ever existed
the migration would fail with a clear ``unique constraint violation``
on the index name, which is the right failure mode — operators must
deactivate the duplicate manually before upgrading.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4f3c812d650"
down_revision: str | Sequence[str] | None = "f2c93a8e54b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEX_NAME = "uq_provider_accounts_active_code"
_TABLE = "provider_accounts"


def upgrade() -> None:
    op.create_index(
        _INDEX_NAME,
        _TABLE,
        ["provider_code"],
        unique=True,
        postgresql_where="is_active = true",
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name=_TABLE)
