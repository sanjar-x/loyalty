"""Dishka provider for the referral bounded context."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from src.modules.referral.application.commands.issue_referral_code import (
    IssueReferralCodeHandler,
)
from src.modules.referral.application.consumers.identity_events import (
    IssueCodeOnIdentityRegisteredConsumer,
    IssueCodeOnLinkedAccountCreatedConsumer,
)
from src.modules.referral.domain.policies import (
    CapsPolicy,
    ReferralProgrammePolicy,
    RewardPolicy,
    TierPolicy,
)
from src.modules.referral.domain.ports import (
    ICodeGenerator,
    IReferralCodeRepository,
)
from src.modules.referral.domain.value_objects import LoyaltyBalanceKind
from src.modules.referral.infrastructure.repositories.loyalty_ledger import (
    SqlLoyaltyLedger,
)
from src.modules.referral.infrastructure.repositories.referral_code_repository import (
    ReferralCodeRepository,
)
from src.modules.referral.infrastructure.services.code_generator import (
    NanoidCodeGenerator,
)
from shared.ledger import ILedger


class ReferralProvider(Provider):
    """Dishka provider for referral domain policies, repositories, and handlers."""

    # --- Policies (immutable, APP-scope) ----------------------------------

    @provide(scope=Scope.APP)
    def programme_policy(self) -> ReferralProgrammePolicy:
        return ReferralProgrammePolicy()

    @provide(scope=Scope.APP)
    def tier_policy(self, programme: ReferralProgrammePolicy) -> TierPolicy:
        return TierPolicy(programme=programme)

    @provide(scope=Scope.APP)
    def reward_policy(self, programme: ReferralProgrammePolicy) -> RewardPolicy:
        return RewardPolicy(programme=programme)

    @provide(scope=Scope.APP)
    def caps_policy(self, programme: ReferralProgrammePolicy) -> CapsPolicy:
        return CapsPolicy(programme=programme)

    # --- Code generator (APP-scope, stateless) ----------------------------

    code_generator = provide(
        NanoidCodeGenerator, scope=Scope.APP, provides=ICodeGenerator
    )

    # --- Repositories (REQUEST-scope, session-bound) ----------------------

    code_repo = provide(
        ReferralCodeRepository,
        scope=Scope.REQUEST,
        provides=IReferralCodeRepository,
    )

    # --- Ledger consumer (REQUEST-scope, session-bound) -------------------
    # First concrete consumer of the shared ledger kernel (PR-6a / ADR-007).
    # Persists LoyaltyAccountModel + LoyaltyTransactionModel atomically and
    # emits LedgerTransactionPostedEvent through the outbox. Pattern
    # reference for any future ledger consumer (cashback, supplier
    # payouts, refund pool).
    loyalty_ledger = provide(
        SqlLoyaltyLedger,
        scope=Scope.REQUEST,
        provides=ILedger[LoyaltyBalanceKind],
    )

    # --- Command handlers (REQUEST-scope) ---------------------------------

    issue_referral_code_handler = provide(IssueReferralCodeHandler, scope=Scope.REQUEST)

    # --- Consumers (REQUEST-scope) ----------------------------------------

    issue_on_identity_registered = provide(
        IssueCodeOnIdentityRegisteredConsumer, scope=Scope.REQUEST
    )
    issue_on_linked_account_created = provide(
        IssueCodeOnLinkedAccountCreatedConsumer, scope=Scope.REQUEST
    )
