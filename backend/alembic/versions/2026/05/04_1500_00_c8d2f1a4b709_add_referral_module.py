"""add referral module — 5 tables + indexes

* ``referral_codes`` — one public code per Customer, immutable string.
* ``referrals`` — referrer ↔ invitee graph with FSM status.
* ``referral_rewards`` — per-reward FSM (welcome / bonus / lifetime share).
* ``loyalty_accounts`` — multi-bucket wallet per Customer.
* ``loyalty_transactions`` — append-only ledger journal entries.

Status discriminators are stored as ``String`` + ``CHECK`` per the
project convention (no PG enum types).

Revision ID: c8d2f1a4b709
Revises: b9c1e7d3f520
Create Date: 2026-05-04 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d2f1a4b709"
down_revision: str | Sequence[str] | None = "b9c1e7d3f520"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Status / kind sets — kept in sync with src.modules.referral.infrastructure.models.
_REFERRAL_STATUSES = (
    "'created', 'pending_review', 'activated', 'rewarded', "
    "'expired', 'cancelled', 'fraud_blocked'"
)
_REWARD_STATUSES = "'pending', 'released', 'reversed', 'expired'"
_REWARD_KINDS = "'invitee_welcome', 'referrer_bonus', 'referrer_lifetime_share'"
_TIERS = "'BRONZE', 'SILVER', 'GOLD'"
_LEDGER_KINDS = (
    "'referral_reward_pending', 'referral_reward_release', "
    "'referral_reward_reverse', 'order_spend', 'order_refund', "
    "'manual_adjustment'"
)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # referral_codes
    # ------------------------------------------------------------------
    op.create_table(
        "referral_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column(
            "issued_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        comment="Public referral codes — one per Customer",
    )
    op.create_index(
        "uq_referral_codes_customer_id",
        "referral_codes",
        ["customer_id"],
        unique=True,
    )
    op.create_index(
        "uq_referral_codes_code_active",
        "referral_codes",
        ["code"],
        unique=True,
        postgresql_where=sa.text("is_revoked IS FALSE"),
    )

    # ------------------------------------------------------------------
    # referrals
    # ------------------------------------------------------------------
    op.create_table(
        "referrals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "referrer_customer_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("invitee_customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "referral_code_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referral_codes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_channel", sa.String(length=32), nullable=False),
        sa.Column(
            "attribution_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("activated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "qualifying_order_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "fraud_score",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("fraud_reason", sa.String(length=255), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=64), nullable=True),
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
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_REFERRAL_STATUSES})",
            name="ck_referrals_valid_status",
        ),
        comment="Referrer ↔ invitee graph with FSM status",
    )
    op.create_index(
        "uq_referrals_invitee_customer_id",
        "referrals",
        ["invitee_customer_id"],
        unique=True,
    )
    op.create_index(
        "ix_referrals_referrer_status",
        "referrals",
        ["referrer_customer_id", "status"],
    )
    op.create_index(
        "ix_referrals_status_expires",
        "referrals",
        ["status", "expires_at"],
        postgresql_where=sa.text("status = 'created'"),
    )
    op.create_index(
        "ix_referrals_qualifying_order",
        "referrals",
        ["qualifying_order_id"],
        postgresql_where=sa.text("qualifying_order_id IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # referral_rewards
    # ------------------------------------------------------------------
    op.create_table(
        "referral_rewards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "referral_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("referrals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("amount_kopecks", sa.BigInteger(), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'RUB'"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("pending_until", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("released_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reversal_reason", sa.String(length=64), nullable=True),
        sa.Column("source_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "ledger_transaction_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
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
            f"status IN ({_REWARD_STATUSES})",
            name="ck_referral_rewards_valid_status",
        ),
        sa.CheckConstraint(
            f"kind IN ({_REWARD_KINDS})",
            name="ck_referral_rewards_valid_kind",
        ),
        sa.CheckConstraint(
            "amount_kopecks > 0",
            name="ck_referral_rewards_positive_amount",
        ),
        comment="Per-reward FSM (welcome / bonus / lifetime share)",
    )
    op.create_index(
        "ix_referral_rewards_pending_until",
        "referral_rewards",
        ["pending_until"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_referral_rewards_customer_status",
        "referral_rewards",
        ["customer_id", "status"],
    )
    op.create_index(
        "ix_referral_rewards_source_order",
        "referral_rewards",
        ["source_order_id"],
        postgresql_where=sa.text("source_order_id IS NOT NULL"),
    )
    op.create_index(
        "ix_referral_rewards_referral",
        "referral_rewards",
        ["referral_id"],
    )

    # ------------------------------------------------------------------
    # loyalty_accounts
    # ------------------------------------------------------------------
    op.create_table(
        "loyalty_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'RUB'"),
            nullable=False,
        ),
        sa.Column(
            "available_kopecks",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "pending_kopecks",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "lifetime_kopecks",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tier",
            sa.String(length=16),
            server_default=sa.text("'BRONZE'"),
            nullable=False,
        ),
        sa.Column(
            "lifetime_activations",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
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
            f"tier IN ({_TIERS})", name="ck_loyalty_accounts_valid_tier"
        ),
        sa.CheckConstraint(
            "available_kopecks >= 0",
            name="ck_loyalty_accounts_available_non_negative",
        ),
        sa.CheckConstraint(
            "lifetime_kopecks >= 0",
            name="ck_loyalty_accounts_lifetime_non_negative",
        ),
        comment="Loyalty wallet — one per Customer",
    )
    op.create_index(
        "uq_loyalty_accounts_customer_id",
        "loyalty_accounts",
        ["customer_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # loyalty_transactions
    # ------------------------------------------------------------------
    op.create_table(
        "loyalty_transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loyalty_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column(
            "amount_available_delta",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "amount_pending_delta",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "amount_lifetime_delta",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("balance_after_available", sa.BigInteger(), nullable=False),
        sa.Column("balance_after_pending", sa.BigInteger(), nullable=False),
        sa.Column("balance_after_lifetime", sa.BigInteger(), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"kind IN ({_LEDGER_KINDS})",
            name="ck_loyalty_transactions_valid_kind",
        ),
        comment="Append-only loyalty ledger",
    )
    op.create_index(
        "ix_loyalty_transactions_account_created",
        "loyalty_transactions",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_loyalty_transactions_reference",
        "loyalty_transactions",
        ["reference_type", "reference_id"],
        postgresql_where=sa.text("reference_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_loyalty_transactions_reference", table_name="loyalty_transactions"
    )
    op.drop_index(
        "ix_loyalty_transactions_account_created",
        table_name="loyalty_transactions",
    )
    op.drop_table("loyalty_transactions")

    op.drop_index("uq_loyalty_accounts_customer_id", table_name="loyalty_accounts")
    op.drop_table("loyalty_accounts")

    op.drop_index("ix_referral_rewards_referral", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_source_order", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_customer_status", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_pending_until", table_name="referral_rewards")
    op.drop_table("referral_rewards")

    op.drop_index("ix_referrals_qualifying_order", table_name="referrals")
    op.drop_index("ix_referrals_status_expires", table_name="referrals")
    op.drop_index("ix_referrals_referrer_status", table_name="referrals")
    op.drop_index("uq_referrals_invitee_customer_id", table_name="referrals")
    op.drop_table("referrals")

    op.drop_index("uq_referral_codes_code_active", table_name="referral_codes")
    op.drop_index("uq_referral_codes_customer_id", table_name="referral_codes")
    op.drop_table("referral_codes")
