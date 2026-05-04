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
from src.modules.referral.infrastructure.repositories.referral_code_repository import (
    ReferralCodeRepository,
)
from src.modules.referral.infrastructure.services.code_generator import (
    NanoidCodeGenerator,
)


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

    # --- Command handlers (REQUEST-scope) ---------------------------------

    issue_referral_code_handler = provide(IssueReferralCodeHandler, scope=Scope.REQUEST)

    # --- Consumers (REQUEST-scope) ----------------------------------------

    issue_on_identity_registered = provide(
        IssueCodeOnIdentityRegisteredConsumer, scope=Scope.REQUEST
    )
    issue_on_linked_account_created = provide(
        IssueCodeOnLinkedAccountCreatedConsumer, scope=Scope.REQUEST
    )
