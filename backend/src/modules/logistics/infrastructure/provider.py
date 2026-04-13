"""
Dishka IoC providers for the Logistics bounded context.

Registers repository implementations, registry, routing policy,
and command/query handlers into the DI container.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.logistics.application.commands.book_shipment import (
    BookShipmentHandler,
)
from src.modules.logistics.application.commands.cancel_shipment import (
    CancelShipmentHandler,
)
from src.modules.logistics.application.commands.create_shipment import (
    CreateShipmentHandler,
)
from src.modules.logistics.application.commands.ingest_tracking import (
    IngestTrackingHandler,
)
from src.modules.logistics.application.queries.calculate_rates import (
    CalculateRatesHandler,
)
from src.modules.logistics.application.queries.get_shipment import (
    GetShipmentHandler,
)
from src.modules.logistics.application.queries.get_tracking import (
    GetTrackingHandler,
)
from src.modules.logistics.application.queries.list_pickup_points import (
    ListPickupPointsHandler,
)
from src.modules.logistics.domain.interfaces import (
    IProviderRoutingPolicy,
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.infrastructure.registry import (
    ShippingProviderRegistry,
)
from src.modules.logistics.infrastructure.repositories.shipment import (
    ShipmentRepository,
)
from src.modules.logistics.infrastructure.routing import (
    DefaultProviderRoutingPolicy,
)


class LogisticsInfraProvider(Provider):
    """DI provider for logistics infrastructure."""

    shipment_repo: CompositeDependencySource = provide(
        ShipmentRepository, scope=Scope.REQUEST, provides=IShipmentRepository
    )
    registry: CompositeDependencySource = provide(
        ShippingProviderRegistry,
        scope=Scope.APP,
        provides=IShippingProviderRegistry,
    )
    routing_policy: CompositeDependencySource = provide(
        DefaultProviderRoutingPolicy,
        scope=Scope.APP,
        provides=IProviderRoutingPolicy,
    )


class LogisticsCommandProvider(Provider):
    """DI provider for logistics command handlers."""

    create_shipment: CompositeDependencySource = provide(
        CreateShipmentHandler, scope=Scope.REQUEST
    )
    book_shipment: CompositeDependencySource = provide(
        BookShipmentHandler, scope=Scope.REQUEST
    )
    cancel_shipment: CompositeDependencySource = provide(
        CancelShipmentHandler, scope=Scope.REQUEST
    )
    ingest_tracking: CompositeDependencySource = provide(
        IngestTrackingHandler, scope=Scope.REQUEST
    )


class LogisticsQueryProvider(Provider):
    """DI provider for logistics query handlers."""

    calculate_rates: CompositeDependencySource = provide(
        CalculateRatesHandler, scope=Scope.REQUEST
    )
    get_tracking: CompositeDependencySource = provide(
        GetTrackingHandler, scope=Scope.REQUEST
    )
    list_pickup_points: CompositeDependencySource = provide(
        ListPickupPointsHandler, scope=Scope.REQUEST
    )
    get_shipment: CompositeDependencySource = provide(
        GetShipmentHandler, scope=Scope.REQUEST
    )
