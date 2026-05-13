"""Bootstrap manifest for the supplier bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.supplier.infrastructure.provider import SupplierProvider
from src.modules.supplier.presentation.router_admin import supplier_admin_router

SUPPLIER_MODULE = ModuleManifest(
    name="supplier",
    providers=(SupplierProvider(),),
    admin_routers=(supplier_admin_router,),
)
