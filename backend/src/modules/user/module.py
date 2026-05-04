"""Bootstrap manifest for the user (Customer / StaffMember PII) bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.user.infrastructure.provider import ProfileProvider
from src.modules.user.presentation.router_profile import profile_router

USER_MODULE = ModuleManifest(
    name="user",
    providers=(ProfileProvider(),),
    customer_routers=(profile_router,),
    task_modules=("src.modules.user.application.consumers.identity_events",),
)
