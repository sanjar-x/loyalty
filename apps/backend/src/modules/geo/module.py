"""Bootstrap manifest for the geo (reference data) bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.geo.infrastructure.provider import GeoProvider
from src.modules.geo.presentation.router_admin import geo_admin_router
from src.modules.geo.presentation.router_geo import geo_router

GEO_MODULE = ModuleManifest(
    name="geo",
    providers=(GeoProvider(),),
    customer_routers=(geo_router,),
    admin_routers=(geo_admin_router,),
)
