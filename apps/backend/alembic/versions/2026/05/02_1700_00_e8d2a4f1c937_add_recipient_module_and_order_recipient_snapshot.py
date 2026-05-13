"""add recipient module + order.recipient_snapshot columns

Revision ID: e8d2a4f1c937
Revises: c1f2d3a4b5e6
Create Date: 2026-05-02 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e8d2a4f1c937"
down_revision: str | Sequence[str] | None = "c1f2d3a4b5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----- recipients -----
    op.create_table(
        "recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name_ru", sa.String(length=255), nullable=False),
        sa.Column("full_name_lat", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("passport_serial", sa.String(length=4), nullable=False),
        sa.Column("passport_number", sa.String(length=6), nullable=False),
        sa.Column("passport_issue_date", sa.Date(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column(
            "validation_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("validation_failed_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending','verified','invalid')",
            name="ck_recipients_valid_status",
        ),
        sa.CheckConstraint(
            "char_length(passport_serial) = 4",
            name="ck_recipients_passport_serial_len",
        ),
        sa.CheckConstraint(
            "char_length(passport_number) = 6",
            name="ck_recipients_passport_number_len",
        ),
        sa.CheckConstraint("char_length(inn) = 12", name="ck_recipients_inn_len"),
        comment="Customer-owned recipients with customs PII",
    )
    op.create_index(
        "ix_recipients_identity",
        "recipients",
        ["identity_id", "is_archived"],
    )
    op.create_index("ix_recipients_inn", "recipients", ["inn"])

    # ----- orders: add recipient snapshot columns -----
    # Existing migration created `orders` empty (no rows yet), so non-null
    # columns are safe.
    op.add_column(
        "orders",
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_full_name_ru", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_full_name_lat", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_phone", sa.String(length=16), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_passport_serial", sa.String(length=4), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_passport_number", sa.String(length=6), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_passport_issue_date", sa.Date(), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_birth_date", sa.Date(), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_inn", sa.String(length=12), nullable=False),
    )
    op.create_index("ix_orders_recipient", "orders", ["recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_recipient", table_name="orders")
    for col in (
        "recipient_inn",
        "recipient_birth_date",
        "recipient_passport_issue_date",
        "recipient_passport_number",
        "recipient_passport_serial",
        "recipient_email",
        "recipient_phone",
        "recipient_full_name_lat",
        "recipient_full_name_ru",
        "recipient_id",
    ):
        op.drop_column("orders", col)

    op.drop_index("ix_recipients_inn", table_name="recipients")
    op.drop_index("ix_recipients_identity", table_name="recipients")
    op.drop_table("recipients")
