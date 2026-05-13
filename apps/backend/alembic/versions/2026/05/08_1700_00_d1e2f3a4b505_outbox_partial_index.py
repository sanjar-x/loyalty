"""outbox partial index on processed_at IS NULL (INFRA-001)

Replaces the full ``ix_outbox_processed_created`` (B-tree on
``(processed_at, created_at)``) with a partial index restricted to
unprocessed rows. The hot relay query is::

    SELECT ... FROM outbox_messages
    WHERE processed_at IS NULL
    ORDER BY created_at
    LIMIT 100 FOR UPDATE SKIP LOCKED

The full index grows unbounded between daily prune runs; the partial
index stays bounded by the in-flight backlog (typically dozens of
rows) so Postgres keeps it cache-hot.

Revision ID: d1e2f3a4b505
Revises: 09b193ac2b43
Create Date: 2026-05-08 17:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d1e2f3a4b505"
down_revision: str | Sequence[str] | None = "09b193ac2b43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CONCURRENTLY can't run inside a transaction; alembic wraps every
    # migration in one by default — execute the index lifecycle inline
    # via the autocommit_block context manager.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_outbox_pending_created_at "
            "ON outbox_messages (created_at) "
            "WHERE processed_at IS NULL"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_outbox_processed_created")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_outbox_processed_created "
            "ON outbox_messages (processed_at, created_at)"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_outbox_pending_created_at")
