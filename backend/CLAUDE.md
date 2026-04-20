# Backend — Loyality Project

**Component:** `backend` | **Vault tag:** `[project/loyality, backend]`

This is the main API service of the Loyality marketplace. Part of a larger project — see `../CLAUDE.md` for project overview, cross-service architecture, and Knowledge Base vault rules.

When saving research/documents to the vault, use `component: backend` in frontmatter and include `backend` in tags.

## Commands

```bash
# Infrastructure (must be running for integration/e2e tests)
docker compose up -d          # Postgres 18, Redis 8.4, RabbitMQ 4.2, MinIO

# Dependencies (uv, NOT pip)
uv sync

# Dev server
uv run uvicorn main:app --reload --port 8080

# Tests (docker compose services required for non-unit tests)
make test                     # all tests
make test-unit                # domain-only, no I/O
make test-integration         # real DB via docker compose
make test-e2e                 # HTTP round-trips
make test-architecture        # Clean Architecture boundary enforcement
uv run pytest tests/path/to/test_file.py::test_name -v  # single test

# Lint & format
make lint                     # ruff check
make format                   # ruff check --fix + ruff format
make typecheck                # mypy

# Migrations (auto-formatted by ruff post-hook in alembic.ini)
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Architecture — Clean Architecture + Modular Monolith

### Modules (bounded contexts)

| Module | Purpose | Files |
|---|---|---|
| `catalog` | Brands, categories, products, variants, SKUs, attributes (EAV), media | 138 |
| `identity` | AuthN/AuthZ: JWT, sessions, RBAC, OIDC, Telegram Mini App, staff invitations | 69 |
| `logistics` | Shipments, tracking events, carrier providers (CDEK, etc.) | 61 |
| `geo` | Reference data: countries, subdivisions, districts, currencies, languages | 37 |
| `cart` | Shopping cart and line items | 35 |
| `supplier` | Supplier accounts and onboarding | 29 |
| `user` | Customer and StaffMember profiles (PII storage) | 28 |

Some modules have an extra `management/` layer (identity, supplier) for admin/back-office use cases.

### Module structure

Each module in `src/modules/<name>/` follows 4 layers:

```
domain/          — attrs entities, value objects, domain events, interfaces (protocols). Zero framework imports.
application/     — commands/ (CQRS write), queries/ (CQRS read, may use ORM directly), consumers/ (event handlers)
infrastructure/  — SQLAlchemy models, repository implementations, Dishka providers, external service clients
presentation/    — FastAPI routers, Pydantic schemas, Dishka DI providers
```

Note: some modules place Dishka providers in `infrastructure/provider.py` (identity, user, cart), others in `presentation/dependencies.py` (catalog, geo, supplier). Both are valid — providers wire infrastructure implementations to domain interfaces.

### Layer rules (enforced by `tests/architecture/test_boundaries.py`)

- Domain MUST NOT import application/infrastructure/presentation or any framework (attrs + stdlib only)
- Application commands MUST NOT import infrastructure (queries and consumers are exempt — CQRS read-side). Exception: `geo` module commands use ORM directly — it is a reference-data module without domain entities/UoW/events
- Modules MUST NOT import each other's domain/application/infrastructure (cross-module deps only at presentation level)
- `src/shared/` is the shared kernel — MUST NOT import any module
- Architecture tests currently parametrize `MODULES = ["catalog", "identity", "user", "cart", "logistics"]` — `geo` and `supplier` are not yet enforced

### Command/Handler pattern

Every write operation follows the same structure:

```python
@dataclass(frozen=True)
class CreateFooCommand:
    name: str
    # ... fields

@dataclass(frozen=True)
class CreateFooResult:
    foo_id: uuid.UUID

class CreateFooHandler:
    def __init__(self, repo: IFooRepository, uow: IUnitOfWork, logger: ILogger) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateFooHandler")

    async def handle(self, command: CreateFooCommand) -> CreateFooResult:
        async with self._uow:
            entity = Foo.create(...)
            entity = await self._repo.add(entity)
            entity.add_domain_event(FooCreatedEvent(...))
            self._uow.register_aggregate(entity)
            await self._uow.commit()
        return CreateFooResult(foo_id=entity.id)
```

- Command = frozen dataclass (input DTO)
- Handler = class with constructor-injected deps + `handle()` method
- Always use `async with self._uow:` context manager
- Call `uow.register_aggregate()` before `uow.commit()` to flush domain events to Outbox

### Domain entities

- `attrs.define` classes inheriting `AggregateRoot` (from `src/shared/interfaces/entities.py`)
- Factory methods (`Entity.create(...)`) preferred over direct construction
- Data Mapper pattern: ORM models in `infrastructure/models.py` are separate from domain entities
- Domain events are dataclass subclasses of `DomainEvent` — must override `aggregate_type` and `event_type`

### Dependency injection (Dishka)

- Container assembled in `src/bootstrap/container.py` → `create_container()`
- Providers define `@provide(scope=Scope.APP|REQUEST)` methods
- In FastAPI routers, inject via `FromDishka[Type]` annotation:
  ```python
  async def endpoint(handler: FromDishka[CreateFooHandler]) -> ...:
  ```
- Auth dependency: `get_current_identity_id` in `src/api/dependencies/auth.py` extracts `sub` from JWT

### Error handling

Uniform JSON envelope: `{"error": {"code", "message", "details", "request_id"}}`.
Exception hierarchy in `src/shared/exceptions.py`:

| Exception                  | HTTP | When to use                                 |
| -------------------------- | ---- | ------------------------------------------- |
| `NotFoundError`            | 404  | Resource doesn't exist                      |
| `UnauthorizedError`        | 401  | Missing/invalid auth token                  |
| `ForbiddenError`           | 403  | Insufficient permissions                    |
| `ValidationError`          | 400  | Business-rule violation on input            |
| `ConflictError`            | 409  | Duplicate slug, version mismatch            |
| `UnprocessableEntityError` | 422  | FK violation, business logic cannot process |

### Transactional Outbox

- Domain events collected in-memory on `AggregateRoot`
- `UnitOfWork.commit()` serializes events to `outbox_messages` table atomically
- Outbox relay publishes to RabbitMQ via TaskIQ scheduler (every minute)
- Events use `dataclasses.asdict()` for serialization — UUID/datetime handled recursively

### Background tasks

TaskIQ with RabbitMQ (aio-pika):
- Broker: `src/bootstrap/broker.py`
- Worker: `src/bootstrap/worker.py`
- Scheduler: `src/bootstrap/scheduler.py`

## Test infrastructure

- **asyncio_mode = auto** with session-scoped event loop
- **DB isolation**: each test gets a nested transaction (savepoint) rolled back after completion
- **Session injection**: `ContextVar[AsyncSession]` (`_db_session_var`) set per test, Dishka `TestOverridesProvider` reads it at REQUEST scope
- **Alembic**: migrations run once per session via subprocess (to avoid async loop conflicts)
- **Redis**: flushed per test in integration/e2e (not autouse at root level to avoid triggering DI for unit tests)
- **Markers**: `@pytest.mark.unit`, `integration`, `e2e`, `architecture`, `load`
- **Factories**: Builder pattern in `tests/factories/` — `*_builder.py` for domain entities, `orm_factories.py` for ORM models
- **Coverage**: auto-collected via pytest.ini `--cov=src --cov-report=term-missing:skip-covered`
- **Timeout**: 30s per test (`pytest-timeout`)

## Database

- PostgreSQL 18, asyncpg driver, SQLAlchemy 2.1+ async
- Naming conventions in `src/infrastructure/database/base.py`: `ix_`, `uq_`, `ck_`, `fk_`, `pk_` prefixes
- Alembic migrations: date-based subdirs (`alembic/versions/YYYY/MM/DD_HHMM_SS_*.py`), auto-formatted by ruff
- Seed data: `scripts/seed_dev.sql` (dev), `src/modules/identity/domain/seed.py` (RBAC, deterministic uuid5)

## Config

Pydantic Settings in `src/bootstrap/config.py`. Reads `.env` file. Key computed fields:
- `database_url` — builds `postgresql+asyncpg://` URL from `PG*` env vars
- `redis_url` — builds `redis://` URL from `REDIS*` env vars

Test settings override in `tests/conftest.py` via `TestOverridesProvider`.
