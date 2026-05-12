"""Bootstrap manifest for the logistics bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.logistics.infrastructure.provider import (
    LogisticsCommandProvider,
    LogisticsInfraProvider,
    LogisticsQueryProvider,
)
from src.modules.logistics.presentation.router_admin import logistics_admin_router
from src.modules.logistics.presentation.router_admin_shipments import (
    logistics_router as logistics_admin_shipments_router,
)
from src.modules.logistics.presentation.router_storefront import (
    logistics_storefront_router,
)
from src.modules.logistics.presentation.router_webhooks import webhook_router

LOGISTICS_MODULE = ModuleManifest(
    name="logistics",
    providers=(
        LogisticsInfraProvider(),
        LogisticsCommandProvider(),
        LogisticsQueryProvider(),
    ),
    customer_routers=(logistics_storefront_router,),
    admin_routers=(
        logistics_admin_router,
        logistics_admin_shipments_router,
    ),
    webhook_routers=(webhook_router,),
    task_modules=("src.modules.logistics.infrastructure.tasks",),
)
