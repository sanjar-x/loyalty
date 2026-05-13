"""SQLAlchemy ORM models for the referral bounded context.

Five tables:

* ``referral_codes`` — one per Customer, immutable code string.
* ``referrals`` — graph edges (referrer ↔ invitee).
* ``referral_rewards`` — every accrual (welcome / bonus / lifetime share).
* ``loyalty_accounts`` — multi-bucket wallet per Customer.
* ``loyalty_transactions`` — append-only ledger journal.

Status enums are stored as ``String(N)`` + ``CheckConstraint`` (the
codebase convention; no PG enum types).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base

# ---------------------------------------------------------------------------
# Status check-constraint helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# referral_codes
# ---------------------------------------------------------------------------


class ReferralCodeModel(Base):
    """Public referral code — one per Customer."""

    __tablename__ = "referral_codes"
    __table_args__ = (
        Index(
            "uq_referral_codes_customer_id",
            "customer_id",
            unique=True,
        ),
        Index(
            "uq_referral_codes_code_active",
            "code",
            unique=True,
            postgresql_where=text("is_revoked IS FALSE"),
        ),
        {"comment": "Public referral codes — one per Customer"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )


# ---------------------------------------------------------------------------
# referrals
# ---------------------------------------------------------------------------


class ReferralModel(Base):
    """Edge in the referrer → invitee graph."""

    __tablename__ = "referrals"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_REFERRAL_STATUSES})",
            name="ck_referrals_valid_status",
        ),
        Index(
            "uq_referrals_invitee_customer_id",
            "invitee_customer_id",
            unique=True,
        ),
        Index(
            "ix_referrals_referrer_status",
            "referrer_customer_id",
            "status",
        ),
        Index(
            "ix_referrals_status_expires",
            "status",
            "expires_at",
            postgresql_where=text("status = 'created'"),
        ),
        Index(
            "ix_referrals_qualifying_order",
            "qualifying_order_id",
            postgresql_where=text("qualifying_order_id IS NOT NULL"),
        ),
        {"comment": "Referrer ↔ invitee graph with FSM status"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    referrer_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    invitee_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    referral_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("referral_codes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_channel: Mapped[str] = mapped_column(String(32), nullable=False)
    attribution_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    qualifying_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    fraud_score: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    fraud_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )


# ---------------------------------------------------------------------------
# referral_rewards
# ---------------------------------------------------------------------------


class ReferralRewardModel(Base):
    """Per-reward FSM row — credit + release / reversal status."""

    __tablename__ = "referral_rewards"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_REWARD_STATUSES})",
            name="ck_referral_rewards_valid_status",
        ),
        CheckConstraint(
            f"kind IN ({_REWARD_KINDS})",
            name="ck_referral_rewards_valid_kind",
        ),
        CheckConstraint(
            "amount_kopecks > 0",
            name="ck_referral_rewards_positive_amount",
        ),
        Index(
            "ix_referral_rewards_pending_until",
            "pending_until",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_referral_rewards_customer_status",
            "customer_id",
            "status",
        ),
        Index(
            "ix_referral_rewards_source_order",
            "source_order_id",
            postgresql_where=text("source_order_id IS NOT NULL"),
        ),
        Index("ix_referral_rewards_referral", "referral_id"),
        {"comment": "Per-reward FSM (welcome / bonus / lifetime share)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    referral_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("referrals.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_kopecks: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'RUB'")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    pending_until: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    ledger_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# loyalty_accounts
# ---------------------------------------------------------------------------


class LoyaltyAccountModel(Base):
    """Multi-bucket wallet per Customer."""

    __tablename__ = "loyalty_accounts"
    __table_args__ = (
        CheckConstraint(
            f"tier IN ({_TIERS})",
            name="ck_loyalty_accounts_valid_tier",
        ),
        CheckConstraint(
            "available_kopecks >= 0",
            name="ck_loyalty_accounts_available_non_negative",
        ),
        CheckConstraint(
            "lifetime_kopecks >= 0",
            name="ck_loyalty_accounts_lifetime_non_negative",
        ),
        Index(
            "uq_loyalty_accounts_customer_id",
            "customer_id",
            unique=True,
        ),
        {"comment": "Loyalty wallet — one per Customer"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'RUB'")
    )
    available_kopecks: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    pending_kopecks: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    lifetime_kopecks: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    tier: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'BRONZE'")
    )
    lifetime_activations: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# loyalty_transactions
# ---------------------------------------------------------------------------


class LoyaltyTransactionModel(Base):
    """Append-only journal entry on a :class:`LoyaltyAccountModel`."""

    __tablename__ = "loyalty_transactions"
    __table_args__ = (
        CheckConstraint(
            f"kind IN ({_LEDGER_KINDS})",
            name="ck_loyalty_transactions_valid_kind",
        ),
        Index(
            "ix_loyalty_transactions_account_created",
            "account_id",
            "created_at",
        ),
        Index(
            "ix_loyalty_transactions_reference",
            "reference_type",
            "reference_id",
            postgresql_where=text("reference_id IS NOT NULL"),
        ),
        {"comment": "Append-only loyalty ledger"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loyalty_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    amount_available_delta: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    amount_pending_delta: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    amount_lifetime_delta: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    balance_after_available: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after_pending: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after_lifetime: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
