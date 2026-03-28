# Testing Patterns

**Analysis Date:** 2026-03-28

## Test Framework

**Runner:**
- pytest 9.x (via `uv run pytest`)
- Config: `backend/pytest.ini` (primary, takes precedence) and `backend/pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- Plain `assert` statements (pytest native)
- `pytest.raises(ExceptionType)` for exception testing, sometimes with `match=` for message validation

**Async Support:**
- pytest-asyncio 1.3+ with `asyncio_mode = "auto"` (all `async def test_*` are auto-detected)
- Session-scoped event loop: `asyncio_default_fixture_loop_scope = session`
- Session-scoped test loop: `asyncio_default_test_loop_scope = session`

**Plugins:**
- `pytest-cov` -- coverage collection (auto-enabled via `addopts`)
- `pytest-archon` -- architecture boundary fitness tests
- `pytest-randomly` -- randomized test ordering
- `pytest-timeout` -- 30s timeout per test (thread method)
- `polyfactory` -- Pydantic/SQLAlchemy model factories
- `respx` -- httpx mock library (available, for mocking HTTP clients)
- `dirty-equals` -- flexible assertion comparisons (available)
- `hypothesis` -- property-based testing (available)
- `testcontainers` -- Docker-based infrastructure (postgres, redis, rabbitmq, minio)
- `schemathesis` -- OpenAPI-driven fuzz testing (available)

**Run Commands:**
```bash
uv run pytest tests/ -v                  # Run all tests
uv run pytest tests/unit/ -v             # Unit tests only
uv run pytest tests/integration/ -v      # Integration tests only
uv run pytest tests/e2e/ -v              # E2E tests only
uv run pytest tests/architecture/ -v     # Architecture fitness tests
make test                                # All tests (via Makefile)
make test-unit                           # Unit tests (via Makefile)
make test-integration                    # Integration tests
make test-e2e                            # E2E tests
make test-architecture                   # Architecture tests
```

## Test File Organization

**Location:**
- Separate `tests/` directory (not co-located with source)
- Mirrors the `src/` module structure under each test category

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestIdentity`, `TestSession`, `TestAdminDeactivateIdentityHandler`)
- Test functions: `test_*` (e.g., `test_create_brand_e2e_success`)

**Structure:**
```
backend/tests/
├── conftest.py                          # Root: event loop, DB/Redis URLs, DI container, db_session
├── architecture/
│   ├── conftest.py                      # pytestmark = pytest.mark.architecture
│   └── test_boundaries.py              # pytest-archon layer/module rules
├── unit/
│   ├── conftest.py                      # (empty marker)
│   ├── infrastructure/
│   │   ├── database/models/            # ORM model unit tests
│   │   ├── logging/                    # DLQ middleware tests
│   │   ├── outbox/                     # Outbox relay tests
│   │   └── security/                   # Telegram validator tests
│   ├── modules/
│   │   ├── catalog/                    # (planned, growing)
│   │   ├── identity/
│   │   │   ├── application/commands/   # Admin RBAC command handler tests
│   │   │   ├── application/consumers/  # Event consumer tests
│   │   │   ├── domain/                 # Entity, VO, event, exception tests
│   │   │   ├── management/             # System role sync tests
│   │   │   └── presentation/           # Schema validation tests
│   │   ├── supplier/domain/            # Supplier entity tests
│   │   └── user/
│   │       ├── application/commands/   # Profile command tests
│   │       ├── application/consumers/  # Identity event consumer tests
│   │       ├── domain/                 # Customer, referral, staff tests
│   │       └── presentation/           # Schema validation tests
│   └── shared/                         # CamelModel, DomainEvent tests
├── integration/
│   ├── conftest.py                     # Overrides db_session, adds _flush_redis
│   ├── bootstrap/                      # Worker init, broker tests
│   └── modules/
│       ├── catalog/
│       │   ├── application/commands/   # CreateBrand with real DB + DI
│       │   └── infrastructure/repositories/  # Brand, Category repos with real DB
│       ├── identity/
│       │   ├── application/commands/   # Login handler integration
│       │   ├── application/queries/    # Permission/role queries
│       │   └── infrastructure/repositories/  # Identity, session, role repos
│       └── supplier/                   # Supplier lifecycle + CRUD tests
├── e2e/
│   ├── conftest.py                     # FastAPI app, httpx AsyncClient, auth fixtures
│   └── api/v1/                         # HTTP round-trip tests per endpoint group
│       ├── test_auth.py               # Register, login
│       ├── test_auth_telegram.py      # Telegram auth flow
│       ├── test_brands.py             # Brand CRUD
│       ├── test_categories.py         # Category CRUD
│       └── test_users.py             # Profile endpoints
├── load/
│   ├── locustfile.py                   # Locust runner
│   └── scenarios/                      # Load test scenarios
│       ├── auth_flow.py
│       ├── browse_catalog.py
│       └── mixed_workload.py
├── factories/
│   ├── builders.py                     # Fluent Builder pattern (RoleBuilder, SessionBuilder, CategoryBuilder)
│   ├── catalog_factories.py           # (empty placeholder)
│   ├── identity_mothers.py            # Object Mother pattern (IdentityMothers, SessionMothers, RoleMothers, etc.)
│   ├── schema_factories.py            # Polyfactory Pydantic schema factories
│   └── storage_factories.py           # (empty placeholder)
├── fakes/
│   └── oidc_provider.py               # StubOIDCProvider for tests
└── utils/
    ├── catalog_query_baselines.py     # Expected query count baselines for N+1 regression
    └── query_counter.py               # assert_query_count() async context manager
```

## Test Types and Markers

**Registered markers** (in `backend/pytest.ini`):
```ini
markers =
    architecture: Fitness functions and boundary enforcement
    unit: Domain-layer pure logic, zero I/O
    integration: Application + Infrastructure with real database
    e2e: Presentation-layer HTTP round-trips
    load: Resilience and threshold testing (Locust)
```

**Strict markers enforced:** `--strict-markers` prevents typos in marker names.

**Default addopts** (from `backend/pytest.ini`):
```ini
addopts =
    -v
    --strict-markers
    --cov=src
    --cov-report=term-missing:skip-covered
    --cov-report=xml
```

**Timeout:** 30 seconds per test (`timeout = 30`, `timeout_method = thread`).

## Test Structure

### Unit Test Pattern (Domain Entity)

Tests organized in `TestClassName` classes with one assertion per test method. Use factory methods or Object Mothers:

```python
# backend/tests/unit/modules/identity/domain/test_entities.py
from tests.factories.identity_mothers import IdentityMothers

class TestIdentity:
    def test_register_creates_active_identity(self):
        identity = Identity.register(IdentityType.LOCAL)
        assert identity.is_active is True
        assert identity.type == IdentityType.LOCAL
        assert isinstance(identity.id, uuid.UUID)

    def test_deactivate_emits_event(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="user_request")
        events = identity.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, IdentityDeactivatedEvent)
        assert event.identity_id == identity.id

    def test_ensure_active_raises_when_deactivated(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="test")
        with pytest.raises(IdentityDeactivatedError):
            identity.ensure_active()
```

### Unit Test Pattern (Command Handler with Mocks)

Use `unittest.mock.AsyncMock` and `MagicMock` for dependencies. Define `make_uow()` and `make_logger()` module-level helpers. Use `_make_handler()` class method to reduce boilerplate:

```python
# backend/tests/unit/modules/identity/application/commands/test_admin_commands.py
from unittest.mock import AsyncMock, MagicMock

def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow

def make_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger

class TestAdminDeactivateIdentityHandler:
    def _make_handler(
        self,
        identity_repo: AsyncMock | None = None,
        uow: AsyncMock | None = None,
        logger: MagicMock | None = None,
    ) -> AdminDeactivateIdentityHandler:
        return AdminDeactivateIdentityHandler(
            identity_repo=identity_repo or AsyncMock(),
            uow=uow or make_uow(),
            logger=logger or make_logger(),
        )

    async def test_admin_deactivate_success(self) -> None:
        identity = make_identity(identity_id=uuid.uuid4(), is_active=True)
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        await handler.handle(AdminDeactivateIdentityCommand(...))

        assert identity.is_active is False
        identity_repo.update.assert_awaited_once_with(identity)

    async def test_admin_deactivate_identity_not_found(self) -> None:
        identity_repo = AsyncMock()
        identity_repo.get.return_value = None
        handler = self._make_handler(identity_repo=identity_repo)

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(AdminDeactivateIdentityCommand(...))
        assert exc_info.value.error_code == "IDENTITY_NOT_FOUND"
```

### Unit Test Pattern (Schema Validation)

Validate Pydantic schema constraints (min/max length, patterns, required fields):

```python
# backend/tests/unit/modules/identity/presentation/test_schemas.py
class TestRegisterRequest:
    def test_valid_registration(self):
        m = RegisterRequest(email="new@example.com", password="S3cure!Pass")
        assert m.email == "new@example.com"

    def test_password_min_length_8(self):
        with pytest.raises(ValidationError, match="password"):
            RegisterRequest(email="new@example.com", password="short")

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError, match="email"):
            RegisterRequest(email="not-an-email", password="S3cure!Pass")

    @pytest.mark.parametrize("name", ["Admin", "has-dash", "has space"])
    def test_name_pattern_rejects_invalid(self, name: str):
        with pytest.raises(ValidationError, match="name"):
            CreateRoleRequest(name=name)
```

### Integration Test Pattern (Repository)

Uses real PostgreSQL via `db_session` fixture. Follow Arrange-Act-Assert with comments:

```python
# backend/tests/integration/modules/catalog/infrastructure/repositories/test_brand.py
async def test_brand_repository_add_and_get(db_session: AsyncSession):
    # Arrange
    repository = BrandRepository(session=db_session)
    brand = Brand.create(name="Nike", slug="nike", logo_url="https://cdn.example.com/nike.png")

    # Act
    added_brand = await repository.add(brand)
    fetched_brand = await repository.get(brand.id)

    # Assert
    assert added_brand.id == brand.id
    assert fetched_brand is not None
    assert fetched_brand.name == "Nike"
```

Some integration tests use local helper functions for entity creation:

```python
# backend/tests/integration/modules/catalog/infrastructure/repositories/test_brand_extended.py
def _make_brand(name: str = "TestBrand", slug: str | None = None) -> Brand:
    return Brand.create(name=name, slug=slug or name.lower().replace(" ", "-"))
```

### Integration Test Pattern (Command Handler via DI)

Uses the Dishka container to get a fully wired handler:

```python
# backend/tests/integration/modules/catalog/application/commands/test_create_brand.py
async def test_create_brand_handler_without_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request_container:
        handler = await request_container.get(CreateBrandHandler)
        command = CreateBrandCommand(name="TestBrand", slug="testbrand")
        result = await handler.handle(command)

    assert result.brand_id is not None
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.slug == "testbrand"
```

### E2E Test Pattern (HTTP Round-Trip)

Uses `httpx.AsyncClient` with `ASGITransport`:

```python
# backend/tests/e2e/api/v1/test_brands.py
pytestmark = pytest.mark.asyncio

async def test_create_brand_e2e_success(
    admin_client: AsyncClient,
    db_session: AsyncSession,
):
    payload = {
        "name": "E2E Brand",
        "slug": "e2e-brand",
        "logoUrl": "https://cdn.example.com/brands/e2e.webp",
    }
    response = await admin_client.post("/api/v1/catalog/brands", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
```

### Architecture Fitness Test Pattern

Uses `pytest-archon` for static import analysis:

```python
# backend/tests/architecture/test_boundaries.py
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
```

**Rules enforced:**
1. Domain layer purity (no outer layer imports)
2. Domain has zero framework imports (no SQLAlchemy, FastAPI, Dishka, etc.)
3. Application layer independence (excludes CQRS queries and event consumers)
4. Infrastructure does not import Presentation
5. Cross-module isolation (explicit allowlist for cross-module dependencies)
6. Shared kernel independence
7. No reverse layer dependencies within a module

## Database Isolation Strategy

### Root conftest (`backend/tests/conftest.py`)

**Session-scoped infrastructure:**
- Single event loop for entire test session
- Single async engine with `NullPool` (no connection pooling in tests)
- `Base.metadata.drop_all` / `create_all` once per session
- Dishka container created once per session with `TestOverridesProvider`
- Fail-fast DB connectivity check: `SELECT 1` before running tests

**Function-scoped isolation:**
- Each test gets a `db_session` wrapped in a nested transaction (savepoint)
- Session stored in `contextvars.ContextVar` (`_db_session_var`) so Dishka injects the same session into handlers
- Automatic rollback after each test -- no data leaks between tests

```python
@pytest.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncIterable[AsyncSession]:
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        await conn.begin_nested()
        maker = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        session = maker()
        token = _db_session_var.set(session)
        yield session
        _db_session_var.reset(token)
        await session.close()
        await transaction.rollback()
```

### Redis Isolation

- `_flush_redis` fixture flushes Redis after each test
- Not autouse at root level -- applied via integration/e2e conftest to avoid triggering DI container for unit tests

### ContextVar Reset

- `_reset_context_vars` (autouse) resets the `request_id` ContextVar per test to prevent cross-test contamination

## Mocking

**Framework:** `unittest.mock` (stdlib) -- `AsyncMock`, `MagicMock`, `patch`

**Standard Mock Patterns (unit tests):**

```python
# UnitOfWork mock (async context manager)
def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow

# Logger mock (bind returns self)
def make_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger

# Repository mock (async methods)
customer_repo = AsyncMock()
customer_repo.get = AsyncMock(return_value=customer_entity)
```

**E2E Auth Mock Pattern** (from `backend/tests/e2e/conftest.py`):
```python
# admin_client fixture seeds Redis cache with permissions to bypass DB checks
payload = jwt.decode(access_token, options={"verify_signature": False})
session_id = payload["sid"]
redis_client = await app_container.get(aioredis.Redis)
await redis_client.set(f"perms:{session_id}", json.dumps(["catalog:manage"]), ex=300)
```

**OIDC Provider Stub** (`backend/tests/fakes/oidc_provider.py`):
- `StubOIDCProvider` injected via `TestOverridesProvider` in root conftest
- Returns configurable `OIDCUserInfo` without real OAuth calls

**What to mock (unit tests):**
- All `I*Repository` interfaces
- `IUnitOfWork`
- `ILogger`
- External service clients (e.g., `IImageBackendClient`)
- `PermissionResolver`

**What NOT to mock (integration/e2e):**
- Database (use real PostgreSQL)
- Redis (use real Redis, flushed per test)
- SQLAlchemy sessions and engine
- Dishka DI container (use real container with TestOverridesProvider)

## Fixtures and Factories

### Object Mothers (`tests/factories/*_mothers.py`)

Pre-configured domain entity builders for common test scenarios. Each module has its own Mothers class:

```python
# backend/tests/factories/identity_mothers.py
class IdentityMothers:
    @staticmethod
    def active_local() -> Identity:
        return Identity.register(PrimaryAuthMethod.LOCAL)

    @staticmethod
    def deactivated(reason: str = "test_deactivation") -> Identity:
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        identity.deactivate(reason=reason)
        identity.clear_domain_events()
        return identity

    @staticmethod
    def with_session(ip_address="127.0.0.1", user_agent="TestAgent/1.0") -> tuple[Identity, Session, str]:
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        raw_token = f"refresh-{uuid.uuid4().hex}"
        session = Session.create(identity_id=identity.id, refresh_token=raw_token, ...)
        return identity, session, raw_token

class SessionMothers:
    @staticmethod
    def active(identity_id=None) -> tuple[Session, str]: ...
    @staticmethod
    def expired(identity_id=None) -> Session: ...
    @staticmethod
    def revoked(identity_id=None) -> Session: ...

class RoleMothers:
    @staticmethod
    def customer() -> Role: ...
    @staticmethod
    def admin() -> Role: ...

class PermissionMothers:
    @staticmethod
    def brand_create() -> Permission: ...

class LinkedAccountMothers:
    @staticmethod
    def google(identity_id=None) -> LinkedAccount: ...
    @staticmethod
    def telegram(identity_id=None) -> LinkedAccount: ...
```

### Fluent Builders (`tests/factories/builders.py`)

For complex entities requiring step-by-step construction:

```python
# backend/tests/factories/builders.py
class SessionBuilder:
    def __init__(self) -> None:
        self._identity_id = uuid.uuid4()
        self._refresh_token = f"refresh-{uuid.uuid4().hex}"
        self._is_revoked = False
        self._expired = False

    def with_identity(self, identity_id: uuid.UUID) -> SessionBuilder:
        self._identity_id = identity_id
        return self

    def expired(self) -> SessionBuilder:
        self._expired = True
        return self

    def revoked(self) -> SessionBuilder:
        self._is_revoked = True
        return self

    def build(self) -> tuple[Session, str]:
        session = Session.create(...)
        if self._expired:
            session.expires_at = datetime.now(UTC) - timedelta(hours=1)
        if self._is_revoked:
            session.revoke()
        return session, self._refresh_token

class CategoryBuilder:
    def with_name_i18n(self, name_i18n) -> CategoryBuilder: ...
    def with_slug(self, slug) -> CategoryBuilder: ...
    def under(self, parent: Category) -> CategoryBuilder: ...
    def build(self) -> Category: ...
```

### Schema Factories (`tests/factories/schema_factories.py`)

Uses `polyfactory` for auto-generating Pydantic request payloads:

```python
# backend/tests/factories/schema_factories.py
from polyfactory.factories.pydantic_factory import ModelFactory

class RegisterRequestFactory(ModelFactory):
    __model__ = RegisterRequest

class BrandCreateRequestFactory(ModelFactory):
    __model__ = BrandCreateRequest
```

### N+1 Query Detection (`tests/utils/query_counter.py`)

Async context manager that hooks into SQLAlchemy's event system to count SQL queries:

```python
# backend/tests/utils/query_counter.py
async with assert_query_count(db_session, expected=1, label="list_brands"):
    result = await brand_repo.list_all()
```

Filters out SAVEPOINT-related statements from the count (test isolation artifacts).

### Query Baselines (`tests/utils/catalog_query_baselines.py`)

Expected query count dictionary for regression testing:

```python
EXPECTED_COUNTS = {
    "brand.get_by_id": 1,
    "category.get_by_id": 1,
    "product.get_with_variants": None,  # TBD
    ...
}
```

### Location Summary

| Pattern | Location | Use Case |
|---------|----------|----------|
| Object Mothers | `backend/tests/factories/*_mothers.py` | Domain entity creation with sensible defaults |
| Fluent Builders | `backend/tests/factories/builders.py` | Complex entity construction with chainable API |
| Schema Factories | `backend/tests/factories/schema_factories.py` | Auto-generated Pydantic request payloads |
| Fakes/Stubs | `backend/tests/fakes/` | Stub implementations of external service ports |
| Query Counter | `backend/tests/utils/query_counter.py` | N+1 detection via SQL statement counting |
| Query Baselines | `backend/tests/utils/catalog_query_baselines.py` | Expected counts for regression |

## Coverage

**Requirements:**
- Coverage automatically collected on every test run via `--cov=src` (in `addopts`)
- Reports: terminal (skip-covered) + XML (for CI/SonarQube)

**View Coverage:**
```bash
uv run pytest tests/ --cov=src --cov-report=term-missing      # Terminal report
uv run pytest tests/ --cov=src --cov-report=html               # HTML report
make coverage                                                   # Via Makefile
```

## Test Types Detail

### Unit Tests
- **Scope:** Domain entities, value objects, event classes, schema validation, command handlers (with mocked deps), infrastructure components
- **I/O:** Zero -- no database, no network, no filesystem
- **Speed:** < 0.01s per test
- **Convention:** No `db_session` fixture. Use Object Mothers, Builders, or direct construction.
- **Async:** Tests can be sync (`def test_*`) or async (`async def test_*`). Domain entity tests are mostly sync. Handler tests are async.

### Integration Tests
- **Scope:** Repositories with real PostgreSQL, command handlers with real DI container + DB
- **I/O:** Database (PostgreSQL via `db_session`), Redis (via `_flush_redis`)
- **Convention:** Use `db_session` fixture for DB access, `app_container` for DI-wired handlers
- **Isolation:** Nested transaction rollback per test (savepoint strategy)

### E2E Tests
- **Scope:** Full HTTP round-trips through FastAPI routers
- **I/O:** In-process ASGI transport (no real HTTP server)
- **Client:** `httpx.AsyncClient` with `ASGITransport(app=fastapi_app)`
- **Auth:** `authenticated_client` (regular user) and `admin_client` (with `catalog:manage` permission seeded in Redis) fixtures
- **Convention:** Assert on HTTP status codes and JSON response shape. Payloads use camelCase (matching API contract).

### Architecture Tests
- **Scope:** Static import analysis across all `src/` modules
- **Tool:** `pytest-archon` (import graph checker)
- **Tests are synchronous** (no `async def`)
- **Parametrized** for cross-module isolation checks

### Load Tests
- **Framework:** Locust
- **Location:** `backend/tests/load/`
- **Scenarios:** `auth_flow.py`, `browse_catalog.py`, `mixed_workload.py`
- **Runner:** `backend/tests/load/locustfile.py`

## Common Patterns

### Async Testing

All async tests are auto-detected (`asyncio_mode = "auto"`). No `@pytest.mark.asyncio` decorator needed for most tests. Some files include `pytestmark = pytest.mark.asyncio` for explicitness in e2e tests.

```python
async def test_brand_repository_add_and_get(db_session: AsyncSession):
    repository = BrandRepository(session=db_session)
    brand = Brand.create(name="Nike", slug="nike")
    added_brand = await repository.add(brand)
    assert added_brand.id == brand.id
```

### Error Testing

```python
# Exception type check
def test_ensure_active_raises_when_deactivated(self):
    identity = Identity.register(IdentityType.LOCAL)
    identity.deactivate(reason="test")
    with pytest.raises(IdentityDeactivatedError):
        identity.ensure_active()

# Error code validation
async def test_admin_deactivate_identity_not_found(self) -> None:
    identity_repo = AsyncMock()
    identity_repo.get.return_value = None
    handler = self._make_handler(identity_repo=identity_repo)
    with pytest.raises(NotFoundError) as exc_info:
        await handler.handle(...)
    assert exc_info.value.error_code == "IDENTITY_NOT_FOUND"

# Validation error with message matching
def test_password_min_length_8(self):
    with pytest.raises(ValidationError, match="password"):
        RegisterRequest(email="new@example.com", password="short")
```

### Domain Event Testing

```python
def test_deactivate_emits_event(self):
    identity = Identity.register(IdentityType.LOCAL)
    identity.deactivate(reason="user_request")
    events = identity.domain_events
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, IdentityDeactivatedEvent)
    assert event.identity_id == identity.id
    assert event.reason == "user_request"
```

### Mock Assertion Patterns

```python
# Verify async method was called
identity_repo.update.assert_awaited_once_with(identity)
uow.commit.assert_awaited_once()

# Verify sync method was called
uow.register_aggregate.assert_called_once_with(identity)

# Verify method was NOT called
permission_repo.get_by_ids.assert_not_awaited()
session.add.assert_not_called()

# Inspect call arguments
failed_task = session.add.call_args[0][0]
assert failed_task.task_name == "test_task"
```

## E2E Auth Fixtures

### `authenticated_client` (regular user)
- Registers a user with unique email
- Logs in to get access token
- Sets `Authorization: Bearer <token>` header on the shared `AsyncClient`
- Cleans up header after test

### `admin_client` (admin with catalog permissions)
- Registers + logs in like `authenticated_client`
- Decodes JWT to extract `sid` (session_id)
- Seeds Redis with `perms:{session_id}` -> `["catalog:manage"]` (cache-aside bypass)
- Cleans up header and Redis key after test

### `fastapi_app` (session-scoped)
- Patches `create_container` to inject the shared `app_container`
- Creates the FastAPI app once per session

### `async_client` (session-scoped)
- `httpx.AsyncClient` with `ASGITransport(app=fastapi_app)`
- Base URL: `http://test`

## Frontend Testing

**Status:** No test infrastructure in either frontend project (`frontend/admin/`, `frontend/main/`). No test files, no test runner config, no test dependencies in `package.json`.

---

*Testing analysis: 2026-03-28*
