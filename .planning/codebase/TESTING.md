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
- Test classes: `Test*` (e.g., `TestIdentity`, `TestSession`, `TestStorageFileCreate`)
- Test functions: `test_*` (e.g., `test_create_brand_handler_without_logo`)

**Structure (backend):**
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
    identity_mothers.py                # Object Mothers (IdentityMothers, SessionMothers, RoleMothers, etc.)
    orm_factories.py                   # Polyfactory-based ORM model factories
    schema_factories.py
    storage_factories.py
  fakes/
    __init__.py
    oidc_provider.py                   # StubOIDCProvider for tests
  load/
    locustfile.py                      # Locust load test entry point (currently empty)
    scenarios/
      auth_flow.py
      browse_catalog.py
      mixed_workload.py
```

**Structure (image_backend):**
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
          test_process_image.py         # TDD tests for image processing pure functions
        domain/
          test_entities.py              # StorageFile entity tests
          test_value_objects.py
        presentation/
          test_sse.py
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

**Scope:** Domain entities, value objects, domain events, presentation schemas, and application command handlers (with mocked dependencies)
**I/O:** Zero I/O. No database, no network, no filesystem.
**Speed:** < 0.01s per test

**Domain entity tests** (`tests/unit/modules/*/domain/test_entities.py`):
- Organized by entity with `class TestEntityName:` grouping
- Test factory methods, mutations, guard methods, and domain event emission
- Use Object Mothers from `tests/factories/` for pre-built configurations

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

**Image backend domain tests** use the same class-per-concept pattern with fine-grained assertions:
```python
# image_backend/tests/unit/modules/storage/domain/test_entities.py
class TestStorageFileCreate:
    def test_create_generates_a_uuid(self):
        sf = StorageFile.create(bucket_name="b", object_key="raw/x/f.jpg", content_type="image/jpeg")
        assert isinstance(sf.id, uuid.UUID)

    def test_create_sets_status_to_pending_upload(self):
        sf = StorageFile.create(bucket_name="b", object_key="raw/x/f.jpg", content_type="image/jpeg")
        assert sf.status == StorageStatus.PENDING_UPLOAD

class TestStorageFileDefaults:
    def test_size_bytes_defaults_to_zero(self):
        sf = StorageFile.create(bucket_name="b", object_key="k", content_type="image/png")
        assert sf.size_bytes == 0
```

**Application handler unit tests** (`tests/unit/modules/*/application/commands/test_*.py`):
- Mock all dependencies with `AsyncMock` / `MagicMock`
- Use local helper functions `make_uow()`, `make_logger()`, `make_identity()`, `make_role()`
- Each test class has a `_make_handler()` factory method for DRY handler construction
- Verify side effects via `assert_awaited_once_with()`, `assert_called_once_with()`

```python
# backend/tests/unit/modules/identity/application/commands/test_admin_commands.py
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
    def _make_handler(self, identity_repo=None, ...) -> AdminDeactivateIdentityHandler:
        return AdminDeactivateIdentityHandler(
            identity_repo=identity_repo or AsyncMock(), ...
        )

    async def test_admin_deactivate_success(self) -> None:
        identity = make_identity(identity_id=identity_id, is_active=True)
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        handler = self._make_handler(identity_repo=identity_repo, ...)
        await handler.handle(command)
        assert identity.is_active is False
        identity_repo.update.assert_awaited_once_with(identity)
        uow.commit.assert_awaited_once()
```

**Pure function TDD tests** (image_backend):
- Test image processing functions with real PIL Image objects
- Use `@pytest.fixture()` for shared test data
- Verify output dimensions, format, aspect ratio, file size

```python
# image_backend/tests/unit/modules/storage/application/test_process_image.py
class TestResizeToFit:
    def test_preserves_aspect_ratio_landscape(self):
        img = Image.new("RGB", (2000, 1000))
        resized = resize_to_fit(img, 600, 600)
        assert resized.width == 600
        assert resized.height == 300

class TestBuildVariants:
    @pytest.fixture()
    def raw_large(self) -> bytes:
        return _make_test_image(2000, 1500)

    def test_produces_three_variant_meta(self, result):
        _, variants_meta, _ = result
        assert len(variants_meta) == 3
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
# backend/tests/integration/modules/identity/application/commands/test_login.py
async def test_login_returns_tokens_for_valid_credentials(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Register first
    async with app_container() as request:
        reg_handler = await request.get(RegisterHandler)
        await reg_handler.handle(RegisterCommand(email="login@example.com", password="S3cure!Pass"))

    # Login
    async with app_container() as request:
        login_handler = await request.get(LoginHandler)
        result = await login_handler.handle(LoginCommand(
            login="login@example.com", password="S3cure!Pass",
            ip_address="127.0.0.1", user_agent="TestAgent/1.0",
        ))

    assert result.access_token is not None
    assert result.refresh_token is not None
```

### E2E Tests

**Scope:** Full HTTP round-trips through FastAPI routers
**Client:** httpx `AsyncClient` with `ASGITransport` (in-process, no real HTTP server)

**Fixtures** in `backend/tests/e2e/conftest.py`:
- `fastapi_app` -- session-scoped, patches `create_container` to use test container
- `async_client` -- session-scoped httpx client
- `authenticated_client` -- function-scoped, registers + logs in, sets `Authorization: Bearer` header
- `admin_client` -- function-scoped, registers + logs in + seeds Redis with admin permissions via cache injection

```python
# backend/tests/e2e/api/v1/test_auth.py
async def test_register_returns_201_with_identity_id(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"reg-{uuid.uuid4().hex[:8]}@test.com"
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cure!Pass"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "identityId" in data

async def test_login_returns_401_for_wrong_password(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"bad-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": "S3cure!Pass"})
    response = await async_client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert response.status_code == 401
```

**E2E test conventions:**
- Use unique emails per test via `f"prefix-{uuid.uuid4().hex[:8]}@test.com"` pattern
- Validate camelCase JSON keys (e.g., `"identityId"`, `"accessToken"`)
- Always depend on `db_session` fixture even if not directly used (ensures transaction rollback)

### Architecture Fitness Functions

**Tool:** pytest-archon
**Location:** `backend/tests/architecture/test_boundaries.py`
**Marker:** `pytest.mark.architecture`

Seven rules enforce Clean Architecture layer boundaries:

1. **Domain layer purity** -- domain MUST NOT import application, infrastructure, or presentation
2. **Domain has zero framework imports** -- no SQLAlchemy, FastAPI, Dishka, Redis, Pydantic in domain (parameterized per module)
3. **Application layer boundaries** -- application MUST NOT import infrastructure or presentation (excludes CQRS queries and consumers)
4. **Infrastructure independence** -- infrastructure MUST NOT import presentation
5. **Cross-module isolation** -- modules MUST NOT import each other's internals (with declared exceptions for presentation-layer auth dependencies)
6. **Shared kernel independence** -- `src/shared/` MUST NOT import from any business module
7. **No reverse layer dependencies** -- Domain <- Application <- Infrastructure <- Presentation (parameterized per module)

```python
# backend/tests/architecture/test_boundaries.py
MODULES = ["catalog", "identity", "user"]

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

@pytest.mark.parametrize("module", MODULES)
def test_domain_has_zero_framework_imports(module: str):
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
```

**Allowed cross-module dependencies** are explicitly declared:
```python
ALLOWED_CROSS_MODULE = {
    ("user", "identity"): {"src.modules.user.presentation.*"},
    ("catalog", "identity"): {"src.modules.catalog.presentation.*"},
}
```

### Load Tests

**Framework:** Locust >= 2.43.3
**Location:** `backend/tests/load/locustfile.py` (currently empty) + `backend/tests/load/scenarios/`
**Scenarios:** `auth_flow.py`, `browse_catalog.py`, `mixed_workload.py`
**Marker:** `pytest.mark.load`

## Mocking

**Framework:** `unittest.mock` (standard library) -- `AsyncMock`, `MagicMock`

**Patterns:**

**Mock UnitOfWork (use in every command handler unit test):**
```python
def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow
```

**Mock Logger (use in every handler unit test):**
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

**Test Fakes:** `backend/tests/fakes/oidc_provider.py` -- `StubOIDCProvider` implements `IOIDCProvider` interface for tests

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

**Four patterns coexist:**

### 1. Object Mothers (preferred for domain entities)
Location: `backend/tests/factories/identity_mothers.py`, `backend/tests/factories/catalog_mothers.py`

Pre-built domain entity configurations with descriptive static method names:
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
```

### 2. Fluent Test Data Builders (for complex construction)
Location: `backend/tests/factories/builders.py`

```python
# backend/tests/factories/builders.py
class SessionBuilder:
    def with_identity(self, identity_id: uuid.UUID) -> SessionBuilder: ...
    def with_roles(self, role_ids: list[uuid.UUID]) -> SessionBuilder: ...
    def expired(self) -> SessionBuilder: ...
    def revoked(self) -> SessionBuilder: ...
    def build(self) -> tuple[Session, str]: ...

class CategoryBuilder:
    def with_name_i18n(self, name_i18n: dict[str, str]) -> CategoryBuilder: ...
    def with_slug(self, slug: str) -> CategoryBuilder: ...
    def under(self, parent: Category) -> CategoryBuilder: ...
    def build(self) -> Category: ...
```

### 3. Polyfactory ORM Factories (for database seeding)
Location: `backend/tests/factories/orm_factories.py`
Library: polyfactory >= 3.3.0

```python
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

class IdentityModelFactory(SQLAlchemyFactory):
    __model__ = IdentityModel
    __set_relationships__ = True

class BrandModelFactory(SQLAlchemyFactory):
    __model__ = BrandModel
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
- Fail-fast check: if DB unreachable, `pytest.exit()` immediately with message to start containers

**Redis:** Real Redis (localhost:6379) -- flushed per test in integration/e2e scopes via `_flush_redis` fixture

**RabbitMQ:** Real RabbitMQ (localhost:5672) -- used in broker integration tests

**Testcontainers:** Available as a dev dependency (`testcontainers[minio,postgres,rabbitmq,redis]>=4.14.1`) but the current `conftest.py` connects to localhost containers instead

**DI Container in Tests:** Full Dishka container is assembled in `backend/tests/conftest.py` with `TestOverridesProvider` that overrides:
- `Settings` with hardcoded test values
- `AsyncEngine` with NullPool (no connection pooling in tests)
- `AsyncSession` via ContextVar injection (so Dishka injects the test-scoped session)
- `redis.Redis` client
- `IOIDCProvider` with `StubOIDCProvider` stub

**ContextVar Isolation:** Autouse fixture `_reset_context_vars` resets `request_id` ContextVar per test to prevent cross-test contamination.

## Frontend Testing

**No test files or test frameworks exist** in either `frontend/admin` or `frontend/main`. No test configuration is present in either `package.json`.

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

**Adding a New Test:**
1. **Unit test for domain entity:** Create `tests/unit/modules/{module}/domain/test_{entity}.py` with `class Test{Entity}:` grouping
2. **Unit test for command handler:** Create `tests/unit/modules/{module}/application/commands/test_{action}.py`, define `make_uow()`, `make_logger()`, handler factory, then test all happy/error paths
3. **Integration test for repository:** Create `tests/integration/modules/{module}/infrastructure/repositories/test_{entity}.py`, inject `db_session: AsyncSession`, instantiate repository directly
4. **Integration test for command handler:** Create `tests/integration/modules/{module}/application/commands/test_{action}.py`, inject `app_container: AsyncContainer` and `db_session: AsyncSession`, resolve handler via container
5. **E2E test for endpoint:** Create `tests/e2e/api/v1/test_{resource}.py`, use `async_client`, `authenticated_client`, or `admin_client` fixture

---

*Testing analysis: 2026-03-28*
