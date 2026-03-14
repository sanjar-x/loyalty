import asyncio
import contextvars
import warnings
from collections.abc import AsyncIterable
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as redis
from aiobotocore.session import get_session
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from src.bootstrap.config import Settings
from src.shared.interfaces.blob_storage import IBlobStorage

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*wait_container_is_ready.*"
)


# ==========================================
# 0. Изоляция Event Loop (Решение проблемы с зависанием БД)
# ==========================================
@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """
    Принудительно создаем один Event Loop для всей тестовой сессии.
    Это решает проблему "Task pending" и "InterfaceError", когда
    движок БД и тесты пытаются работать в разных циклах.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==========================================
# 1. URL-адреса для подключения...
# ==========================================
# 1. URL-адреса для подключения к локальным контейнерам
# ==========================================


@pytest.fixture(scope="session")
def db_url() -> str:
    return "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres"


@pytest.fixture(scope="session")
def redis_url() -> str:
    return "redis://:password@127.0.0.1:6379/0"


@pytest.fixture(scope="session")
def rabbitmq_url() -> str:
    return "amqp://admin:password@127.0.0.1:5672/"


@pytest.fixture(scope="session")
def test_settings(db_url, redis_url, rabbitmq_url) -> Settings:
    return Settings(
        PROJECT_NAME="Enterprise API - Test",
        ENVIRONMENT="test",
        DEBUG=True,
        SECRET_KEY=SecretStr("test-secret"),
        PGHOST="127.0.0.1",
        PGPORT=5432,
        PGUSER="postgres",
        PGPASSWORD=SecretStr("postgres"),
        PGDATABASE="postgres",
        REDISHOST="127.0.0.1",
        REDISPORT=6379,
        S3_ENDPOINT_URL="http://127.0.0.1:9000",
        S3_ACCESS_KEY="admin",
        S3_SECRET_KEY="password",
        S3_REGION="us-east-1",
        S3_BUCKET_NAME="test-bucket",
        S3_PUBLIC_BASE_URL="http://127.0.0.1:9000/test-bucket",
        RABBITMQ_URL=rabbitmq_url,
    )


# ==========================================
# 2. Провайдеры Dishka
# ==========================================

test_session_var = contextvars.ContextVar("test_session_var")


class TestOverridesProvider(Provider):
    def __init__(self, db_url: str, redis_url: str, settings: Settings):
        super().__init__()
        self.db_url = db_url
        self.redis_url = redis_url
        self.test_settings = settings

    @provide(scope=Scope.APP, override=True)
    async def settings(self) -> Settings:
        return self.test_settings

    @provide(scope=Scope.APP, override=True)
    async def engine(self) -> AsyncIterable[AsyncEngine]:
        from sqlalchemy.pool import NullPool

        engine = create_async_engine(url=self.db_url, poolclass=NullPool)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.REQUEST, override=True)
    async def session(self) -> AsyncSession:
        return test_session_var.get()

    @provide(scope=Scope.APP, override=True)
    async def redis_client(self) -> AsyncIterable[redis.Redis]:
        pool = redis.ConnectionPool.from_url(self.redis_url)
        client = redis.Redis(connection_pool=pool)
        yield client
        await client.close()
        await pool.disconnect()

    # 👇 ДОБАВЛЕНО: Заглушка для стораджа, чтобы воркеры не падали при старте
    @provide(scope=Scope.APP, override=True)
    async def blob_storage(self) -> IBlobStorage:
        return AsyncMock(spec=IBlobStorage)


# ==========================================
# 3. Инициализация IoC и БД (Session Scope)
# ==========================================


@pytest.fixture(scope="session")
async def app_container(
    db_url, redis_url, test_settings
) -> AsyncIterable[AsyncContainer]:
    from src.infrastructure.cache.provider import CacheProvider
    from src.infrastructure.database.provider import DatabaseProvider
    from src.infrastructure.security.provider import SecurityProvider
    from src.modules.catalog.presentation.dependencies import (
        BrandProvider,
        CategoryProvider,
    )
    from src.modules.storage.presentation.dependencies import StorageProvider

    container = make_async_container(
        DatabaseProvider(),
        CacheProvider(),
        SecurityProvider(),
        StorageProvider(),
        CategoryProvider(),
        BrandProvider(),
        TestOverridesProvider(
            db_url=db_url, redis_url=redis_url, settings=test_settings
        ),
    )
    yield container
    await container.close()


@pytest.fixture(scope="session")
async def test_engine(app_container: AsyncContainer) -> AsyncEngine:
    engine = await app_container.get(AsyncEngine)

    from src.infrastructure.database.registry import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    return engine


@pytest.fixture(scope="session")
async def setup_infrastructure(test_engine: AsyncEngine, test_settings: Settings):
    """
    Создает бакет в MinIO при запуске тестов (если его нет).
    """
    session = get_session()

    async with session.create_client(
        "s3",
        endpoint_url=test_settings.S3_ENDPOINT_URL,
        aws_access_key_id=test_settings.S3_ACCESS_KEY,
        aws_secret_access_key=test_settings.S3_SECRET_KEY,
        region_name=test_settings.S3_REGION,
    ) as s3_client:
        try:
            await s3_client.create_bucket(Bucket=test_settings.S3_BUCKET_NAME)
        except Exception as e:
            # В тестах бакет может уже существовать, игнорируем
            print(f"Bucket creation info: {e}")

    return True


# ==========================================
# 4. Изоляция Тестов (Function Scope)
# ==========================================


@pytest.fixture(scope="function")
async def db_session(
    test_engine: AsyncEngine, setup_infrastructure
) -> AsyncIterable[AsyncSession]:
    # setup_infrastructure добавлен в аргументы, чтобы гарантировать
    # создание бакета и таблиц перед первым тестом
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        nested = await conn.begin_nested()

        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            token = test_session_var.set(session)
            yield session
            test_session_var.reset(token)

        await nested.rollback()
        await transaction.rollback()
