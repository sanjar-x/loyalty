"""
Dishka IoC providers for the Logistics bounded context.

Registers repository implementations, registry, routing policy,
and command/query handlers into the DI container.
"""

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.logistics.application.commands.book_shipment import (
    BookShipmentHandler,
)
from src.modules.logistics.application.commands.cancel_intake import (
    CancelIntakeHandler,
)
from src.modules.logistics.application.commands.cancel_shipment import (
    CancelShipmentHandler,
)
from src.modules.logistics.application.commands.create_cross_border_shipment import (
    CreateCrossBorderShipmentHandler,
)
from src.modules.logistics.application.commands.create_intake import (
    CreateIntakeHandler,
)
from src.modules.logistics.application.commands.create_shipment import (
    CreateShipmentHandler,
)
from src.modules.logistics.application.commands.edit_order import (
    EditOrderHandler,
)
from src.modules.logistics.application.commands.edit_order_items import (
    EditOrderItemsHandler,
)
from src.modules.logistics.application.commands.edit_order_packages import (
    EditOrderPackagesHandler,
)
from src.modules.logistics.application.commands.handle_dobropost_passport_validation import (
    HandleDobroPostPassportValidationHandler,
)
from src.modules.logistics.application.commands.ingest_tracking import (
    IngestTrackingHandler,
)
from src.modules.logistics.application.commands.manage_provider_accounts import (
    CreateProviderAccountHandler,
    DeleteProviderAccountHandler,
    SetProviderAccountActiveHandler,
    UpdateProviderAccountHandler,
)
from src.modules.logistics.application.commands.register_client_return import (
    RegisterClientReturnHandler,
)
from src.modules.logistics.application.commands.register_refusal import (
    RegisterRefusalHandler,
)
from src.modules.logistics.application.commands.remove_order_items import (
    RemoveOrderItemsHandler,
)
from src.modules.logistics.application.queries.calculate_rates import (
    CalculateRatesHandler,
)
from src.modules.logistics.application.queries.check_reverse_availability import (
    CheckReverseAvailabilityHandler,
)
from src.modules.logistics.application.queries.get_actual_delivery_info import (
    GetActualDeliveryInfoHandler,
)
from src.modules.logistics.application.queries.get_available_intake_days import (
    GetAvailableIntakeDaysHandler,
)
from src.modules.logistics.application.queries.get_delivery_intervals import (
    GetDeliveryIntervalsHandler,
)
from src.modules.logistics.application.queries.get_edit_task_status import (
    GetEditTaskStatusHandler,
)
from src.modules.logistics.application.queries.get_estimated_delivery_intervals import (
    GetEstimatedDeliveryIntervalsHandler,
)
from src.modules.logistics.application.queries.get_intake import (
    GetIntakeHandler,
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
from src.modules.logistics.application.queries.list_provider_accounts import (
    GetProviderAccountHandler,
    ListProviderAccountsHandler,
)
from src.modules.logistics.application.queries.quote_for_pickup_point import (
    QuoteForPickupPointHandler,
)
from src.modules.logistics.domain.interfaces import (
    IDeliveryQuoteRepository,
    IOriginAddressResolver,
    IPickupPointResolver,
    IProviderAccountRepository,
    IProviderRoutingPolicy,
    IShipmentRepository,
    IShippingProviderRegistry,
    ISkuWeightResolver,
)
from src.modules.logistics.infrastructure.adapters.origin_address_resolver import (
    ProviderAccountOriginResolver,
)
from src.modules.logistics.infrastructure.adapters.pickup_point_cache import (
    RedisPickupPointResolver,
)
from src.modules.logistics.infrastructure.adapters.pricing_weight_adapter import (
    PricingWeightAdapter,
)
from src.modules.logistics.infrastructure.bootstrap import bootstrap_registry
from src.modules.logistics.infrastructure.repositories.delivery_quote import (
    DeliveryQuoteRepository,
)
from src.modules.logistics.infrastructure.repositories.provider_account import (
    ProviderAccountRepository,
)
from src.modules.logistics.infrastructure.repositories.shipment import (
    ShipmentRepository,
)
from src.modules.logistics.infrastructure.services.registry_refresh import (
    ProviderRegistryRefresher,
)
from src.modules.logistics.infrastructure.services.routing import (
    DefaultProviderRoutingPolicy,
)


class LogisticsInfraProvider(Provider):
    """DI provider for logistics infrastructure."""

    shipment_repo: CompositeDependencySource = provide(
        ShipmentRepository, scope=Scope.REQUEST, provides=IShipmentRepository
    )
    quote_repo: CompositeDependencySource = provide(
        DeliveryQuoteRepository,
        scope=Scope.REQUEST,
        provides=IDeliveryQuoteRepository,
    )
    provider_account_repo: CompositeDependencySource = provide(
        ProviderAccountRepository,
        scope=Scope.REQUEST,
        provides=IProviderAccountRepository,
    )
    routing_policy: CompositeDependencySource = provide(
        DefaultProviderRoutingPolicy,
        scope=Scope.APP,
        provides=IProviderRoutingPolicy,
    )
    sku_weight_resolver: CompositeDependencySource = provide(
        PricingWeightAdapter,
        scope=Scope.REQUEST,
        provides=ISkuWeightResolver,
    )
    pickup_point_resolver: CompositeDependencySource = provide(
        RedisPickupPointResolver,
        scope=Scope.REQUEST,
        provides=IPickupPointResolver,
    )
    origin_address_resolver: CompositeDependencySource = provide(
        ProviderAccountOriginResolver,
        scope=Scope.REQUEST,
        provides=IOriginAddressResolver,
    )

    @provide(scope=Scope.APP, provides=IShippingProviderRegistry)
    async def registry(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[IShippingProviderRegistry]:
        # Generator scope so Dishka calls registry.close() at app
        # shutdown — this releases the cached httpx.AsyncClient pools
        # in CDEK / Yandex factories instead of leaking sockets.
        registry = await bootstrap_registry(session_factory)
        try:
            yield registry
        finally:
            await registry.close()

    registry_refresher: CompositeDependencySource = provide(
        ProviderRegistryRefresher, scope=Scope.REQUEST
    )


class LogisticsCommandProvider(Provider):
    """DI provider for logistics command handlers."""

    create_shipment: CompositeDependencySource = provide(
        CreateShipmentHandler, scope=Scope.REQUEST
    )
    create_cross_border_shipment: CompositeDependencySource = provide(
        CreateCrossBorderShipmentHandler, scope=Scope.REQUEST
    )
    handle_dobropost_passport_validation: CompositeDependencySource = provide(
        HandleDobroPostPassportValidationHandler, scope=Scope.REQUEST
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
    create_intake: CompositeDependencySource = provide(
        CreateIntakeHandler, scope=Scope.REQUEST
    )
    cancel_intake: CompositeDependencySource = provide(
        CancelIntakeHandler, scope=Scope.REQUEST
    )
    register_client_return: CompositeDependencySource = provide(
        RegisterClientReturnHandler, scope=Scope.REQUEST
    )
    register_refusal: CompositeDependencySource = provide(
        RegisterRefusalHandler, scope=Scope.REQUEST
    )
    edit_order: CompositeDependencySource = provide(
        EditOrderHandler, scope=Scope.REQUEST
    )
    edit_order_packages: CompositeDependencySource = provide(
        EditOrderPackagesHandler, scope=Scope.REQUEST
    )
    edit_order_items: CompositeDependencySource = provide(
        EditOrderItemsHandler, scope=Scope.REQUEST
    )
    remove_order_items: CompositeDependencySource = provide(
        RemoveOrderItemsHandler, scope=Scope.REQUEST
    )
    create_provider_account: CompositeDependencySource = provide(
        CreateProviderAccountHandler, scope=Scope.REQUEST
    )
    update_provider_account: CompositeDependencySource = provide(
        UpdateProviderAccountHandler, scope=Scope.REQUEST
    )
    set_provider_account_active: CompositeDependencySource = provide(
        SetProviderAccountActiveHandler, scope=Scope.REQUEST
    )
    delete_provider_account: CompositeDependencySource = provide(
        DeleteProviderAccountHandler, scope=Scope.REQUEST
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
    quote_for_pickup_point: CompositeDependencySource = provide(
        QuoteForPickupPointHandler, scope=Scope.REQUEST
    )
    get_shipment: CompositeDependencySource = provide(
        GetShipmentHandler, scope=Scope.REQUEST
    )
    get_available_intake_days: CompositeDependencySource = provide(
        GetAvailableIntakeDaysHandler, scope=Scope.REQUEST
    )
    get_intake: CompositeDependencySource = provide(
        GetIntakeHandler, scope=Scope.REQUEST
    )
    get_delivery_intervals: CompositeDependencySource = provide(
        GetDeliveryIntervalsHandler, scope=Scope.REQUEST
    )
    get_estimated_delivery_intervals: CompositeDependencySource = provide(
        GetEstimatedDeliveryIntervalsHandler, scope=Scope.REQUEST
    )
    check_reverse_availability: CompositeDependencySource = provide(
        CheckReverseAvailabilityHandler, scope=Scope.REQUEST
    )
    get_edit_task_status: CompositeDependencySource = provide(
        GetEditTaskStatusHandler, scope=Scope.REQUEST
    )
    get_actual_delivery_info: CompositeDependencySource = provide(
        GetActualDeliveryInfoHandler, scope=Scope.REQUEST
    )
    list_provider_accounts: CompositeDependencySource = provide(
        ListProviderAccountsHandler, scope=Scope.REQUEST
    )
    get_provider_account: CompositeDependencySource = provide(
        GetProviderAccountHandler, scope=Scope.REQUEST
    )
