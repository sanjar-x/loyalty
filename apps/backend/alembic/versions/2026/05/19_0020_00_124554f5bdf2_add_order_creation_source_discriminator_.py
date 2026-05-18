"""add Order.creation_source discriminator BE-6

Revision ID: 124554f5bdf2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-19 00:20:00.876056

BE-6 / Sprint 1.5 — adds the ``orders.creation_source`` discriminator
(``cart_checkout`` | ``buy_now`` | ``walk_in``) plus two CHECK
constraints that pin the enum values and enforce the
ADR-010 §I3 invariant (``creation_source = 'walk_in'`` ⇔
``is_walk_in = TRUE``).

Backfill rule for existing rows:

* ``is_walk_in = TRUE`` → ``'walk_in'``
* ``is_walk_in = FALSE`` → ``'cart_checkout'`` (safe default; historic
  Buy Now orders cannot be retroactively reclassified — no
  discriminator existed in the source data. From now on every new
  Buy Now order is flagged correctly by the handler.)

After backfill the ``server_default`` is dropped so future inserts MUST
specify ``creation_source`` explicitly (avoid silent 'cart_checkout'
drift if a future handler forgets to pass the enum).

NOTE: this migration deliberately covers ONLY the ``orders`` table.
The unrelated autogen noise (activity partition drops, index DESC
normalisation, server_default cleanups on order_state_history /
recipients / pricing_contexts / product_variants / skus) detected by
Alembic was discarded — those are pre-existing model-drift artefacts
that belong in their own migrations.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import MetaData  # noqa: F401

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "124554f5bdf2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``orders.creation_source`` + constraints + backfill."""
    # 1) Add column with temporary server_default so the NOT NULL
    #    constraint passes for existing rows without a full table
    #    rewrite (server_default fills them on column add).
    op.add_column(
        "orders",
        sa.Column(
            "creation_source",
            sa.String(length=32),
            server_default=sa.text("'cart_checkout'"),
            nullable=False,
            comment="Order entry-point: cart_checkout | buy_now | walk_in",
        ),
    )

    # 2) Backfill: walk-in rows → 'walk_in'. Buy Now historical rows
    #    cannot be reclassified (no source discriminator existed) —
    #    they stay as 'cart_checkout' along with real cart-flow rows.
    #    From this point onwards every new order writes the correct
    #    value via the handler.
    op.execute(
        """
        UPDATE orders
        SET creation_source = CASE
            WHEN is_walk_in = TRUE THEN 'walk_in'
            ELSE 'cart_checkout'
        END
        """
    )

    # 3) Drop the server_default so future inserts MUST specify the
    #    column explicitly. Catches a regression where a handler
    #    forgets to pass ``creation_source`` and quietly defaults to
    #    cart_checkout (would silently misclassify Buy Now / walk-in).
    op.alter_column("orders", "creation_source", server_default=None)

    # 4) Index for admin BI «Buy Now conversion rate» / per-source
    #    analytics. No predicate — three-value cardinality keeps the
    #    index small and full scans cheap.
    op.create_index(
        op.f("ix_orders_creation_source"),
        "orders",
        ["creation_source"],
        unique=False,
    )

    # 5) Constraints: enum whitelist + ADR-010 §I3 invariant.
    op.create_check_constraint(
        "ck_orders_valid_creation_source",
        "orders",
        "creation_source IN ('cart_checkout','buy_now','walk_in')",
    )
    op.create_check_constraint(
        "ck_orders_walk_in_source_consistent",
        "orders",
        "(creation_source = 'walk_in') = is_walk_in",
    )


def downgrade() -> None:
    """Reverse the upgrade: drop constraints + index + column."""
    op.drop_constraint("ck_orders_walk_in_source_consistent", "orders", type_="check")
    op.drop_constraint("ck_orders_valid_creation_source", "orders", type_="check")
    op.drop_index(op.f("ix_orders_creation_source"), table_name="orders")
    op.drop_column("orders", "creation_source")
