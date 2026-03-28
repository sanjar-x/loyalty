# Testing Patterns

**Analysis Date:** 2026-03-28

## Test Framework

**Runner:**
- pytest 9.x (via `uv run pytest`)
- Config: `backend/pyproject.toml` `[tool.pytest.ini_options]` and `backend/pytest.ini`
- Note: `pytest.ini` takes precedence and contains the full configuration

**Assertion Library:**
- Plain `assert` statements (pytest native)
- `pytest.raises(ExceptionType)` for exception testing

**Async Support:**
- pytest-asyncio 1.3+ with `asyncio_mode = "auto"` (all `async def test_*` are auto-detected)
- Session-scoped event loop: `asyncio_default_fixture_loop_scope = session`
- Session-scoped test loop: `asyncio_default_test_loop_scope = session`

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
- Mirror the `src/` module structure under each test category

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestIdentity`, `TestCustomer`, `TestSupplierCreate`)
- Test functions: `test_*` (e.g., `test_create_brand_e2e_success`)

**Structure:**
```
backend/tests/
├── conftest.py                          # Root conftest: event loop, DB/Redis URLs, DI container, db_session fixture
├── architecture/
│   ├── conftest.py                      # pytestmark = pytest.mark.architecture
│   └── test_boundaries.py              # pytest-archon layer/module rules
├── unit/
│   ├── infrastructure/
│   │   ├── database/models/            # ORM model unit tests
│   │   ├── logging/                    # Logging infrastructure tests
│   │   ├── outbox/                     # Outbox pattern tests
│   │   └── security/                   # Security infrastructure tests
│   ├── modules/
│   │   ├── catalog/
│   │   │   ├── application/            # Command handler unit tests (mocked deps)
│   │   │   ├── domain/                 # Domain entity pure-logic tests
│   │   │   └── infrastructure/         # Repository mapping tests
│   │   ├── identity/
│   │   │   ├── application/commands/   # Command handler tests
│   │   │   ├── application/consumers/  # Event consumer tests
│   │   │   ├── domain/                 # Entity, VO, event, exception tests
│   │   │   ├── management/             # System role sync tests
│   │   │   └── presentation/           # Schema validation tests
│   │   ├── supplier/domain/            # Supplier entity tests
│   │   └── user/
│   │       ├── application/commands/   # Profile command tests
│   │       ├── application/consumers/  # Event consumer tests
│   │       ├── domain/                 # Customer entity tests
│   │       └── presentation/           # Schema tests
│   └── shared/                         # Shared kernel tests
├── integration/
│   ├── conftest.py                     # Overrides db_session with nested-transaction rollback
│   ├── bootstrap/                      # App bootstrap tests
│   └── modules/
│       ├── catalog/
│       │   ├── application/commands/   # Command handler tests with real DB
│       │   └── infrastructure/repositories/  # Repository tests with real DB
│       ├── identity/application/       # Identity handler integration tests
│       └── supplier/infrastructure/    # Supplier repo integration tests
├── e2e/
│   ├── conftest.py                     # FastAPI app, httpx AsyncClient, auth fixtures
│   └── api/v1/                         # HTTP round-trip tests per endpoint group
│       ├── test_auth.py
│       ├── test_auth_telegram.py
│       ├── test_brands.py
│       ├── test_categories.py
│       └── test_users.py
├── load/
│   ├── locustfile.py                   # Locust runner
│   └── scenarios/                      # Load test scenarios
│       ├── auth_flow.py
│       ├── browse_catalog.py
│       └── mixed_workload.py
├── factories/
│   ├── builders.py                     # Fluent Builder pattern
│   ├── catalog_mothers.py             # Object Mother pattern (catalog domain)
│   ├── identity_mothers.py            # Object Mother pattern (identity domain)
│   ├── orm_factories.py               # Polyfactory ORM model factories
│   ├── schema_factories.py            # Pydantic schema factories
│   └── storage_factories.py           # Storage-related factories
└── fakes/
    └── oidc_provider.py               # Stub OIDC provider for tests
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

**Test counts (as of analysis date):**
- Unit tests: 28 test files
- Integration tests: 20 test files
- E2E tests: 5 test files
- Architecture tests: 1 test file
- Load test scenarios: 4 files

**Strict markers enforced:** `--strict-markers` prevents typos in marker names.

## Test Structure

### Unit Test Pattern (Domain Entity)

Tests are organized in `TestClassName` classes with one assertion per test method. Use factory methods or Object Mothers to set up entities:

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

Use `unittest.mock.AsyncMock` and `MagicMock` for dependencies:

```python
# backend/tests/unit/modules/user/application/commands/test_commands.py
from unittest.mock import AsyncMock, MagicMock

def make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow

def make_logger():
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger

class TestUpdateProfileHandler:
    async def test_update_profile_success(self):
        customer = MagicMock()
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=customer)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(customer_repo=customer_repo, uow=uow, logger=logger)
        command = UpdateProfileCommand(customer_id=uuid.uuid4(), first_name="Alice")

        await handler.handle(command)

        customer.update_profile.assert_called_once_with(first_name="Alice", ...)
        uow.commit.assert_awaited_once()

    async def test_update_profile_not_found(self):
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=None)
        handler = UpdateProfileHandler(customer_repo=customer_repo, uow=make_uow(), logger=make_logger())

        with pytest.raises(CustomerNotFoundError):
            await handler.handle(UpdateProfileCommand(customer_id=uuid.uuid4(), first_name="Bob"))
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

### Integration Test Pattern (Command Handler via DI)

Uses the Dishka container to get a fully wired handler:

```python
# backend/tests/integration/modules/catalog/application/commands/test_create_brand.py
async def test_create_brand_handler_without_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request_container:
        handler = await request_container.get(CreateBrandHandler)
        command = CreateBrandCommand(name="TestBrand", slug="testbrand")

        # Act
        result = await handler.handle(command)

    # Assert
    assert result.brand_id is not None
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.slug == "testbrand"
```

### E2E Test Pattern (HTTP Round-Trip)

Uses `httpx.AsyncClient` with `ASGITransport`:

```python
# backend/tests/e2e/api/v1/test_brands.py
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

## Database Isolation Strategy

### Root conftest (`backend/tests/conftest.py`)

**Session-scoped infrastructure:**
- Single event loop for entire test session
- Single async engine with `NullPool` (no connection pooling in tests)
- `Base.metadata.drop_all` / `create_all` once per session
- Dishka container created once per session with `TestOverridesProvider`

**Function-scoped isolation:**
- Each test gets a `db_session` wrapped in a nested transaction (savepoint)
- Session stored in `contextvars.ContextVar` so Dishka injects the same session into handlers
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

**Patterns for unit tests:**

```python
# UnitOfWork mock (async context manager)
def make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow

# Logger mock (bind returns self)
def make_logger():
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger

# Repository mock (async methods)
customer_repo = AsyncMock()
customer_repo.get = AsyncMock(return_value=customer_entity)
```

**E2E auth mock pattern:**
```python
# Seed Redis cache with permissions to bypass DB permission checks
redis_client = await app_container.get(aioredis.Redis)
await redis_client.set(f"perms:{session_id}", json.dumps(["catalog:manage"]), ex=300)
```

**OIDC provider stub:**
```python
# backend/tests/fakes/oidc_provider.py -- StubOIDCProvider injected via TestOverridesProvider
```

**What to mock (unit tests):**
- Repositories (all `I*Repository` interfaces)
- `IUnitOfWork`
- `ILogger`
- External service clients

**What NOT to mock (integration/e2e):**
- Database (use real PostgreSQL)
- Redis (use real Redis, flushed per test)
- SQLAlchemy sessions and engine
- Dishka DI container

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
    def with_session() -> tuple[Identity, Session, str]:
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        raw_token = f"refresh-{uuid.uuid4().hex}"
        session = Session.create(identity_id=identity.id, ...)
        return identity, session, raw_token
```

```python
# backend/tests/factories/catalog_mothers.py
class CategoryMothers:
    @staticmethod
    def root(name_i18n=None, slug=None) -> Category:
        return Category.create_root(
            name_i18n=name_i18n or {"en": "Electronics"},
            slug=slug or f"electronics-{uuid.uuid4().hex[:6]}",
        )

    @staticmethod
    def deep_nested(depth: int = 3) -> list[Category]:
        # Returns chain of parent->child->grandchild
```

### Fluent Builders (`tests/factories/builders.py`)

For complex entities requiring step-by-step construction:

```python
# backend/tests/factories/builders.py
class SessionBuilder:
    def __init__(self) -> None:
        self._identity_id = uuid.uuid4()
        self._refresh_token = f"refresh-{uuid.uuid4().hex}"
        ...

    def with_identity(self, identity_id: uuid.UUID) -> SessionBuilder:
        self._identity_id = identity_id
        return self

    def expired(self) -> SessionBuilder:
        self._expired = True
        return self

    def build(self) -> tuple[Session, str]:
        session = Session.create(...)
        return session, self._refresh_token
```

### ORM Factories (`tests/factories/orm_factories.py`)

Uses `polyfactory` (Pydantic/SQLAlchemy factory library) for auto-generating ORM model instances:

```python
# backend/tests/factories/orm_factories.py
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

class BrandModelFactory(SQLAlchemyFactory):
    __model__ = BrandModel
    __set_relationships__ = True
```

### Location Summary

| Pattern | Location | Use Case |
|---------|----------|----------|
| Object Mothers | `backend/tests/factories/*_mothers.py` | Domain entity creation with sensible defaults |
| Fluent Builders | `backend/tests/factories/builders.py` | Complex entity construction with chainable API |
| ORM Factories | `backend/tests/factories/orm_factories.py` | Auto-generated ORM model instances for DB seeding |
| Fakes/Stubs | `backend/tests/fakes/` | Stub implementations of external service ports |

## Coverage

**Requirements:**
- Coverage automatically collected on every test run via `--cov=src`
- Reports: terminal (skip-covered) + XML (for CI/SonarQube)
- `.coverage` SQLite file and `coverage.xml` present in `backend/`

**View Coverage:**
```bash
uv run pytest tests/ --cov=src --cov-report=term-missing      # Terminal report
uv run pytest tests/ --cov=src --cov-report=html               # HTML report
make coverage                                                   # Via Makefile
```

**Default addopts** (from `backend/pytest.ini`):
```ini
addopts =
    -v
    --strict-markers
    --cov=src
    --cov-report=term-missing:skip-covered
    --cov-report=xml
```

## Test Types Detail

### Unit Tests
- **Scope:** Domain entities, value objects, event classes, schema validation, command handlers (with mocked deps)
- **I/O:** Zero -- no database, no network, no filesystem
- **Speed:** < 0.01s per test
- **Convention:** No `db_session` fixture. Use Object Mothers, Builders, or direct construction.

### Integration Tests
- **Scope:** Repositories with real PostgreSQL, command handlers with real DI container + DB
- **I/O:** Database (PostgreSQL via `db_session`), Redis (via `_flush_redis`)
- **Convention:** Use `db_session` fixture for DB access, `app_container` for DI-wired handlers
- **Isolation:** Nested transaction rollback per test

### E2E Tests
- **Scope:** Full HTTP round-trips through FastAPI routers
- **I/O:** In-process ASGI transport (no real HTTP server)
- **Client:** `httpx.AsyncClient` with `ASGITransport(app=fastapi_app)`
- **Auth:** `authenticated_client` (regular user) and `admin_client` (with permissions seeded in Redis) fixtures
- **Convention:** Assert on HTTP status codes and JSON response shape

### Architecture Tests
- **Scope:** Static import analysis across all `src/` modules
- **Tool:** `pytest-archon` (import graph checker)
- **Rules enforced:**
  1. Domain layer is pure (no outer layer imports)
  2. Domain has zero framework imports (no SQLAlchemy, FastAPI, Dishka, etc.)
  3. Application layer does not import Infrastructure or Presentation (with exceptions for CQRS queries and event consumers)
  4. Infrastructure does not import Presentation
  5. Cross-module isolation (modules cannot import each other's internals, with explicit exceptions)
  6. Shared kernel is independent of business modules
  7. No reverse layer dependencies within a module

### Load Tests
- **Framework:** Locust
- **Location:** `backend/tests/load/`
- **Scenarios:** `auth_flow.py`, `browse_catalog.py`, `mixed_workload.py`
- **Runner:** `backend/tests/load/locustfile.py`

## Common Patterns

### Async Testing

All async tests are auto-detected (`asyncio_mode = "auto"`). No `@pytest.mark.asyncio` decorator needed for most tests. Some files include `pytestmark = pytest.mark.asyncio` for explicitness.

```python
async def test_brand_repository_add_and_get(db_session: AsyncSession):
    repository = BrandRepository(session=db_session)
    brand = Brand.create(name="Nike", slug="nike")
    added_brand = await repository.add(brand)
    assert added_brand.id == brand.id
```

### Error Testing

```python
def test_create_empty_name_raises(self):
    with pytest.raises(ValueError, match="name is required"):
        Supplier.create(name="", supplier_type=SupplierType.LOCAL, region="Moscow")

def test_ensure_active_raises_when_deactivated(self):
    identity = Identity.register(IdentityType.LOCAL)
    identity.deactivate(reason="test")
    with pytest.raises(IdentityDeactivatedError):
        identity.ensure_active()
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

### Guard Field Testing (DDD-01 pattern)

```python
def test_create_child_own_template_overrides_parent(self):
    parent_fid = uuid.uuid4()
    child_fid = uuid.uuid4()
    parent = Category.create_root(name_i18n=_i18n("P"), slug="p", template_id=parent_fid)
    child = Category.create_child(
        name_i18n=_i18n("C"), slug="c", parent=parent, template_id=child_fid
    )
    assert child.effective_template_id == child_fid
```

## Frontend Testing

**Status:** No test infrastructure in either frontend project. No test files, no test runner config, no test dependencies in `package.json`.

---

*Testing analysis: 2026-03-28*
