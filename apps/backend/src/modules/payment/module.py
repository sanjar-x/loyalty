"""Bootstrap manifest for the payment bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.payment.infrastructure.provider import PaymentProviderDI
from src.modules.payment.presentation.router_payments import payment_router
from src.modules.payment.presentation.router_webhooks import payment_webhook_router

PAYMENT_MODULE = ModuleManifest(
    name="payment",
    providers=(PaymentProviderDI(),),
    customer_routers=(payment_router,),
    webhook_routers=(payment_webhook_router,),
    task_modules=("src.modules.payment.infrastructure.tasks",),
)
