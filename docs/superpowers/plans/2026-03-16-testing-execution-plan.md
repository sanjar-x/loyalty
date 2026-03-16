# Testing Architecture — Execution Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full Testing Design Specification (`docs/superpowers/specs/testing-design-specification.md`) across 5 sequential chunks with maximum intra-chunk parallelism.

**Architecture:** Nested Transaction Pattern for DB isolation, Object Mothers for domain data generation, Dishka-exclusive DI overrides, pytest-archon fitness functions, CQRS-aware integration tests, httpx ASGI e2e tests, and Locust load scenarios.

**Tech Stack:** pytest 9+ · pytest-asyncio · pytest-archon · pytest-cov · polyfactory · httpx · Locust · SQLAlchemy 2.1 async · Dishka 1.9 · FastAPI · attrs · structlog

---

## Dependency Graph

```
Chunk 1 (Foundation)          [SEQUENTIAL — root fixture DAG]
    │
    ├──→ Chunk 2 (Data Generation)    [PARALLEL — 7 independent files]
    │        │
    │        ├──→ Chunk 3a (Architecture Tests)  [PARALLEL — no data deps]
    │        └──→ Chunk 3b (Unit Tests)          [PARALLEL — per-module]
    │                 │
    │                 └──→ Chunk 4 (Integration Tests)  [PARALLEL — per-module]
    │                          │
    │                          └──→ Chunk 5 (E2E + Load) [PARALLEL — after helper]
    │
    └──→ Chunk 3a can start in parallel with Chunk 2 (no shared files)
```

---

## Current State Audit

| Area | Status | Gap |
|------|--------|-----|
| `tests/conftest.py` | Exists | Missing `join_transaction_mode`, fail-fast DB check, ContextVar reset, uses `AsyncMock` not Fake |
| `tests/integration/conftest.py` | Correct | Already uses `join_transaction_mode="create_savepoint"` |
| `tests/e2e/conftest.py` | Correct | ASGI transport, session-scoped app |
| `tests/unit/conftest.py` | Empty | Correct — unit tests need no DB |
| `tests/architecture/conftest.py` | Missing | Needs `pytestmark` |
| `pyproject.toml` pytest config | Partial | Missing `asyncio_mode`, `filterwarnings`, full marker list |
| Object Mothers | Missing | No `identity_mothers.py`, `catalog_mothers.py`, `user_mothers.py`, `storage_mothers.py` |
| Builders | Missing | No `builders.py` |
| ORM Factories | Empty stubs | `catalog_factories.py` and `storage_factories.py` exist but are empty |
| Fakes/Stubs | Missing | No `InMemoryBlobStorage`, `StubOIDCProvider` |
| Architecture tests | Partial | 9 rules exist; missing parameterized framework checks, reverse-layer rules |
| Unit tests | Partial | Identity=13, Catalog=9, User=6. Missing: Storage, events expansion |
| Integration tests | Partial | Catalog only (8 tests). Missing: Identity, User, Storage handlers |
| E2E tests | Minimal | Brands=2, Categories=2. Missing: Auth, Users, error paths |
| Load tests | Skeleton | 1 scenario. Missing: auth_flow, thresholds.yml |

---

## Files That MUST NOT Be Edited Concurrently

| File | Edited in | Reason |
|------|-----------|--------|
| `tests/conftest.py` | Chunk 1 only | Root fixture DAG — all tests depend on it |
| `tests/e2e/conftest.py` | Chunk 5a.5 only | E2E fixture DAG |
| `tests/integration/conftest.py` | Chunk 1 only (if needed) | Integration fixture DAG |
| `pyproject.toml` | Chunk 1 only | Global pytest configuration |
| `tests/architecture/test_boundaries.py` | Chunk 3a only | Single architecture test file |

---

## Chunk 1: Foundation (Test Infrastructure)

> **Effort:** Critical
> **Parallelism:** `[SEQUENTIAL]` — root of fixture DAG; concurrent edits will conflict
> **Files touched:** 6 files (config + test root + fakes)

### Task 1.1: Update pytest configuration

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `[tool.pytest.ini_options]`**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "architecture: Fitness functions and boundary enforcement",
    "unit: Domain-layer pure logic, zero I/O",
    "integration: Application + Infrastructure with real database",
    "e2e: Presentation-layer HTTP round-trips",
    "load: Resilience and threshold testing (Locust)",
]
filterwarnings = [
    "ignore::DeprecationWarning:dishka.*",
]
testpaths = ["tests"]
```

- [ ] **Step 2: Verify pytest collects tests**

Run: `uv run pytest --co -q | tail -5`
Expected: Shows test count, no warnings about unknown markers

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(tests): update pytest config with asyncio_mode, markers, filterwarnings"
```

---

### Task 1.2: Create test fakes directory

**Files:**
- Create: `tests/fakes/__init__.py`
- Create: `tests/fakes/blob_storage.py`
- Create: `tests/fakes/oidc_provider.py`

- [ ] **Step 1: Create `tests/fakes/__init__.py`**

```python
# tests/fakes/__init__.py
```

- [ ] **Step 2: Create `InMemoryBlobStorage` fake**

```python
# tests/fakes/blob_storage.py
"""
Fake implementation of IBlobStorage for testing.
Uses an in-memory dict instead of S3/MinIO.
"""
from collections.abc import AsyncIterator
from typing import Any


class InMemoryBlobStorage:
    """In-memory fake implementing IBlobStorage protocol."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    async def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        data = self._objects.get(object_name, b"")
        yield data

    async def get_presigned_url(
        self, object_name: str, expiration: int = 3600
    ) -> str:
        return f"https://fake-s3.test/{object_name}?expires={expiration}"

    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict:
        return {
            "url": f"https://fake-s3.test/{object_name}",
            "fields": {"key": object_name},
        }

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        return f"https://fake-s3.test/{object_name}?content_type={content_type}&expires={expiration}"

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        chunks = []
        async for chunk in data_stream:
            chunks.append(chunk)
        self._objects[object_name] = b"".join(chunks)
        self._metadata[object_name] = {"content_type": content_type}
        return object_name

    async def object_exists(self, object_name: str) -> bool:
        return object_name in self._objects

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]:
        return self._metadata.get(object_name, {})

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict:
        keys = [k for k in self._objects if k.startswith(prefix)][:limit]
        return {"objects": keys, "continuation_token": None}

    async def delete_object(self, object_name: str) -> None:
        self._objects.pop(object_name, None)
        self._metadata.pop(object_name, None)

    async def delete_file(self, object_name: str) -> None:
        await self.delete_object(object_name)

    async def delete_objects(self, object_names: list[str]) -> list[str]:
        deleted = []
        for name in object_names:
            if name in self._objects:
                await self.delete_object(name)
                deleted.append(name)
        return deleted

    async def copy_object(self, source_name: str, dest_name: str) -> None:
        if source_name in self._objects:
            self._objects[dest_name] = self._objects[source_name]
            self._metadata[dest_name] = self._metadata.get(source_name, {}).copy()
```

- [ ] **Step 3: Create `StubOIDCProvider`**

```python
# tests/fakes/oidc_provider.py
"""
Stub implementation of IOIDCProvider for testing.
Returns configurable OIDCUserInfo without real OAuth calls.
"""
from src.shared.interfaces.security import OIDCUserInfo


class StubOIDCProvider:
    """Stub that returns pre-configured OIDC user info."""

    def __init__(
        self,
        default_user: OIDCUserInfo | None = None,
    ) -> None:
        self._default_user = default_user or OIDCUserInfo(
            provider="google",
            sub="stub-oidc-sub-12345",
            email="oidc-user@example.com",
        )
        self._users: dict[str, OIDCUserInfo] = {}

    def configure_token(self, token: str, user_info: OIDCUserInfo) -> None:
        """Pre-configure a token -> user mapping for testing."""
        self._users[token] = user_info

    async def validate_token(self, token: str) -> OIDCUserInfo:
        if token in self._users:
            return self._users[token]
        return self._default_user

    async def get_authorization_url(self, state: str) -> str:
        return f"https://fake-oidc.test/authorize?state={state}"
```

- [ ] **Step 4: Verify fakes are importable**

Run: `uv run python -c "from tests.fakes.blob_storage import InMemoryBlobStorage; from tests.fakes.oidc_provider import StubOIDCProvider; print('OK')"`
Expected: `OK`

---

### Task 1.3: Harden root `tests/conftest.py`

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Replace with hardened version — InMemoryBlobStorage, StubOIDCProvider, fail-fast DB, ContextVar reset, Redis flush, `join_transaction_mode`**

The full updated `tests/conftest.py`:

```python
# tests/conftest.py
import asyncio
import contextvars
import warnings
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
from src.shared.interfaces.security import IOIDCProvider
from tests.fakes.blob_storage import InMemoryBlobStorage
from tests.fakes.oidc_provider import StubOIDCProvider

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*wait_container_is_ready.*"
)

# ==========================================
# 0. Event Loop Isolation
# ==========================================

test_session_var: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar(
    "test_session_var"
)


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Single event loop for entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
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
        S3_ACCESS_KEY="admin",
        S3_SECRET_KEY="password",
        S3_REGION="us-east-1",
        S3_BUCKET_NAME="test-bucket",
        S3_PUBLIC_BASE_URL="http://127.0.0.1:9000/test-bucket",
        RABBITMQ_URL=rabbitmq_url,
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
        return test_session_var.get()

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


# ==========================================
# 3. IoC Container & DB Initialization (Session Scope)
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
    from src.modules.identity.infrastructure.provider import IdentityProvider
    from src.modules.storage.presentation.dependencies import StorageProvider
    from src.modules.user.infrastructure.provider import UserProvider

    container = make_async_container(
        DatabaseProvider(),
        CacheProvider(),
        SecurityProvider(),
        StorageProvider(),
        CategoryProvider(),
        BrandProvider(),
        IdentityProvider(),
        UserProvider(),
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
        try:
            await s3_client.create_bucket(Bucket=test_settings.S3_BUCKET_NAME)
        except Exception:
            pass  # Bucket already exists

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

        token = test_session_var.set(session)
        yield session
        test_session_var.reset(token)

        await session.close()
        await transaction.rollback()


# ==========================================
# 5. Redis Isolation (Function Scope)
# ==========================================


@pytest.fixture(autouse=True)
async def _flush_redis(app_container: AsyncContainer):
    """Flush Redis after each test for cache isolation."""
    yield
    try:
        redis_client = await app_container.get(redis.Redis)
        await redis_client.flushdb()
    except Exception:
        pass  # Redis may not be needed for unit tests
```

- [ ] **Step 2: Verify all existing tests still pass**

Run: `uv run pytest tests/ -v --tb=short -x`
Expected: All tests pass (architecture + unit + integration + e2e)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py tests/fakes/
git commit -m "feat(tests): harden root conftest — InMemoryBlobStorage, StubOIDCProvider, fail-fast DB, ContextVar reset, Redis flush"
```

---

### Task 1.4: Create architecture conftest

**Files:**
- Create: `tests/architecture/conftest.py`

- [ ] **Step 1: Create the file**

```python
# tests/architecture/conftest.py
import pytest

pytestmark = pytest.mark.architecture
```

- [ ] **Step 2: Verify architecture tests still collect**

Run: `uv run pytest tests/architecture/ --co -q`
Expected: Shows test list with `architecture` marker

- [ ] **Step 3: Commit**

```bash
git add tests/architecture/conftest.py
git commit -m "chore(tests): add architecture conftest with pytestmark"
```

---

### Task 1.5: Create factories `__init__.py`

**Files:**
- Modify: `tests/factories/__init__.py` (create if missing)

- [ ] **Step 1: Ensure the file exists and is importable**

```python
# tests/factories/__init__.py
```

- [ ] **Step 2: Verify**

Run: `uv run python -c "import tests.factories; print('OK')"`
Expected: `OK`

---

### Chunk 1 — Verification Gate

```bash
# ALL existing tests must still pass after foundation changes
uv run pytest tests/ -v --tb=short -x
# Expected: architecture (9) + unit (~30) + integration (~8) + e2e (~4) = ~51 tests PASS
```

---

## Chunk 2: Data Generation (Object Mothers & Factories)

> **Effort:** Medium
> **Parallelism:** `[PARALLEL]` — each file is independent, no shared state
> **Files touched:** 7 new files in `tests/factories/`
> **Subagent isolation:** Each task gets its own worktree. Zero conflict risk.

### Task 2.1: Identity Object Mothers `[PARALLEL]`

**Files:**
- Create: `tests/factories/identity_mothers.py`

- [ ] **Step 1: Create identity mothers**

```python
# tests/factories/identity_mothers.py
"""Object Mothers for Identity module domain entities."""
import uuid
from datetime import datetime, timezone

from src.modules.identity.domain.entities import (
    Identity,
    LinkedAccount,
    LocalCredentials,
    Permission,
    Role,
    Session,
)
from src.modules.identity.domain.value_objects import IdentityType


class IdentityMothers:
    """Pre-built Identity aggregate configurations."""

    @staticmethod
    def active_local() -> Identity:
        """Standard active identity with LOCAL credentials."""
        return Identity.register(IdentityType.LOCAL)

    @staticmethod
    def active_oidc() -> Identity:
        """Standard active identity via OIDC provider."""
        return Identity.register(IdentityType.OIDC)

    @staticmethod
    def deactivated(reason: str = "test_deactivation") -> Identity:
        """Identity that has been deactivated — ensure_active() will raise."""
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason=reason)
        identity.clear_domain_events()
        return identity

    @staticmethod
    def with_credentials(
        email: str = "test@example.com",
        password_hash: str = "$argon2id$v=19$m=65536,t=3,p=4$test",
    ) -> tuple[Identity, LocalCredentials]:
        """Identity + LocalCredentials pair."""
        identity = Identity.register(IdentityType.LOCAL)
        creds = LocalCredentials(
            identity_id=identity.id,
            email=email,
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return identity, creds

    @staticmethod
    def with_session(
        ip_address: str = "127.0.0.1",
        user_agent: str = "TestAgent/1.0",
    ) -> tuple[Identity, Session, str]:
        """Identity + active Session + raw refresh token."""
        identity = Identity.register(IdentityType.LOCAL)
        raw_token = f"refresh-{uuid.uuid4().hex}"
        session = Session.create(
            identity_id=identity.id,
            refresh_token=raw_token,
            ip_address=ip_address,
            user_agent=user_agent,
            role_ids=[],
            expires_days=30,
        )
        return identity, session, raw_token


class SessionMothers:
    """Pre-built Session configurations."""

    @staticmethod
    def active(identity_id: uuid.UUID | None = None) -> tuple[Session, str]:
        """Active, non-expired session + raw refresh token."""
        identity_id = identity_id or uuid.uuid4()
        raw_token = f"refresh-{uuid.uuid4().hex}"
        session = Session.create(
            identity_id=identity_id,
            refresh_token=raw_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        return session, raw_token

    @staticmethod
    def expired(identity_id: uuid.UUID | None = None) -> Session:
        """Expired session."""
        from datetime import timedelta

        identity_id = identity_id or uuid.uuid4()
        session = Session.create(
            identity_id=identity_id,
            refresh_token="expired-token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return session

    @staticmethod
    def revoked(identity_id: uuid.UUID | None = None) -> Session:
        """Revoked session."""
        identity_id = identity_id or uuid.uuid4()
        session = Session.create(
            identity_id=identity_id,
            refresh_token="revoked-token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
            expires_days=30,
        )
        session.revoke()
        return session


class RoleMothers:
    """Pre-built Role configurations."""

    @staticmethod
    def customer() -> Role:
        return Role(
            id=uuid.uuid4(),
            name="customer",
            description="Default customer role",
            is_system=False,
        )

    @staticmethod
    def admin() -> Role:
        return Role(
            id=uuid.uuid4(),
            name="admin",
            description="Administrator role",
            is_system=True,
        )

    @staticmethod
    def system_role(name: str = "system") -> Role:
        return Role(
            id=uuid.uuid4(),
            name=name,
            description=f"System role: {name}",
            is_system=True,
        )


class PermissionMothers:
    """Pre-built Permission configurations."""

    @staticmethod
    def brand_create() -> Permission:
        return Permission(
            id=uuid.uuid4(),
            codename="brands:create",
            resource="brands",
            action="create",
        )

    @staticmethod
    def brand_read() -> Permission:
        return Permission(
            id=uuid.uuid4(),
            codename="brands:read",
            resource="brands",
            action="read",
        )

    @staticmethod
    def category_manage() -> Permission:
        return Permission(
            id=uuid.uuid4(),
            codename="categories:manage",
            resource="categories",
            action="manage",
        )


class LinkedAccountMothers:
    """Pre-built LinkedAccount configurations."""

    @staticmethod
    def google(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="google",
            provider_sub_id=f"google-{uuid.uuid4().hex[:8]}",
            provider_email="user@gmail.com",
        )

    @staticmethod
    def github(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="github",
            provider_sub_id=f"github-{uuid.uuid4().hex[:8]}",
            provider_email="user@github.com",
        )
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.identity_mothers import IdentityMothers, SessionMothers, RoleMothers, PermissionMothers, LinkedAccountMothers; print('OK')"`

---

### Task 2.2: Catalog Object Mothers `[PARALLEL]`

**Files:**
- Create: `tests/factories/catalog_mothers.py`

- [ ] **Step 1: Create catalog mothers**

```python
# tests/factories/catalog_mothers.py
"""Object Mothers for Catalog module domain entities."""
import uuid

from src.modules.catalog.domain.entities import Brand, Category
from src.modules.catalog.domain.value_objects import MediaProcessingStatus


class BrandMothers:
    """Pre-built Brand aggregate configurations."""

    @staticmethod
    def without_logo() -> Brand:
        """Brand with no logo — simplest valid state."""
        return Brand.create(name="Test Brand", slug=f"test-brand-{uuid.uuid4().hex[:6]}")

    @staticmethod
    def with_pending_logo() -> Brand:
        """Brand with logo in PENDING_UPLOAD state."""
        brand = Brand.create(name="Logo Brand", slug=f"logo-brand-{uuid.uuid4().hex[:6]}")
        brand.init_logo_upload(
            object_key=f"raw_uploads/catalog/brands/{brand.id}/logo_raw",
            content_type="image/png",
        )
        brand.clear_domain_events()
        return brand

    @staticmethod
    def with_processing_logo() -> Brand:
        """Brand with logo in PROCESSING state (upload confirmed)."""
        brand = BrandMothers.with_pending_logo()
        brand.confirm_logo_upload()
        brand.clear_domain_events()
        return brand

    @staticmethod
    def with_completed_logo() -> Brand:
        """Brand with logo in COMPLETED state."""
        brand = BrandMothers.with_processing_logo()
        brand.complete_logo_processing(url="https://cdn.test/logo.webp")
        brand.clear_domain_events()
        return brand

    @staticmethod
    def with_failed_logo() -> Brand:
        """Brand with logo in FAILED state."""
        brand = BrandMothers.with_processing_logo()
        brand.fail_logo_processing()
        brand.clear_domain_events()
        return brand


class CategoryMothers:
    """Pre-built Category aggregate configurations."""

    @staticmethod
    def root(name: str = "Electronics", slug: str | None = None) -> Category:
        """Root-level category (level=0, no parent)."""
        return Category.create_root(
            name=name,
            slug=slug or f"electronics-{uuid.uuid4().hex[:6]}",
            sort_order=0,
        )

    @staticmethod
    def child(parent: Category | None = None, name: str = "Smartphones") -> Category:
        """Child category under given parent (or creates a root parent)."""
        if parent is None:
            parent = CategoryMothers.root()
        return Category.create_child(
            name=name,
            slug=f"smartphones-{uuid.uuid4().hex[:6]}",
            parent=parent,
            sort_order=0,
        )

    @staticmethod
    def deep_nested(depth: int = 3) -> list[Category]:
        """Chain of nested categories up to the given depth. Returns [root, child, grandchild, ...]."""
        categories: list[Category] = []
        names = ["Electronics", "Smartphones", "Android", "Samsung", "Galaxy"]
        root = CategoryMothers.root(name=names[0])
        categories.append(root)
        for i in range(1, min(depth, len(names))):
            child = Category.create_child(
                name=names[i],
                slug=f"{names[i].lower()}-{uuid.uuid4().hex[:6]}",
                parent=categories[-1],
                sort_order=0,
            )
            categories.append(child)
        return categories
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.catalog_mothers import BrandMothers, CategoryMothers; print('OK')"`

---

### Task 2.3: User Object Mothers `[PARALLEL]`

**Files:**
- Create: `tests/factories/user_mothers.py`

- [ ] **Step 1: Create user mothers**

```python
# tests/factories/user_mothers.py
"""Object Mothers for User module domain entities."""
import uuid

from src.modules.user.domain.entities import User


class UserMothers:
    """Pre-built User aggregate configurations."""

    @staticmethod
    def active(identity_id: uuid.UUID | None = None) -> User:
        """Standard active user with profile data."""
        return User.create_from_identity(
            identity_id=identity_id or uuid.uuid4(),
            profile_email="user@example.com",
        )

    @staticmethod
    def with_profile(
        first_name: str = "John",
        last_name: str = "Doe",
        phone: str = "+1234567890",
        identity_id: uuid.UUID | None = None,
    ) -> User:
        """User with full profile populated."""
        user = User.create_from_identity(
            identity_id=identity_id or uuid.uuid4(),
            profile_email="user@example.com",
        )
        user.update_profile(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )
        return user

    @staticmethod
    def anonymized(identity_id: uuid.UUID | None = None) -> User:
        """User after GDPR anonymization — PII replaced."""
        user = UserMothers.with_profile(identity_id=identity_id)
        user.anonymize()
        return user
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.user_mothers import UserMothers; print('OK')"`

---

### Task 2.4: Storage Object Mothers `[PARALLEL]`

**Files:**
- Create: `tests/factories/storage_mothers.py`

- [ ] **Step 1: Create storage mothers**

```python
# tests/factories/storage_mothers.py
"""Object Mothers for Storage module domain entities."""
import uuid

from src.modules.storage.domain.entities import StorageFile


class StorageFileMothers:
    """Pre-built StorageFile configurations."""

    @staticmethod
    def pending(
        bucket_name: str = "test-bucket",
        owner_module: str = "catalog",
    ) -> StorageFile:
        """StorageFile just created, not yet processed."""
        return StorageFile.create(
            bucket_name=bucket_name,
            object_key=f"raw_uploads/{owner_module}/{uuid.uuid4().hex}/file",
            content_type="image/png",
            size_bytes=0,
            owner_module=owner_module,
        )

    @staticmethod
    def active(
        bucket_name: str = "test-bucket",
        size_bytes: int = 1024,
    ) -> StorageFile:
        """StorageFile with known size (upload completed)."""
        return StorageFile.create(
            bucket_name=bucket_name,
            object_key=f"processed/catalog/{uuid.uuid4().hex}/image.webp",
            content_type="image/webp",
            size_bytes=size_bytes,
            owner_module="catalog",
        )
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.storage_mothers import StorageFileMothers; print('OK')"`

---

### Task 2.5: Test Data Builders `[PARALLEL]`

**Files:**
- Create: `tests/factories/builders.py`

- [ ] **Step 1: Create builders**

```python
# tests/factories/builders.py
"""Fluent Test Data Builders for complex aggregate construction."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from src.modules.identity.domain.entities import Role, Session
from src.modules.catalog.domain.entities import Category


class RoleBuilder:
    """Fluent builder for Role entities with sensible defaults."""

    def __init__(self) -> None:
        self._id = uuid.uuid4()
        self._name = "test-role"
        self._description: str | None = "Test role"
        self._is_system = False

    def with_name(self, name: str) -> RoleBuilder:
        self._name = name
        return self

    def with_description(self, description: str | None) -> RoleBuilder:
        self._description = description
        return self

    def as_system_role(self) -> RoleBuilder:
        self._is_system = True
        return self

    def build(self) -> Role:
        return Role(
            id=self._id,
            name=self._name,
            description=self._description,
            is_system=self._is_system,
        )


class SessionBuilder:
    """Fluent builder for Session entities."""

    def __init__(self) -> None:
        self._identity_id = uuid.uuid4()
        self._refresh_token = f"refresh-{uuid.uuid4().hex}"
        self._ip_address = "127.0.0.1"
        self._user_agent = "TestAgent/1.0"
        self._role_ids: list[uuid.UUID] = []
        self._expires_days = 30
        self._is_revoked = False
        self._expired = False

    def with_identity(self, identity_id: uuid.UUID) -> SessionBuilder:
        self._identity_id = identity_id
        return self

    def with_roles(self, role_ids: list[uuid.UUID]) -> SessionBuilder:
        self._role_ids = role_ids
        return self

    def expired(self) -> SessionBuilder:
        self._expired = True
        return self

    def revoked(self) -> SessionBuilder:
        self._is_revoked = True
        return self

    def build(self) -> tuple[Session, str]:
        """Returns (session, raw_refresh_token)."""
        session = Session.create(
            identity_id=self._identity_id,
            refresh_token=self._refresh_token,
            ip_address=self._ip_address,
            user_agent=self._user_agent,
            role_ids=self._role_ids,
            expires_days=self._expires_days,
        )
        if self._expired:
            session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        if self._is_revoked:
            session.revoke()
        return session, self._refresh_token


class CategoryBuilder:
    """Fluent builder for Category tree construction."""

    def __init__(self) -> None:
        self._name = "Test Category"
        self._slug: str | None = None
        self._sort_order = 0
        self._parent: Category | None = None

    def with_name(self, name: str) -> CategoryBuilder:
        self._name = name
        return self

    def with_slug(self, slug: str) -> CategoryBuilder:
        self._slug = slug
        return self

    def under(self, parent: Category) -> CategoryBuilder:
        self._parent = parent
        return self

    def build(self) -> Category:
        slug = self._slug or f"{self._name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        if self._parent is None:
            return Category.create_root(
                name=self._name, slug=slug, sort_order=self._sort_order
            )
        return Category.create_child(
            name=self._name, slug=slug, parent=self._parent, sort_order=self._sort_order
        )
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.builders import RoleBuilder, SessionBuilder, CategoryBuilder; print('OK')"`

---

### Task 2.6: ORM Factories (Polyfactory) `[PARALLEL]`

**Files:**
- Create: `tests/factories/orm_factories.py`

- [ ] **Step 1: Create polyfactory-based ORM model factories**

```python
# tests/factories/orm_factories.py
"""Polyfactory-based ORM model factories for integration test data seeding."""
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.modules.identity.infrastructure.models import (
    Identity as IdentityModel,
    LocalCredentials as CredentialsModel,
    Session as SessionModel,
    Role as RoleModel,
)
from src.modules.catalog.infrastructure.models import (
    Brand as BrandModel,
    Category as CategoryModel,
)
from src.modules.user.infrastructure.models import User as UserModel


class IdentityModelFactory(SQLAlchemyFactory):
    __model__ = IdentityModel
    __set_relationships__ = True


class CredentialsModelFactory(SQLAlchemyFactory):
    __model__ = CredentialsModel
    __set_relationships__ = True


class SessionModelFactory(SQLAlchemyFactory):
    __model__ = SessionModel
    __set_relationships__ = True


class RoleModelFactory(SQLAlchemyFactory):
    __model__ = RoleModel
    __set_relationships__ = True


class BrandModelFactory(SQLAlchemyFactory):
    __model__ = BrandModel
    __set_relationships__ = True


class CategoryModelFactory(SQLAlchemyFactory):
    __model__ = CategoryModel
    __set_relationships__ = True


class UserModelFactory(SQLAlchemyFactory):
    __model__ = UserModel
    __set_relationships__ = True
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.orm_factories import IdentityModelFactory, BrandModelFactory; print('OK')"`

---

### Task 2.7: Schema Factories (Polyfactory) `[PARALLEL]`

**Files:**
- Create: `tests/factories/schema_factories.py`

- [ ] **Step 1: Create polyfactory-based Pydantic schema factories**

```python
# tests/factories/schema_factories.py
"""Polyfactory-based Pydantic schema factories for e2e test payloads."""
from polyfactory.factories.pydantic_factory import ModelFactory

from src.modules.identity.presentation.schemas import (
    RegisterRequest,
    LoginRequest,
)
from src.modules.catalog.presentation.schemas import (
    CreateBrandRequest,
    CreateCategoryRequest,
)


class RegisterRequestFactory(ModelFactory):
    __model__ = RegisterRequest


class LoginRequestFactory(ModelFactory):
    __model__ = LoginRequest


class CreateBrandRequestFactory(ModelFactory):
    __model__ = CreateBrandRequest


class CreateCategoryRequestFactory(ModelFactory):
    __model__ = CreateCategoryRequest
```

- [ ] **Step 2: Verify importable**

Run: `uv run python -c "from tests.factories.schema_factories import RegisterRequestFactory; print('OK')"`

---

### Chunk 2 — Verification Gate

```bash
# All factories importable and valid
uv run python -c "
from tests.factories.identity_mothers import IdentityMothers, SessionMothers, RoleMothers
from tests.factories.catalog_mothers import BrandMothers, CategoryMothers
from tests.factories.user_mothers import UserMothers
from tests.factories.storage_mothers import StorageFileMothers
from tests.factories.builders import RoleBuilder, SessionBuilder, CategoryBuilder
from tests.factories.orm_factories import IdentityModelFactory, BrandModelFactory
print('All factories importable and valid')
"

# Existing tests must still pass
uv run pytest tests/ -v --tb=short -x
```

**Commit all Chunk 2 work:**
```bash
git add tests/factories/
git commit -m "feat(tests): add Object Mothers, Builders, ORM and schema factories for all modules"
```

---

## Chunk 3: Architecture Boundary Tests & Domain Unit Tests

> **Effort:** High
> **Parallelism:** `[PARALLEL]` — 3a (architecture) and each 3b.x (unit per module) touch completely different files

### Task 3a.1: Enhance architecture boundary tests `[PARALLEL]`

**Files:**
- Modify: `tests/architecture/test_boundaries.py`

- [ ] **Step 1: Replace the file with enhanced version including all spec rules**

```python
# tests/architecture/test_boundaries.py
"""
Architectural Fitness Functions — pytest-archon boundary enforcement.
Spec reference: docs/superpowers/specs/testing-design-specification.md Section 5
"""
import pytest
from pytest_archon import archrule

pytestmark = pytest.mark.architecture

MODULES = ["catalog", "storage", "identity", "user"]


# Rule 1: Domain Layer Purity (Clean Architecture)
def test_domain_layer_is_pure():
    """Domain MUST NOT import from any outer layer."""
    (
        archrule("domain_independence")
        .match("src.modules.*.domain.*")
        .should_not_import("src.modules.*.application.*")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .should_not_import("src.bootstrap.*")
        .check("src")
    )


# Rule 2: Domain Has Zero Framework Imports
@pytest.mark.parametrize("module", MODULES)
def test_domain_has_zero_framework_imports(module: str):
    """Domain entities use attrs and stdlib only."""
    (
        archrule(f"{module}_domain_no_frameworks")
        .match(f"src.modules.{module}.domain.*")
        .should_not_import("sqlalchemy.*")
        .should_not_import("fastapi.*")
        .should_not_import("dishka.*")
        .should_not_import("redis.*")
        .should_not_import("taskiq.*")
        .should_not_import("pydantic.*")
        .should_not_import("alembic.*")
        .check("src")
    )


# Rule 3: Application Layer Boundaries
def test_application_layer_boundaries():
    """Application may import Domain but NOT Infrastructure or Presentation."""
    (
        archrule("application_independence")
        .match("src.modules.*.application.*")
        .exclude("src.modules.catalog.application.queries.get_category_tree")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )


# Rule 4: Infrastructure Does Not Import Presentation
def test_infrastructure_does_not_import_presentation():
    """Infrastructure MUST NOT depend on web routers."""
    (
        archrule("infrastructure_independence")
        .match("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )


# Rule 5: Modular Monolith Cross-Module Isolation
@pytest.mark.parametrize(
    "source,target",
    [(s, t) for s in MODULES for t in MODULES if s != t],
)
def test_module_isolation(source: str, target: str):
    """Modules MUST NOT directly import each other's internals."""
    for layer in ["domain", "application", "infrastructure"]:
        (
            archrule(f"{source}_cannot_import_{target}_{layer}")
            .match(f"src.modules.{source}.*")
            .should_not_import(f"src.modules.{target}.{layer}.*")
            .check("src")
        )


# Rule 6: Shared Kernel Independence
def test_shared_kernel_is_independent():
    """src/shared/ MUST NOT import from any business module."""
    (
        archrule("shared_kernel_independence")
        .match("src.shared.*")
        .should_not_import("src.modules.*")
        .check("src")
    )


# Rule 7: No Reverse Layer Dependencies
@pytest.mark.parametrize("module", MODULES)
def test_no_reverse_layer_dependencies(module: str):
    """Within a module: Domain <- Application <- Infrastructure <- Presentation."""
    # Domain must not import Application
    (
        archrule(f"{module}_domain_not_import_application")
        .match(f"src.modules.{module}.domain.*")
        .should_not_import(f"src.modules.{module}.application.*")
        .check("src")
    )
    # Application must not import Infrastructure
    (
        archrule(f"{module}_application_not_import_infrastructure")
        .match(f"src.modules.{module}.application.*")
        .exclude("src.modules.catalog.application.queries.get_category_tree")
        .should_not_import(f"src.modules.{module}.infrastructure.*")
        .check("src")
    )
```

- [ ] **Step 2: Run architecture tests**

Run: `uv run pytest tests/architecture/ -v --tb=short -x`
Expected: All rules pass

- [ ] **Step 3: Commit**

```bash
git add tests/architecture/test_boundaries.py
git commit -m "feat(tests): enhance architecture fitness functions — all 7 spec rules with parameterization"
```

---

### Task 3b.1: Identity domain unit tests `[PARALLEL]`

**Files:**
- Modify: `tests/unit/modules/identity/domain/test_entities.py`
- Modify: `tests/unit/modules/identity/domain/test_value_objects.py`
- Create: `tests/unit/modules/identity/domain/test_events.py`

- [ ] **Step 1: Refactor `test_entities.py` to use IdentityMothers + add missing tests**

Add these tests to the existing file (refactor existing tests to use `IdentityMothers` where applicable):

```python
# Add to imports:
from tests.factories.identity_mothers import IdentityMothers

# Add to class TestIdentity:
def test_register_oidc_type(self):
    identity = IdentityMothers.active_oidc()
    assert identity.type == IdentityType.OIDC
    assert identity.is_active is True

# Add to class TestSession:
def test_ensure_valid_passes_when_fresh(self):
    _, session, _ = IdentityMothers.with_session()
    session.ensure_valid()  # should not raise
```

- [ ] **Step 2: Create `test_events.py`**

```python
# tests/unit/modules/identity/domain/test_events.py
"""Tests for Identity domain event field population."""
import uuid
from datetime import datetime

from src.modules.identity.domain.events import (
    IdentityDeactivatedEvent,
    IdentityRegisteredEvent,
    RoleAssignmentChangedEvent,
)


class TestIdentityRegisteredEvent:
    def test_fields_populated(self):
        event = IdentityRegisteredEvent(
            identity_id=uuid.uuid4(),
            email="test@example.com",
        )
        assert event.aggregate_type == "Identity"
        assert event.event_type == "IdentityRegisteredEvent"
        assert event.email == "test@example.com"
        assert isinstance(event.registered_at, datetime)

    def test_aggregate_id_set_from_identity_id(self):
        identity_id = uuid.uuid4()
        event = IdentityRegisteredEvent(identity_id=identity_id, email="a@b.com")
        assert event.aggregate_id == str(identity_id)


class TestIdentityDeactivatedEvent:
    def test_fields_populated(self):
        identity_id = uuid.uuid4()
        event = IdentityDeactivatedEvent(
            identity_id=identity_id, reason="user_request"
        )
        assert event.aggregate_type == "Identity"
        assert event.event_type == "IdentityDeactivatedEvent"
        assert event.reason == "user_request"
        assert isinstance(event.deactivated_at, datetime)


class TestRoleAssignmentChangedEvent:
    def test_assigned_action(self):
        event = RoleAssignmentChangedEvent(
            identity_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            action="assigned",
        )
        assert event.action == "assigned"
        assert event.aggregate_type == "Identity"

    def test_revoked_action(self):
        event = RoleAssignmentChangedEvent(
            identity_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            action="revoked",
        )
        assert event.action == "revoked"
```

- [ ] **Step 3: Enhance `test_value_objects.py` — add PermissionCode format validation tests**

```python
# Add to test_value_objects.py:
def test_permission_code_valid_format(self):
    pc = PermissionCode("brands:create")
    assert pc.resource == "brands"
    assert pc.action == "create"

def test_permission_code_invalid_format_raises(self):
    with pytest.raises(ValueError):
        PermissionCode("invalid_no_colon")
```

- [ ] **Step 4: Run identity unit tests**

Run: `uv run pytest tests/unit/modules/identity/ -v --tb=short`
Expected: All tests pass

---

### Task 3b.2: Catalog domain unit tests `[PARALLEL]`

**Files:**
- Modify: `tests/unit/modules/catalog/domain/test_entities.py`
- Modify: `tests/unit/modules/catalog/domain/test_events.py`
- Modify: `tests/unit/modules/catalog/domain/test_value_objects.py`

- [ ] **Step 1: Refactor `test_entities.py` to use BrandMothers + add missing FSM coverage**

Add these tests:
```python
from tests.factories.catalog_mothers import BrandMothers, CategoryMothers

# Full Brand FSM — invalid transitions:
def test_brand_confirm_upload_from_completed_raises():
    brand = BrandMothers.with_completed_logo()
    with pytest.raises(InvalidLogoStateException):
        brand.confirm_logo_upload()

def test_brand_complete_processing_from_pending_raises():
    brand = BrandMothers.with_pending_logo()
    with pytest.raises(InvalidLogoStateException):
        brand.complete_logo_processing(url="https://cdn.test/logo.webp")

# Category depth enforcement:
def test_category_create_child_increments_level():
    root = CategoryMothers.root()
    child = CategoryMothers.child(parent=root)
    assert child.level == root.level + 1

def test_category_create_child_builds_full_slug():
    root = CategoryMothers.root(slug="electronics")
    child = Category.create_child(name="Phones", slug="phones", parent=root)
    assert child.full_slug == "electronics/phones"
```

- [ ] **Step 2: Add `MediaProcessingStatus` enum tests to `test_value_objects.py`**

```python
def test_media_processing_status_members():
    assert set(MediaProcessingStatus) == {
        MediaProcessingStatus.PENDING_UPLOAD,
        MediaProcessingStatus.PROCESSING,
        MediaProcessingStatus.COMPLETED,
        MediaProcessingStatus.FAILED,
    }
```

- [ ] **Step 3: Run catalog unit tests**

Run: `uv run pytest tests/unit/modules/catalog/ -v --tb=short`

---

### Task 3b.3: User domain unit tests `[PARALLEL]`

**Files:**
- Modify: `tests/unit/modules/user/domain/test_entities.py`

- [ ] **Step 1: Refactor to use UserMothers + add missing tests**

```python
from tests.factories.user_mothers import UserMothers

# Replace self._make_user() calls with UserMothers.with_profile()
# Add:
def test_create_from_identity_uses_shared_pk(self):
    identity_id = uuid.uuid4()
    user = UserMothers.active(identity_id=identity_id)
    assert user.id == identity_id

def test_update_profile_partial_fields(self):
    user = UserMothers.with_profile(first_name="John", last_name="Doe")
    user.update_profile(first_name="Jane")
    assert user.first_name == "Jane"
    assert user.last_name == "Doe"  # unchanged
```

- [ ] **Step 2: Run user unit tests**

Run: `uv run pytest tests/unit/modules/user/ -v --tb=short`

---

### Task 3b.4: Storage domain unit tests `[PARALLEL]`

**Files:**
- Create: `tests/unit/modules/storage/__init__.py`
- Create: `tests/unit/modules/storage/domain/__init__.py`
- Create: `tests/unit/modules/storage/domain/test_entities.py`

- [ ] **Step 1: Create directory structure with `__init__.py` files**

- [ ] **Step 2: Create `test_entities.py`**

```python
# tests/unit/modules/storage/domain/test_entities.py
"""Tests for Storage domain entity."""
import uuid

from tests.factories.storage_mothers import StorageFileMothers


class TestStorageFile:
    def test_create_sets_fields(self):
        sf = StorageFileMothers.pending()
        assert sf.bucket_name == "test-bucket"
        assert sf.content_type == "image/png"
        assert isinstance(sf.id, uuid.UUID)
        assert sf.is_latest is True

    def test_create_with_owner_module(self):
        sf = StorageFileMothers.pending(owner_module="identity")
        assert sf.owner_module == "identity"

    def test_create_active_has_size(self):
        sf = StorageFileMothers.active(size_bytes=2048)
        assert sf.size_bytes == 2048
        assert sf.content_type == "image/webp"
```

- [ ] **Step 3: Run storage unit tests**

Run: `uv run pytest tests/unit/modules/storage/ -v --tb=short`

---

### Chunk 3 — Verification Gate

```bash
# Architecture tests — HARD BLOCK if any fail
uv run pytest tests/architecture/ -v --tb=short -x

# Unit tests — all modules
uv run pytest tests/unit/ -v --tb=short

# Combined
uv run pytest tests/architecture/ tests/unit/ -v --tb=short -x
```

**Commit:**
```bash
git add tests/architecture/ tests/unit/
git commit -m "feat(tests): architecture fitness functions (7 rules) + domain unit tests (all modules)"
```

---

## Chunk 4: CQRS Integration Tests (Application + Infrastructure)

> **Effort:** High
> **Parallelism:** `[PARALLEL]` across modules — each module's tests are in separate directories
> **Prerequisites:** Chunks 1-3 complete, Docker containers running (`docker compose up -d`)

### Task 4a.1: Identity repository tests `[PARALLEL]`

**Files:**
- Create: `tests/integration/modules/identity/__init__.py`
- Create: `tests/integration/modules/identity/infrastructure/__init__.py`
- Create: `tests/integration/modules/identity/infrastructure/repositories/__init__.py`
- Create: `tests/integration/modules/identity/infrastructure/repositories/test_identity_repo.py`

- [ ] **Step 1: Create directory structure with `__init__.py` files**

- [ ] **Step 2: Create `test_identity_repo.py`**

```python
# tests/integration/modules/identity/infrastructure/repositories/test_identity_repo.py
"""Integration tests for IdentityRepository — Data Mapper correctness."""
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.models import Identity as IdentityModel
from src.modules.identity.infrastructure.repositories import IdentityRepository


async def test_add_identity_persists_to_db(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        repo = await request.get(IdentityRepository)
        identity = Identity.register(IdentityType.LOCAL)
        await repo.add(identity)
        await db_session.flush()

    orm = await db_session.get(IdentityModel, identity.id)
    assert orm is not None
    assert orm.type == IdentityType.LOCAL.value


async def test_get_identity_returns_domain_entity(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        repo = await request.get(IdentityRepository)
        identity = Identity.register(IdentityType.LOCAL)
        await repo.add(identity)
        await db_session.flush()

        result = await repo.get(identity.id)

    assert result is not None
    assert result.id == identity.id
    assert result.is_active is True


async def test_email_exists_returns_true_for_existing(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """Register via handler to get credentials, then check email_exists."""
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        await handler.handle(
            RegisterCommand(email="exists@example.com", password="S3cure!Pass")
        )

    async with app_container() as request:
        repo = await request.get(IdentityRepository)
        assert await repo.email_exists("exists@example.com") is True
        assert await repo.email_exists("nope@example.com") is False
```

- [ ] **Step 3: Run**

Run: `uv run pytest tests/integration/modules/identity/infrastructure/ -v --tb=short -x`

---

### Task 4a.2: Identity session repository tests `[PARALLEL]`

**Files:**
- Create: `tests/integration/modules/identity/infrastructure/repositories/test_session_repo.py`

- [ ] **Step 1: Create test file**

```python
# tests/integration/modules/identity/infrastructure/repositories/test_session_repo.py
"""Integration tests for SessionRepository."""
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, Session
from src.modules.identity.domain.value_objects import IdentityType
from src.modules.identity.infrastructure.repositories import (
    IdentityRepository,
    SessionRepository,
)


async def test_add_session_persists_with_hashed_token(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        identity_repo = await request.get(IdentityRepository)
        session_repo = await request.get(SessionRepository)

        identity = Identity.register(IdentityType.LOCAL)
        await identity_repo.add(identity)
        await db_session.flush()

        raw_token = "test-refresh-token"
        session = Session.create(
            identity_id=identity.id,
            refresh_token=raw_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            role_ids=[],
        )
        await session_repo.add(session)
        await db_session.flush()

        result = await session_repo.get(session.id)

    assert result is not None
    assert result.identity_id == identity.id


async def test_revoke_all_for_identity(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        identity_repo = await request.get(IdentityRepository)
        session_repo = await request.get(SessionRepository)

        identity = Identity.register(IdentityType.LOCAL)
        await identity_repo.add(identity)
        await db_session.flush()

        for i in range(3):
            s = Session.create(
                identity_id=identity.id,
                refresh_token=f"token-{i}",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
                role_ids=[],
            )
            await session_repo.add(s)
        await db_session.flush()

        revoked_ids = await session_repo.revoke_all_for_identity(identity.id)

    assert len(revoked_ids) == 3
```

- [ ] **Step 2: Run**

Run: `uv run pytest tests/integration/modules/identity/infrastructure/repositories/test_session_repo.py -v --tb=short -x`

---

### Task 4a.3: Identity command handler tests `[PARALLEL]`

**Files:**
- Create: `tests/integration/modules/identity/application/__init__.py`
- Create: `tests/integration/modules/identity/application/commands/__init__.py`
- Create: `tests/integration/modules/identity/application/commands/test_register.py`
- Create: `tests/integration/modules/identity/application/commands/test_login.py`

- [ ] **Step 1: Create `test_register.py`**

```python
# tests/integration/modules/identity/application/commands/test_register.py
"""Integration tests for RegisterHandler — full CQRS command flow."""
import pytest
from dishka import AsyncContainer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.domain.exceptions import IdentityAlreadyExistsError
from src.modules.identity.infrastructure.models import Identity as IdentityModel


async def test_register_creates_identity_and_credentials(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        result = await handler.handle(
            RegisterCommand(email="new@example.com", password="S3cure!Pass")
        )

    assert result.identity_id is not None
    orm = await db_session.get(IdentityModel, result.identity_id)
    assert orm is not None
    assert orm.type == "LOCAL"


async def test_register_emits_identity_registered_event_to_outbox(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        result = await handler.handle(
            RegisterCommand(email="outbox@example.com", password="S3cure!Pass")
        )

    outbox_result = await db_session.execute(
        select(OutboxMessage).where(
            OutboxMessage.aggregate_type == "Identity",
            OutboxMessage.aggregate_id == str(result.identity_id),
            OutboxMessage.event_type == "IdentityRegisteredEvent",
        )
    )
    outbox_row = outbox_result.scalar_one_or_none()
    assert outbox_row is not None


async def test_register_raises_conflict_on_duplicate_email(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        await handler.handle(
            RegisterCommand(email="dupe@example.com", password="S3cure!Pass")
        )

    with pytest.raises((IdentityAlreadyExistsError, Exception)):
        async with app_container() as request:
            handler = await request.get(RegisterHandler)
            await handler.handle(
                RegisterCommand(email="dupe@example.com", password="S3cure!Pass")
            )
```

- [ ] **Step 2: Create `test_login.py`**

```python
# tests/integration/modules/identity/application/commands/test_login.py
"""Integration tests for LoginHandler."""
import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.commands.login import (
    LoginCommand,
    LoginHandler,
)
from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.domain.exceptions import InvalidCredentialsError


async def test_login_returns_tokens_for_valid_credentials(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Register first
    async with app_container() as request:
        reg_handler = await request.get(RegisterHandler)
        await reg_handler.handle(
            RegisterCommand(email="login@example.com", password="S3cure!Pass")
        )

    # Login
    async with app_container() as request:
        login_handler = await request.get(LoginHandler)
        result = await login_handler.handle(
            LoginCommand(
                email="login@example.com",
                password="S3cure!Pass",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
            )
        )

    assert result.access_token is not None
    assert result.refresh_token is not None


async def test_login_raises_invalid_credentials_for_wrong_password(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        reg_handler = await request.get(RegisterHandler)
        await reg_handler.handle(
            RegisterCommand(email="wrongpw@example.com", password="S3cure!Pass")
        )

    with pytest.raises(InvalidCredentialsError):
        async with app_container() as request:
            handler = await request.get(LoginHandler)
            await handler.handle(
                LoginCommand(
                    email="wrongpw@example.com",
                    password="WrongPassword!",
                    ip_address="127.0.0.1",
                    user_agent="TestAgent/1.0",
                )
            )
```

- [ ] **Step 3: Run identity integration tests**

Run: `uv run pytest tests/integration/modules/identity/ -v --tb=short -x`

---

### Task 4b.1: Refactor existing catalog integration tests `[PARALLEL]`

**Files:**
- Modify: `tests/integration/modules/catalog/application/commands/test_create_brand.py`

- [ ] **Step 1: Refactor to use `InMemoryBlobStorage` Fake instead of `patch.object` + `AsyncMock`**

Replace `patch.object(blob_storage, ...)` with direct assertions against the `InMemoryBlobStorage` behavior. The Fake returns deterministic presigned URLs.

- [ ] **Step 2: Run catalog integration tests**

Run: `uv run pytest tests/integration/modules/catalog/ -v --tb=short -x`

---

### Task 4c.1: User integration tests `[PARALLEL]`

**Files:**
- Create: `tests/integration/modules/user/__init__.py`
- Create: `tests/integration/modules/user/application/__init__.py`
- Create: `tests/integration/modules/user/application/commands/__init__.py`
- Create: `tests/integration/modules/user/application/commands/test_create_user.py`

- [ ] **Step 1: Create `test_create_user.py`**

```python
# tests/integration/modules/user/application/commands/test_create_user.py
"""Integration tests for CreateUserHandler."""
import uuid

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.application.commands.create_user import (
    CreateUserCommand,
    CreateUserHandler,
)
from src.modules.user.infrastructure.models import User as UserModel


async def test_create_user_from_identity_event(
    app_container: AsyncContainer, db_session: AsyncSession
):
    identity_id = uuid.uuid4()

    async with app_container() as request:
        handler = await request.get(CreateUserHandler)
        await handler.handle(
            CreateUserCommand(identity_id=identity_id, profile_email="new@example.com")
        )

    orm = await db_session.get(UserModel, identity_id)
    assert orm is not None
    assert orm.id == identity_id  # Shared PK with Identity
```

- [ ] **Step 2: Run user integration tests**

Run: `uv run pytest tests/integration/modules/user/ -v --tb=short -x`

---

### Chunk 4 — Verification Gate

```bash
# All integration tests
uv run pytest tests/integration/ -v --tb=short -x

# Full regression: architecture + unit + integration
uv run pytest tests/architecture/ tests/unit/ tests/integration/ -v --tb=short -x
```

**Commit:**
```bash
git add tests/integration/
git commit -m "feat(tests): CQRS integration tests — Identity handlers, session repo, user creation"
```

---

## Chunk 5: E2E Tests & Load Testing Setup

> **Effort:** Medium
> **Parallelism:** `[PARALLEL]` after Task 5a.5 (auth helper) is done first
> **Prerequisites:** Chunks 1-4 complete

### Task 5a.5: E2E auth helper fixture `[SEQUENTIAL — must complete before 5a.1-5a.4]`

**Files:**
- Modify: `tests/e2e/conftest.py`

- [ ] **Step 1: Add `authenticated_client` fixture**

Add to `tests/e2e/conftest.py`:

```python
@pytest.fixture
async def authenticated_client(
    async_client: AsyncClient, db_session: AsyncSession
) -> AsyncClient:
    """Register a user, login, and return a client with Authorization header."""
    import uuid

    email = f"e2e-{uuid.uuid4().hex[:8]}@test.com"
    password = "S3cure!TestPass"

    # Register
    await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
    })

    # Login
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    tokens = login_resp.json()
    access_token = tokens["access_token"]

    # Return client with auth header set
    async_client.headers["Authorization"] = f"Bearer {access_token}"
    return async_client
```

- [ ] **Step 2: Run existing e2e tests**

Run: `uv run pytest tests/e2e/ -v --tb=short -x`

---

### Task 5a.1: Auth e2e tests `[PARALLEL]`

**Files:**
- Create: `tests/e2e/api/v1/test_auth.py`

- [ ] **Step 1: Create auth e2e tests**

```python
# tests/e2e/api/v1/test_auth.py
"""E2E tests for /auth/* endpoints."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_register_returns_201_with_identity_id(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"reg-{uuid.uuid4().hex[:8]}@test.com"
    response = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "S3cure!Pass",
    })
    assert response.status_code == 201
    assert "identity_id" in response.json()


async def test_register_returns_409_when_email_exists(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"dupe-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "S3cure!Pass",
    })
    response = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "S3cure!Pass",
    })
    assert response.status_code == 409


async def test_login_returns_200_with_tokens(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"login-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "S3cure!Pass",
    })
    response = await async_client.post("/api/v1/auth/login", json={
        "email": email, "password": "S3cure!Pass",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_returns_401_for_wrong_password(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"bad-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "S3cure!Pass",
    })
    response = await async_client.post("/api/v1/auth/login", json={
        "email": email, "password": "WrongPassword!",
    })
    assert response.status_code == 401
```

- [ ] **Step 2: Run auth e2e tests**

Run: `uv run pytest tests/e2e/api/v1/test_auth.py -v --tb=short -x`

---

### Task 5a.2: Users e2e tests `[PARALLEL]`

**Files:**
- Create: `tests/e2e/api/v1/test_users.py`

- [ ] **Step 1: Create users e2e tests**

```python
# tests/e2e/api/v1/test_users.py
"""E2E tests for /users/* endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_get_my_profile_returns_401_without_token(
    async_client: AsyncClient, db_session: AsyncSession
):
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 401
```

- [ ] **Step 2: Run users e2e tests**

Run: `uv run pytest tests/e2e/api/v1/test_users.py -v --tb=short -x`

---

### Task 5b.1: Load test thresholds `[PARALLEL]`

**Files:**
- Create: `tests/load/thresholds.yml`

- [ ] **Step 1: Create threshold definitions**

```yaml
# tests/load/thresholds.yml
scenarios:
  auth_flow:
    max_p99_ms: 500
    max_error_rate: 0.001
    min_rps: 100
  catalog_browse:
    max_p99_ms: 200
    max_error_rate: 0.0001
    min_rps: 500
  connection_pool_saturation:
    expect_graceful_503: true
    max_connection_leak_count: 0
  mixed_workload:
    max_p99_ms: 300
    max_error_rate: 0.005
    min_rps: 1000
    duration_minutes: 5
```

---

### Task 5b.2: Auth flow load test `[PARALLEL]`

**Files:**
- Create: `tests/load/scenarios/auth_flow.py`

- [ ] **Step 1: Create auth flow scenario**

```python
# tests/load/scenarios/auth_flow.py
"""Locust scenario: Register -> Login -> Refresh -> Logout."""
import uuid

from locust import HttpUser, between, task


class AuthFlowUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        self.email = f"load-{uuid.uuid4().hex[:8]}@test.com"
        self.password = "S3cure!LoadTest"
        self.access_token = None
        self.refresh_token = None

    @task(1)
    def full_auth_flow(self):
        # Register
        self.client.post("/api/v1/auth/register", json={
            "email": self.email,
            "password": self.password,
        })

        # Login
        resp = self.client.post("/api/v1/auth/login", json={
            "email": self.email,
            "password": self.password,
        })
        if resp.status_code == 200:
            data = resp.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")

        # Refresh
        if self.refresh_token:
            self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token},
            )

        # Logout
        if self.access_token:
            self.client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

        # Reset for next iteration
        self.email = f"load-{uuid.uuid4().hex[:8]}@test.com"
```

---

### Task 5b.3: Mixed workload load test `[PARALLEL]`

**Files:**
- Create: `tests/load/scenarios/mixed_workload.py`

- [ ] **Step 1: Create mixed workload scenario**

```python
# tests/load/scenarios/mixed_workload.py
"""Locust scenario: 80% reads, 20% writes — realistic multi-user simulation."""
import uuid

from locust import HttpUser, between, task


class MixedWorkloadUser(HttpUser):
    wait_time = between(0.5, 2)
    host = "http://localhost:8000"

    @task(8)
    def browse_categories(self):
        """80% weight: read category tree."""
        self.client.get("/api/v1/catalog/categories")

    @task(2)
    def create_brand(self):
        """20% weight: create a brand."""
        self.client.post("/api/v1/catalog/brands", json={
            "name": f"Load Brand {uuid.uuid4().hex[:6]}",
            "slug": f"load-brand-{uuid.uuid4().hex[:6]}",
        })
```

---

### Chunk 5 — Verification Gate

```bash
# E2E tests
uv run pytest tests/e2e/ -v --tb=short -x

# FULL SUITE — the final quality gate
uv run ruff check --fix . && uv run ruff format .
uv run pytest tests/architecture/ -v -x
uv run pytest tests/unit/ -v --tb=short
uv run pytest tests/integration/ -v --tb=short
uv run pytest tests/e2e/ -v --tb=short

# Coverage gate
uv run pytest tests/unit/ tests/integration/ tests/e2e/ \
    --cov=src --cov-branch \
    --cov-fail-under=80 \
    --cov-report=term-missing
```

**Commit:**
```bash
git add tests/e2e/ tests/load/
git commit -m "feat(tests): e2e auth/user tests + Locust load test scenarios + thresholds"
```

---

## Execution Summary

| Chunk | Name | Effort | Parallelism | Tasks | Key Constraint |
|-------|------|--------|-------------|-------|----------------|
| **1** | Foundation | Critical | `SEQUENTIAL` | 5 | Root fixtures — no concurrent edits |
| **2** | Data Generation | Medium | `PARALLEL` (7 subagents) | 7 | Each file independent |
| **3a** | Architecture Tests | Medium | `PARALLEL` with 3b | 1 | Single file |
| **3b** | Unit Tests | High | `PARALLEL` (4 subagents) | 4 | One subagent per module |
| **4** | Integration Tests | High | `PARALLEL` (3 module groups) | 5 | Docker containers required |
| **5a** | E2E Tests | Medium | `PARALLEL` (after helper) | 3 | Auth helper first |
| **5b** | Load Tests | Low | `PARALLEL` | 3 | Separate runner |

### Maximum Parallelism Points

| Phase | Max Concurrent Subagents | Conflict Risk |
|-------|--------------------------|---------------|
| Chunk 2 | **7** | None — all new files in `tests/factories/` |
| Chunk 3 | **5** (1 arch + 4 unit modules) | None — separate directories |
| Chunk 4 | **5** (all tasks independent) | None — separate module directories |
| Chunk 5a | **3** (after helper built) | `tests/e2e/conftest.py` done first |

### Subagent Worktree Isolation Rules

Per CLAUDE.md Section 2:
- All `[PARALLEL]` tasks MUST use `isolation: "worktree"`
- Each subagent creates files in its own worktree branch
- Merge order: Chunk N fully merged before Chunk N+1 starts
- Conflict resolution: if two subagents accidentally touch the same file, the later merge is rebased
