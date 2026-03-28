# Testing Patterns

**Analysis Date:** 2026-03-28

## Test Framework

**Runner:**
- pytest >= 9.0.2
- pytest-asyncio >= 1.3.0 (auto mode -- all `async def test_*` detected automatically)
- Config: `backend/pyproject.toml` `[tool.pytest.ini_options]` + `backend/pytest.ini` (detailed)

**Assertion Library:**
- Standard `assert` statements (pytest rewriting)
- `pytest.raises(ExceptionClass)` for expected exceptions

**Async Mode:**
- `asyncio_mode = "auto"` -- no need for `@pytest.mark.asyncio` on individual tests (though some files still use `pytestmark = pytest.mark.asyncio` for explicitness)
- Session-scoped event loop: `asyncio_default_fixture_loop_scope = session`
- All tests share a single event loop across the session

**Run Commands:**
```bash
uv run pytest tests/ -v              # Run all tests
uv run pytest tests/unit/ -v         # Unit tests only
uv run pytest tests/integration/ -v  # Integration tests only
uv run pytest tests/e2e/ -v          # E2E tests only
uv run pytest tests/architecture/ -v # Architecture fitness functions
make test                            # Equivalent to running all tests
make test-unit                       # Unit only
make test-integration                # Integration only
make test-e2e                        # E2E only
make test-architecture               # Architecture only
```

## Test File Organization

**Location:** Separate `tests/` directory tree mirroring `src/` structure

**Naming:**
- Test files: `test_*.py` (prefix convention)
- Test classes: `Test*` (e.g., `TestIdentity`, `TestSession`, `TestAdminDeactivateIdentityHandler`)
- Test functions: `test_*` (e.g., `test_create_brand_handler_without_logo`)

**Structure:**
```
backend/tests/
  __init__.py
  conftest.py                          # Root fixtures: DB, Redis, Dishka container, event loop
  architecture/
    conftest.py                        # pytestmark = pytest.mark.architecture
    test_boundaries.py                 # Architectural fitness functions (pytest-archon)
  unit/
    conftest.py                        # (minimal/empty)
    infrastructure/
      database/...
      logging/
        test_dlq_middleware.py
      outbox/
        test_relay.py
        test_tasks.py
      security/
        test_telegram_validator.py
    modules/
      catalog/
        application/
          test_sync_product_media.py
        domain/
          test_category_effective_family.py
        infrastructure/
          test_image_backend_client.py
      identity/
        application/
          commands/
            test_admin_commands.py
          consumers/
            test_role_events.py
        domain/
          test_entities.py
          test_events.py
          test_exceptions.py
          test_session_timeouts.py
          test_telegram.py
          test_token_version.py
          test_value_objects.py
        management/
          test_sync_system_roles.py
        presentation/
          test_schemas.py
      supplier/
        domain/
          test_entities.py
      user/
        application/
          commands/
            test_commands.py
          consumers/
            test_identity_events.py
        domain/
          test_customer.py
          test_entities.py
          test_referral_code.py
          test_staff_member.py
        presentation/
          test_schemas.py
    shared/
      test_domain_event.py
      test_schemas.py
  integration/
    conftest.py                        # db_session fixture (nested transaction per test)
    bootstrap/
      test_broker.py
      test_worker_init.py
    modules/
      catalog/
        application/
          commands/
            test_create_brand.py
        infrastructure/
          repositories/
            test_brand.py
            test_brand_extended.py
            test_category.py
            test_category_effective_family.py
            test_category_extended.py
      identity/
        application/
          commands/
            test_login.py
          queries/
            test_get_identity_roles.py
            test_list_permissions.py
            test_list_roles.py
        infrastructure/
          repositories/
            test_identity_repo_extended.py
            test_permission_repo.py
            test_role_repo.py
            test_session_repo.py
            test_session_repo_extended.py
      supplier/
        infrastructure/
          repositories/
            test_supplier.py
        test_supplier_crud.py
        test_supplier_lifecycle.py
  e2e/
    conftest.py                        # FastAPI app, AsyncClient, authenticated/admin clients
    api/v1/
      test_auth.py
      test_auth_telegram.py
      test_brands.py
      test_categories.py
      test_users.py
  factories/
    __init__.py
    builders.py                        # Fluent Test Data Builders (RoleBuilder, SessionBuilder, CategoryBuilder)
    catalog_factories.py
    catalog_mothers.py
    identity_mothers.py                # Object Mothers (IdentityMothers, SessionMothers, RoleMothers, PermissionMothers)
    orm_factories.py                   # Polyfactory-based ORM model factories
    schema_factories.py
    storage_factories.py
  fakes/
    __init__.py
    oidc_provider.py                   # StubOIDCProvider for tests
  load/
    locustfile.py                      # Locust load test entry point
    scenarios/
      auth_flow.py
      browse_catalog.py
      mixed_workload.py
```

## Test Markers (Test Pyramid)

Five registered markers define the test pyramid:
```python
# backend/pytest.ini
markers =
    architecture: Fitness functions and boundary enforcement
    unit: Domain-layer pure logic, zero I/O
    integration: Application + Infrastructure with real database
    e2e: Presentation-layer HTTP round-trips
    load: Resilience and threshold testing (Locust)
```

**Run by marker:**
```bash
uv run pytest -m unit              # Unit tests only
uv run pytest -m integration       # Integration tests only
uv run pytest -m architecture      # Architecture fitness functions
uv run pytest -m "not load"        # Everything except load tests
```

**Strict markers enabled:** `--strict-markers` prevents typos in marker names.

## Test Types and Patterns

### Unit Tests

**Scope:** Domain entities, value objects, and application command handlers (with mocked dependencies)
**I/O:** Zero I/O. No database, no network, no filesystem.
**Speed:** < 0.01s per test

**Domain entity tests** (`tests/unit/modules/*/domain/test_entities.py`):
```python
# backend/tests/unit/modules/identity/domain/test_entities.py
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

**Application handler tests** (`tests/unit/modules/*/application/commands/test_*.py`):
- Mock all dependencies with `AsyncMock` / `MagicMock`
- Use local helper functions `make_uow()`, `make_logger()`, `make_identity()`, `make_role()`
- Each test class has a `_make_handler()` factory method
- Verify side effects via `assert_awaited_once_with()`, `assert_called_once_with()`

```python
# backend/tests/unit/modules/identity/application/commands/test_admin_commands.py
def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow

class TestAdminDeactivateIdentityHandler:
    def _make_handler(self, identity_repo=None, ...) -> AdminDeactivateIdentityHandler:
        return AdminDeactivateIdentityHandler(
            identity_repo=identity_repo or AsyncMock(), ...
        )

    async def test_admin_deactivate_success(self) -> None:
        identity = make_identity(identity_id=identity_id, is_active=True)
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        # ... setup ...
        handler = self._make_handler(identity_repo=identity_repo, ...)
        await handler.handle(command)
        assert identity.is_active is False
        identity_repo.update.assert_awaited_once_with(identity)
        uow.commit.assert_awaited_once()
```

### Integration Tests

**Scope:** Repository implementations and command handlers with real PostgreSQL via docker-compose
**I/O:** Real database (PostgreSQL), sometimes Redis
**Speed:** Variable, depends on DB setup

**Database isolation pattern: nested transactions per test.**
Each test gets a `db_session` fixture that wraps in a savepoint, rolls back after test:
```python
# backend/tests/integration/conftest.py
@pytest.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncGeneratorType:
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

**Repository tests** use Arrange-Act-Assert with direct repository instantiation:
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
    assert fetched_brand is not None
    assert fetched_brand.name == "Nike"
```

**Command handler integration tests** use the Dishka container to resolve handlers:
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
```

### E2E Tests

**Scope:** Full HTTP round-trips through FastAPI routers
**Client:** httpx `AsyncClient` with `ASGITransport` (in-process, no real HTTP server)

**Fixtures** in `backend/tests/e2e/conftest.py`:
- `fastapi_app` -- session-scoped, patches `create_container` to use test container
- `async_client` -- session-scoped httpx client
- `authenticated_client` -- function-scoped, registers + logs in, sets `Authorization: Bearer` header
- `admin_client` -- function-scoped, registers + logs in + seeds Redis with admin permissions

```python
# backend/tests/e2e/api/v1/test_brands.py
async def test_create_brand_e2e_success(
    admin_client: AsyncClient, db_session: AsyncSession
):
    payload = {"name": "E2E Brand", "slug": "e2e-brand", "logoUrl": "https://cdn.example.com/brands/e2e.webp"}
    response = await admin_client.post("/api/v1/catalog/brands", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
```

### Architecture Fitness Functions

**Tool:** pytest-archon
**Location:** `backend/tests/architecture/test_boundaries.py`
**Marker:** `pytest.mark.architecture`

Tests enforce Clean Architecture layer boundaries:
1. **Domain layer purity** -- domain MUST NOT import application, infrastructure, or presentation
2. **Domain has zero framework imports** -- no SQLAlchemy, FastAPI, Dishka, Redis, Pydantic in domain
3. **Application layer boundaries** -- application MUST NOT import infrastructure or presentation (excludes CQRS queries and consumers)
4. **Infrastructure independence** -- infrastructure MUST NOT import presentation
5. **Cross-module isolation** -- modules MUST NOT import each other's internals (with declared exceptions)
6. **Shared kernel independence** -- `src/shared/` MUST NOT import from any business module
7. **No reverse layer dependencies** -- Domain <- Application <- Infrastructure <- Presentation

```python
def test_domain_layer_is_pure():
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

### Load Tests

**Framework:** Locust >= 2.43.3
**Location:** `backend/tests/load/locustfile.py` + `backend/tests/load/scenarios/`
**Scenarios:** `auth_flow.py`, `browse_catalog.py`, `mixed_workload.py`
**Marker:** `pytest.mark.load`

## Mocking

**Framework:** `unittest.mock` (standard library) -- `AsyncMock`, `MagicMock`

**Patterns:**

**Mock UnitOfWork:**
```python
def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow
```

**Mock Logger:**
```python
def make_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger
```

**Mock Repositories:** Use `AsyncMock()` with `.return_value` for simple cases:
```python
identity_repo = AsyncMock()
identity_repo.get.return_value = identity
role_repo = AsyncMock()
role_repo.get_identity_role_ids.return_value = [admin_role.id]
```

**What to mock in unit tests:**
- All repository interfaces (`IIdentityRepository`, `IBrandRepository`, etc.)
- `IUnitOfWork`
- `ILogger`
- `IPasswordHasher`, `ITokenProvider`
- `IOIDCProvider` (replaced with `StubOIDCProvider` in `tests/fakes/`)

**What NOT to mock:**
- Domain entities -- test them directly
- Value objects and enums
- In integration tests: repositories, database session, command handlers (they use real DB)

## Fixtures and Factories

**Three patterns coexist:**

### 1. Object Mothers (preferred for domain entities)
Location: `backend/tests/factories/identity_mothers.py`, `backend/tests/factories/catalog_mothers.py`

Pre-built domain entity configurations with descriptive names:
```python
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
        # Returns (identity, session, raw_refresh_token)
        ...
```

### 2. Fluent Test Data Builders (for complex construction)
Location: `backend/tests/factories/builders.py`

```python
class SessionBuilder:
    def with_identity(self, identity_id: uuid.UUID) -> SessionBuilder: ...
    def with_roles(self, role_ids: list[uuid.UUID]) -> SessionBuilder: ...
    def expired(self) -> SessionBuilder: ...
    def revoked(self) -> SessionBuilder: ...
    def build(self) -> tuple[Session, str]: ...
```

### 3. Polyfactory ORM Factories (for database seeding)
Location: `backend/tests/factories/orm_factories.py`
Library: polyfactory >= 3.3.0

```python
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

class IdentityModelFactory(SQLAlchemyFactory):
    __model__ = IdentityModel
    __set_relationships__ = True
```

### 4. Local helper functions (in test files)
For simpler cases, test files define `make_*` helpers inline:
```python
def make_identity(identity_id=None, is_active=True) -> Identity:
    return Identity(id=identity_id or uuid.uuid4(), ...)
```

## Coverage

**Requirements:** Coverage is auto-collected via `--cov=src` in `backend/pytest.ini`

**Addopts:**
```ini
addopts = -v --strict-markers --cov=src --cov-report=term-missing:skip-covered --cov-report=xml
```

**Coverage output:**
- Terminal: `term-missing:skip-covered` (only shows files with uncovered lines)
- XML: `coverage.xml` for CI integration (SonarQube/GitLab)

**View coverage:**
```bash
uv run pytest tests/ -v              # Auto-generates coverage report
make coverage                        # Runs with HTML report
```

## Test Infrastructure

**Database:** Real PostgreSQL (localhost:5432) -- requires running containers via `docker compose up -d`
- Tables are dropped and recreated per session via `Base.metadata.drop_all` / `create_all`
- Each test gets a savepoint-based isolated session (auto-rollback)
- Fail-fast check: if DB unreachable, `pytest.exit()` immediately

**Redis:** Real Redis (localhost:6379) -- flushed per test in integration/e2e scopes via `_flush_redis` fixture

**RabbitMQ:** Real RabbitMQ (localhost:5672) -- used in broker integration tests

**Testcontainers:** Available as a dev dependency (`testcontainers[minio,postgres,rabbitmq,redis]>=4.14.1`) but the current `conftest.py` connects to localhost containers instead

**DI Container in Tests:** Full Dishka container is assembled in `tests/conftest.py` with `TestOverridesProvider` that overrides:
- `Settings` with test values
- `AsyncEngine` with NullPool
- `AsyncSession` via ContextVar injection
- `redis.Redis` client
- `IOIDCProvider` with `StubOIDCProvider` stub

## image_backend Test Structure

The image_backend service has its own test suite with the same patterns:

```
image_backend/tests/
  __init__.py
  integration/
    __init__.py
    test_upload_flow.py
  unit/
    __init__.py
    modules/
      storage/
        application/
          test_process_image.py
        domain/
          test_entities.py
          test_value_objects.py
        presentation/
          test_sse.py
```

Config in `image_backend/pyproject.toml`:
```ini
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Common Patterns Summary

**Async Testing:**
```python
# All async tests are auto-detected (asyncio_mode = "auto")
async def test_login_returns_tokens(app_container, db_session):
    async with app_container() as request:
        handler = await request.get(LoginHandler)
        result = await handler.handle(command)
    assert result.access_token is not None
```

**Error Testing:**
```python
async def test_login_raises_invalid_credentials(app_container, db_session):
    with pytest.raises(InvalidCredentialsError):
        async with app_container() as request:
            handler = await request.get(LoginHandler)
            await handler.handle(bad_command)
```

**Domain Event Verification:**
```python
def test_deactivate_emits_event(self):
    identity = Identity.register(IdentityType.LOCAL)
    identity.deactivate(reason="test")
    events = identity.domain_events
    assert len(events) == 1
    assert isinstance(events[0], IdentityDeactivatedEvent)
    assert events[0].identity_id == identity.id
```

**Mock Verification:**
```python
identity_repo.update.assert_awaited_once_with(identity)
uow.register_aggregate.assert_called_once_with(identity)
uow.commit.assert_awaited_once()
permission_resolver.invalidate_many.assert_awaited_once_with(revoked_ids)
```

---

*Testing analysis: 2026-03-28*
