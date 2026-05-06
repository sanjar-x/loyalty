"""drop customers referral columns

Drops the ``referral_code`` and ``referred_by`` columns from the
``customers`` table. Referral data moves to the new ``referral`` bounded
context introduced in the next migration (``add referral module``) —
public referral code now lives in ``referral_codes`` and referrer-
invitee linkage in ``referrals``.

Pre-launch posture: the columns are dropped without data migration
because the customers table contains only test data; no production
loyalty programme has launched yet (BRD §1.2).

Revision ID: b8f3c2e6a401
Revises: a7d2c8f1e034
Create Date: 2026-05-06 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f3c2e6a401"
down_revision: str | Sequence[str] | None = "a7d2c8f1e034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Self-FK from customers.referred_by → customers.id is dropped first so
    # the column drop below succeeds.
    op.drop_constraint(
        "fk_customers_referred_by_customers",
        "customers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_customers_referral_code",
        "customers",
        type_="unique",
    )
    op.drop_column("customers", "referred_by")
    op.drop_column("customers", "referral_code")
    op.create_table_comment(
        "customers",
        "Customer profiles (GDPR-isolated)",
        existing_comment="Customer profiles with referral data (GDPR-isolated)",
        schema=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "customers",
        sa.Column(
            "referral_code",
            sa.VARCHAR(length=12),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "referred_by",
            sa.UUID(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_customers_referral_code",
        "customers",
        ["referral_code"],
    )
    op.create_foreign_key(
        "fk_customers_referred_by_customers",
        "customers",
        "customers",
        ["referred_by"],
        ["id"],
    )
    op.create_table_comment(
        "customers",
        "Customer profiles with referral data (GDPR-isolated)",
        existing_comment="Customer profiles (GDPR-isolated)",
        schema=None,
    )
