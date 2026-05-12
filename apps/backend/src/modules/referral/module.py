"""Bootstrap manifest for the referral bounded context.

Phase-1 skeleton: only the policy provider and (future) tasks module
are wired here. Customer / admin routers and consumers join in
subsequent PRs.
"""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.referral.infrastructure.provider import ReferralProvider

REFERRAL_MODULE = ModuleManifest(
    name="referral",
    providers=(ReferralProvider(),),
    task_modules=("src.modules.referral.infrastructure.tasks",),
)
