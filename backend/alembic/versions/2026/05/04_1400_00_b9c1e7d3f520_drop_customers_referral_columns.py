"""drop customers.referral_code and customers.referred_by

The referral graph (referral codes, referred-by edges, loyalty wallet)
is owned by the dedicated ``referral`` bounded context — see
[[BRD - Referral System]] / ADR-006. The legacy columns on
``customers`` are removed pre-launch so the new module is the single
source of truth from day one and there is no parallel-write window
that could drift.

Revision ID: b9c1e7d3f520
Revises: a7d2c8f1e034
Create Date: 2026-05-04 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9c1e7d3f520"
down_revision: str | Sequence[str] | None = "a7d2c8f1e034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop self-FK first, then the column it pointed at.
    op.drop_constraint(
        "fk_customers_referred_by_customers",
        "customers",
        type_="foreignkey",
    )
    op.drop_column("customers", "referred_by")
    op.drop_index("uq_customers_referral_code", table_name="customers")
    op.drop_column("customers", "referral_code")


def downgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("referral_code", sa.String(length=12), nullable=True),
    )
    op.create_index(
        "uq_customers_referral_code",
        "customers",
        ["referral_code"],
        unique=True,
    )
    op.add_column(
        "customers",
        sa.Column("referred_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_customers_referred_by_customers",
        "customers",
        "customers",
        ["referred_by"],
        ["id"],
    )
