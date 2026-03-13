import asyncio
import contextvars
from collections.abc import AsyncIterable

import pytest
import redis.asyncio as redis
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


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    url = postgres_container.get_connection_url()
    # testcontainers python returns postgresql+asyncpg://...
    # we can use it directly
    return url


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis_container:
        yield redis_container


@pytest.fixture(scope="session")
def redis_url(redis_container) -> str:
    port = redis_container.get_exposed_port(6379)
    host = redis_container.get_container_host_ip()
    return f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:3-management-alpine") as rabbitmq:
        yield rabbitmq


@pytest.fixture(scope="session")
def rabbitmq_url(rabbitmq_container) -> str:
    return rabbitmq_container.get_connection_url()


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(image="minio/minio:latest") as minio:
        yield minio


@pytest.fixture(scope="session")
def test_settings(db_url, redis_url, rabbitmq_url, minio_container) -> Settings:
    return Settings(
        PROJECT_NAME="Enterprise API - Test",
        ENVIRONMENT="test",
        DEBUG=True,
        SECRET_KEY=SecretStr("test-secret"),
        PGHOST="localhost",  # overwritten by database_url below
        PGPORT=5432,
        PGUSER="postgres",
        PGPASSWORD=SecretStr("postgres"),
        PGDATABASE="postgres",
        REDISHOST="localhost",  # overwritten by redis_url below
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
    def __init__(self, db_url: str, redis_url: str, settings: Settings):
        super().__init__()
        self.db_url = db_url
        self.redis_url = redis_url
        self.test_settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self.test_settings

    @provide(scope=Scope.APP)
    async def engine(self) -> AsyncIterable[AsyncEngine]:
        from sqlalchemy.pool import NullPool

        # using NullPool to prevent connection leaks across test runs
        engine = create_async_engine(url=self.db_url, poolclass=NullPool)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.REQUEST)
    async def session(self) -> AsyncSession:
        # returns the session bound to the nested transaction
        return test_session_var.get()

    @provide(scope=Scope.APP)
    async def redis_client(self) -> AsyncIterable[redis.Redis]:
        pool = redis.ConnectionPool.from_url(self.redis_url)
        client = redis.Redis(connection_pool=pool)
        yield client
        await client.close()
        await pool.disconnect()


@pytest.fixture(scope="session")
async def app_container(
    db_url, redis_url, test_settings
) -> AsyncIterable[AsyncContainer]:
    # Import actual providers
    from src.infrastructure.cache.provider import CacheProvider
    from src.infrastructure.database.provider import DatabaseProvider
    from src.infrastructure.security.provider import SecurityProvider
    from src.modules.catalog.presentation.dependencies import (
        BrandProvider,
        CategoryProvider,
    )
    from src.modules.storage.presentation.dependencies import StorageProvider

    # TestOverridesProvider overrides DatabaseProvider's engine/session, CacheProvider's redis_client, and Settings
    container = make_async_container(
        TestOverridesProvider(
            db_url=db_url, redis_url=redis_url, settings=test_settings
        ),
        DatabaseProvider(),
        CacheProvider(),
        SecurityProvider(),
        StorageProvider(),
        CategoryProvider(),
        BrandProvider(),
    )
    yield container
    await container.close()


@pytest.fixture(scope="session")
async def test_engine(app_container: AsyncContainer) -> AsyncEngine:
    engine = await app_container.get(AsyncEngine)
    # import models to register with Base
    from src.infrastructure.database.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine
