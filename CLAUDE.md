<!-- GSD:project-start source:PROJECT.md -->
## Project

**Product Creation Flow — Integration Fix**

Исправление интеграционных расхождений между backend, admin frontend и image_backend в Product Creation Flow. Аудит выявил 14 проблем (6 critical, 4 major, 4 minor), из-за которых сквозной flow создания товара от формы до публикации не работает. Основные блокеры: отсутствующие media proxy-маршруты, несовпадение i18n-полей, несовпадение request/response schemas между frontend и image_backend.

**Core Value:** Сквозной flow создания товара (form → draft → media upload → SKU → attributes → publish) должен работать end-to-end через admin panel без ошибок интеграции.

### Constraints

- **Architecture:** Admin BFF proxy → image_backend напрямую для media операций (не через main backend)
- **Backend contracts:** Не ломать существующие API-контракты — только расширять (добавлять поля, делать optional)
- **I18n convention:** Backend отдаёт `I18N` (uppercase N) — это факт, frontend адаптируется
- **Tech stack:** Существующий стек без изменений (FastAPI, Next.js, Pydantic)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 - Backend API (`backend/`) and Image microservice (`image_backend/`)
- TypeScript - Customer-facing Telegram Mini App frontend (`frontend/main/`)
- JavaScript (ES2017+) - Admin dashboard frontend (`frontend/admin/`), no TypeScript
- SQL - Alembic migration scripts (`backend/alembic/versions/`, `image_backend/alembic/versions/`)
- Shell (bash) - Entrypoint script (`backend/scripts/entrypoint.sh`)
## Runtime
- CPython 3.14 (pinned in `backend/.python-version` and `image_backend/.python-version`)
- Docker base image: `python:3.14-slim-trixie` (`backend/Dockerfile`, `image_backend/Dockerfile`)
- Node.js (version not pinned; no `.nvmrc` detected)
- Browser target: Telegram WebApp WebView (primary), desktop browsers (admin)
- `uv` (Python) - Both backend services
- `npm` (JavaScript/TypeScript) - Both frontends
## Frameworks
- FastAPI `>=0.115.0` - REST API for both backends (`backend/src/bootstrap/web.py`, `image_backend/src/bootstrap/web.py`)
- Next.js `^16.1.x` - Both frontend applications using App Router (`frontend/main/package.json`, `frontend/admin/package.json`)
- React `19.x` - UI rendering for both frontends
- Aiogram `>=3.26.0` - Telegram bot framework (`backend/src/bot/factory.py`)
- SQLAlchemy `>=2.1.0b1` (async mode) - ORM and query builder (`backend/pyproject.toml`)
- Alembic `>=1.18.4` - Database migrations (`backend/alembic.ini`, `image_backend/alembic.ini`)
- Dishka `>=1.9.1` - Async dependency injection container (`backend/src/bootstrap/container.py`)
- TaskIQ `>=0.12.1` + TaskIQ AioPika `>=0.6.0` - Background task queue via RabbitMQ (`backend/src/bootstrap/broker.py`)
- pytest `>=9.0.2` - Test runner (`backend/pyproject.toml`)
- pytest-asyncio `>=1.3.0` - Async test support (mode: `auto`)
- pytest-cov `>=7.0.0` - Coverage reporting
- pytest-archon `>=0.0.7` - Architecture fitness functions
- pytest-randomly `>=4.0.1` - Random test ordering
- pytest-timeout `>=2.4.0` - Test timeout enforcement
- polyfactory `>=3.3.0` - Test data factories
- testcontainers `>=4.14.1` - Docker-based integration tests (postgres, redis, rabbitmq, minio)
- respx `>=0.22.0` - httpx mock library
- hypothesis `>=6.151.9` - Property-based testing
- dirty-equals `>=0.11` - Flexible test assertions
- schemathesis `>=4.14.1` - OpenAPI schema-based fuzzing
- Locust `>=2.43.3` - Load/performance testing
- Ruff - Python linting and formatting (target: `py314`, line-length: 88, config in `backend/pyproject.toml`)
- mypy `>=1.19.1` - Static type checking (strict mode, pydantic plugin, config in `backend/pyproject.toml`)
- ESLint 9 - JavaScript/TypeScript linting (`eslint-config-next`)
- Prettier `^3.6.2` - Code formatting (admin only, with `prettier-plugin-tailwindcss`)
- Make - Build shortcuts (`backend/Makefile`)
## Key Dependencies
- `asyncpg >=0.31.0` - PostgreSQL async driver (the only DB driver)
- `pydantic-settings` - Environment-based configuration (`backend/src/bootstrap/config.py`, `image_backend/src/bootstrap/config.py`)
- `attrs >=25.4.0` - Domain model definitions (immutable value objects and entities)
- `pyjwt[crypto] >=2.12.0` - JWT access token creation/verification (`backend/src/infrastructure/security/jwt.py`)
- `pwdlib[argon2,bcrypt] >=0.3.0` - Password hashing with Argon2id primary, Bcrypt legacy fallback (`backend/src/infrastructure/security/password.py`)
- `structlog >=25.5.0` - Structured JSON logging throughout both backends (`backend/src/bootstrap/logger.py`)
- `redis[hiredis] >=7.3.0` - Cache, session storage, FSM state (with hiredis C extension)
- `httpx[http2] >=0.28.1` - Async HTTP client for service-to-service calls (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)
- `aiobotocore >=3.2.1` - S3-compatible object storage client (`image_backend/src/infrastructure/storage/factory.py`)
- `pillow >=11.0.0` - Image processing (resize, thumbnails, WebP conversion)
- `python-multipart >=0.0.22` - File upload handling
- `cachetools >=7.0.5` - In-memory TTL caches (backend only)
- `taskiq-aio-pika >=0.6.0` - RabbitMQ broker adapter for TaskIQ
- `@reduxjs/toolkit ^2.11.2` + `react-redux ^9.2.0` - State management with RTK Query for API calls (`frontend/main/lib/store/api.ts`)
- `leaflet ^1.9.4` + `leaflet.markercluster ^1.5.3` - Map rendering for pickup points
- `lucide-react 0.555.0` - Icon library
- `dayjs ^1.11.18` - Date/time formatting (`frontend/admin/src/lib/dayjs.js`)
- `clsx ^2.1.1` + `tailwind-merge ^3.4.0` - Conditional CSS class merging
- `@svgr/webpack ^8.1.0` - SVG-as-React-component imports (`frontend/admin/next.config.js`)
- Tailwind CSS `^4.1.12` - Utility-first CSS with `@tailwindcss/postcss` (`frontend/admin/package.json`)
## Configuration
- Configuration via Pydantic Settings (`backend/src/bootstrap/config.py`, `image_backend/src/bootstrap/config.py`)
- Loads from `.env` file and environment variables; validated at startup (fail-fast)
- Secrets use `SecretStr` type for safe handling
- Computed fields derive `database_url` and `redis_url` from individual env vars
- Three environments: `dev`, `test`, `prod` (controlled by `ENVIRONMENT` var)
- `SECRET_KEY` - HS256 JWT signing key (SecretStr)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT` - Redis connection (password optional)
- `RABBITMQ_PRIVATE_URL` - AMQP connection string
- `BOT_TOKEN` - Telegram bot token (SecretStr)
- `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY` - Service-to-service image calls
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL (separate DB)
- `REDISHOST`, `REDISPORT` - Redis
- `RABBITMQ_PRIVATE_URL` - RabbitMQ
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3 storage
- `INTERNAL_API_KEY` - Service auth key (SecretStr)
- `BACKEND_API_BASE_URL` - Server-side backend URL for BFF proxy
- `NEXT_PUBLIC_API_BASE_URL` - Client-side API base (defaults to `/api/backend`)
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData address suggestion/cleaning API
- `BROWSER_DEBUG_AUTH_ENABLED` - Debug auth bypass for local dev (optional)
- `COOKIE_DOMAIN` - Cookie domain for cross-subdomain auth (optional)
- `BACKEND_URL` - Server-side backend URL (`frontend/admin/src/lib/api-client.js`)
- `backend/pyproject.toml` - Python project, ruff, mypy, pytest configuration
- `backend/alembic.ini` - Migration config (date-based subdirectories)
- `image_backend/pyproject.toml` - Image backend Python project config
- `image_backend/alembic.ini` - Image backend migration config
- `frontend/main/tsconfig.json` - TypeScript strict mode, `@/*` path alias, ES2017 target
- `frontend/main/next.config.ts` - Minimal config, remote image patterns
- `frontend/admin/next.config.js` - Webpack customization, SVG loader, security headers, `@` path alias
- `frontend/admin/tailwind.config.js` - Custom `app-*` design tokens
## Platform Requirements
- Docker + Docker Compose - Infrastructure services (`backend/docker-compose.yml`, `image_backend/docker-compose.yml`)
- Python 3.14 with `uv` package manager
- Node.js with `npm`
- Make (optional, for `backend/Makefile` shortcuts)
- Railway (PaaS) - Both backends deployed via Dockerfile (`backend/railway.toml`, `image_backend/railway.toml`)
- Backend startup: `alembic upgrade head` then `uvicorn main:app --host 0.0.0.0 --port $PORT` (`backend/scripts/entrypoint.sh`)
- Image backend startup: `uvicorn main:app --host 0.0.0.0 --port 8001` (`image_backend/Dockerfile`)
- Frontend deployment target: Not explicitly configured (standard Next.js deployment)
- Web API process: FastAPI/ASGI via Uvicorn (`backend/src/bootstrap/web.py`)
- Background Worker: TaskIQ worker consuming RabbitMQ tasks (`backend/src/bootstrap/worker.py`)
- Scheduler (Beat): TaskIQ scheduler dispatching periodic tasks (`backend/src/bootstrap/scheduler.py`)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python source: `snake_case.py` everywhere -- `create_brand.py`, `router_brands.py`, `value_objects.py`
- One command per file, named after the action: `create_brand.py`, `update_category.py`, `delete_product.py`
- One query per file, named after the read: `list_brands.py`, `get_category.py`, `get_category_tree.py`
- Routers: prefixed with `router_`: `router_brands.py`, `router_categories.py`
- Domain layer files: `entities.py` (or `entities/` package), `value_objects.py`, `exceptions.py`, `interfaces.py`, `events.py`, `constants.py`
- ORM models: single `models.py` per module infrastructure layer
- Schemas: single `schemas.py` per module presentation layer
- Test files: `test_` prefix: `test_brand.py`, `test_brand_handlers.py`
- Test builders: `{entity}_builder.py` -- `brand_builder.py`, `product_builder.py`
- Test mothers: `{module}_mothers.py` -- `catalog_mothers.py`, `identity_mothers.py`
- Use `snake_case` for all functions and methods
- Async handlers: `async def handle(self, command: XCommand) -> XResult`
- Factory methods: `Entity.create(...)`, `Entity.create_root(...)`, `Entity.create_child(...)`
- Validators: prefixed with `_validate_`: `_validate_slug()`, `_validate_sort_order()`
- Private helper functions: leading underscore: `_validate_string_rules()`, `_check_nesting_depth()`
- Use `snake_case` for all variables
- Private attributes: prefixed with `_`: `self._brand_repo`, `self._uow`, `self._logger`
- Constants: `UPPER_SNAKE_CASE`: `MAX_CATEGORY_DEPTH`, `DEFAULT_CURRENCY`, `REQUIRED_LOCALES`
- ClassVar guarded fields: `_BRAND_GUARDED_FIELDS`, `_UPDATABLE_FIELDS`
- Domain entities: bare `PascalCase`: `Brand`, `Category`, `Product`, `SKU`
- Value objects: descriptive `PascalCase`: `Money`, `BehaviorFlags`, `ProductStatus`
- Exceptions: suffixed with `Error`: `BrandNotFoundError`, `CategoryMaxDepthError`
- Repository interfaces: prefixed with `I`: `IBrandRepository`, `ICategoryRepository`
- Generic base: `ICatalogRepository[T]`
- Commands: suffixed with `Command`: `CreateBrandCommand`, `UpdateCategoryCommand`
- Handlers: suffixed with `Handler`: `CreateBrandHandler`, `ListBrandsHandler`
- Results: suffixed with `Result`: `CreateBrandResult`, `UpdateBrandResult`
- Events: suffixed with `Event`: `BrandCreatedEvent`, `ProductStatusChangedEvent`
- Read models: suffixed with `ReadModel`: `BrandReadModel`, `BrandListReadModel`
- Pydantic schemas: suffixed with `Request`/`Response`: `BrandCreateRequest`, `BrandResponse`
- ORM factories (tests): suffixed with `ModelFactory`: `BrandModelFactory`
- Object Mothers (tests): suffixed with `Mothers`: `IdentityMothers`, `CategoryMothers`
- Test builders (tests): suffixed with `Builder`: `BrandBuilder`, `ProductBuilder`
- Domain enums: `StrEnum` with lowercase string values: `ProductStatus.DRAFT = "draft"`
## Code Style
- Ruff as formatter and linter (replaces Black + isort + flake8)
- Line length: 88 characters
- Target Python version: 3.14
- Config in `backend/pyproject.toml`
- Ruff rule selection: `["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`
- Suppressed rules: `["E501", "RUF001", "RUF002", "RUF003", "B008", "UP042", "UP046"]`
- mypy with `disallow_untyped_defs = true` for production code
- `disallow_untyped_defs = false` for tests (relaxed)
- `pydantic.mypy` plugin enabled
- `warn_return_any = true`, `warn_unused_configs = true`
- Config in `backend/pyproject.toml` `[tool.mypy]`
## Import Organization
- No aliases. All imports use full paths from `src.` root:
- Tests import from `tests.` root:
- isort `known-first-party = ["src"]`
## Error Handling
- All expected errors inherit from `AppException` (`backend/src/shared/exceptions.py`)
- Base `AppException` carries: `message: str`, `status_code: int`, `error_code: str`, `details: dict`
- HTTP-mapped subclasses:
- Module-specific exceptions inherit from the appropriate HTTP base
- Naming: `{Entity}{Issue}Error` -- e.g., `BrandNotFoundError`, `CategoryMaxDepthError`
- Constructor always passes `message`, `error_code`, and `details` to super()
- `error_code` is `UPPER_SNAKE_CASE`: `"CATEGORY_NOT_FOUND"`, `"BRAND_SLUG_CONFLICT"`
- `details` contains relevant entity IDs as strings
- Location: `backend/src/modules/{module}/domain/exceptions.py`
- Centralized in `backend/src/api/exceptions/handlers.py`
- Uniform JSON envelope: `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}`
- `AppException` -> mapped to its `status_code`
- `RequestValidationError` -> 422 with per-field error details
- `StarletteHTTPException` -> wrapped in uniform envelope
- Unhandled `Exception` -> 500 with generic message, full traceback logged
- Domain entities validate in `create()` factory methods and `update()` methods
- Raise `ValueError` for invariant violations (caught by global handler as 422/500)
- Raise specific domain exceptions for business rule violations
- Use `__setattr__` guard pattern (DDD-01) to prevent direct mutation of guarded fields:
## Logging
- Bind handler name at construction: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Log after successful operations: `self._logger.info("Brand created", brand_id=str(brand.id))`
- Use structured key-value pairs, not string interpolation
- Log levels: `info` for success, `warning` for client errors (4xx), `error` for server errors (5xx)
- ILogger protocol at `backend/src/shared/interfaces/logger.py`
## Comments
- Module-level docstrings on every Python file explaining purpose and layer placement
- Class-level docstrings with Attributes section listing all fields
- Method-level docstrings with Args/Returns/Raises sections (Google style)
- Inline comments for DDD pattern markers: `# DDD-01: guard slug against direct mutation`
- Architecture decision markers: `# ARCH-03: Domain enums moved from infrastructure`
- Quality markers: `# QUAL-01: BehaviorFlags value object`
## Function Design
- One public method: `async def handle(self, command: XCommand) -> XResult`
- Dependencies injected via `__init__` and stored as `_private_attrs`
- Return a frozen dataclass result (not the entity itself)
- Wrap mutations in `async with self._uow:` context manager
- Call `self._uow.register_aggregate(entity)` before commit
- Log after successful operations (outside the UoW context)
- One public method: `async def handle(self, query: XQuery) -> ReadModel`
- Inject `AsyncSession` directly (CQRS read side skips UoW/repositories)
- Return Pydantic read models, not domain entities
- `@classmethod def create(cls, *, keyword_only_args) -> Self`
- Validate all invariants before constructing
- Generate UUIDs internally (uuid7 preferred, uuid4 fallback)
- `_UPDATABLE_FIELDS: ClassVar[frozenset[str]]` whitelist on entities
- `update(**kwargs)` rejects unknown fields via `TypeError`
- Uses `...` (Ellipsis) sentinel for "keep current" on nullable fields
- Pattern for nullable with keep-current:
## Module Design
- No barrel `__init__.py` re-exports in production code (most `__init__.py` files are empty)
- Each file exports its own classes/functions directly
- Exception: `backend/src/modules/catalog/domain/entities/__init__.py` re-exports all entity classes from submodules
- Tests use `__init__.py` as empty markers for pytest discovery
- All schemas inherit from `CamelModel` (`backend/src/shared/schemas.py`)
- `CamelModel` auto-converts `snake_case` Python fields to `camelCase` JSON
- Request schemas: `BrandCreateRequest`, `BrandUpdateRequest`
- Response schemas: `BrandResponse`, `BrandListResponse`
- Generic pagination: `PaginatedResponse[S]`
- i18n fields validated with custom `I18nDict` annotated type
- JSON bomb protection with `BoundedJsonDict` (10 KB size, depth 4 limit)
- Each router file defines one `APIRouter` with prefix and tags
- Uses `DishkaRoute` for automatic DI injection
- `FromDishka[HandlerType]` for handler injection in endpoint params
- Permission checks via `Depends(RequirePermission(codename="catalog:manage"))`
- Mutating endpoints: POST (201), PATCH (200), DELETE (204)
- Read endpoints: GET (200) with `Cache-Control: no-store` header
- Dishka as the DI framework
- Each module has a `dependencies.py` (presentation layer) or `provider.py` (infrastructure layer) with Dishka Provider classes
- Scopes: `APP` for singletons (engine, redis), `REQUEST` for per-request (session, handlers)
## Domain Enums
- Use `StrEnum` for all domain enums (enables string-based DB mapping without translation)
- Values are lowercase strings: `ProductStatus.DRAFT = "draft"`, `AttributeDataType.STRING = "string"`
- Location: `backend/src/modules/catalog/domain/value_objects.py`
## Value Objects
- Use `@frozen` from `attrs` for immutable value objects: `Money`, `BehaviorFlags`
- Validation in `__attrs_post_init__()` (read-only; no assignment)
- Comparison operators defined manually when ordering matters (e.g., `Money.__lt__`)
- Currency mismatch raises `ValueError` on comparison
## i18n Conventions
- Required locales: `{"ru", "en"}` -- enforced at both domain and schema level
- i18n fields are `dict[str, str]` with ISO 639-1 two-letter lowercase keys
- Domain validation: `validate_i18n_completeness()` in `backend/src/modules/catalog/domain/value_objects.py`
- Schema validation: `I18nDict` annotated type in `backend/src/modules/catalog/presentation/schemas.py`
- Max 20 language entries, max 10,000 chars per value
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Bounded contexts as self-contained modules under `backend/src/modules/` with strict 4-layer structure (presentation, application, domain, infrastructure)
- Strict Dependency Inversion: application layer depends on abstract interfaces (ports); infrastructure provides concrete implementations (adapters)
- CQRS split: Commands flow through domain entities + UnitOfWork + repositories; Queries bypass domain and read directly from ORM via `AsyncSession`
- Transactional Outbox pattern: domain events are persisted atomically with business data in the same DB transaction, then relayed asynchronously via TaskIQ workers
- Dishka IoC container as the single composition root for all dependency injection
- Three separate deployable processes sharing the same codebase: Web API (FastAPI/ASGI), Background Worker (TaskIQ), Scheduler (TaskIQ Beat)
- A separate Image Backend microservice mirrors the same architectural patterns
## Layers
- Purpose: HTTP request/response handling, input validation via Pydantic schemas, route-level authorization
- Location: `backend/src/modules/{module}/presentation/`
- Contains: FastAPI routers (`router_*.py`), Pydantic request/response schemas (`schemas.py`), Dishka DI providers (`dependencies.py`), DTO mappers (`mappers.py`), update helpers (`update_helpers.py`)
- Depends on: Application layer (command/query handlers), Shared schemas (`src/shared/schemas.py`)
- Used by: FastAPI framework (registered in `backend/src/api/router.py`)
- Pattern: Each router file defines one `APIRouter` with prefix and tags, uses `DishkaRoute` for automatic DI injection, `FromDishka[HandlerType]` for handler injection in endpoint params
- Auth: `Depends(RequirePermission(codename="catalog:manage"))` for permission checks
- Purpose: Orchestrate business use cases; enforce application-level rules
- Location: `backend/src/modules/{module}/application/`
- Contains:
- Depends on: Domain layer (entities, interfaces, exceptions), Shared kernel (`IUnitOfWork`, `ILogger`)
- Used by: Presentation layer via Dishka DI injection
- Pattern: Each command/query is a frozen `@dataclass`; each handler is a class with an `async def handle()` method; constructor injection of repositories and UoW
- Purpose: Core business logic, entities, value objects, domain events, repository interfaces (ports)
- Location: `backend/src/modules/{module}/domain/`
- Contains:
- Depends on: Shared kernel only (`src/shared/interfaces/entities.py`)
- Used by: Application layer, Infrastructure layer (for interface implementation)
- Rule: Zero infrastructure imports. Domain is pure business logic.
- Purpose: Concrete implementations of domain interfaces (repositories, external clients)
- Location: `backend/src/modules/{module}/infrastructure/`
- Contains:
- Depends on: Domain interfaces, SQLAlchemy, external SDKs
- Used by: DI container (wired via Dishka providers)
- Pattern: Data Mapper via `BaseRepository` that converts between ORM models and domain entities
- Purpose: Cross-cutting abstractions shared by all modules
- Location: `backend/src/shared/`
- Contains:
- Used by: All layers across all modules
- Purpose: Application wiring, configuration, process entry points
- Location: `backend/src/bootstrap/`
- Contains:
- Rule: Only this layer wires concrete implementations to interfaces.
- Purpose: Shared HTTP middleware, exception handlers, auth dependencies
- Location: `backend/src/api/`
- Contains:
## Data Flow
- Server-side: PostgreSQL (ACID) as single source of truth; Redis for caching (permissions, storefront attributes, category tree)
- Client-side (main frontend): Redux Toolkit + RTK Query with automatic token refresh
- Client-side (admin frontend): Server-state via Next.js API routes, no global state manager
## Key Abstractions
- Purpose: Base for domain entities that emit events; events are collected in-memory and flushed to Outbox on commit
- Examples: `backend/src/shared/interfaces/entities.py`
- Concrete entities: `backend/src/modules/catalog/domain/entities/brand.py`, `backend/src/modules/catalog/domain/entities/product.py`, `backend/src/modules/catalog/domain/entities/category.py`
- Pattern: `AggregateRoot` mixin with `add_domain_event()` / `clear_domain_events()` / `domain_events` property; entities use `attrs @dataclass` decorator
- Purpose: Transactional boundary that coordinates commit, rollback, and domain event persistence
- Interface: `backend/src/shared/interfaces/uow.py`
- Implementation: `backend/src/infrastructure/database/uow.py`
- Pattern: Async context manager (`async with uow:`); aggregates are registered for event extraction on commit; catches `IntegrityError` and maps to domain exceptions
- Purpose: Generic CRUD port for catalog aggregates (add, get, update, delete)
- Interface: `backend/src/modules/catalog/domain/interfaces.py`
- Pattern: Generic ABC with type parameter; module-specific repos extend with additional query methods (e.g., `check_slug_exists`, `get_for_update`, `has_products`)
- Purpose: Data Mapper base that converts between ORM models and domain entities
- Implementation: `backend/src/modules/catalog/infrastructure/repositories/base.py`
- Pattern: Subclasses declare `model_class` via class argument, implement `_to_domain()` and `_to_orm()` hooks; provides generic `add`, `get`, `update`, `delete`, `get_for_update`, `_field_exists` methods
- Purpose: Single-responsibility use case orchestrators
- Command examples: `backend/src/modules/catalog/application/commands/create_brand.py`, `backend/src/modules/catalog/application/commands/create_product.py`
- Query examples: `backend/src/modules/catalog/application/queries/list_brands.py`, `backend/src/modules/catalog/application/queries/storefront.py`
- Pattern: Frozen `@dataclass` for input (Command/Query), handler class with `async def handle()` method; constructor injection of repos, UoW, logger via Dishka
- Purpose: DI registration mapping interfaces to implementations at specific scopes
- Examples: `backend/src/modules/catalog/presentation/dependencies.py`, `backend/src/infrastructure/database/provider.py`, `backend/src/bootstrap/container.py`
- Pattern: One or more `Provider` classes per module; `provide(ConcreteClass, scope=Scope.REQUEST, provides=IInterface)`; scopes: APP (singletons), REQUEST (per-request)
- Purpose: Declarative route-level RBAC authorization
- Location: `backend/src/modules/identity/presentation/dependencies.py`
- Pattern: Callable class used as FastAPI dependency; resolves permissions via cache-aside with Redis + PostgreSQL recursive CTE fallback; permission codenames follow `module:action` pattern (e.g., `catalog:manage`, `catalog:read`)
- Purpose: Base Pydantic schema with automatic snake_case-to-camelCase aliasing
- Location: `backend/src/shared/schemas.py`
- Pattern: All presentation-layer request/response schemas inherit from `CamelModel`
## Entry Points
- Location: `backend/main.py` -> `backend/src/bootstrap/web.py`
- Triggers: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Responsibilities: Creates FastAPI app via `create_app()`, wires CORS middleware, access logging middleware, exception handlers, API router (all modules under `/api/v1`), health check endpoint, Dishka DI container, TaskIQ broker startup/shutdown in lifespan
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker`
- Responsibilities: Initializes DI container, registers DLQ middleware (persists failed tasks to DB), imports task modules (outbox relay, role events consumer, identity events consumer), processes queued tasks from RabbitMQ
- Critical ordering: DI setup must happen before task imports (tasks register via `@broker.task()` decorator at import time)
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler`
- Responsibilities: Dispatches `outbox_relay_task` every minute, `outbox_pruning_task` daily at 03:00 UTC
- Constraint: Exactly one instance must run to avoid duplicate dispatches
- Location: `image_backend/main.py` -> `image_backend/src/bootstrap/web.py`
- Triggers: `uvicorn main:app --host 0.0.0.0 --port 8001`
- Responsibilities: Image upload, processing (resize/crop/WebP conversion), S3-compatible storage, SSE for processing status
- Location: `backend/src/bot/factory.py`
- Triggers: Webhook or long-polling via aiogram Dispatcher
- Responsibilities: User-facing Telegram bot with FSM, inline keyboards, throttling
## Error Handling
- `AppException` (base, `backend/src/shared/exceptions.py`) -> status_code, error_code, message, details
- Domain modules define their own exceptions inheriting from the appropriate base (e.g., `BrandHasProductsError`, `InvalidStatusTransitionError`, `CategoryMaxDepthError` in `backend/src/modules/catalog/domain/exceptions.py`)
- `IntegrityError` with sqlstate `23503` (FK violation) -> `UnprocessableEntityError`
- Other `IntegrityError` -> `ConflictError`
- Entity factory methods (`create()`, `create_root()`, `create_child()`) validate invariants (slug format, i18n completeness, max depth) and raise `ValueError` or domain-specific exceptions
- `__setattr__` guard pattern (DDD-01) prevents direct mutation of guarded fields (e.g., `slug`, `status`)
```json
```
## Cross-Cutting Concerns
- structlog with contextvars for request-scoped fields (request_id, correlation_id, ip, method, path, identity_id, session_id)
- `ILogger` protocol (`backend/src/shared/interfaces/logger.py`) injected via Dishka
- Access logging middleware (`backend/src/api/middlewares/logger.py`) emits one structured log per HTTP request with timing
- Handlers bind their own name: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Log levels: `info` for success, `warning` for 4xx, `error` for 5xx
- Input: Pydantic schemas in presentation layer with automatic camelCase aliasing via `CamelModel`
- Domain: Entity factory methods and `update()` methods validate business rules
- Database: Constraint-level validation (unique indexes, FK constraints) caught by UoW and re-raised as domain exceptions
- i18n fields: Must include `ru` and `en` locales (enforced by `validate_i18n_completeness()`)
- JWT Bearer tokens with `sub` (identity_id), `sid` (session_id), `tv` (token_version) claims
- `get_auth_context()` dependency in `backend/src/modules/identity/presentation/dependencies.py`
- Token version validation against database per request (`tv` claim vs `identity.token_version`)
- Telegram authentication via `initData` validation (`backend/src/infrastructure/security/telegram.py`)
- `RequirePermission` callable dependency checks session permissions
- Cache-aside pattern: Redis cache with TTL -> PostgreSQL recursive CTE fallback
- Permission codenames: `module:action` (e.g., `catalog:manage`, `catalog:read`)
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing
- Response headers include `X-Process-Time-Ms` and `X-Request-ID`
- Redis for: permission resolution, storefront attribute queries, category tree
- Cache keys defined in `backend/src/modules/catalog/application/constants.py`
- Pattern: cache-aside (check cache -> miss -> query DB -> populate cache)
- TTL: 1 hour for storefront caches, 300s for permissions
## Bounded Contexts (Modules)
- Location: `backend/src/modules/catalog/`
- Entities: Brand, Category, Product (aggregate root with ProductVariant + SKU children), Attribute, AttributeGroup, AttributeValue, AttributeTemplate, TemplateAttributeBinding, MediaAsset, ProductAttributeValue
- Commands: 48 command handlers covering full CRUD + bulk operations + status FSM + SKU matrix generation
- Queries: 25 query handlers including storefront-specific queries (filterable, card, comparison, form attributes)
- EAV pattern: Products have dynamic attributes via ProductAttributeValue join table; categories define attribute templates
- Routers: 11 router files (`router_brands.py`, `router_categories.py`, `router_products.py`, `router_variants.py`, `router_skus.py`, `router_attributes.py`, `router_attribute_values.py`, `router_attribute_templates.py`, `router_product_attributes.py`, `router_media.py`, `router_storefront.py`)
- Location: `backend/src/modules/identity/`
- Entities: Identity, Role, Permission, Session, LinkedAccount, LocalCredentials, StaffInvitation
- Handles: Authentication (JWT, Telegram), RBAC, staff management, customer management
- Routers: `router_auth.py`, `router_admin.py`, `router_staff.py`, `router_customers.py`, `router_account.py`, `router_invitation.py`
- Location: `backend/src/modules/user/`
- Entities: Customer, StaffMember (Profile)
- Handles: User profile CRUD, customer creation/anonymization
- Event consumers: Listens for identity events to auto-create profiles
- Location: `backend/src/modules/geo/`
- Contains: Country, Subdivision, Currency, Language reference data
- Read-only: Queries only, no commands (seed data)
- Location: `backend/src/modules/supplier/`
- Entities: Supplier
- Handles: Supplier CRUD for the marketplace
- Location: `image_backend/src/modules/storage/`
- Entities: StorageObject
- Handles: Image upload, processing (resize, WebP conversion), S3 storage
- Pattern: Same hexagonal architecture as main backend
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
