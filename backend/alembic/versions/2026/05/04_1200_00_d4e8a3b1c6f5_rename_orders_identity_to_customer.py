"""rename orders.identity_id → customer_id (semantic alignment)

Order aggregate is owned by Customer, not Identity. Customer.id ==
Identity.id via shared PK in the user module, so the column value is
unchanged — only its name and indexes need to follow.

Affected:
* ``orders.identity_id`` → ``orders.customer_id``
  + ``ix_orders_identity_id`` → ``ix_orders_customer_id``
  + ``ix_orders_identity_created`` → ``ix_orders_customer_created``
* ``order_idempotency_keys.identity_id`` → ``order_idempotency_keys.customer_id``

Other tables (payment_intents, recipients, carts) keep their
``identity_id`` columns — those modules are owned by Identity.

Revision ID: d4e8a3b1c6f5
Revises: b1c4d7e2a830
Create Date: 2026-05-04 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8a3b1c6f5"
down_revision: str | Sequence[str] | None = "b1c4d7e2a830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- orders.identity_id -> customer_id ---
    op.alter_column("orders", "identity_id", new_column_name="customer_id")
    op.execute("ALTER INDEX ix_orders_identity_id RENAME TO ix_orders_customer_id")
    op.execute(
        "ALTER INDEX ix_orders_identity_created RENAME TO ix_orders_customer_created"
    )

    # --- order_idempotency_keys.identity_id -> customer_id ---
    op.alter_column(
        "order_idempotency_keys", "identity_id", new_column_name="customer_id"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "order_idempotency_keys", "customer_id", new_column_name="identity_id"
    )
    op.execute(
        "ALTER INDEX ix_orders_customer_created RENAME TO ix_orders_identity_created"
    )
    op.execute("ALTER INDEX ix_orders_customer_id RENAME TO ix_orders_identity_id")
    op.alter_column("orders", "customer_id", new_column_name="identity_id")
