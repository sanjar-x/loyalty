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
make typecheck                # ty check (Astral type checker; mypy is also configured in pyproject.toml)

# Migrations (auto-formatted by ruff post-hook in alembic.ini)
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Architecture — Clean Architecture + Modular Monolith

### Modules (bounded contexts) — 13 total

| Module | Purpose |
|---|---|
| `catalog` | Brands, categories, products, variants, SKUs, attributes (EAV), attribute templates, media |
| `identity` | AuthN/AuthZ: JWT, sessions, RBAC, OIDC, Telegram Mini App, staff invitations |
| `pricing` | Variables, formula AST + evaluator, pricing contexts, product pricing profiles, supplier/category settings, SKU autonomous recompute (ADR-005) |
| `logistics` | Shipments, tracking events, carrier providers (CDEK, Yandex Delivery, DobroPost cross-border) |
| `geo` | Reference data: countries, subdivisions, districts, currencies, languages |
| `cart` | Shopping cart and line items, checkout snapshots (with pickup_carrier + recipient_id) |
| `favorites` | Multi-list favorites (products & brands), default-list invariant |
| `supplier` | Supplier accounts (cross-border / local) and onboarding |
| `user` | Customer and StaffMember profiles (PII storage) |
| `activity` | User activity tracking (Redis hot path → partitioned PG), trending, co-view recommendations |
| `order` | 14-state Loyality FSM, recipient snapshot, dual-leg tracking (DobroPost cross-border + russian carrier last-mile), DobroPost int-id ↔ UUID side mapping with retry + circuit-breaker, webhook → outbox dispatch |
| `payment` | Two-step authorize-only at create + capture deferred to procure, payment intents FSM, refund, Visa-standard auth TTL, fake/yookassa/sbp/tinkoff providers behind `IPaymentProvider` |
| `recipient` | Customer-owned customs recipients with passport (4+6) / INN (12, Минфин checksum) / birth_date validation, ownership boundary check at checkout, validation status FSM |

Some modules have an extra `management/` layer (identity, supplier) for admin/back-office use cases.

There is no separate `storage` module — image lifecycle is delegated to the `image_backend/` microservice; backend talks to it through `src/modules/catalog/infrastructure/adapters/image_backend_client.py` (X-API-Key, server-to-server).

### Module structure

Each module in `src/modules/<name>/` follows 4 layers:

```
domain/          — attrs entities, value objects, domain events, interfaces (protocols). Zero framework imports.
                   Use entities.py for ≤2 aggregates; entities/ package (one file per aggregate) when more.
application/     — commands/ (CQRS write), queries/ (CQRS read, may use ORM directly), consumers/ (event handlers; only when subscribers exist)
infrastructure/  — SQLAlchemy models, repository implementations, Dishka provider, external clients in adapters/, services in services/
presentation/    — FastAPI routers (`router_<scope>.py`), Pydantic schemas, FastAPI deps in dependencies.py (NOT Dishka)
```

**Naming conventions:**
- Dishka providers: ALWAYS in `infrastructure/provider.py` — wiring infrastructure implementations to domain interfaces is an infrastructure concern.
- FastAPI dependencies (`Depends`-callables, security): in `presentation/dependencies.py` — only the identity module currently uses this for `Auth` / `RequirePermission` / `BearerCredentials`.
- External HTTP/RPC clients: `infrastructure/adapters/<service>_client.py` (e.g. catalog's `image_backend_client`, cart's `catalog_adapter`).
- Stateless domain helpers: `domain/services.py` (e.g. user's `generate_referral_code`).
- Bootstrap/CLI tooling: `<module>/management/<task>.py` — admin scripts that reach into the full DI container; not production request paths.

### Router naming convention (audience-based)

**Один файл — одна аудитория.** Каждый модуль с admin- и customer-аудиторией одновременно
ОБЯЗАН иметь как минимум 2 router-файла. Три зарезервированных имени:

| File                          | URL prefix                            | Audience                  | Auth                                                |
| ----------------------------- | ------------------------------------- | ------------------------- | --------------------------------------------------- |
| `router_admin.py`             | `/admin/<module-or-scope>/<resource>` | staff (admin/manager)     | `Depends(RequireStaffRole)` + permission per route  |
| `router_<audience>.py`        | `/<resource>` или `/storefront/<resource>` | customer / public    | optional JWT (`Auth` или public)                    |
| `router_webhooks.py`          | `/webhooks/<provider>`                | server-to-server          | shared secret / token / IP whitelist                |

`<audience>`-варианты:
- `router_customer.py` — customer-only с авторизацией (cart, orders, favorites, payments, recipients).
- `router_storefront.py` — public read (storefront catalog, brands, search).
- `router_account.py` — авторизованный пользователь любой роли (sessions, password).
- `router_<resource>.py` — когда у модуля одна аудитория и это понятно (`router_auth.py`,
  `router_invitation.py`, `router_profile.py`).

**URL-уровень (3 namespace'а в `/api/v1/`):**

```
/api/v1/admin/<module>/<resource>     ← staff-only (admin panel)
/api/v1/<resource>                    ← customer/public (storefront, cart, orders, ...)
/api/v1/webhooks/<provider>           ← server-to-server (DobroPost, CDEK, Yandex, ...)
```

**Tag convention** (для группировки в `/docs`):
- Admin: `tags=["Admin / <Resource>"]` → `Admin / Catalog / Brands`, `Admin / Pricing / Variables`
- Customer: `tags=["<Resource>"]` → `Cart`, `Orders`, `Favorites`, `Storefront / Products`
- Webhooks: `tags=["Webhooks / <Provider>"]` → `Webhooks / DobroPost`

**DI baseline** для admin-routers:
```python
admin_router = APIRouter(
    prefix="/admin/catalog/brands",
    tags=["Admin / Catalog / Brands"],
    dependencies=[Depends(RequireStaffRole)],  # baseline: must be staff
    route_class=DishkaRoute,
)
# каждый endpoint может уточнить более узкое permission через RequirePermission("catalog:manage")
```

**Architecture fitness test** (`tests/architecture/test_router_audience.py`) проверяет:
1. Файл `router_admin*.py` ⇒ APIRouter prefix начинается с `/admin/`.
2. Endpoint в `/admin/*` ⇒ есть dependency на `RequireStaffRole` (или permission `*:manage`).
3. Endpoint вне `/admin/*` НЕ использует `RequireStaffRole`.

Полный список «было → стало» по URL и план рефакторинга — `docs/api/router-restructure-2026-05.md`.

Dishka providers always live in `infrastructure/provider.py` — providers wire infrastructure implementations to domain interfaces, which is an infrastructure-layer concern. `presentation/dependencies.py`, when present, is reserved for FastAPI dependencies (e.g. `Auth`, `RequirePermission` in `identity/presentation/dependencies.py`).

### Layer rules (enforced by `tests/architecture/test_boundaries.py`)

- Domain MUST NOT import application/infrastructure/presentation or any framework (attrs + stdlib only)
- Application commands MUST NOT import infrastructure. Exempt by rule: `*.application.queries.*` (CQRS read-side reads ORM directly), `*.application.consumers.*` (event consumers wire infrastructure), `geo.application.commands.*` (reference-data module without domain entities/UoW/events). Commands may compose queries (read-your-writes)
- Modules MUST NOT import each other's domain/application/infrastructure. Whitelisted exceptions in `ALLOWED_CROSS_MODULE`: presentation→identity for auth/permission deps (user, catalog, pricing, activity); `cart.infrastructure.adapters.catalog_adapter` (anti-corruption adapter reading catalog/supplier ORM to validate SKUs); `identity.management.*` (admin CLI bootstrap reaching into the full DI container)
- `src/shared/` is the shared kernel — MUST NOT import any module
- Architecture tests parametrize `MODULES = ["catalog", "identity", "user", "cart", "logistics", "pricing", "activity", "geo", "supplier", "favorites", "order", "payment", "recipient"]` — all 13 modules are enforced

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
- `UnitOfWork.commit()` serializes events to `outbox_messages` table atomically (via `dataclasses.asdict()` with recursive UUID/datetime serialization, also persists `correlation_id` from request context)
- Outbox Relay (`src/infrastructure/outbox/relay.py`) polls `outbox_messages` with `FOR UPDATE SKIP LOCKED`, processes each event in its own transaction, dispatches via `_EVENT_HANDLERS` registry, and prunes processed records older than 7 days. Multiple workers can run in parallel without blocking each other
- **Current handlers (in `src/infrastructure/outbox/tasks.py`):** 4 IAM dispatchers with real consumers (`identity_registered`, `identity_deactivated`, `role_assignment_changed`, `linked_account_created`); 18 logistics + 5 favorites handlers wired as structured-log-only (replace body with `.kicker().kiq(...)` to attach a real consumer). Catalog / cart / pricing / supplier events are persisted but have no subscribers — they are marked processed by the relay's "unknown event_type, skipping" branch. Add a handler via `register_event_handler(event_type, handler)`. Relay runs every minute (cron `* * * * *`, batch=100, timeout=55s); pruning runs daily at 03:00 UTC

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
- Seed data: `seed/` package with step-based runner (`uv run python -m seed.main`); steps: `roles`/`admin` (DB-only), `geo`/`brands`/`categories`/`attributes`/`products` (require running API). RBAC roles defined in `src/modules/identity/management/seed_data.py` (deterministic uuid5)

## Config

Pydantic Settings in `src/bootstrap/config.py`. Reads `.env` file. Key computed fields:
- `database_url` — builds `postgresql+asyncpg://` URL from `PG*` env vars
- `redis_url` — builds `redis://` URL from `REDIS*` env vars

Test settings override in `tests/conftest.py` via `TestOverridesProvider`.
