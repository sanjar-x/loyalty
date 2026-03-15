# src/infrastructure/database/provider.py
from collections.abc import AsyncIterable

import structlog
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
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
    async def engine(self) -> AsyncIterable[AsyncEngine]:
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

        yield engine

        logger.info("Закрытие пула соединений с БД (Engine Dispose)...")
        await engine.dispose()

    @provide(scope=Scope.APP)
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @provide(scope=Scope.REQUEST)
    async def session(
        self, maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with maker() as session:
            yield session

    uow: CompositeDependencySource = provide(
        source=UnitOfWork, scope=Scope.REQUEST, provides=IUnitOfWork
    )
