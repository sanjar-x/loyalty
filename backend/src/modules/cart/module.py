"""Bootstrap manifest for the cart bounded context."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.cart.infrastructure.provider import CartProvider
from src.modules.cart.presentation.router_customer import cart_router

CART_MODULE = ModuleManifest(
    name="cart",
    providers=(CartProvider(),),
    customer_routers=(cart_router,),
)
