"""Bootstrap manifest for the image bounded context.

Consolidated from the standalone ``image_backend`` microservice into a
main-backend module per CEO directive 2026-05-08 (β: hard cutover,
no parallel period). The legacy microservice's ``media`` records are
not migrated (D2.c — accept image-loss for existing rows).
"""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.image.infrastructure.provider import ImageProvider
from src.modules.image.presentation.router_admin import media_admin_router

IMAGE_MODULE = ModuleManifest(
    name="image",
    providers=(ImageProvider(),),
    admin_routers=(media_admin_router,),
    task_modules=("src.modules.image.infrastructure.tasks",),
)
