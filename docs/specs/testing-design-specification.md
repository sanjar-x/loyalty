# Testing Design Specification

> **Status:** Normative
> **Authority:** Chief QA Architect / Lead SDET
> **Scope:** All test code in `tests/` — applies to every module, every layer, every contributor
> **Stack:** Python 3.14 · pytest 9+ · pytest-asyncio · SQLAlchemy 2.1 (async) · Dishka 1.9 · FastAPI · attrs · polyfactory · testcontainers · Locust
> **Architecture:** DDD / Clean Architecture / CQRS / Modular Monolith / Transactional Outbox

---

## Table of Contents

1. [Test Runner & Determinism](#1-test-runner--determinism)
2. [Infrastructure Isolation — The Nested Transaction Pattern](#2-infrastructure-isolation--the-nested-transaction-pattern)
3. [Data Generation — Rich Domains & Aggregates](#3-data-generation--rich-domains--aggregates)
4. [DI Overrides — Strict IoC Container Exclusivity](#4-di-overrides--strict-ioc-container-exclusivity)
5. [Architectural Enforcement — Fitness Functions](#5-architectural-enforcement--fitness-functions)
6. [Strict Layered Directory Taxonomy](#6-strict-layered-directory-taxonomy)

---

## 1. Test Runner & Determinism

### 1.1. Runner Configuration (pytest)

All test execution MUST be governed by a single deterministic configuration in `pyproject.toml`:

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

### 1.2. Parallel Execution Rules

| Rule | Rationale |
|------|-----------|
| `unit/` tests MAY run with `pytest-xdist -n auto` | Zero I/O, no shared state — safe to parallelize |
| `integration/` tests MUST run sequentially (`-n 0`) | Nested transactions share a single engine connection; parallel workers break SAVEPOINT isolation |
| `e2e/` tests MUST run sequentially | ASGI transport shares one FastAPI app instance; concurrent requests corrupt shared session state |
| `architecture/` tests MAY run in parallel | Pure static analysis via `pytest-archon`, no runtime state |
| `load/` tests run outside pytest via `locust` CLI | Dedicated runner with its own process model |

### 1.3. Async Context Isolation

**Problem:** asyncio event loop leaks between test modules cause `InterfaceError`, `Task pending`, and phantom connection pool exhaustion.

**Mandatory Rules:**

1. **Single event loop per session.** A session-scoped fixture MUST create exactly one `asyncio` event loop. All async fixtures and tests share this loop.

```python
@pytest.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

2. **No `loop.run_until_complete()` in fixtures.** All fixtures MUST be native `async def`. Mixing sync and async event loop access is a class-A defect.

3. **ContextVar isolation.** Any `ContextVar` used by application code (e.g., `request_id`, `test_session_var`) MUST be reset per test via fixture teardown. Leaked context vars cause cross-test contamination.

```python
@pytest.fixture(autouse=True)
def _reset_context_vars():
    from src.shared.context import _request_id_var
    token = _request_id_var.set("test-request-id")
    yield
    _request_id_var.reset(token)
```

4. **No global event loop policy mutation.** Tests MUST NOT call `asyncio.set_event_loop_policy()`. The session fixture owns the loop lifecycle exclusively.

### 1.4. Determinism Guarantees

| Source of flakiness | Mitigation |
|---------------------|------------|
| Time-dependent assertions | Use `freezegun` or inject a `Clock` protocol; never assert on `datetime.now()` |
| UUID ordering | Assert on membership (`in`, `set`), not on list position |
| Random data in factories | Factories MUST be seedable; provide a `seed` fixture for reproducibility |
| Network I/O in unit tests | Prohibited. Any test importing `httpx`, `aiohttp`, or `requests` outside `e2e/` or `load/` is a hard failure |
| File system writes | Prohibited in `unit/` and `integration/`. Use `tmp_path` fixture only in `e2e/` when testing file uploads |

### 1.5. Mandatory Coverage Quality Gates

Coverage thresholds are enforced per architectural layer. Falling below these thresholds MUST block the CI pipeline:

| Layer | Scope | Minimum Coverage | Rationale |
|-------|-------|-----------------|-----------|
| **Domain** (`src/modules/*/domain/`) | Branch coverage | **95%** | Core business logic — the highest-value, lowest-cost test target |
| **Application** (`src/modules/*/application/`) | Branch coverage | **85%** | Command/query handlers; all happy + primary error paths |
| **Infrastructure** (`src/modules/*/infrastructure/`) | Line coverage | **70%** | Repository data mapping; ORM-to-domain correctness |
| **Presentation** (`src/modules/*/presentation/`) | Line coverage | **60%** | Routing, schema validation; covered by e2e happy-path tests |
| **Shared** (`src/shared/`) | Branch coverage | **90%** | Foundation abstractions; failure here cascades everywhere |

**Enforcement command:**

```bash
uv run pytest tests/unit/ tests/integration/ tests/e2e/ \
    --cov=src --cov-branch \
    --cov-fail-under=80 \
    --cov-report=term-missing \
    --cov-report=html:reports/coverage
```

> The global `--cov-fail-under=80` is the floor. Per-layer thresholds are enforced by a custom `conftest.py` plugin or CI script that parses the coverage JSON report.

---

## 2. Infrastructure Isolation — The Nested Transaction Pattern

### 2.1. Design Philosophy

Integration tests MUST interact with a **real PostgreSQL database** — never SQLite, never mocks. The Nested Transaction Pattern achieves:

- **Millisecond-level test isolation** — no `DROP/CREATE TABLE` per test
- **Pristine state guarantee** — every test sees an empty database
- **Session-once schema creation** — `Base.metadata.create_all()` runs exactly once per `pytest` session

### 2.2. Transaction Topology

```
┌─────────────────────────────────────────────────────────────────┐
│ TEST SESSION (scope="session")                                  │
│                                                                 │
│  AsyncEngine ← create_async_engine(poolclass=NullPool)          │
│  Base.metadata.create_all()  ← runs once                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ TEST FUNCTION (scope="function")                          │  │
│  │                                                           │  │
│  │  conn = engine.connect()                                  │  │
│  │  transaction = conn.begin()           ← OUTER TRANSACTION │  │
│  │  nested = conn.begin_nested()         ← SAVEPOINT         │  │
│  │                                                           │  │
│  │  session = AsyncSession(bind=conn,                        │  │
│  │      join_transaction_mode="create_savepoint")            │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ APPLICATION CODE (UnitOfWork)                       │  │  │
│  │  │                                                     │  │  │
│  │  │  session.add(entity)                                │  │  │
│  │  │  session.commit()  → commits to SAVEPOINT, not DB   │  │  │
│  │  │  session.flush()   → writes visible within conn     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  TEARDOWN:                                                │  │
│  │    await session.close()                                  │  │
│  │    await transaction.rollback()       ← ROLLS BACK ALL    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ NEXT TEST FUNCTION → pristine state, zero cost            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3. Critical Implementation Rules

1. **`NullPool` is mandatory for test engines.** Connection pooling across tests causes leaked connections and phantom deadlocks. `NullPool` creates a fresh connection per `.connect()` call.

2. **`join_transaction_mode="create_savepoint"` is mandatory.** This tells SQLAlchemy that when application code calls `session.commit()`, it should commit to a SAVEPOINT (not the real transaction). Without this, `session.commit()` inside a `UnitOfWork.commit()` call would finalize the outer transaction, destroying test isolation.

3. **`expire_on_commit=False` is mandatory.** After `session.commit()` inside nested transactions, ORM objects must remain accessible without re-querying (the outer transaction hasn't committed, so a re-query would see stale data).

4. **The `test_session_var` ContextVar bridges Dishka and the test session.** The `TestOverridesProvider` overrides `Scope.REQUEST` session to return `test_session_var.get()`, ensuring all application code within a test uses the same nested-transaction-bound session.

5. **Never call `await session.commit()` in test setup/assertion code.** Use `await session.flush()` to make data visible for assertions, or read directly from the same session. Committing in test code breaks the SAVEPOINT boundary.

### 2.4. Infrastructure Container Lifecycle

External infrastructure (PostgreSQL, Redis, MinIO, RabbitMQ) MUST be spun up exactly **once per test session**, not per test:

| Strategy | When to use |
|----------|-------------|
| **`docker-compose.yml` (pre-started)** | Local development, CI with pre-configured services. Fastest startup. **Current default.** |
| **`testcontainers`** | CI environments without pre-configured Docker services. Containers auto-start and auto-destroy. |

**Rule:** Tests MUST NOT assume infrastructure availability. If a container is unreachable, the test session MUST fail fast with a clear diagnostic message — not hang on connection timeouts.

```python
@pytest.fixture(scope="session")
async def test_engine(app_container: AsyncContainer) -> AsyncEngine:
    engine = await app_container.get(AsyncEngine)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.exit(f"Database unreachable: {e}. Start containers: docker compose up -d")
    # Schema creation...
```

### 2.5. Redis & External State Isolation

Redis state MUST be isolated per test. Two strategies:

| Strategy | Implementation |
|----------|---------------|
| **`FLUSHDB` per test** (default) | `@pytest.fixture(autouse=True)` calls `await redis.flushdb()` in teardown |
| **Key-prefix per test** | Prefix all keys with `test_{test_id}_` — allows parallel test runs against shared Redis |

**Rule:** Never use Redis database `0` in production. Tests use database `0` exclusively.

---

## 3. Data Generation — Rich Domains & Aggregates

### 3.1. Prohibition: No Manual Mocking of Domain Objects

**FORBIDDEN:**

```python
# ❌ NEVER DO THIS
identity = MagicMock(spec=Identity)
identity.id = uuid.uuid4()
identity.is_active = True
```

**Why:** Mocking domain objects bypasses invariant enforcement, factory methods, and `__attrs_post_init__`. A mock that "passes" tests doesn't prove the domain logic works — it proves the mock was configured to pass.

**REQUIRED:** All domain entities MUST be created via their factory methods (`.register()`, `.create()`) or via Object Mother / Test Data Builder patterns.

### 3.2. Object Mother Pattern

An **Object Mother** provides pre-configured, valid-by-default domain entities. Each module MUST have an Object Mother in `tests/factories/`.

**Naming convention:** `{Module}Mothers` — e.g., `IdentityMothers`, `CatalogMothers`

```python
# tests/factories/identity_mothers.py
import uuid
from datetime import datetime, timezone

from src.modules.identity.domain.entities import (
    Identity, LocalCredentials, Role, Permission, Session, LinkedAccount,
)
from src.modules.identity.domain.value_objects import IdentityType


class IdentityMothers:
    """Pre-built Identity aggregate configurations for common test scenarios."""

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
        identity.clear_domain_events()  # Clean slate for test assertions
        return identity

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
```

### 3.3. Test Data Builder Pattern

For complex aggregates requiring fine-grained customization, use the **Builder** pattern:

```python
# tests/factories/builders.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from src.modules.identity.domain.entities import Role, Permission


class RoleBuilder:
    """Fluent builder for Role entities with sensible defaults."""

    def __init__(self) -> None:
        self._id = uuid.uuid4()
        self._name = "test-role"
        self._description = "Test role"
        self._is_system = False

    def with_name(self, name: str) -> RoleBuilder:
        self._name = name
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
```

### 3.4. Polyfactory for Infrastructure-Layer Test Data

For ORM models (used in integration tests to pre-populate database state), use `polyfactory`:

```python
# tests/factories/orm_factories.py
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from src.modules.identity.infrastructure.models import IdentityModel


class IdentityModelFactory(SQLAlchemyFactory):
    __model__ = IdentityModel
    __set_relationships__ = True
```

**Rules for Polyfactory usage:**

| Context | Use polyfactory? | Rationale |
|---------|-------------------|-----------|
| Domain entities (unit tests) | **NO** — use Object Mothers | Domain entities have invariants enforced by factory methods; polyfactory bypasses them |
| ORM models (integration tests) | **YES** | ORM models are data containers; polyfactory generates valid column data efficiently |
| Pydantic schemas (e2e tests) | **YES** | Request/response schemas are validation-only; polyfactory covers edge cases |

### 3.5. Factory Organization

```
tests/factories/
├── __init__.py
├── identity_mothers.py      # Object Mothers for Identity module domain entities
├── catalog_mothers.py        # Object Mothers for Catalog module domain entities
├── user_mothers.py           # Object Mothers for User module domain entities
├── storage_mothers.py        # Object Mothers for Storage module domain entities
├── builders.py               # Test Data Builders for complex aggregate construction
├── orm_factories.py          # Polyfactory-based ORM model factories (integration layer)
└── schema_factories.py       # Polyfactory-based Pydantic schema factories (e2e layer)
```

---

## 4. DI Overrides — Strict IoC Container Exclusivity

### 4.1. The Cardinal Rule

> **All dependency resolution in tests MUST go through the Dishka IoC container. FastAPI's `app.dependency_overrides` is FORBIDDEN.**

**Why:**

- `app.dependency_overrides` operates at the web framework level, not at the business logic level. It cannot override dependencies injected into command handlers, query handlers, or domain services.
- It creates a parallel DI mechanism that diverges from production behavior.
- It doesn't respect Dishka scopes (`Scope.APP` vs `Scope.REQUEST`), leading to lifecycle bugs that only manifest in production.

### 4.2. The TestOverridesProvider Pattern

All test-specific dependency replacements MUST be implemented as a Dishka `Provider` with `override=True`:

```python
class TestOverridesProvider(Provider):
    """
    Overrides production I/O boundaries with test-safe alternatives.
    Registered LAST in make_async_container() to take precedence.
    """

    @provide(scope=Scope.APP, override=True)
    async def engine(self) -> AsyncIterable[AsyncEngine]:
        engine = create_async_engine(url=self.db_url, poolclass=NullPool)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.REQUEST, override=True)
    async def session(self) -> AsyncSession:
        return test_session_var.get()

    @provide(scope=Scope.APP, override=True)
    async def blob_storage(self) -> IBlobStorage:
        return InMemoryBlobStorage()  # Fake, not Mock
```

**Override registration order matters.** `TestOverridesProvider` MUST be the last provider passed to `make_async_container()`. Dishka resolves conflicts by last-registered-wins.

### 4.3. Stubs & Fakes over Spies & Mocks (Martin Fowler's Taxonomy)

| Test Double | Definition | When to Use | When NOT to Use |
|-------------|------------|-------------|-----------------|
| **Stub** | Returns canned responses, no behavior verification | Replacing read-only external services (e.g., `IOIDCProvider` returning a fixed `UserInfo`) | When you need to verify interactions |
| **Fake** | Working implementation with shortcuts (e.g., in-memory dict instead of Redis) | Replacing stateful external services (e.g., `IBlobStorage` → in-memory file store) | When the fake would be as complex as the real thing |
| **Mock** (`unittest.mock`) | Records calls, verifies interactions | **ONLY** for verifying side-effects at I/O boundaries (e.g., "did we call `S3.put_object`?") | Anywhere inside the domain or application layer |
| **Spy** | Wraps real object, records calls | **PROHIBITED in this codebase** | Everywhere — spies couple tests to implementation details |

**Mandatory rules:**

1. **Domain layer tests:** Zero mocks. Zero stubs. Only real domain objects created via Object Mothers.
2. **Application layer tests (unit):** Stubs for repository interfaces. Fakes for external services. No mocks on domain entities.
3. **Application layer tests (integration):** Real repositories, real database. Fakes for external I/O (S3, OIDC, email).
4. **Presentation layer tests (e2e):** Real application stack. Fakes for external I/O only.

### 4.4. Boundary Definition: What Gets Overridden

Only **external I/O boundaries** may be overridden. Internal application wiring MUST use production implementations:

| Dependency | Category | Override Strategy |
|------------|----------|-------------------|
| `AsyncEngine` | Infrastructure (DB) | **Override** — point to test database URL, `NullPool` |
| `AsyncSession` | Infrastructure (DB) | **Override** — inject nested-transaction session via `ContextVar` |
| `redis.Redis` | Infrastructure (Cache) | **Override** — point to test Redis instance |
| `IBlobStorage` | External I/O (S3) | **Override with Fake** — `InMemoryBlobStorage` |
| `IOIDCProvider` | External I/O (Auth) | **Override with Stub** — returns pre-configured `OIDCUserInfo` |
| `IEmailSender` | External I/O (Email) | **Override with Fake** — `InMemoryEmailSender` with sent-message inspection |
| `ITokenProvider` | Infrastructure (JWT) | **DO NOT override** — use real JWT encoding/decoding |
| `IPasswordHasher` | Infrastructure (Security) | **DO NOT override** — use real Argon2 hashing |
| `IPermissionResolver` | Infrastructure (Cache) | **DO NOT override** — use real resolver with test Redis |
| `*Repository` | Infrastructure (Data Access) | **DO NOT override** — use real repositories with nested-transaction DB |
| `*Handler` | Application (CQRS) | **DO NOT override** — use real handlers with real repositories |

### 4.5. Accessing Handlers in Integration Tests

Tests MUST obtain command/query handlers through the Dishka container, not through direct instantiation:

```python
async def test_register_handler(app_container: AsyncContainer, db_session: AsyncSession):
    async with app_container() as request_container:
        handler = await request_container.get(RegisterHandler)
        result = await handler.handle(RegisterCommand(email="test@example.com", password="S3cure!"))

    assert result.identity_id is not None
```

**Why:** Direct instantiation (`handler = RegisterHandler(repo=..., uow=...)`) bypasses the DI graph. If a handler's constructor signature changes, manually instantiated tests become stale without failing — the most dangerous kind of test rot.

---

## 5. Architectural Enforcement — Fitness Functions

### 5.1. Purpose

Fitness functions are **automated architectural boundary checks** that run as part of the test suite. They physically prevent dependency violations from entering the codebase. Unlike code reviews (which are human and fallible), fitness functions are deterministic and unskippable.

### 5.2. Implementation: pytest-archon

All fitness functions live in `tests/architecture/test_boundaries.py` and use the `pytest-archon` library.

### 5.3. Mandatory Rules (The Fitness Function Catalog)

#### Rule 1: Domain Layer Purity

The Domain layer is the innermost ring. It MUST NOT import from any outer layer or any framework.

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

#### Rule 2: Domain Has Zero Framework Imports

Domain entities use `attrs` and stdlib only. No SQLAlchemy, no FastAPI, no Dishka, no Redis, no TaskIQ.

```python
@pytest.mark.parametrize("module", ["identity", "catalog", "user", "storage"])
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

#### Rule 3: Application Layer Boundaries

Application may import Domain but MUST NOT import Infrastructure or Presentation.

```python
def test_application_layer_boundaries():
    (
        archrule("application_independence")
        .match("src.modules.*.application.*")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )
```

#### Rule 4: Infrastructure Does Not Import Presentation

```python
def test_infrastructure_does_not_import_presentation():
    (
        archrule("infrastructure_independence")
        .match("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )
```

#### Rule 5: Modular Monolith Cross-Module Isolation

Modules MUST NOT directly import each other's internals. Inter-module communication happens exclusively via:
- Domain events (Transactional Outbox → Message Broker → Consumer)
- Shared kernel interfaces (`src/shared/interfaces/`)
- Public presentation facades (`src/modules/*/presentation/facade.py`)

```python
# Generate all forbidden cross-module import pairs
MODULES = ["catalog", "storage", "identity", "user"]

@pytest.mark.parametrize("source,target", [
    (s, t) for s in MODULES for t in MODULES if s != t
])
def test_module_isolation(source: str, target: str):
    for layer in ["domain", "application", "infrastructure"]:
        (
            archrule(f"{source}_cannot_import_{target}_{layer}")
            .match(f"src.modules.{source}.*")
            .should_not_import(f"src.modules.{target}.{layer}.*")
            .check("src")
        )
```

> **Allowed exception:** `user.presentation` → `identity.presentation` for shared auth dependencies. Document all exceptions with an `exclude()` clause and a code comment explaining why.

#### Rule 6: Shared Kernel Independence

The `src/shared/` package is the foundation. It MUST NOT import from any business module.

```python
def test_shared_kernel_is_independent():
    (
        archrule("shared_kernel_independence")
        .match("src.shared.*")
        .should_not_import("src.modules.*")
        .check("src")
    )
```

#### Rule 7: No Circular Dependencies Between Layers

Within a single module, the dependency graph MUST be acyclic: `Domain ← Application ← Infrastructure ← Presentation`.

```python
def test_no_reverse_layer_dependencies():
    for module in MODULES:
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
            .should_not_import(f"src.modules.{module}.infrastructure.*")
            .check("src")
        )
```

### 5.4. Fitness Function Execution

```bash
# Run as a mandatory CI gate — failure = build rejection
uv run pytest tests/architecture/ -v --tb=short -x
```

**Rule:** Architecture tests MUST run **before** any other tests in the CI pipeline. If boundaries are violated, there is no point running unit or integration tests — the architecture itself is broken.

---

## 6. Strict Layered Directory Taxonomy

### 6.1. Directory Structure

```
tests/
├── conftest.py                      # Session-scoped: event loop, engine, container, db_session
├── architecture/
│   ├── conftest.py                  # pytestmark = pytest.mark.architecture
│   └── test_boundaries.py          # ALL fitness functions (Section 5)
├── factories/
│   ├── __init__.py
│   ├── identity_mothers.py          # Object Mothers: Identity, Session, Role, Permission
│   ├── catalog_mothers.py           # Object Mothers: Brand, Category, Product, SKU
│   ├── user_mothers.py              # Object Mothers: User
│   ├── storage_mothers.py           # Object Mothers: StorageObject
│   ├── builders.py                  # Test Data Builders for complex aggregates
│   ├── orm_factories.py             # Polyfactory SQLAlchemy model factories
│   └── schema_factories.py          # Polyfactory Pydantic schema factories
├── unit/
│   ├── conftest.py                  # Empty or minimal; no DB fixtures
│   └── modules/
│       ├── identity/
│       │   └── domain/
│       │       ├── test_entities.py
│       │       ├── test_value_objects.py
│       │       └── test_events.py
│       ├── catalog/
│       │   └── domain/
│       │       ├── test_entities.py
│       │       ├── test_value_objects.py
│       │       └── test_events.py
│       ├── user/
│       │   └── domain/
│       │       └── test_entities.py
│       └── storage/
│           └── domain/
│               └── test_entities.py
├── integration/
│   ├── conftest.py                  # Overrides db_session with join_transaction_mode
│   └── modules/
│       ├── identity/
│       │   ├── infrastructure/
│       │   │   └── repositories/
│       │   │       ├── test_identity_repo.py
│       │   │       ├── test_session_repo.py
│       │   │       └── test_role_repo.py
│       │   └── application/
│       │       └── commands/
│       │           ├── test_register.py
│       │           ├── test_login.py
│       │           └── test_login_oidc.py
│       ├── catalog/
│       │   ├── infrastructure/
│       │   │   └── repositories/
│       │   │       ├── test_brand.py
│       │   │       └── test_category.py
│       │   └── application/
│       │       └── commands/
│       │           ├── test_create_brand.py
│       │           └── test_confirm_brand_logo.py
│       ├── user/
│       │   └── ...
│       └── storage/
│           └── ...
├── e2e/
│   ├── conftest.py                  # FastAPI app, AsyncClient via ASGI transport
│   └── api/
│       └── v1/
│           ├── test_auth.py         # /auth/* endpoints
│           ├── test_brands.py       # /catalog/brands/* endpoints
│           ├── test_categories.py   # /catalog/categories/* endpoints
│           └── test_users.py        # /users/* endpoints
└── load/
    ├── locustfile.py                # Locust user definitions
    ├── scenarios/
    │   ├── auth_flow.py             # Login → Token refresh → Logout
    │   ├── catalog_browse.py        # Category tree → Product search
    │   └── mixed_workload.py        # Realistic multi-user simulation
    └── thresholds.yml               # SLA definitions (p99 latency, error rate)
```

### 6.2. Layer Definitions and Contracts

#### `tests/architecture/` — Fitness Functions

| Attribute | Value |
|-----------|-------|
| **What it tests** | Dependency rules between layers and modules |
| **I/O allowed** | None (pure static analysis via `pytest-archon`) |
| **Database** | Not used |
| **Fixtures required** | None |
| **Execution speed** | < 1 second total |
| **Failure semantics** | Architecture violation = **HARD BLOCK**. No code ships until fixed. |

#### `tests/factories/` — Data Generation

| Attribute | Value |
|-----------|-------|
| **What it contains** | Object Mothers, Test Data Builders, Polyfactory definitions |
| **Not a test directory** | Factories are imported by tests, never executed directly |
| **No test files** | Files MUST NOT contain test functions (`test_*`) |
| **Naming** | `{module}_mothers.py`, `builders.py`, `orm_factories.py`, `schema_factories.py` |

#### `tests/unit/` — Domain Layer ONLY

| Attribute | Value |
|-----------|-------|
| **What it tests** | Entity behavior, value object validation, domain event emission, aggregate invariants |
| **Layer scope** | `src/modules/*/domain/` exclusively |
| **I/O allowed** | **ZERO**. No database, no network, no file system, no Redis |
| **Database** | **Prohibited**. Tests MUST NOT depend on `db_session` fixture |
| **Mocks allowed** | **ZERO**. Only real domain objects via Object Mothers |
| **Execution speed** | < 1ms per test. Total suite < 5 seconds |
| **Directory mirrors source** | `tests/unit/modules/{module}/domain/` mirrors `src/modules/{module}/domain/` |

**Naming convention:** `test_{entity_name}.py` or `test_{value_object_name}.py`

**Test structure:**
```python
class TestIdentity:
    def test_register_creates_active_identity(self):
        identity = IdentityMothers.active_local()
        assert identity.is_active is True

    def test_deactivate_emits_event(self):
        identity = IdentityMothers.active_local()
        identity.deactivate(reason="test")
        assert len(identity.domain_events) == 1
        assert isinstance(identity.domain_events[0], IdentityDeactivatedEvent)
```

> **Note:** Unit tests are synchronous (`def test_*`), not async. Domain logic MUST NOT contain `await` calls.

#### `tests/integration/` — Application + Infrastructure

| Attribute | Value |
|-----------|-------|
| **What it tests** | Command handler orchestration, query handler results, repository data mapping, UoW commit/rollback, Outbox event persistence |
| **Layer scope** | `src/modules/*/application/` and `src/modules/*/infrastructure/` |
| **I/O allowed** | **Database only** (via nested transactions). External I/O (S3, OIDC) overridden with Fakes |
| **Database** | **Required**. All tests depend on `db_session` fixture |
| **Mocks allowed** | Fakes for external I/O boundaries (see Section 4.4). No mocks on domain or repositories |
| **Execution speed** | < 100ms per test (nested transactions, no schema recreation) |
| **Handler access** | Via Dishka container: `await request_container.get(RegisterHandler)` |

**Test structure:**
```python
async def test_register_handler_creates_identity(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request:
        handler = await request.get(RegisterHandler)

        # Act
        result = await handler.handle(
            RegisterCommand(email="new@example.com", password="S3cure!Pass")
        )

    # Assert — query the DB directly via the same session
    orm = await db_session.get(IdentityModel, result.identity_id)
    assert orm is not None
    assert orm.type == "LOCAL"
```

**What integration tests MUST verify:**

| Verification | Example |
|-------------|---------|
| Handler produces correct result | `result.identity_id is not None` |
| Data persisted correctly | `await db_session.get(Model, id)` returns expected state |
| Domain events written to Outbox | Query `outbox_messages` table for expected event type |
| Unique constraint violations raise `ConflictError` | Register same email twice → `ConflictError` |
| Foreign key violations raise `UnprocessableEntityError` | Reference non-existent entity → `UnprocessableEntityError` |

#### `tests/e2e/` — Presentation Layer

| Attribute | Value |
|-----------|-------|
| **What it tests** | HTTP routing, request/response schema validation, status codes, global exception handler mapping, authentication/authorization flow |
| **Layer scope** | `src/modules/*/presentation/` and `src/api/` |
| **I/O allowed** | Full application stack via ASGI transport (no real HTTP server) |
| **Database** | Real database via nested transactions (same as integration) |
| **Focus** | **Happy paths** and critical error paths. Not exhaustive edge-case testing |
| **Client** | `httpx.AsyncClient` with `ASGITransport` |

**Test structure:**
```python
async def test_register_returns_201(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "S3cure!Pass",
    })
    assert response.status_code == 201
    assert "identity_id" in response.json()
```

**What e2e tests MUST verify:**

| Verification | Example |
|-------------|---------|
| Correct HTTP status code | `201 Created`, `409 Conflict`, `401 Unauthorized` |
| Response body matches Pydantic schema | All expected fields present, correct types |
| Global exception handler maps AppException → HTTP | `IdentityAlreadyExistsError` → `409` |
| Authentication guard rejects anonymous requests | `GET /users/me` without token → `401` |
| Permission guard rejects unauthorized requests | `POST /admin/roles` without `admin` role → `403` |

**What e2e tests MUST NOT do:**

- Test business logic exhaustively (that's unit/integration territory)
- Verify database state directly (that's integration territory)
- Mock internal services (use the full stack)

#### `tests/load/` — Resilience & Threshold Testing

| Attribute | Value |
|-----------|-------|
| **What it tests** | Throughput under load, p99 latency SLAs, connection pool saturation, cache hit rates, error rates under stress |
| **Runner** | Locust (separate from pytest) |
| **Database** | Real database (separate test instance, not nested transactions) |
| **Environment** | Closest to production: real HTTP server, real connection pools, real Redis caching |
| **Execution** | Manual or scheduled CI — never on every commit |

**Mandatory load test scenarios:**

| Scenario | Target | Failure Threshold |
|----------|--------|-------------------|
| **Auth flow** (register → login → refresh → logout) | 100 concurrent users | p99 < 500ms, error rate < 0.1% |
| **Catalog browse** (category tree → product search) | 500 concurrent users | p99 < 200ms, error rate < 0.01% |
| **Connection pool saturation** | Ramp to `pool_size + max_overflow + 10` | Graceful 503, no connection leak |
| **Cache invalidation storm** | Flush Redis mid-test | Recovery < 5s, no cascading failures |
| **Mixed realistic workload** | 80% reads, 20% writes | Sustained 1000 RPS for 5 minutes |

**Threshold file format** (`tests/load/thresholds.yml`):

```yaml
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
```

---

## Appendix A: CI Pipeline Integration Order

```
1. uv run ruff check --fix . && uv run ruff format .     # Lint & Format
2. uv run pytest tests/architecture/ -v -x                 # Fitness Functions (HARD BLOCK)
3. uv run pytest tests/unit/ -v --tb=short -n auto         # Unit Tests (parallel OK)
4. uv run pytest tests/integration/ -v --tb=short          # Integration Tests (sequential)
5. uv run pytest tests/e2e/ -v --tb=short                  # E2E Tests (sequential)
6. uv run pytest tests/unit/ tests/integration/ tests/e2e/ \
       --cov=src --cov-branch --cov-fail-under=80          # Coverage Gate
7. uv run mypy src/                                         # Type Check
```

**Rule:** Each step is a separate CI job. Steps 2-5 are sequential (fail-fast). If step 2 fails, steps 3-7 do not run.

## Appendix B: Anti-Patterns Registry

| Anti-Pattern | Why It's Wrong | Correct Alternative |
|-------------|----------------|---------------------|
| `MagicMock(spec=Identity)` in unit tests | Bypasses domain invariants | Object Mother: `IdentityMothers.active_local()` |
| `app.dependency_overrides[Dep] = lambda: mock` | Parallel DI system, scope-unaware | `TestOverridesProvider` with `override=True` |
| `@pytest.fixture(scope="session") def db_session` | Session-scoped DB session shares state across all tests | `scope="function"` with nested transactions |
| `await session.commit()` in test assertions | Breaks SAVEPOINT boundary, pollutes DB for next test | `await session.flush()` or read from same session |
| `sqlite://` as test database | Different SQL dialect, missing features (JSON, arrays, CTEs) | Real PostgreSQL via docker-compose or testcontainers |
| `time.sleep(1)` in async tests | Introduces flakiness, slows suite | Use `asyncio.Event` or polling with timeout |
| `from unittest.mock import patch` on domain classes | Patches bypass attrs `__init__`, break invariants | Inject via DI; replace at boundary only |
| `pytest-xdist` on integration tests | Parallel workers share DB engine; SAVEPOINT isolation breaks | Sequential execution (`-n 0`) |
| Direct handler instantiation in tests | Bypasses DI graph; stale on constructor changes | `await container.get(Handler)` |
| Testing private methods (`_method`) | Couples tests to implementation, not behavior | Test via public API only |

## Appendix C: Test Naming Conventions

```
test_{action}_{expected_outcome}[_{condition}]

Examples:
  test_register_creates_active_identity
  test_deactivate_emits_event
  test_login_raises_when_identity_deactivated
  test_create_brand_persists_to_database_with_logo
  test_register_endpoint_returns_201
  test_register_endpoint_returns_409_when_email_exists
```

**Rules:**
- Use `snake_case` exclusively
- Start with `test_`
- Include the action being tested
- Include the expected outcome
- Optionally include the condition/scenario after a trailing underscore
- Class grouping: `class Test{Entity}:` or `class Test{Handler}:`
