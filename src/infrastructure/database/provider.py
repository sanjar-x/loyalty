"""Dishka dependency provider for the async SQLAlchemy database stack.

Manages the lifecycle of the ``AsyncEngine``, ``async_sessionmaker``,
per-request ``AsyncSession``, and ``IUnitOfWork`` binding.
"""

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
        "application_name": "enterprise_api",
        "statement_timeout": "30000",
        "idle_in_transaction_session_timeout": "60000",
        "timezone": "UTC",
    }
}


class DatabaseProvider(Provider):
    """Dishka provider that supplies the async database engine, session factory, and UoW."""

    @provide(scope=Scope.APP)
    async def engine(self) -> AsyncIterable[AsyncEngine]:
        """Create and yield an ``AsyncEngine`` with a connection pool.

        The engine is disposed when the application scope shuts down.

        Yields:
            AsyncEngine: A configured SQLAlchemy async engine.
        """
        logger.info("Initializing database connection pool (AsyncEngine)...")
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

        logger.info("Disposing database connection pool (Engine Dispose)...")
        await engine.dispose()

    @provide(scope=Scope.APP)
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        """Build an ``async_sessionmaker`` bound to the engine.

        Args:
            engine: The application-scoped async engine.

        Returns:
            A session factory configured with ``autoflush=False`` and
            ``expire_on_commit=False``.
        """
        return async_sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @provide(scope=Scope.REQUEST)
    async def session(self, maker: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        """Provide a per-request ``AsyncSession``.

        Args:
            maker: The application-scoped session factory.

        Yields:
            AsyncSession: A new session that is closed at the end of the request.
        """
        async with maker() as session:
            yield session

    uow: CompositeDependencySource = provide(
        source=UnitOfWork, scope=Scope.REQUEST, provides=IUnitOfWork
    )
