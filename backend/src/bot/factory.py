"""Bot and Dispatcher factory.

Creates and wires the Aiogram Bot, Dispatcher, FSM storage,
middleware chain, routers, and Dishka DI integration.
"""

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka

from src.bootstrap.config import Settings
from src.bot.handlers.registry import get_all_routers
from src.bot.middlewares.logging import LoggingMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware

logger = structlog.get_logger(__name__)


def create_bot(settings: Settings) -> Bot:
    """Create the Aiogram Bot instance with default HTML parse mode."""
    return Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def _create_fsm_storage(settings: Settings) -> RedisStorage:
    """Create Redis-backed FSM storage from settings.

    Uses its own Redis connection (not from DI) because the storage
    must exist before the Dispatcher is created.
    """
    return RedisStorage.from_url(
        url=settings.redis_url,
        key_builder=DefaultKeyBuilder(
            prefix="fsm",
            separator=":",
            with_bot_id=True,
            with_destiny=True,
        ),
        state_ttl=settings.FSM_STATE_TTL,
        data_ttl=settings.FSM_DATA_TTL,
    )


def create_dispatcher(
    settings: Settings,
    container: AsyncContainer,
) -> Dispatcher:
    """Create and configure the Dispatcher.

    Wiring order:
    1. FSM storage (Redis)
    2. Middleware chain (outer → inner)
    3. Routers (priority order)
    4. Dishka DI
    5. Lifecycle hooks
    """
    storage = _create_fsm_storage(settings)
    dp = Dispatcher(storage=storage)

    # -- Middleware chain (order matters!) -------------------------------------
    # 1. Logging — outermost, captures everything
    dp.update.outer_middleware(LoggingMiddleware())
    # 2. Throttling — after logging, before handlers
    dp.message.middleware(ThrottlingMiddleware(throttle_rate=settings.THROTTLE_RATE))

    # -- Routers --------------------------------------------------------------
    for router in get_all_routers():
        dp.include_router(router)

    # -- Dishka DI ------------------------------------------------------------
    setup_dishka(container=container, router=dp, auto_inject=True)

    # -- Lifecycle hooks ------------------------------------------------------
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)

    return dp


async def _on_startup(bot: Bot) -> None:
    """Called when the dispatcher starts polling/webhook."""
    bot_info = await bot.me()
    logger.info("bot_started", username=bot_info.username, id=bot_info.id)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Перезапустить бота"),
            BotCommand(command="help", description="Список команд"),
            BotCommand(command="cancel", description="Отменить действие"),
        ],
        scope=BotCommandScopeDefault(),
    )


async def _on_shutdown(bot: Bot) -> None:
    """Called when the dispatcher is shutting down."""
    bot_info = await bot.me()
    logger.info("bot_stopped", username=bot_info.username)
