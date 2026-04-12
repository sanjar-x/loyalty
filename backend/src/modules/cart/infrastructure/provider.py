"""
Dishka IoC provider for the Cart bounded context.

Registers repository implementations, adapters, and command/query handlers
into the request-scoped DI container.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.cart.application.commands.add_item import AddItemHandler
from src.modules.cart.application.commands.cancel_checkout import CancelCheckoutHandler
from src.modules.cart.application.commands.clear_cart import ClearCartHandler
from src.modules.cart.application.commands.confirm_checkout import (
    ConfirmCheckoutHandler,
)
from src.modules.cart.application.commands.initiate_checkout import (
    InitiateCheckoutHandler,
)
from src.modules.cart.application.commands.merge_carts import MergeCartsHandler
from src.modules.cart.application.commands.remove_item import RemoveItemHandler
from src.modules.cart.application.commands.update_quantity import UpdateQuantityHandler
from src.modules.cart.application.queries.get_cart import GetCartHandler
from src.modules.cart.application.queries.get_cart_summary import GetCartSummaryHandler
from src.modules.cart.domain.interfaces import (
    ICartRepository,
    IOrderCreationService,
    IPickupPointReadService,
    ISkuReadService,
)
from src.modules.cart.infrastructure.adapters.catalog_adapter import CatalogSkuAdapter
from src.modules.cart.infrastructure.adapters.order_adapter import OrderCreationStub
from src.modules.cart.infrastructure.adapters.pickup_point_adapter import (
    StubPickupPointAdapter,
)
from src.modules.cart.infrastructure.repositories.cart_repository import CartRepository


class CartProvider(Provider):
    """DI provider for cart repositories, adapters, and handlers."""

    # --- Repositories ---
    cart_repo: CompositeDependencySource = provide(
        CartRepository, scope=Scope.REQUEST, provides=ICartRepository
    )

    # --- Adapters (ACL) ---
    sku_read_service: CompositeDependencySource = provide(
        CatalogSkuAdapter, scope=Scope.REQUEST, provides=ISkuReadService
    )
    pickup_point_service: CompositeDependencySource = provide(
        StubPickupPointAdapter, scope=Scope.REQUEST, provides=IPickupPointReadService
    )
    order_creation_service: CompositeDependencySource = provide(
        OrderCreationStub, scope=Scope.REQUEST, provides=IOrderCreationService
    )

    # --- Command handlers ---
    add_item_handler: CompositeDependencySource = provide(
        AddItemHandler, scope=Scope.REQUEST
    )
    remove_item_handler: CompositeDependencySource = provide(
        RemoveItemHandler, scope=Scope.REQUEST
    )
    update_quantity_handler: CompositeDependencySource = provide(
        UpdateQuantityHandler, scope=Scope.REQUEST
    )
    clear_cart_handler: CompositeDependencySource = provide(
        ClearCartHandler, scope=Scope.REQUEST
    )
    initiate_checkout_handler: CompositeDependencySource = provide(
        InitiateCheckoutHandler, scope=Scope.REQUEST
    )
    confirm_checkout_handler: CompositeDependencySource = provide(
        ConfirmCheckoutHandler, scope=Scope.REQUEST
    )
    cancel_checkout_handler: CompositeDependencySource = provide(
        CancelCheckoutHandler, scope=Scope.REQUEST
    )
    merge_carts_handler: CompositeDependencySource = provide(
        MergeCartsHandler, scope=Scope.REQUEST
    )

    # --- Query handlers ---
    get_cart_handler: CompositeDependencySource = provide(
        GetCartHandler, scope=Scope.REQUEST
    )
    get_cart_summary_handler: CompositeDependencySource = provide(
        GetCartSummaryHandler, scope=Scope.REQUEST
    )
