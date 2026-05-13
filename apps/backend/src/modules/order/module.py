"""Bootstrap manifest for the order bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.order.infrastructure.provider import OrderProvider
from src.modules.order.presentation.router_admin import admin_order_router
from src.modules.order.presentation.router_orders import order_router
from src.modules.order.presentation.router_webhooks import dobropost_webhook_router

ORDER_MODULE = ModuleManifest(
    name="order",
    providers=(OrderProvider(),),
    customer_routers=(order_router,),
    admin_routers=(admin_order_router,),
    webhook_routers=(dobropost_webhook_router,),
    task_modules=("src.modules.order.infrastructure.tasks",),
)
