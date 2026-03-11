# src\infrastructure\database\provider.py
from collections.abc import AsyncIterable

import structlog
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.bootstrap.config import settings
from src.infrastructure.database.uow import UnitOfWork
from src.shared.interfaces.uow import IUnitOfWork

# Инициализируем логер для этого модуля
logger = structlog.get_logger(__name__)

DBA_CONNECT_ARGS = {
    "server_settings": {
        "application_name": "loyality",
        "statement_timeout": "30000",
        "idle_in_transaction_session_timeout": "60000",
        "timezone": "UTC",
    }
}


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_engine(self) -> AsyncIterable[AsyncEngine]:
        logger.info("Инициализация пула соединений с БД (AsyncEngine)...")
        engine = create_async_engine(
            url=settings.database_url,
            echo=settings.DEBUG,
            execution_options={"isolation_level": "READ COMMITTED"},
            poolclass=AsyncAdaptedQueuePool,
            pool_size=15,
            max_overflow=10,
            pool_timeout=30.0,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_use_lifo=True,
            connect_args=DBA_CONNECT_ARGS,
        )

        # Отдаем движок контейнеру
        yield engine

        # Этот код выполнится при остановке приложения (Graceful Shutdown)
        logger.info("Закрытие пула соединений с БД (Engine Dispose)...")
        await engine.dispose()

    @provide(scope=Scope.APP)
    def provide_sessionmaker(
        self, engine: AsyncEngine
    ) -> async_sessionmaker[AsyncSession]:
        logger.debug("Создание фабрики сессий (async_sessionmaker)")
        return async_sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @provide(scope=Scope.REQUEST)
    async def provide_session(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        logger.debug("Открытие сессии БД для запроса")
        async with session_maker() as session:
            yield session
        logger.debug("Сессия БД закрыта и возвращена в пул")

    @provide(scope=Scope.REQUEST)
    def provide_uow(
        self,
        session: AsyncSession,
    ) -> IUnitOfWork:
        logger.debug("Инициализация UnitOfWork")
        return UnitOfWork(session=session)
