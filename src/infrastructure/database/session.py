# src/infrastructure/database/session.py
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.bootstrap.config import settings

logger: Any = structlog.get_logger(__name__)

DBA_CONNECT_ARGS = {
    "server_settings": {
        "application_name": "loyality",
        "statement_timeout": "30000",
        "idle_in_transaction_session_timeout": "60000",
        "timezone": "UTC",
    }
}

engine: AsyncEngine = create_async_engine(
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

async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def close_db_connection() -> None:
    logger.info("Закрытие пула соединений с PostgreSQL...")
    await engine.dispose()
    logger.info("Соединения с БД успешно закрыты.")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Ошибка в транзакции, выполняем rollback", exc_info=e)
            await session.rollback()
            raise e
