"""Dishka IoC provider for the Order bounded context — Loyality FSM."""

from collections.abc import AsyncIterator

from aiogram import Bot
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import settings
from src.modules.order.application.commands.admin_create_walk_in_order import (
    AdminCreateWalkInOrderHandler,
)
from src.modules.order.application.commands.cancel_order import CancelOrderHandler
from src.modules.order.application.commands.change_pickup_point import (
    ChangePickupPointHandler,
)
from src.modules.order.application.commands.close_order import CloseOrderHandler
from src.modules.order.application.commands.create_buy_now_order import (
    CreateBuyNowOrderHandler,
)
from src.modules.order.application.commands.create_order_from_cart import (
    CreateOrderFromCartHandler,
)
from src.modules.order.application.commands.hold_order import HoldOrderHandler
from src.modules.order.application.commands.ingest_dobropost_webhook import (
    IngestDobroPostWebhookHandler,
)
from src.modules.order.application.commands.mark_order_arrived_in_ru import (
    MarkOrderArrivedInRuHandler,
)
from src.modules.order.application.commands.mark_order_awaiting_pickup import (
    MarkOrderAwaitingPickupHandler,
)
from src.modules.order.application.commands.mark_order_delivered import (
    MarkOrderDeliveredHandler,
)
from src.modules.order.application.commands.mark_order_in_last_mile import (
    MarkOrderInLastMileHandler,
)
from src.modules.order.application.commands.mark_order_paid import (
    MarkOrderPaidHandler,
)
from src.modules.order.application.commands.procure_order import ProcureOrderHandler
from src.modules.order.application.commands.refresh_recipient_snapshot import (
    RefreshRecipientSnapshotHandler,
)
from src.modules.order.application.commands.resume_order import ResumeOrderHandler
from src.modules.order.application.commands.return_flow import (
    MarkOrderNotDeliveredHandler,
    MarkOrderReturningToWarehouseHandler,
    MarkReturnReceivedHandler,
    RegisterReturnHandler,
)
from src.modules.order.application.consumers.logistics_events import (
    DobroPostPassportInvalidConsumer,
    DobroPostStatusUpdatedConsumer,
    RussianCarrierTrackingConsumer,
)
from src.modules.order.application.consumers.order_procured import (
    OrderProcuredConsumer,
)
from src.modules.order.application.consumers.payment_events import (
    PaymentCapturedConsumer,
    PaymentFailedConsumer,
)
from src.modules.order.application.consumers.telegram_notifications import (
    TelegramOrderNotifier,
)
from src.modules.order.application.ports import (
    ICatalogSkuPriceReader,
    IDobroPostGateway,
    IDobroPostShipmentMappingRepository,
    IPaymentGateway,
    IPriceOverrideAuditWriter,
    IRussianCarrierGateway,
    ITelegramChatLookup,
    ITelegramNotifier,
    IWalkInIdentityProvisioner,
)
from src.modules.order.application.queries.admin_list_orders import (
    AdminGetOrderHandler,
    AdminListOrdersHandler,
)
from src.modules.order.application.queries.get_order import GetOrderHandler
from src.modules.order.application.queries.get_order_state_history import (
    GetOrderStateHistoryHandler,
)
from src.modules.order.application.queries.get_order_tracking import (
    GetOrderTrackingHandler,
)
from src.modules.order.application.queries.list_my_orders import ListMyOrdersHandler
from src.modules.order.domain.interfaces import (
    ICartSnapshotReader,
    IDeliveryQuoteLookup,
    IOrderRepository,
    IOrderStateHistoryWriter,
    IRecipientLookup,
)
from src.modules.order.infrastructure.adapters.cart_snapshot_reader import (
    CartSnapshotReader,
)
from src.modules.order.infrastructure.adapters.catalog_sku_reader import (
    CatalogSkuPriceReader,
)
from src.modules.order.infrastructure.adapters.delivery_quote_adapter import (
    DeliveryQuoteAdapter,
)
from src.modules.order.infrastructure.adapters.dobropost_client import (
    DobroPostHttpClient,
)
from src.modules.order.infrastructure.adapters.dobropost_gateway import (
    DobroPostGatewayReal,
    DobroPostGatewayStub,
)
from src.modules.order.infrastructure.adapters.payment_gateway import PaymentGateway
from src.modules.order.infrastructure.adapters.recipient_lookup import (
    RecipientLookupAdapter,
)
from src.modules.order.infrastructure.adapters.russian_carrier_gateway import (
    RussianCarrierGatewayStub,
)
from src.modules.order.infrastructure.adapters.telegram_chat_lookup import (
    TelegramChatLookup,
)
from src.modules.order.infrastructure.adapters.telegram_notifier import (
    AiogramTelegramNotifier,
)
from src.modules.order.infrastructure.adapters.walk_in_identity_provisioner import (
    WalkInIdentityProvisioner,
)
from src.modules.order.infrastructure.repositories.dobropost_shipment_mapping_repository import (
    DobroPostShipmentMappingRepository,
)
from src.modules.order.infrastructure.repositories.order_repository import (
    OrderRepository,
)
from src.modules.order.infrastructure.repositories.price_override_audit_repository import (
    PriceOverrideAuditRepository,
)
from src.modules.order.infrastructure.repositories.state_history_writer import (
    OrderStateHistoryWriter,
)


class OrderProvider(Provider):
    # --- Repositories / stores ---
    order_repo: CompositeDependencySource = provide(
        OrderRepository, scope=Scope.REQUEST, provides=IOrderRepository
    )
    # NOTE -- idempotency_store / inbox_store moved to the framework-shared
    # ``IdempotencyProvider`` (registered in ``src.bootstrap.container``)
    # per REFACT-001 PR-3a + PR-3b. Order consumes the same
    # ``IIdempotencyStore`` / ``IInboxStore`` ports as every other module.
    dpsm_repo: CompositeDependencySource = provide(
        DobroPostShipmentMappingRepository,
        scope=Scope.REQUEST,
        provides=IDobroPostShipmentMappingRepository,
    )
    state_history_writer: CompositeDependencySource = provide(
        OrderStateHistoryWriter,
        scope=Scope.REQUEST,
        provides=IOrderStateHistoryWriter,
    )

    # --- ACL adapters ---
    cart_snapshot_reader: CompositeDependencySource = provide(
        CartSnapshotReader, scope=Scope.REQUEST, provides=ICartSnapshotReader
    )
    payment_gateway: CompositeDependencySource = provide(
        PaymentGateway, scope=Scope.REQUEST, provides=IPaymentGateway
    )

    # DobroPost: stub vs real chosen by settings.DOBROPOST_USE_STUB.
    # Async-generator factory ensures the underlying httpx client is
    # closed when the Dishka APP container shuts down (lifespan-end).
    @provide(scope=Scope.APP)
    async def dobropost_http_client(self) -> AsyncIterator[DobroPostHttpClient]:
        client = DobroPostHttpClient()
        try:
            yield client
        finally:
            await client.aclose()

    @provide(scope=Scope.REQUEST)
    def dobropost_gateway(
        self,
        client: DobroPostHttpClient,
        session: AsyncSession,
        mapping_repo: IDobroPostShipmentMappingRepository,
    ) -> IDobroPostGateway:
        import structlog

        from src.infrastructure.logging.adapter import StructlogAdapter

        if settings.DOBROPOST_USE_STUB:
            return DobroPostGatewayStub(
                mapping_repo=mapping_repo,
                logger=StructlogAdapter(structlog.get_logger("dobropost.stub")),
            )
        return DobroPostGatewayReal(
            client=client,
            session=session,
            mapping_repo=mapping_repo,
            logger=StructlogAdapter(structlog.get_logger("dobropost.real")),
        )

    russian_carrier_gateway: CompositeDependencySource = provide(
        RussianCarrierGatewayStub,
        scope=Scope.REQUEST,
        provides=IRussianCarrierGateway,
    )
    recipient_lookup: CompositeDependencySource = provide(
        RecipientLookupAdapter,
        scope=Scope.REQUEST,
        provides=IRecipientLookup,
    )
    delivery_quote_lookup: CompositeDependencySource = provide(
        DeliveryQuoteAdapter,
        scope=Scope.REQUEST,
        provides=IDeliveryQuoteLookup,
    )
    # Walk-in admin-create-order ACLs (whitelisted in tests/architecture
    # as ``("order","catalog")``, ``("order","identity")``, ``("order","user")``).
    catalog_sku_reader: CompositeDependencySource = provide(
        CatalogSkuPriceReader,
        scope=Scope.REQUEST,
        provides=ICatalogSkuPriceReader,
    )
    walk_in_identity_provisioner: CompositeDependencySource = provide(
        WalkInIdentityProvisioner,
        scope=Scope.REQUEST,
        provides=IWalkInIdentityProvisioner,
    )
    price_override_audit_writer: CompositeDependencySource = provide(
        PriceOverrideAuditRepository,
        scope=Scope.REQUEST,
        provides=IPriceOverrideAuditWriter,
    )

    # --- Command handlers ---
    create_order_handler: CompositeDependencySource = provide(
        CreateOrderFromCartHandler, scope=Scope.REQUEST
    )
    create_buy_now_order_handler: CompositeDependencySource = provide(
        CreateBuyNowOrderHandler, scope=Scope.REQUEST
    )
    admin_create_walk_in_order_handler: CompositeDependencySource = provide(
        AdminCreateWalkInOrderHandler, scope=Scope.REQUEST
    )
    mark_paid_handler: CompositeDependencySource = provide(
        MarkOrderPaidHandler, scope=Scope.REQUEST
    )
    procure_handler: CompositeDependencySource = provide(
        ProcureOrderHandler, scope=Scope.REQUEST
    )
    refresh_recipient_handler: CompositeDependencySource = provide(
        RefreshRecipientSnapshotHandler, scope=Scope.REQUEST
    )
    mark_arrived_handler: CompositeDependencySource = provide(
        MarkOrderArrivedInRuHandler, scope=Scope.REQUEST
    )
    mark_in_last_mile_handler: CompositeDependencySource = provide(
        MarkOrderInLastMileHandler, scope=Scope.REQUEST
    )
    mark_awaiting_pickup_handler: CompositeDependencySource = provide(
        MarkOrderAwaitingPickupHandler, scope=Scope.REQUEST
    )
    mark_delivered_handler: CompositeDependencySource = provide(
        MarkOrderDeliveredHandler, scope=Scope.REQUEST
    )
    close_handler: CompositeDependencySource = provide(
        CloseOrderHandler, scope=Scope.REQUEST
    )
    hold_handler: CompositeDependencySource = provide(
        HoldOrderHandler, scope=Scope.REQUEST
    )
    resume_handler: CompositeDependencySource = provide(
        ResumeOrderHandler, scope=Scope.REQUEST
    )
    cancel_handler: CompositeDependencySource = provide(
        CancelOrderHandler, scope=Scope.REQUEST
    )
    register_return_handler: CompositeDependencySource = provide(
        RegisterReturnHandler, scope=Scope.REQUEST
    )
    mark_return_received_handler: CompositeDependencySource = provide(
        MarkReturnReceivedHandler, scope=Scope.REQUEST
    )
    mark_returning_handler: CompositeDependencySource = provide(
        MarkOrderReturningToWarehouseHandler, scope=Scope.REQUEST
    )
    mark_not_delivered_handler: CompositeDependencySource = provide(
        MarkOrderNotDeliveredHandler, scope=Scope.REQUEST
    )
    change_pickup_handler: CompositeDependencySource = provide(
        ChangePickupPointHandler, scope=Scope.REQUEST
    )
    ingest_dobropost_webhook_handler: CompositeDependencySource = provide(
        IngestDobroPostWebhookHandler, scope=Scope.REQUEST
    )

    # --- Consumers ---
    payment_captured_consumer: CompositeDependencySource = provide(
        PaymentCapturedConsumer, scope=Scope.REQUEST
    )
    payment_failed_consumer: CompositeDependencySource = provide(
        PaymentFailedConsumer, scope=Scope.REQUEST
    )
    dobropost_status_consumer: CompositeDependencySource = provide(
        DobroPostStatusUpdatedConsumer, scope=Scope.REQUEST
    )
    dobropost_passport_consumer: CompositeDependencySource = provide(
        DobroPostPassportInvalidConsumer, scope=Scope.REQUEST
    )
    russian_carrier_consumer: CompositeDependencySource = provide(
        RussianCarrierTrackingConsumer, scope=Scope.REQUEST
    )
    order_procured_consumer: CompositeDependencySource = provide(
        OrderProcuredConsumer, scope=Scope.REQUEST
    )

    # T-2 / D3.1 — Telegram push for order lifecycle.
    telegram_chat_lookup: CompositeDependencySource = provide(
        TelegramChatLookup, scope=Scope.REQUEST, provides=ITelegramChatLookup
    )

    @provide(scope=Scope.APP)
    async def telegram_bot(self) -> AsyncIterator[Bot]:
        """Aiogram Bot with the platform ``BOT_TOKEN`` for outbound pushes.

        APP-scoped because the Bot owns an httpx ``AsyncClient`` pool —
        re-creating it per request would burn sockets. Closed at
        application shutdown via the generator finally-clause so
        Railway redeploys don't leak connections.
        """
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        bot = Bot(
            token=settings.BOT_TOKEN.get_secret_value(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            yield bot
        finally:
            await bot.session.close()

    @provide(scope=Scope.REQUEST)
    def telegram_notifier(self, bot: Bot) -> ITelegramNotifier:
        return AiogramTelegramNotifier(bot=bot)

    telegram_order_notifier: CompositeDependencySource = provide(
        TelegramOrderNotifier, scope=Scope.REQUEST
    )

    # --- Query handlers ---
    get_order_handler: CompositeDependencySource = provide(
        GetOrderHandler, scope=Scope.REQUEST
    )
    get_order_tracking_handler: CompositeDependencySource = provide(
        GetOrderTrackingHandler, scope=Scope.REQUEST
    )
    list_my_orders_handler: CompositeDependencySource = provide(
        ListMyOrdersHandler, scope=Scope.REQUEST
    )
    admin_get_order_handler: CompositeDependencySource = provide(
        AdminGetOrderHandler, scope=Scope.REQUEST
    )
    admin_list_orders_handler: CompositeDependencySource = provide(
        AdminListOrdersHandler, scope=Scope.REQUEST
    )
    state_history_handler: CompositeDependencySource = provide(
        GetOrderStateHistoryHandler, scope=Scope.REQUEST
    )
