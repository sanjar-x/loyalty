"""Bootstrap manifest for the favorites bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.favorites.infrastructure.provider import FavoritesProvider
from src.modules.favorites.presentation.router_favorites import favorite_router

FAVORITES_MODULE = ModuleManifest(
    name="favorites",
    providers=(FavoritesProvider(),),
    customer_routers=(favorite_router,),
)
