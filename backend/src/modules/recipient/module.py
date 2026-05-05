"""Bootstrap manifest for the recipient bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.recipient.infrastructure.provider import RecipientProvider
from src.modules.recipient.presentation.router_recipients import recipient_router

RECIPIENT_MODULE = ModuleManifest(
    name="recipient",
    providers=(RecipientProvider(),),
    customer_routers=(recipient_router,),
)
