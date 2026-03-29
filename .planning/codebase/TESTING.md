# Testing Patterns

**Analysis Date:** 2026-03-29

## Test Framework

**Runner:**
- pytest `>=9.0.2`
- Config: `backend/pyproject.toml` `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` -- all async tests run without `@pytest.mark.asyncio` on each function (but some files still use `pytestmark = pytest.mark.asyncio`)

**Assertion Library:**
- Built-in `assert` statements (pytest rewrites)
- `dirty-equals>=0.11` available for flexible equality checks
- `pytest.raises()` for exception assertions, often with `match=` or `.value.error_code` checks

**Property-Based Testing:**
- Hypothesis `>=6.151.9` with custom strategies in `backend/tests/factories/strategies/`

**Run Commands:**
```bash
make test                  # Run all tests
make test-unit             # Run unit tests only
make test-integration      # Run integration tests only
make test-e2e              # Run E2E tests only
make test-architecture     # Run architecture fitness functions only
uv run pytest tests/ -v    # Direct pytest invocation
uv run pytest tests/ --cov=project --cov-report=term-missing --cov-report=html  # Coverage
```

## Test File Organization

**Location:**
- Separate `tests/` directory, mirroring source structure
- NOT co-located with source code

**Naming:**
- Test files: `test_{subject}.py`
- Test classes: `Test{Subject}` -- e.g., `TestCreateBrand`, `TestBrandUpdate`
- Test methods: `test_{behavior_description}` -- e.g., `test_creates_brand_and_commits`, `test_rejects_duplicate_slug`

**Structure:**
```
backend/tests/
  conftest.py                          # Root: DB engine, DI container, event loop, db_session
  architecture/
    conftest.py                        # Architecture test config
    test_boundaries.py                 # pytest-archon layer enforcement
  unit/
    conftest.py                        # Empty (unit tests need no DB)
    modules/catalog/
      domain/
        test_brand.py                  # Entity factory, update, guard, deletion tests
        test_category.py               # Category-specific domain tests
        test_product.py                # Product aggregate domain tests
        test_value_objects.py          # Money, BehaviorFlags, enum tests
      application/commands/
        test_brand_handlers.py         # CreateBrand, UpdateBrand, DeleteBrand handlers
        test_category_handlers.py      # Category command handler tests
        test_product_handlers.py       # Product command handler tests
      infrastructure/
        test_image_backend_client.py   # HTTP client unit tests (respx)
    shared/
      test_domain_event.py             # DomainEvent base class tests
      test_schemas.py                  # CamelModel tests
  integration/
    conftest.py                        # Overrides db_session with nested transaction pattern
    modules/catalog/
      infrastructure/repositories/
        conftest.py                    # Seed fixtures (brand, category, currency, attributes)
        test_brand.py                  # BrandRepository add/get/check_slug tests
        test_category.py               # CategoryRepository tests
        test_product.py                # ProductRepository with variants/SKUs
        test_soft_delete.py            # Soft-delete behavior tests
        test_schema_constraints.py     # DB constraint enforcement tests
  e2e/
    conftest.py                        # FastAPI app, AsyncClient, authenticated_client, admin_client
    api/v1/catalog/
      conftest.py                      # Helper functions: create_brand(), create_category(), etc.
      test_brands.py                   # Brand CRUD endpoint contract tests
      test_categories.py               # Category endpoint tests
      test_products.py                 # Product endpoint tests
      test_auth_enforcement.py         # 401/403 enforcement tests
      test_storefront.py               # Public storefront endpoint tests
      test_pagination.py               # Pagination contract tests
      test_lifecycle.py                # Product status lifecycle tests
  factories/                           # Shared test data infrastructure
    orm_factories.py                   # Polyfactory-based ORM model factories
    identity_mothers.py                # Object Mothers for Identity entities
    catalog_mothers.py                 # Object Mothers for Catalog entities
    brand_builder.py                   # Fluent Builder for Brand
    product_builder.py                 # Fluent Builder for Product
    attribute_builder.py               # Fluent Builder for Attribute
    strategies/                        # Hypothesis strategies
      primitives.py                    # Leaf strategies (slugs, i18n, money, enums)
      entity_strategies.py             # Entity-level strategies
      aggregate_strategies.py          # Aggregate-level strategies
  fakes/                               # In-memory test doubles
    fake_uow.py                        # FakeUnitOfWork + FakeRepository base
    fake_catalog_repos.py              # All 10 catalog repository fakes
    oidc_provider.py                   # StubOIDCProvider
  load/                                # Load tests
    locustfile.py                      # Locust entry point
    scenarios/                         # Specific load test scenarios
  utils/                               # Test utility helpers
```

## Test Markers

Defined in `backend/pyproject.toml`:
```python
markers = [
    "architecture: Fitness functions and boundary enforcement",
    "unit: Domain-layer pure logic, zero I/O",
    "integration: Application + Infrastructure with real database",
    "e2e: Presentation-layer HTTP round-trips",
    "load: Resilience and threshold testing (Locust)",
]
```

Usage: `uv run pytest -m unit`, `uv run pytest -m "not load"`

## Test Structure

**Suite Organization:**
```python
# Per D-01: one test class per handler
# Per D-02: one test file per entity domain
class TestCreateBrand:
    """Tests for CreateBrandHandler."""

    async def test_creates_brand_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )
        result = await handler.handle(CreateBrandCommand(name="Nike", slug="nike"))
        assert uow.committed is True
        assert result.brand_id in uow.brands._store

    async def test_rejects_duplicate_slug(self):
        uow = FakeUnitOfWork()
        existing = BrandBuilder().with_slug("nike").build()
        uow.brands._store[existing.id] = existing
        handler = CreateBrandHandler(brand_repo=uow.brands, uow=uow, logger=make_logger())
        with pytest.raises(BrandSlugConflictError):
            await handler.handle(CreateBrandCommand(name="Nike New", slug="nike"))
        assert uow.committed is False
```

**Patterns:**
- Happy path first, then rejection/error cases
- Per D-07: assert `uow.committed is True` on success, `uow.committed is False` on rejection
- Per D-08: assert events via `uow.collected_events` (not `entity.domain_events`)
- One test class per handler or per entity behavior group
- Descriptive test names: `test_{action}_{condition}` or `test_{expected_behavior}`

## Test Isolation

**Database Isolation (Integration/E2E):**
- Nested transaction pattern: each test runs inside a SAVEPOINT that is rolled back after the test
- Implemented in `backend/tests/conftest.py` `db_session` fixture (function scope)
- Session is propagated via `ContextVar` (`_db_session_var`) so Dishka injects the same session
- Schema is dropped and recreated once per session; Alembic migrations run once
- Redis flushed per test via `_flush_redis` fixture (applied in integration/e2e conftest)

**Unit Test Isolation:**
- No database, no DI container -- unit tests are pure and fast
- `FakeUnitOfWork` with in-memory `dict`-based repositories
- `MagicMock` logger with `.bind()` chaining support

**Key fixture (function-scoped db_session):**
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

## Mocking

**Unit Tests -- FakeUnitOfWork Pattern:**
- Primary mocking mechanism for command handler tests
- `FakeUnitOfWork` (`backend/tests/fakes/fake_uow.py`) provides in-memory dict-based repos
- 10 fake repositories in `backend/tests/fakes/fake_catalog_repos.py`
- Cross-repo references wired in `FakeUnitOfWork.__init__()` (e.g., `brands._product_store = products._store`)
- Tracks: `committed`, `rolled_back`, `collected_events`

```python
# Setup pattern for unit tests:
uow = FakeUnitOfWork()
handler = CreateBrandHandler(brand_repo=uow.brands, uow=uow, logger=make_logger())

# Pre-seed with existing data:
existing = BrandBuilder().with_slug("nike").build()
uow.brands._store[existing.id] = existing

# Assert after handler execution:
assert uow.committed is True
assert len(uow.collected_events) == 1
```

**Logger Mock Pattern:**
```python
def make_logger():
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger
```

**HTTP Client Mock (respx):**
- `respx>=0.22.0` for mocking httpx calls
- Used in `backend/tests/unit/modules/catalog/infrastructure/test_image_backend_client.py`

**What to Mock:**
- Logger: always mock via `make_logger()` helper
- IImageBackendClient: `AsyncMock()` for brand/product handlers that need it
- UnitOfWork: `FakeUnitOfWork` for command handler unit tests
- External HTTP: `respx` for httpx-based service clients

**What NOT to Mock:**
- Domain entities -- test real `create()`, `update()`, validation logic
- Repository implementations in integration tests -- use real SQLAlchemy + PostgreSQL
- FastAPI app in E2E tests -- test full HTTP stack

## Fixtures and Factories

**Test Data -- Builders (Fluent API):**
```python
# backend/tests/factories/brand_builder.py
brand = BrandBuilder().build()                              # Sensible defaults
brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
brand = BrandBuilder().with_logo("https://img.co/logo.png", storage_id).build()
```
Builders available: `BrandBuilder`, `ProductBuilder`, `AttributeBuilder`, `AttributeValueBuilder`, `AttributeGroupBuilder`, `AttributeTemplateBuilder`, `VariantBuilder`, `SKUBuilder`, `MediaAssetBuilder`

**Test Data -- Object Mothers (Preset Configurations):**
```python
# backend/tests/factories/catalog_mothers.py
brand = BrandMothers.default()
brand = BrandMothers.with_logo()
category = CategoryMothers.root()
category = CategoryMothers.child(parent=root)
categories = CategoryMothers.deep_nested(depth=3)
attr = AttributeMothers.string_dictionary()
attr = AttributeMothers.variant_level()
value = AttributeValueMothers.color_red(attribute_id=attr.id)
```

```python
# backend/tests/factories/identity_mothers.py
identity = IdentityMothers.active_local()
identity = IdentityMothers.deactivated(reason="test")
identity, creds = IdentityMothers.with_credentials(email="test@example.com")
identity, session, raw_token = IdentityMothers.with_session()
session = SessionMothers.expired()
role = RoleMothers.admin()
```

**Test Data -- ORM Factories (Polyfactory):**
```python
# backend/tests/factories/orm_factories.py
class BrandModelFactory(SQLAlchemyFactory):
    __model__ = BrandModel
    __set_relationships__ = True
```
Used primarily for integration tests that need ORM-level seeding.

**Test Data -- Hypothesis Strategies:**
```python
# backend/tests/factories/strategies/primitives.py
from tests.factories.strategies.primitives import i18n_names, valid_slugs, money, behavior_flags

@given(slug=valid_slugs())
def test_brand_create_with_random_slug(slug):
    brand = Brand.create(name="Test", slug=slug)
    assert brand.slug == slug
```

**Seed Fixtures (Integration):**
```python
# backend/tests/integration/modules/catalog/infrastructure/repositories/conftest.py
@pytest.fixture()
async def seed_brand(db_session: AsyncSession) -> Brand:
    repo = BrandRepository(session=db_session)
    brand = Brand.create(name="Test Brand", slug="test-brand")
    return await repo.add(brand)

@pytest.fixture()
async def seed_product_deps(seed_currency, seed_brand, seed_category) -> dict[str, uuid.UUID]:
    return {"brand_id": seed_brand.id, "category_id": seed_category.id}
```

**E2E Helper Functions (NOT fixtures):**
```python
# backend/tests/e2e/api/v1/catalog/conftest.py
async def create_brand(client: AsyncClient, *, name="Test Brand", slug=None) -> dict:
    slug = slug or f"brand-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/api/v1/catalog/brands", json={"name": name, "slug": slug})
    assert resp.status_code == 201
    return resp.json()
```

## Coverage

**Requirements:** No enforced minimum threshold currently

**View Coverage:**
```bash
make coverage
# or
uv run pytest tests/ --cov=project --cov-report=term-missing --cov-report=html
```

**Tool:** pytest-cov `>=7.0.0`

## Test Types

**Architecture Tests:**
- Framework: pytest-archon `>=0.0.7`
- Location: `backend/tests/architecture/test_boundaries.py`
- Purpose: Enforce layer dependency rules (domain purity, no cross-module imports, shared kernel independence)
- 7 rules enforced: domain layer purity, zero framework imports, application boundaries, infrastructure boundaries, module isolation, shared kernel independence, no reverse dependencies
- Example:
  ```python
  def test_domain_layer_is_pure():
      archrule("domain_independence")
          .match("src.modules.*.domain.*")
          .should_not_import("src.modules.*.application.*")
          .should_not_import("src.modules.*.infrastructure.*")
          .should_not_import("src.modules.*.presentation.*")
          .check("src")
  ```

**Unit Tests:**
- Scope: Domain entities, value objects, command/query handlers
- Zero I/O: no database, no network, no file system
- Dependencies: `FakeUnitOfWork`, `MagicMock` logger, `BrandBuilder`/`ProductBuilder`
- Location: `backend/tests/unit/`
- Pattern: create handler with fakes -> call `handle()` -> assert state

**Integration Tests:**
- Scope: Repository implementations, ORM mapping correctness, DB constraints
- Infrastructure: Real PostgreSQL via `db_session` fixture (nested transaction rollback)
- Location: `backend/tests/integration/`
- Pattern: create repository with real session -> call method -> assert DB state
- Seed data via domain factory methods + repository `add()`, or direct ORM inserts

**E2E Tests:**
- Scope: Full HTTP round-trip through FastAPI, DI, handlers, repositories, and back
- Infrastructure: ASGI transport (httpx `ASGITransport`), real PostgreSQL, real Redis
- Location: `backend/tests/e2e/`
- Two client fixtures:
  - `authenticated_client`: registered user with JWT token
  - `admin_client`: registered user with `catalog:manage` permission seeded in Redis
- Pattern: call HTTP endpoint -> assert status code + response shape
- E2E helper functions in `conftest.py` create prerequisite entities via API calls

**Load Tests:**
- Framework: Locust `>=2.43.3`
- Location: `backend/tests/load/`
- Scenarios: `auth_flow.py`, `browse_catalog.py`, `mixed_workload.py`

## Common Patterns

**Async Testing:**
```python
# All async -- asyncio_mode = "auto" means no decorator needed
class TestCreateBrand:
    async def test_creates_brand_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(brand_repo=uow.brands, uow=uow, logger=make_logger())
        result = await handler.handle(CreateBrandCommand(name="Nike", slug="nike"))
        assert uow.committed is True
```

**Error Testing:**
```python
async def test_rejects_duplicate_slug(self):
    uow = FakeUnitOfWork()
    existing = BrandBuilder().with_slug("nike").build()
    uow.brands._store[existing.id] = existing

    handler = CreateBrandHandler(brand_repo=uow.brands, uow=uow, logger=make_logger())

    with pytest.raises(BrandSlugConflictError):
        await handler.handle(CreateBrandCommand(name="Nike New", slug="nike"))

    assert uow.committed is False  # D-07: verify no commit on rejection

# With error_code assertion:
with pytest.raises(ValidationError) as exc_info:
    await handler.handle(BulkCreateBrandsCommand(items=items))
assert exc_info.value.error_code == "BULK_LIMIT_EXCEEDED"
```

**Domain Entity Testing:**
```python
class TestBrand:
    def test_create_with_valid_inputs(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        assert brand.name == "Nike"
        assert isinstance(brand.id, uuid.UUID)

    def test_create_rejects_empty_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            Brand.create(name="", slug="valid")

class TestBrandGuard:
    def test_direct_slug_assignment_raises(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        with pytest.raises(AttributeError, match="Cannot set 'slug' directly"):
            brand.slug = "hacked"
```

**Integration Test Pattern (Arrange-Act-Assert):**
```python
async def test_brand_repository_add_and_get(db_session: AsyncSession):
    # Arrange
    repository = BrandRepository(session=db_session)
    brand = Brand.create(name="Nike", slug="nike")

    # Act
    added_brand = await repository.add(brand)
    fetched_brand = await repository.get(brand.id)

    # Assert
    assert fetched_brand is not None
    assert fetched_brand.name == "Nike"
```

**E2E Test Pattern:**
```python
class TestBrandEndpoints:
    async def test_create_brand_success(self, admin_client: AsyncClient, db_session: AsyncSession):
        slug = f"nike-{uuid.uuid4().hex[:8]}"
        resp = await admin_client.post("/api/v1/catalog/brands", json={"name": "Nike", "slug": slug})
        assert resp.status_code == 201
        assert "id" in resp.json()

    async def test_create_brand_duplicate_slug_returns_409(self, admin_client, db_session):
        slug = f"dup-{uuid.uuid4().hex[:8]}"
        await admin_client.post("/api/v1/catalog/brands", json={"name": "A", "slug": slug})
        resp = await admin_client.post("/api/v1/catalog/brands", json={"name": "B", "slug": slug})
        assert resp.status_code == 409
```

**Event Assertion Pattern:**
```python
async def test_emits_brand_created_event(self):
    uow = FakeUnitOfWork()
    handler = CreateBrandHandler(brand_repo=uow.brands, uow=uow, logger=make_logger())
    await handler.handle(CreateBrandCommand(name="Adidas", slug="adidas"))

    assert len(uow.collected_events) == 1
    assert isinstance(uow.collected_events[0], BrandCreatedEvent)
```

## DI Container in Tests

**Session-scoped container:**
- Full Dishka container assembled in `backend/tests/conftest.py` `app_container` fixture
- `TestOverridesProvider` overrides: `Settings`, `AsyncEngine` (NullPool), `AsyncSession` (from ContextVar), `Redis`, `IOIDCProvider`
- Container is shared across all tests in a session; only `AsyncSession` varies per test

**E2E app creation:**
```python
@pytest.fixture(scope="session")
async def fastapi_app(app_container: AsyncContainer):
    with patch("src.bootstrap.web.create_container", return_value=app_container):
        app = create_app()
        yield app
```

---

*Testing analysis: 2026-03-29*
