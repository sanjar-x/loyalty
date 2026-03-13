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


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:18-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:8.4-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def redis_url(redis_container) -> str:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(redis_container.port)
    password = redis_container.password
    auth = f":{password}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


@pytest.fixture(scope="session")
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:3-alpine") as rabbitmq:
        yield rabbitmq


@pytest.fixture(scope="session")
def rabbitmq_url(rabbitmq_container) -> str:
    host = rabbitmq_container.get_container_host_ip()
    exposed_port = rabbitmq_container.get_exposed_port(rabbitmq_container.port)
    user = rabbitmq_container.username
    password = rabbitmq_container.password
    vhost = rabbitmq_container.vhost
    vhost_path = vhost.lstrip("/")
    return f"amqp://{user}:{password}@{host}:{exposed_port}/{vhost_path}"


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="minio/minio:latest", access_key="minioadmin", secret_key="minioadmin"
    ) as minio:
        yield minio


@pytest.fixture(scope="session")
def test_settings(db_url, redis_url, rabbitmq_url, minio_container) -> Settings:
    minio_config = minio_container.get_config()
    minio_endpoint = f"http://{minio_config['endpoint']}"

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
        S3_ENDPOINT_URL=minio_endpoint,
        S3_ACCESS_KEY=minio_config["access_key"],
        S3_SECRET_KEY=minio_config["secret_key"],
        S3_REGION="us-east-1",
        S3_BUCKET_NAME="test-bucket",
        RABBITMQ_URL=rabbitmq_url,
    )


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


# ==========================================
# 4. Инициализация IoC и БД (Session Scope)
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
    Создает бакет в MinIO при запуске тестов.
    """
    # Вызываем get_session, чтобы получить объект сессии
    session = get_session()

    # Используем session.create_client (а не просто .client)
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
# 5. Изоляция Тестов (Function Scope)
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
