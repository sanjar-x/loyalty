# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
loyality/
├── backend/                    # Main Python backend (FastAPI)
│   ├── main.py                 # ASGI entry point
│   ├── pyproject.toml          # Python dependencies (uv)
│   ├── pytest.ini              # Test configuration
│   ├── alembic/                # Database migrations
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/2026/03/   # Migration scripts
│   ├── scripts/                # Dev utilities (entrypoint.sh, seed_dev.sql)
│   ├── seed/                   # Data seeding scripts
│   │   ├── __main__.py         # Seed entry point (python -m seed)
│   │   ├── main.py             # Seed orchestrator
│   │   ├── attributes/         # Attribute seeding
│   │   ├── brands/             # Brand seeding
│   │   ├── categories/         # Category seeding
│   │   ├── geo/                # Geo/currency seeding
│   │   └── products/           # Product seeding
│   ├── src/                    # Application source code
│   │   ├── api/                # Cross-cutting HTTP layer
│   │   │   ├── router.py       # Root router (aggregates all module routers)
│   │   │   ├── dependencies/   # Shared auth dependencies
│   │   │   ├── exceptions/     # Centralized exception handlers
│   │   │   └── middlewares/    # Access logging middleware
│   │   ├── bootstrap/          # App wiring & process entry points
│   │   │   ├── config.py       # Pydantic Settings (env vars)
│   │   │   ├── container.py    # Dishka DI composition root
│   │   │   ├── web.py          # FastAPI app factory
│   │   │   ├── worker.py       # TaskIQ worker entry point
│   │   │   ├── scheduler.py    # TaskIQ Beat scheduler entry point
│   │   │   ├── broker.py       # RabbitMQ broker configuration
│   │   │   ├── bot.py          # Telegram bot factory (empty stub)
│   │   │   └── logger.py       # structlog configuration
│   │   ├── bot/                # Telegram bot (aiogram)
│   │   │   ├── factory.py      # Bot & Dispatcher creation
│   │   │   ├── callbacks/      # Callback query handlers
│   │   │   ├── filters/        # Custom message filters
│   │   │   ├── handlers/       # Message/command handlers
│   │   │   ├── keyboards/      # Inline & reply keyboards
│   │   │   ├── middlewares/    # Bot middleware (throttling, logging, user identify)
│   │   │   └── states/         # FSM state groups
│   │   ├── infrastructure/     # Cross-cutting infra (shared across modules)
│   │   │   ├── cache/          # Redis cache service & DI provider
│   │   │   ├── database/       # SQLAlchemy engine, session, UoW, base model, registry
│   │   │   ├── logging/        # Logging adapters & TaskIQ middleware
│   │   │   ├── outbox/         # Transactional Outbox relay & scheduled tasks
│   │   │   └── security/       # JWT, password hashing, RBAC resolver, Telegram auth
│   │   ├── modules/            # Bounded context modules
│   │   │   ├── catalog/        # Product catalog (brands, categories, attributes, products, SKUs, media)
│   │   │   ├── geo/            # Geography (countries, currencies, languages, subdivisions)
│   │   │   ├── identity/       # IAM (authentication, sessions, roles, permissions, invitations)
│   │   │   ├── supplier/       # Supplier management
│   │   │   └── user/           # User profiles (customer, staff member)
│   │   └── shared/             # Shared kernel (interfaces, exceptions, pagination)
│   ├── tests/                  # Test suite
│   │   ├── architecture/       # Architectural boundary enforcement tests
│   │   ├── e2e/                # End-to-end API tests
│   │   ├── integration/        # Integration tests (DB-backed)
│   │   ├── factories/          # Test factories, builders, mothers
│   │   └── fakes/              # Fake implementations for testing
│   └── docs/                   # Backend documentation
│       ├── api/                # API flow docs
│       ├── research/           # Architecture research notes
│       └── reference/          # Reference documentation
├── image_backend/              # Image processing microservice (FastAPI)
│   ├── main.py                 # ASGI entry point
│   ├── pyproject.toml          # Dependencies
│   ├── alembic/                # Separate migrations
│   ├── src/                    # Same layered structure as backend
│   │   ├── api/                # HTTP layer
│   │   ├── bootstrap/          # App wiring
│   │   ├── infrastructure/     # Cache, DB, logging, blob storage
│   │   ├── modules/storage/    # Single "storage" bounded context
│   │   └── shared/             # Shared kernel
│   └── tests/                  # Tests
├── frontend/
│   ├── admin/                  # Admin dashboard (Next.js 16)
│   │   ├── src/app/            # App Router pages & API routes
│   │   ├── src/components/     # UI components (admin-specific + shadcn/ui)
│   │   ├── src/hooks/          # Custom React hooks
│   │   ├── src/lib/            # Utilities and helpers
│   │   ├── src/data/           # Static data
│   │   └── src/assets/         # Icons & static assets
│   └── main/                   # Customer storefront (Next.js 16)
│       ├── app/                # App Router pages & API routes
│       └── (similar structure)
├── .planning/                  # Project planning docs
├── .postman/                   # Postman collection
├── postman/                    # Postman environments
└── docs/                       # Project-level documentation
```

## Directory Purposes

**`backend/src/modules/{module}/`:**
- Purpose: Self-contained bounded context with all business logic
- Contains: Four sub-directories following hexagonal architecture
- Key pattern: Each module is independently developable; inter-module communication is via domain events (Outbox) or direct repository queries

**`backend/src/modules/{module}/domain/`:**
- Purpose: Pure business logic with zero infrastructure dependencies
- Contains: `entities.py` (attrs dataclasses with factory methods), `value_objects.py` (enums, frozen dataclasses), `events.py` (DomainEvent subclasses), `interfaces.py` (abstract repository contracts), `exceptions.py` (domain-specific errors), `constants.py`
- Key files:
  - `backend/src/modules/catalog/domain/entities.py`: Brand, Category, Product (aggregate roots), SKU, ProductVariant, Attribute, MediaAsset
  - `backend/src/modules/identity/domain/entities.py`: Identity, Role, Session, Permission

**`backend/src/modules/{module}/application/`:**
- Purpose: Use case orchestration (CQRS handlers)
- Contains: `commands/` (one file per write operation), `queries/` (one file per read operation), `queries/read_models.py` (Pydantic DTOs), `consumers/` (event-driven task handlers)
- Key pattern: Each command handler file contains: a frozen `Command` dataclass, an optional `Result` dataclass, and a `Handler` class

**`backend/src/modules/{module}/infrastructure/`:**
- Purpose: Concrete implementations of domain interfaces
- Contains: `models.py` (SQLAlchemy ORM models), `repositories/*.py` (repository implementations), `provider.py` (Dishka DI provider), external clients
- Key files:
  - `backend/src/modules/catalog/infrastructure/repositories/base.py`: Generic Data Mapper base class
  - `backend/src/modules/catalog/infrastructure/models.py`: All catalog ORM models

**`backend/src/modules/{module}/presentation/`:**
- Purpose: HTTP API surface (routers, schemas, DI wiring)
- Contains: `router_*.py` (FastAPI routers, one per entity/resource), `schemas.py` (Pydantic request/response schemas), `dependencies.py` (Dishka Provider classes), `mappers.py` (DTO mapping functions)
- Key pattern: Each router file handles CRUD for one resource type

**`backend/src/modules/{module}/management/`:**
- Purpose: Administrative/CLI scripts for one-time or infrequent operations
- Contains: Scripts like `create_admin.py`, `sync_system_roles.py`, `sync_suppliers.py`
- Exists in: `identity`, `supplier` modules

**`backend/src/infrastructure/`:**
- Purpose: Cross-cutting infrastructure shared by all modules
- Contains: Database engine/session/UoW (`database/`), Redis cache (`cache/`), Outbox relay (`outbox/`), Security (JWT, passwords, RBAC) (`security/`), Logging adapters (`logging/`)

**`backend/src/shared/`:**
- Purpose: Shared kernel -- interfaces and utilities used by all modules
- Contains:
  - `interfaces/entities.py`: `IBase` protocol, `DomainEvent` base, `AggregateRoot` mixin
  - `interfaces/uow.py`: `IUnitOfWork` abstract class
  - `interfaces/auth.py`: `AuthContext` dataclass
  - `interfaces/cache.py`: `ICacheService` protocol
  - `interfaces/security.py`: `ITokenProvider`, `IPermissionResolver` protocols
  - `interfaces/logger.py`: `ILogger` protocol
  - `exceptions.py`: `AppException` hierarchy (NotFound, Unauthorized, Forbidden, Conflict, Validation, UnprocessableEntity)
  - `pagination.py`: Generic `paginate()` helper for CQRS queries
  - `schemas.py`: `CamelModel` base with automatic snake_case -> camelCase aliasing
  - `context.py`: Request ID propagation via `ContextVar`

**`backend/src/api/`:**
- Purpose: Cross-cutting HTTP concerns (routing aggregation, middleware, exception handlers)
- Key files:
  - `router.py`: Aggregates all module routers under `/api/v1` prefix
  - `exceptions/handlers.py`: Uniform JSON error envelope for all exception types
  - `dependencies/auth.py`: Shared JWT extraction dependency
  - `middlewares/logger.py`: Access logging with request/response timing

**`backend/src/bootstrap/`:**
- Purpose: Composition root -- wires the entire application
- Key files:
  - `config.py`: `Settings` class (Pydantic Settings, loads from `.env`)
  - `container.py`: `create_container()` assembles all Dishka providers
  - `web.py`: `create_app()` FastAPI factory (CORS, middleware, routers, DI, health check)
  - `worker.py`: TaskIQ worker initialization (critical import order for Dishka + task registration)
  - `scheduler.py`: TaskIQ Beat scheduler with outbox relay/pruning schedules
  - `broker.py`: AioPikaBroker (RabbitMQ) configuration

## Key File Locations

**Entry Points:**
- `backend/main.py`: Web API ASGI entry point -> calls `create_app()`
- `backend/src/bootstrap/worker.py`: TaskIQ worker entry point
- `backend/src/bootstrap/scheduler.py`: TaskIQ Beat scheduler entry point
- `image_backend/main.py`: Image backend ASGI entry point

**Configuration:**
- `backend/src/bootstrap/config.py`: All environment variables and computed fields
- `backend/pyproject.toml`: Python dependencies (managed by uv)
- `backend/alembic.ini`: Alembic migration configuration
- `backend/pytest.ini`: Test configuration and markers

**Core Logic:**
- `backend/src/modules/catalog/domain/entities.py`: Product aggregate root with FSM, variants, SKUs
- `backend/src/modules/identity/domain/entities.py`: Identity/session/role domain model
- `backend/src/infrastructure/database/uow.py`: UnitOfWork with outbox event persistence
- `backend/src/infrastructure/outbox/relay.py`: Outbox polling publisher
- `backend/src/infrastructure/security/authorization.py`: RBAC permission resolver with Redis cache

**Testing:**
- `backend/tests/conftest.py`: Root test configuration
- `backend/tests/e2e/conftest.py`: E2E test fixtures (HTTP client, auth helpers)
- `backend/tests/factories/`: Test data factories and builders
- `backend/tests/architecture/test_boundaries.py`: Architectural boundary enforcement

**ORM Model Registry:**
- `backend/src/infrastructure/database/registry.py`: Imports all ORM models for Alembic auto-generation
- `backend/src/infrastructure/database/base.py`: Shared SQLAlchemy `Base` with naming conventions

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`
- Command handlers: `verb_noun.py` (e.g., `create_product.py`, `delete_brand.py`, `change_product_status.py`)
- Query handlers: `get_noun.py` or `list_nouns.py` (e.g., `get_brand.py`, `list_brands.py`)
- Routers: `router_{resource}.py` (e.g., `router_brands.py`, `router_products.py`) or `router.py` for single-resource modules
- ORM models: `models.py` (one file per module containing all ORM models for that module)

**Directories:**
- Modules: `snake_case` matching the bounded context name (e.g., `catalog`, `identity`, `user`, `geo`, `supplier`)
- Layer directories: `domain/`, `application/`, `infrastructure/`, `presentation/`
- Sub-layers: `commands/`, `queries/`, `repositories/`, `consumers/`

**Classes:**
- Domain entities: `PascalCase` (e.g., `Product`, `Brand`, `Category`)
- Command dataclasses: `{Verb}{Noun}Command` (e.g., `CreateProductCommand`, `UpdateBrandCommand`)
- Command result dataclasses: `{Verb}{Noun}Result` (e.g., `CreateProductResult`)
- Handler classes: `{Verb}{Noun}Handler` (e.g., `CreateProductHandler`, `ListBrandsHandler`)
- Repository interfaces: `I{Noun}Repository` (e.g., `IBrandRepository`, `IProductRepository`)
- Repository implementations: `{Noun}Repository` (e.g., `BrandRepository`, `ProductRepository`)
- DI providers: `{Noun}Provider` (e.g., `BrandProvider`, `CategoryProvider`, `DatabaseProvider`)
- ORM models: `PascalCase` matching the domain entity or suffixed with `Model` (e.g., `Brand`, `IdentityModel`, `SessionModel`)
- Read models: `{Noun}ReadModel` or `{Noun}ListReadModel` (e.g., `BrandReadModel`, `BrandListReadModel`)
- Pydantic schemas: `{Noun}{Action}Request` / `{Noun}{Action}Response` (e.g., `BrandCreateRequest`, `BrandResponse`)

**Enums and Constants:**
- Enum classes: `PascalCase` (e.g., `ProductStatus`, `AttributeDataType`, `MediaRole`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_CATEGORY_DEPTH`, `DEFAULT_CURRENCY`)

## Where to Add New Code

**New Bounded Context Module:**
1. Create `backend/src/modules/{module_name}/` with subdirectories: `domain/`, `application/`, `infrastructure/`, `presentation/`
2. Domain: Create `entities.py`, `interfaces.py`, `exceptions.py`, `events.py`, `value_objects.py`
3. Infrastructure: Create `models.py` (ORM), `repositories/` directory, `provider.py` (if independent DI)
4. Application: Create `commands/` and `queries/` directories with handlers
5. Presentation: Create `router.py`, `schemas.py`, `dependencies.py`
6. Register ORM models in `backend/src/infrastructure/database/registry.py`
7. Register DI providers in `backend/src/bootstrap/container.py`
8. Register router in `backend/src/api/router.py`
9. Create Alembic migration: `alembic revision --autogenerate -m "add {module} tables"`

**New Command (Write Operation):**
1. Create `backend/src/modules/{module}/application/commands/{verb}_{noun}.py`
2. Define frozen `{Verb}{Noun}Command` dataclass with input fields
3. Define `{Verb}{Noun}Result` dataclass (if needed)
4. Create `{Verb}{Noun}Handler` class with constructor-injected dependencies and `async def handle()` method
5. Register handler in the module's `presentation/dependencies.py` Dishka provider
6. Add router endpoint in `presentation/router_{resource}.py`

**New Query (Read Operation):**
1. Create `backend/src/modules/{module}/application/queries/{action}_{noun}.py`
2. Define frozen `{Action}{Noun}Query` dataclass with filter/pagination params
3. Add read model to `application/queries/read_models.py` (if new shape needed)
4. Create `{Action}{Noun}Handler` class injecting `AsyncSession` and `ILogger`
5. Use `paginate()` helper from `backend/src/shared/pagination.py` for list queries
6. Register handler in module's `presentation/dependencies.py`
7. Add router endpoint

**New Domain Entity:**
1. Add attrs `@dataclass` to `backend/src/modules/{module}/domain/entities.py`
2. Include `classmethod create()` factory method with validation
3. Add `update()` method with guarded fields pattern if needed
4. Define repository interface in `domain/interfaces.py`
5. Create SQLAlchemy ORM model in `infrastructure/models.py`
6. Create repository implementation in `infrastructure/repositories/`
7. Register ORM model in `backend/src/infrastructure/database/registry.py`

**New Domain Event:**
1. Add `@dataclass` subclass of `DomainEvent` to `backend/src/modules/{module}/domain/events.py`
2. Override `aggregate_type` and `event_type` with non-empty string defaults
3. Emit via `aggregate.add_domain_event(MyEvent(...))` in entity methods
4. Register handler in `backend/src/infrastructure/outbox/tasks.py` via `register_event_handler()`
5. Create consumer task in `backend/src/modules/{module}/application/consumers/`
6. Import consumer in `backend/src/bootstrap/worker.py`

**New Frontend Page (Admin):**
1. Create `frontend/admin/src/app/admin/{section}/page.tsx` for the page
2. Create `frontend/admin/src/app/api/{resource}/route.ts` for API proxy
3. Create components in `frontend/admin/src/components/admin/{section}/`

**New Migration:**
- Run: `cd backend && alembic revision --autogenerate -m "description"`
- Migrations live in: `backend/alembic/versions/YYYY/MM/`

## Special Directories

**`backend/src/infrastructure/outbox/`:**
- Purpose: Transactional Outbox pattern implementation (relay, pruning, event handler registry)
- Generated: No
- Committed: Yes

**`backend/alembic/versions/`:**
- Purpose: Database migration scripts (auto-generated + manual)
- Generated: Partially (via `--autogenerate`)
- Committed: Yes

**`backend/seed/`:**
- Purpose: Development/staging data seeding (categories, brands, attributes, products, geo data)
- Generated: No
- Committed: Yes

**`backend/tests/factories/`:**
- Purpose: Test data factories and object mothers for unit/integration tests
- Generated: No
- Committed: Yes
- Key files: `catalog_mothers.py` (domain entity factories), `orm_factories.py` (ORM model factories), `builders.py` (builder pattern for complex test scenarios)

**`backend/.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (via `uv sync`)
- Committed: No

**`frontend/admin/.next/`:**
- Purpose: Next.js build cache
- Generated: Yes
- Committed: No

**`frontend/admin/node_modules/`:**
- Purpose: NPM dependencies
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-03-28*
