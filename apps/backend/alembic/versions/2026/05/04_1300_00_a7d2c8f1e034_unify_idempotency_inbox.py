"""unify idempotency keys + consumer inbox into shared tables

Replaces ``order_idempotency_keys`` and ``order_inbox_events`` with
shared, module-independent ``idempotency_keys`` and ``consumer_inbox``
tables. Per-module discrimination is achieved through the existing
``scope`` / ``consumer`` columns — no functional change for the order
module, just a naming move.

Affected:
* ``idempotency_keys`` (new) — replaces ``order_idempotency_keys``.
* ``consumer_inbox`` (new) — replaces ``order_inbox_events``.

Pre-launch posture: the previous tables are dropped without data
migration because the order module is not yet customer-facing in
production.

Revision ID: a7d2c8f1e034
Revises: d4e8a3b1c6f5
Create Date: 2026-05-04 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7d2c8f1e034"
# Migration history note (BE-2 inheritance, 2026-05-08):
# down_revision originally pointed at d4e8a3b1c6f5 (the
# orders_identity → customer rename migration) which is part of the
# in-flight refactor and not yet on main. BE-1's wip-commit re-anchored
# at ``b1c4d7e2a830`` (DobroPost shipment mappings — main head at the
# time of his commit). PR-S6 merged subsequently, advancing main head
# to ``79792d3c84ee`` (failure_kind column) -- per the pre-push
# migration protocol the sibling head was resolved by re-anchoring
# this revision onto the new main head, restoring a linear single-head
# chain (b1c4d7e2a830 → 79792d3c84ee → a7d2c8f1e034).
# The d4e8a3b1c6f5 rename migration will land in its own PR (likely
# PR-6b alongside referral) and re-anchor itself if needed.
down_revision: str | Sequence[str] | None = "79792d3c84ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create the shared idempotency-keys table.
    # ------------------------------------------------------------------
    op.create_table(
        "idempotency_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        comment="Per-request write-idempotency reservations (TTL-bounded)",
    )
    op.create_index(
        "uq_idempotency_keys_scope_key",
        "idempotency_keys",
        ["scope", "key"],
        unique=True,
    )
    op.create_index(
        "ix_idempotency_keys_expires_at",
        "idempotency_keys",
        ["expires_at"],
    )

    # ------------------------------------------------------------------
    # 2. Create the shared consumer-inbox table.
    # ------------------------------------------------------------------
    op.create_table(
        "consumer_inbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consumer", sa.String(length=64), nullable=False),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        comment="Idempotent consumer dedup (event_id + consumer)",
    )
    op.create_index(
        "uq_consumer_inbox_event_consumer",
        "consumer_inbox",
        ["event_id", "consumer"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 3. Drop the order-scoped tables they replace.
    #
    # ``if_exists=True`` is required because the dev/staging databases
    # may have skipped the prior ``order_idempotency_keys`` /
    # ``order_inbox_events`` creation entirely (the order module landed
    # late in pre-launch and these tables never made it onto every
    # local DB). Without the guard, ``upgrade head`` from a pristine
    # database would fail on a missing table.
    # ------------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS uix_order_inbox_events_event_consumer")
    op.execute("DROP TABLE IF EXISTS order_inbox_events")

    op.execute("DROP INDEX IF EXISTS ix_order_idempotency_keys_expires_at")
    op.execute("DROP INDEX IF EXISTS uix_order_idempotency_keys_key_scope")
    op.execute("DROP TABLE IF EXISTS order_idempotency_keys")


def downgrade() -> None:
    # Restore the order-scoped tables.
    op.create_table(
        "order_idempotency_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        comment="Idempotency keys (TTL 24h+)",
    )
    op.create_index(
        "uix_order_idempotency_keys_key_scope",
        "order_idempotency_keys",
        ["key", "scope"],
        unique=True,
    )
    op.create_index(
        "ix_order_idempotency_keys_expires_at",
        "order_idempotency_keys",
        ["expires_at"],
    )

    op.create_table(
        "order_inbox_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consumer", sa.String(length=64), nullable=False),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        comment="Idempotent consumer dedup (event_id + consumer)",
    )
    op.create_index(
        "uix_order_inbox_events_event_consumer",
        "order_inbox_events",
        ["event_id", "consumer"],
        unique=True,
    )

    # Drop the shared tables.
    op.drop_index("uq_consumer_inbox_event_consumer", table_name="consumer_inbox")
    op.drop_table("consumer_inbox")

    op.drop_index("ix_idempotency_keys_expires_at", table_name="idempotency_keys")
    op.drop_index("uq_idempotency_keys_scope_key", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
