"""Referral domain events.

Validation and ``aggregate_id`` auto-fill come from
:class:`shared.interfaces.entities.ModuleDomainEvent`. Referral
spans four aggregate kinds (``ReferralCode``, ``Referral``,
``ReferralReward``, ``CustomerLoyalty``) so each concrete event MUST
override ``aggregate_type``; the validator below enforces that.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class ReferralEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for every referral-domain event."""

    aggregate_type: str = "Referral"

    def __init_subclass__(
        cls,
        *,
        abstract: bool = False,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(
            abstract=abstract,
            required_fields=required_fields,
            aggregate_id_field=aggregate_id_field,
            **kwargs,
        )
        if abstract or required_fields is None:
            return
        if "aggregate_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' — referral "
                "events span multiple aggregate kinds (ReferralCode, "
                "Referral, ReferralReward, CustomerLoyalty)."
            )


# ---------------------------------------------------------------------------
# ReferralCode aggregate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferralCodeIssuedEvent(
    ReferralEvent,
    required_fields=("code_id", "customer_id"),
    aggregate_id_field="code_id",
):
    code_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "ReferralCode"
    event_type: str = "ReferralCodeIssuedEvent"


@dataclass(frozen=True)
class ReferralCodeRevokedEvent(
    ReferralEvent,
    required_fields=("code_id", "customer_id"),
    aggregate_id_field="code_id",
):
    code_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    reason: str = ""
    aggregate_type: str = "ReferralCode"
    event_type: str = "ReferralCodeRevokedEvent"


# ---------------------------------------------------------------------------
# Referral aggregate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferralCreatedEvent(
    ReferralEvent,
    required_fields=("referral_id", "referrer_customer_id", "invitee_customer_id"),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    referrer_customer_id: uuid.UUID | None = None
    invitee_customer_id: uuid.UUID | None = None
    source_channel: str = ""
    aggregate_type: str = "Referral"
    event_type: str = "ReferralCreatedEvent"


@dataclass(frozen=True)
class ReferralActivatedEvent(
    ReferralEvent,
    required_fields=(
        "referral_id",
        "referrer_customer_id",
        "invitee_customer_id",
        "qualifying_order_id",
    ),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    referrer_customer_id: uuid.UUID | None = None
    invitee_customer_id: uuid.UUID | None = None
    qualifying_order_id: uuid.UUID | None = None
    fraud_score: int = 0
    aggregate_type: str = "Referral"
    event_type: str = "ReferralActivatedEvent"


@dataclass(frozen=True)
class ReferralRewardedEvent(
    ReferralEvent,
    required_fields=("referral_id", "referrer_customer_id"),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    referrer_customer_id: uuid.UUID | None = None
    aggregate_type: str = "Referral"
    event_type: str = "ReferralRewardedEvent"


@dataclass(frozen=True)
class ReferralExpiredEvent(
    ReferralEvent,
    required_fields=("referral_id",),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    aggregate_type: str = "Referral"
    event_type: str = "ReferralExpiredEvent"


@dataclass(frozen=True)
class ReferralCancelledEvent(
    ReferralEvent,
    required_fields=("referral_id",),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    reason: str = ""
    aggregate_type: str = "Referral"
    event_type: str = "ReferralCancelledEvent"


@dataclass(frozen=True)
class ReferralFraudBlockedEvent(
    ReferralEvent,
    required_fields=("referral_id",),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    fraud_score: int = 0
    reason: str = ""
    aggregate_type: str = "Referral"
    event_type: str = "ReferralFraudBlockedEvent"


@dataclass(frozen=True)
class ReferralPendingReviewEvent(
    ReferralEvent,
    required_fields=("referral_id",),
    aggregate_id_field="referral_id",
):
    referral_id: uuid.UUID | None = None
    fraud_score: int = 0
    aggregate_type: str = "Referral"
    event_type: str = "ReferralPendingReviewEvent"


# ---------------------------------------------------------------------------
# ReferralReward aggregate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferralRewardAccruedEvent(
    ReferralEvent,
    required_fields=("reward_id", "customer_id"),
    aggregate_id_field="reward_id",
):
    reward_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    referral_id: uuid.UUID | None = None
    kind: str = ""
    amount_kopecks: int = 0
    aggregate_type: str = "ReferralReward"
    event_type: str = "ReferralRewardAccruedEvent"


@dataclass(frozen=True)
class ReferralRewardReleasedEvent(
    ReferralEvent,
    required_fields=("reward_id", "customer_id"),
    aggregate_id_field="reward_id",
):
    reward_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    amount_kopecks: int = 0
    aggregate_type: str = "ReferralReward"
    event_type: str = "ReferralRewardReleasedEvent"


@dataclass(frozen=True)
class ReferralRewardReversedEvent(
    ReferralEvent,
    required_fields=("reward_id", "customer_id"),
    aggregate_id_field="reward_id",
):
    reward_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    amount_kopecks: int = 0
    previous_status: str = ""
    reason: str = ""
    aggregate_type: str = "ReferralReward"
    event_type: str = "ReferralRewardReversedEvent"


@dataclass(frozen=True)
class ReferralRewardExpiredEvent(
    ReferralEvent,
    required_fields=("reward_id",),
    aggregate_id_field="reward_id",
):
    reward_id: uuid.UUID | None = None
    aggregate_type: str = "ReferralReward"
    event_type: str = "ReferralRewardExpiredEvent"


# ---------------------------------------------------------------------------
# CustomerLoyalty aggregate (tier upgrades; balance changes are emitted by
# the shared ledger as ``LedgerTransactionPostedEvent``).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CustomerTierUpgradedEvent(
    ReferralEvent,
    required_fields=("customer_id",),
    aggregate_id_field="customer_id",
):
    customer_id: uuid.UUID | None = None
    previous_tier: str = ""
    new_tier: str = ""
    aggregate_type: str = "CustomerLoyalty"
    event_type: str = "CustomerTierUpgradedEvent"
