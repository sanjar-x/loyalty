# tests/conftest.py
import asyncio
import contextlib
import contextvars
import warnings
from asyncio.events import AbstractEventLoop
from collections.abc import AsyncIterable

import pytest
import redis.asyncio as redis
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.bootstrap.config import Settings
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.security import IOIDCProvider
from tests.fakes.blob_storage import InMemoryBlobStorage
from tests.fakes.oidc_provider import StubOIDCProvider

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*wait_container_is_ready.*"
)

# ==========================================
# 0. Event Loop Isolation
# ==========================================

_db_session_var: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar(
    "_db_session_var"
)


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Single event loop for entire test session."""
    loop: AbstractEventLoop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==========================================
# 0.1. ContextVar Isolation (autouse)
# ==========================================


@pytest.fixture(autouse=True)
def _reset_context_vars():
    """Reset request_id ContextVar per test to prevent cross-test contamination."""
    from src.shared.context import _request_id_var

    token = _request_id_var.set("test-request-id")
    yield
    _request_id_var.reset(token)


# ==========================================
# 1. Connection URLs
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
        S3_ACCESS_KEY=SecretStr("admin"),
        S3_SECRET_KEY=SecretStr("password"),
        S3_REGION="us-east-1",
        S3_BUCKET_NAME="test-bucket",
        S3_PUBLIC_BASE_URL="http://127.0.0.1:9000/test-bucket",
        RABBITMQ_PRIVATE_URL=rabbitmq_url,
        BOT_TOKEN=SecretStr(""),
    )


# ==========================================
# 2. Dishka Test Overrides Provider
# ==========================================


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
        return _db_session_var.get()

    @provide(scope=Scope.APP, override=True)
    async def redis_client(self) -> AsyncIterable[redis.Redis]:
        pool = redis.ConnectionPool.from_url(self.redis_url)
        client = redis.Redis(connection_pool=pool)
        yield client
        await client.close()
        await pool.disconnect()

    @provide(scope=Scope.APP, override=True)
    async def blob_storage(self) -> IBlobStorage:
        return InMemoryBlobStorage()

    @provide(scope=Scope.APP, override=True)
    async def oidc_provider(self) -> IOIDCProvider:
        return StubOIDCProvider()

    @provide(scope=Scope.APP, override=True)
    async def storage_config(self) -> IStorageConfig:
        return self.test_settings


# ==========================================
# 3. IoC Container & DB Initialization (Session Scope)
# ==========================================


@pytest.fixture(scope="session")
async def app_container(
    db_url, redis_url, test_settings
) -> AsyncIterable[AsyncContainer]:
    from src.infrastructure.cache.provider import CacheProvider
    from src.infrastructure.database.provider import DatabaseProvider
    from src.infrastructure.logging.provider import LoggingProvider
    from src.infrastructure.security.provider import SecurityProvider
    from src.modules.catalog.presentation.dependencies import (
        BrandProvider,
        CategoryProvider,
    )
    from src.modules.identity.infrastructure.provider import IdentityProvider
    from src.modules.storage.presentation.dependencies import StorageProvider
    from src.modules.supplier.presentation.dependencies import SupplierProvider
    from src.modules.user.infrastructure.provider import ProfileProvider

    container = make_async_container(
        DatabaseProvider(),
        LoggingProvider(),
        CacheProvider(),
        SecurityProvider(),
        StorageProvider(),
        CategoryProvider(),
        BrandProvider(),
        IdentityProvider(),
        ProfileProvider(),
        SupplierProvider(),
        TestOverridesProvider(
            db_url=db_url, redis_url=redis_url, settings=test_settings
        ),
    )
    yield container
    await container.close()


@pytest.fixture(scope="session")
async def test_engine(app_container: AsyncContainer) -> AsyncEngine:
    engine = await app_container.get(AsyncEngine)

    # Fail-fast DB connectivity check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.exit(
            f"Database unreachable: {e}. Start containers: docker compose up -d"
        )

    from src.infrastructure.database.registry import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    return engine


@pytest.fixture(scope="session")
async def setup_infrastructure(test_engine: AsyncEngine, test_settings: Settings):
    """Create MinIO bucket for tests (if not exists)."""
    from aiobotocore.session import get_session

    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=test_settings.S3_ENDPOINT_URL,
        aws_access_key_id=test_settings.S3_ACCESS_KEY,
        aws_secret_access_key=test_settings.S3_SECRET_KEY,
        region_name=test_settings.S3_REGION,
    ) as s3_client:
        with contextlib.suppress(Exception):
            await s3_client.create_bucket(Bucket=test_settings.S3_BUCKET_NAME)

    return True


# ==========================================
# 4. Test Isolation (Function Scope)
# ==========================================


@pytest.fixture(scope="function")
async def db_session(
    test_engine: AsyncEngine, setup_infrastructure
) -> AsyncIterable[AsyncSession]:
    """Nested transaction per test — automatic rollback ensures pristine state."""
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        await conn.begin_nested()

        maker = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        session = maker()

        token = _db_session_var.set(session)
        yield session
        _db_session_var.reset(token)

        await session.close()
        await transaction.rollback()


# ==========================================
# 5. Redis Isolation (Function Scope)
# ==========================================


@pytest.fixture()
async def _flush_redis(app_container: AsyncContainer):
    """Flush Redis after each test for cache isolation.

    Not autouse at root level — applied as autouse in integration/e2e conftest
    to avoid triggering DI container creation for unit/architecture tests.
    """
    yield
    try:
        redis_client = await app_container.get(redis.Redis)
        await redis_client.flushdb()
    except Exception:
        pass
