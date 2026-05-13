"""Bootstrap manifest for the activity bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.activity.infrastructure.provider import ActivityProvider
from src.modules.activity.presentation.router_admin import activity_admin_router

ACTIVITY_MODULE = ModuleManifest(
    name="activity",
    providers=(ActivityProvider(),),
    admin_routers=(activity_admin_router,),
    task_modules=("src.modules.activity.infrastructure.tasks",),
)
