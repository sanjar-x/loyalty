import contextvars
import warnings
from collections.abc import AsyncIterable

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
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
from testcontainers.redis import RedisContainer

from src.bootstrap.config import Settings

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*wait_container_is_ready.*"
)

# ==========================================
# 1. Эфемерная Инфраструктура (Testcontainers)
# ==========================================


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:18-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:8.4-alpine") as redis_container:
        yield redis_container


@pytest.fixture(scope="session")
def redis_url(redis_container) -> str:
    port = redis_container.get_exposed_port(6379)
    host = redis_container.get_container_host_ip()
    return f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:4.2.4-management-alpine") as rabbitmq:
        yield rabbitmq


@pytest.fixture(scope="session")
def rabbitmq_url(rabbitmq_container) -> str:
    return rabbitmq_container.get_connection_url()


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(image="minio/minio:latest") as minio:
        yield minio


# ==========================================
# 2. Настройки и Подготовка Среды
# ==========================================


@pytest.fixture(scope="session")
def test_settings(db_url, redis_url, rabbitmq_url, minio_container) -> Settings:
    return Settings(
        PROJECT_NAME="Enterprise API - Test",
        ENVIRONMENT="test",
        DEBUG=True,
        SECRET_KEY=SecretStr("test-secret"),
        PGHOST="localhost",
        PGPORT=5432,
        PGUSER="postgres",
        PGPASSWORD=SecretStr("postgres"),
        PGDATABASE="postgres",
        REDISHOST="localhost",
        REDISPORT=6379,
        S3_ENDPOINT_URL=minio_container.get_url(),
        S3_ACCESS_KEY="minioadmin",
        S3_SECRET_KEY="minioadmin",
        S3_REGION="us-east-1",
        S3_BUCKET_NAME="test-bucket",
        RABBITMQ_URL=rabbitmq_url,
    )


test_session_var = contextvars.ContextVar("test_session_var")


class TestOverridesProvider(Provider):
    """
    Провайдер-заглушка для тестов.
    Используем override=True, чтобы Dishka не ругался на дублирование провайдеров.
    """

    def __init__(self, db_url: str, redis_url: str, settings: Settings):
        super().__init__()
        self.db_url = db_url
        self.redis_url = redis_url
        self.test_settings = settings

    @provide(scope=Scope.APP, override=True)
    def settings(self) -> Settings:
        return self.test_settings

    @provide(scope=Scope.APP, override=True)
    async def engine(self) -> AsyncIterable[AsyncEngine]:
        from sqlalchemy.pool import NullPool

        # NullPool обязателен в тестах, чтобы не исчерпать соединения Testcontainers
        engine = create_async_engine(url=self.db_url, poolclass=NullPool)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.REQUEST, override=True)
    async def session(self) -> AsyncSession:
        # Извлекаем сессию, привязанную к транзакции текущего теста
        return test_session_var.get()

    @provide(scope=Scope.APP, override=True)
    async def redis_client(self) -> AsyncIterable[redis.Redis]:
        pool = redis.ConnectionPool.from_url(self.redis_url)
        client = redis.Redis(connection_pool=pool)
        yield client
        await client.close()
        await pool.disconnect()


# ==========================================
# 4. Инициализация IoC и БД (Session Scope)
# ==========================================


@pytest.fixture(scope="session")
async def app_container(
    db_url, redis_url, test_settings
) -> AsyncIterable[AsyncContainer]:
    # Импортируем реальные провайдеры приложения
    from src.bootstrap.ioc import ConfigProvider

    from src.infrastructure.cache.provider import CacheProvider
    from src.infrastructure.database.provider import DatabaseProvider
    from src.infrastructure.security.provider import SecurityProvider
    from src.modules.catalog.presentation.dependencies import (
        BrandProvider,
        CategoryProvider,
    )
    from src.modules.storage.presentation.dependencies import StorageProvider

    # Собираем контейнер с перезаписью (TestOverridesProvider накладывается поверх)
    container = make_async_container(
        ConfigProvider(),
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
    """
    Достает движок из DI и создает все таблицы (один раз за запуск тестов).
    """
    engine = await app_container.get(AsyncEngine)

    # Подтягиваем все модели, чтобы Алхимия увидела их метадату
    import src.infrastructure.database.models  # noqa

    import src.modules.catalog.infrastructure.models  # noqa
    import src.modules.storage.infrastructure.models  # noqa
    from src.infrastructure.database.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


@pytest.fixture(scope="session")
async def setup_infrastructure(test_engine: AsyncEngine, test_settings: Settings):
    """
    Хук, который автоматически подготавливает всю инфраструктуру (БД и S3)
    до запуска первого теста.
    """
    # 1. БД уже готова (test_engine запрошен в аргументах)

    # 2. Инициализируем S3 Bucket в MinIO

    session = get_session
    async with session.client(
        "s3",
        endpoint_url=test_settings.S3_ENDPOINT_URL,
        aws_access_key_id=test_settings.S3_ACCESS_KEY,
        aws_secret_access_key=test_settings.S3_SECRET_KEY,
    ) as s3_client:
        try:
            await s3_client.create_bucket(Bucket=test_settings.S3_BUCKET_NAME)
        except Exception:
            pass  # Бакет уже существует

    return True


# ==========================================
# 5. Изоляция Тестов (Function Scope)
# ==========================================


@pytest.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncIterable[AsyncSession]:
    """
    Изолированная сессия с использованием Nested Transactions (SAVEPOINT).
    Тест пишет в БД, а после его завершения делается мгновенный ROLLBACK.
    """
    async with test_engine.connect() as conn:
        # Открываем главную транзакцию
        transaction = await conn.begin()
        # Открываем вложенную транзакцию (SAVEPOINT)
        nested = await conn.begin_nested()

        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            # Кладем сессию в ContextVar, чтобы Dishka мог ее инжектить
            token = test_session_var.set(session)

            yield session  # 🚀 Здесь выполняется сам тест

            # Очищаем ContextVar после выполнения
            test_session_var.reset(token)

        # Откатываем все изменения теста (таблицы остаются чистыми)
        await nested.rollback()
        await transaction.rollback()
