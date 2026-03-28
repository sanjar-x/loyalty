<!-- GSD:project-start source:PROJECT.md -->
## Project

**Loyality — EAV Catalog Hardening**

A hybrid e-commerce platform combining traditional online retail with cross-border marketplace aggregation (Poizon, Taobao, Pinduoduo, 1688). Customers buy from Chinese marketplaces and local/Russian suppliers in one unified storefront, with orders delivered to local pickup points (PVZ) via dropshipping logistics partners.

The backend is a DDD modular monolith (Python/FastAPI/SQLAlchemy/PostgreSQL) with hexagonal architecture. This milestone focuses exclusively on hardening the existing EAV Catalog module — analyzing it for correctness, achieving comprehensive test coverage, validating API contracts and data integrity, fixing discovered issues, and making the catalog production-ready as the foundation for the upcoming order system.

**Core Value:** The EAV Catalog module must be provably correct and thoroughly tested — it is the foundation for cart, checkout, and order management. Every SKU, price, variant, and attribute must be reliable before building on top of it.

### Constraints

- **Keep EAV pattern**: The Entity-Attribute-Value architecture for the catalog is a deliberate design choice — do not refactor away from it
- **Tech stack**: Python 3.14, FastAPI, SQLAlchemy 2.1 (async), PostgreSQL, Dishka DI
- **Architecture**: Must follow existing hexagonal/CQRS patterns — commands through domain, queries direct to ORM
- **Testing**: Use existing test infrastructure (pytest, testcontainers, polyfactory)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 - Backend API (`backend/`) and Image microservice (`image_backend/`)
- TypeScript - Main customer-facing frontend (`frontend/main/`)
- JavaScript (ES2017+) - Admin dashboard frontend (`frontend/admin/`)
- SQL - Alembic migrations (`backend/alembic/`, `image_backend/alembic/`)
- Shell (bash) - Entrypoint scripts (`backend/scripts/entrypoint.sh`)
## Runtime
- CPython 3.14 (pinned in `backend/.python-version` and `image_backend/.python-version`)
- Docker base image: `python:3.14-slim-trixie`
- Node.js (version not pinned; no `.nvmrc` detected)
- Browser: Telegram WebApp WebView (primary), desktop browsers (admin)
- `uv` (Python) - Used for both backend services; lockfiles present (`backend/uv.lock`, `image_backend/uv.lock`)
- `npm` (JavaScript/TypeScript) - Used for both frontends; lockfiles present (`frontend/admin/package-lock.json`, `frontend/main/package-lock.json`)
## Frameworks
- FastAPI `>=0.115.0` - Backend REST API framework (`backend/src/bootstrap/web.py`, `image_backend/src/bootstrap/web.py`)
- Next.js `^16.1.x` - Both frontend applications (App Router)
- React `19.x` - UI rendering for both frontends
- Aiogram `>=3.26.0` - Telegram bot framework (`backend/src/bot/`)
- SQLAlchemy `>=2.1.0b1` (async mode) - ORM and query builder for both backends
- Alembic `>=1.18.4` - Database migrations for both backends
- asyncpg `>=0.31.0` - PostgreSQL async driver
- Dishka `>=1.9.1` - Async dependency injection container (`backend/src/bootstrap/container.py`)
- TaskIQ `>=0.12.1` - Task queue framework with RabbitMQ backend
- TaskIQ AioPika `>=0.6.0` - RabbitMQ broker adapter (`backend/src/bootstrap/broker.py`)
- pytest `>=9.0.2` - Test runner
- pytest-asyncio `>=1.3.0` - Async test support (mode: `auto`)
- pytest-cov `>=7.0.0` - Coverage reporting
- pytest-archon `>=0.0.7` - Architecture fitness functions (backend only)
- polyfactory `>=3.3.0` - Test data factories (backend only)
- testcontainers `>=4.14.1` - Docker-based integration tests (postgres, redis, rabbitmq, minio)
- Locust `>=2.43.3` - Load testing
- Ruff - Python linting and formatting (target: `py314`, line-length: 88)
- mypy `>=1.19.1` - Static type checking (strict, with pydantic plugin)
- ESLint 9 - JavaScript/TypeScript linting (next core-web-vitals config)
- Prettier `3.x` - Code formatting (admin only; with tailwindcss plugin)
## Key Dependencies
- `pydantic-settings` - Environment-based configuration (`backend/src/bootstrap/config.py`)
- `attrs >=25.4.0` - Domain model definitions (immutable value objects)
- `pyjwt[crypto] >=2.12.0` - JWT access token creation/verification (`backend/src/infrastructure/security/jwt.py`)
- `pwdlib[argon2,bcrypt] >=0.3.0` - Password hashing with Argon2id (`backend/src/infrastructure/security/password.py`)
- `structlog >=25.5.0` - Structured JSON logging throughout both backends
- `redis[hiredis] >=7.3.0` - Cache, session storage, FSM state (with hiredis C extension)
- `cachetools >=7.0.5` - In-memory TTL caches (backend only)
- `httpx[http2] >=0.28.1` - Async HTTP client for service-to-service calls (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)
- `aiobotocore >=3.2.1` - S3-compatible object storage client (`image_backend/src/infrastructure/storage/factory.py`)
- `pillow >=11.0.0` - Image processing (resize, thumbnails, WebP conversion)
- `python-multipart >=0.0.22` - File upload handling
- `@reduxjs/toolkit ^2.11.2` + `react-redux ^9.2.0` - State management with RTK Query for API calls (`frontend/main/lib/store/`)
- `leaflet ^1.9.4` + `leaflet.markercluster ^1.5.3` - Map rendering (pickup points, geo features)
- `lucide-react 0.555.0` - Icon library
- `dayjs ^1.11.18` - Date/time formatting (`frontend/admin/src/lib/dayjs.js`)
- `clsx ^2.1.1` + `tailwind-merge ^3.4.0` - Conditional CSS class merging
- `@svgr/webpack ^8.1.0` - SVG-as-React-component imports
- Tailwind CSS `^4.1.12` - Utility-first CSS (admin uses v4 with `@tailwindcss/postcss`)
- CSS Modules - Used for complex animations/page layouts in admin (`frontend/admin/src/app/admin/layout.module.css`)
- Global CSS imports - Main frontend uses `app/globals.css`
## Configuration
- Configuration via Pydantic Settings (`backend/src/bootstrap/config.py`, `image_backend/src/bootstrap/config.py`)
- Loads from `.env` file and environment variables
- Validated at startup; app fails fast on missing required vars
- Secrets use `SecretStr` type for safe handling
- Computed fields derive `database_url` and `redis_url` from individual env vars
- `ENVIRONMENT`: `dev | test | prod` (controls docs URL visibility, debug mode)
- `SECRET_KEY`: HS256 JWT signing key
- `API_V1_STR`: `/api/v1` (route prefix)
- Database: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- Redis: `REDISHOST`, `REDISPORT`, `REDISUSER`, `REDISPASSWORD`, `REDISDATABASE`
- RabbitMQ: `RABBITMQ_PRIVATE_URL` (AMQP connection string)
- Telegram: `BOT_TOKEN`, `BOT_ADMIN_IDS`, `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET`
- Service-to-service: `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY`
- S3: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL`
- Service auth: `INTERNAL_API_KEY` (API key for backend-to-image calls)
- Processing: `MAX_FILE_SIZE` (50MB), `SSE_TIMEOUT`, `PROCESSING_TIMEOUT`
- `BACKEND_URL` - Server-side backend URL (admin, via `frontend/admin/src/lib/api-client.js`)
- `NEXT_PUBLIC_API_BASE_URL` - Client-side API base (main, defaults to `/api/backend`)
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData address suggestions API (main)
- `BROWSER_DEBUG_AUTH_ENABLED` - Debug auth bypass for local dev (main)
- `BACKEND_API_BASE_URL` - Server-side backend URL for BFF proxy (main)
- `backend/pyproject.toml` - Python project definition, ruff/mypy config
- `backend/alembic.ini` - Migration config (date-based subdirectories, recursive versions)
- `frontend/admin/next.config.js` - Webpack customization, SVG loader, security headers, `@` path alias
- `frontend/main/next.config.ts` - Minimal config, remote image patterns
- `frontend/admin/tailwind.config.js` - Custom `app-*` design tokens, Inter font family
- `frontend/main/tsconfig.json` - Strict mode, `@/*` path alias, ES2017 target
## Platform Requirements
- Docker + Docker Compose - Infrastructure services (`backend/docker-compose.yml`, `image_backend/docker-compose.yml`)
- Python 3.14 with `uv` package manager
- Node.js with `npm`
- Make (optional, for `backend/Makefile` shortcuts)
- Railway (PaaS) - Both backends deployed via Dockerfile (`backend/railway.toml`, `image_backend/railway.toml`)
- Backend runs: `alembic upgrade head` then `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Image backend runs: `uvicorn main:app --host 0.0.0.0 --port 8001`
- Frontend deployment target: Not explicitly configured (standard Next.js deployment)
## Process Architecture
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Project Structure
- **backend/** -- Main API (Python, FastAPI, Clean Architecture + CQRS)
- **image_backend/** -- Image processing microservice (same stack, same conventions)
- **frontend/admin/** -- Admin panel (Next.js 16, React 19, JSX, no TypeScript)
- **frontend/main/** -- Customer-facing Telegram Mini App (Next.js 16, React 19, TypeScript)
## Naming Patterns
### Python (backend, image_backend)
- Use `snake_case.py` for all Python files
- Domain layer: `entities.py`, `value_objects.py`, `exceptions.py`, `interfaces.py`, `events.py`, `constants.py`
- Commands: one command per file, named after the action: `create_brand.py`, `update_category.py`, `delete_product.py`
- Queries: one query per file, named after the read: `list_brands.py`, `get_category.py`, `get_category_tree.py`
- Repositories: named after the aggregate: `brand.py`, `category.py`, `product.py`
- Routers: prefixed with `router_`: `router_brands.py`, `router_categories.py`, `router_storefront.py`
- ORM models: `models.py` (single file per module's infrastructure layer)
- Schemas: `schemas.py` (single file per module's presentation layer)
- Use `snake_case` for all functions and methods
- Async functions: `async def handle(...)`, `async def get(...)`, `async def add(...)`
- Validators: prefixed with `_validate_`: `_validate_slug()`, `_validate_sort_order()`
- Factory methods on entities: `Entity.create(...)`, `Entity.create_root(...)`, `Entity.create_child(...)`
- Use `snake_case` for all variables
- Private attributes: prefixed with `_`: `self._brand_repo`, `self._uow`, `self._logger`
- Constants: `UPPER_SNAKE_CASE`: `MAX_CATEGORY_DEPTH`, `GENERAL_GROUP_CODE`, `DEFAULT_CURRENCY`
- ClassVar guarded fields: `_PRODUCT_GUARDED_FIELDS`, `_UPDATABLE_FIELDS`
- Use `PascalCase` for all classes
- Domain entities: bare names: `Brand`, `Category`, `Product`, `SKU`
- Value objects: descriptive names: `Money`, `BehaviorFlags`, `ProductStatus`
- Exceptions: suffixed with `Error`: `BrandNotFoundError`, `CategoryMaxDepthError`, `InvalidStatusTransitionError`
- Repository interfaces: prefixed with `I`: `IBrandRepository`, `ICategoryRepository`, `IProductRepository`
- Generic base: `ICatalogRepository[T]`
- Commands: suffixed with `Command`: `CreateBrandCommand`, `UpdateCategoryCommand`
- Handlers: suffixed with `Handler`: `CreateBrandHandler`, `ListBrandsHandler`
- Results: suffixed with `Result`: `CreateBrandResult`, `UpdateBrandResult`
- Events: suffixed with `Event`: `BrandCreatedEvent`, `ProductStatusChangedEvent`
- Read models: suffixed with `ReadModel`: `BrandReadModel`, `BrandListReadModel`
- Pydantic schemas: suffixed with `Request`/`Response`: `BrandCreateRequest`, `BrandResponse`
- ORM factories (tests): suffixed with `ModelFactory`: `BrandModelFactory`
- Object Mothers (tests): suffixed with `Mothers`: `IdentityMothers`, `CategoryMothers`
- Test builders (tests): suffixed with `Builder`: `RoleBuilder`, `SessionBuilder`, `CategoryBuilder`
- Use `StrEnum` for all domain enums (enables string-based DB mapping without translation)
- Values are lowercase strings: `ProductStatus.DRAFT = "draft"`, `AttributeDataType.STRING = "string"`
### JavaScript/TypeScript (frontend)
- React components: `PascalCase.jsx` -- `Modal.jsx`, `Badge.jsx`, `ProductRow.jsx`
- Non-component files: `camelCase.js` / `kebab-case.js` -- `api-client.js`, `dayjs.js`
- Next.js route files: `route.js`, `page.jsx`, `layout.jsx`, `loading.jsx`, `error.jsx`
- Hooks: `use` prefix: `useAuth.jsx`, `useBodyScrollLock.js`
- Frontend/main (TypeScript): `kebab-case.ts` -- `cookie-helpers.ts`, `brand-image.ts`
- React components: `PascalCase` -- `export function Modal({ open, onClose, ... })`
- Hooks: `camelCase` with `use` prefix -- `useAuth()`, `useBodyScrollLock()`
- Utility functions: `camelCase` -- `backendFetch()`, `formatPrice()`
- `camelCase` for local variables and props
- `UPPER_SNAKE_CASE` for constants: `BACKEND_URL`
## Code Style
- Ruff as formatter and linter (replaces Black + isort + flake8)
- Line length: 88 characters
- Target Python version: 3.14
- Config in `backend/pyproject.toml` and `image_backend/pyproject.toml`
- Ruff rules: `["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`
- Suppressed rules: `["E501", "RUF001", "RUF002", "RUF003", "B008", "UP042", "UP046"]` (long lines, unicode chars, `Depends()` in signatures, PEP 695 types)
- isort first-party: `["src"]`
- mypy with `disallow_untyped_defs = true` for production code
- `disallow_untyped_defs = false` for tests (relaxed)
- `pydantic.mypy` plugin enabled
- Config in `backend/pyproject.toml` `[tool.mypy]`
- Admin panel: Prettier with `prettier-plugin-tailwindcss`
- ESLint with `eslint-config-next`
## Import Organization
### Python
- No aliases. All imports use full paths from `src.` root: `from src.modules.catalog.domain.entities import Brand`
- Tests import from `tests.factories.*`: `from tests.factories.identity_mothers import IdentityMothers`
### JavaScript/TypeScript
- `'use client'` directive at top when needed
- React imports first
- Third-party libraries second
- Local imports (`@/`, `../`) last
## Error Handling
### Domain Exception Hierarchy
- Name: `{Entity}{Issue}Error` -- e.g., `BrandNotFoundError`, `CategoryMaxDepthError`
- Constructor: Always pass `message`, `error_code`, and `details` to super()
- `error_code`: `UPPER_SNAKE_CASE` string constant -- e.g., `"CATEGORY_NOT_FOUND"`, `"BRAND_SLUG_CONFLICT"`
- `details`: dict with relevant entity IDs as strings
### Global Exception Handler
### Domain Validation
- Domain entities validate in `create()` factory methods and `update()` methods
- Raise `ValueError` for invariant violations (caught by global handler as 422/500)
- Raise specific domain exceptions (e.g., `CategoryMaxDepthError`) for business rule violations
- Use `__setattr__` guard pattern (DDD-01) to prevent direct mutation of guarded fields:
### Command Handler Error Flow
## Logging
- Bind handler name at construction: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Log after successful operations: `self._logger.info("Brand created", brand_id=str(brand.id))`
- Use structured key-value pairs, not string interpolation
- Log levels: `info` for success, `warning` for client errors (4xx), `error` for server errors (5xx)
## Comments
- Module-level docstrings on every Python file explaining purpose and layer placement
- Class-level docstrings with Attributes section listing all fields
- Method-level docstrings with Args/Returns/Raises sections (Google style)
- Inline comments for DDD pattern markers: `# DDD-01: guard slug against direct mutation`
- Architecture decision markers: `# ARCH-03: Domain enums moved from infrastructure`
## Function Design
- One public method: `async def handle(self, command: XCommand) -> XResult`
- Dependencies injected via `__init__` and stored as `_private_attrs`
- Return a frozen dataclass result (not the entity itself)
- One public method: `async def handle(self, query: XQuery) -> ReadModel`
- Inject `AsyncSession` directly (CQRS read side skips UoW/repositories)
- Return Pydantic read models, not domain entities
- `@classmethod def create(cls, *, keyword_only_args) -> Self`
- Validate all invariants before constructing
- Generate UUIDs internally (uuid7 preferred, uuid4 fallback)
- `_UPDATABLE_FIELDS: ClassVar[frozenset[str]]` whitelist on entities
- `update(**kwargs)` rejects unknown fields via `TypeError`
- Uses `...` (Ellipsis) sentinel for "keep current" on nullable fields
## Module Design
- No barrel `__init__.py` re-exports in production code (most `__init__.py` files are empty)
- Each file exports its own classes/functions directly
- Tests use `__init__.py` as empty markers for pytest discovery
- All Pydantic schemas inherit from `CamelModel` (`backend/src/shared/schemas.py`)
- `CamelModel` auto-converts `snake_case` Python fields to `camelCase` JSON
- Request schemas: `BrandCreateRequest`, `BrandUpdateRequest`
- Response schemas: `BrandResponse`, `BrandListResponse`
- Generic pagination: `PaginatedResponse[S]`
- i18n fields validated with custom `I18nDict` annotated type
- Each router file defines one `APIRouter` with prefix and tags
- Uses `DishkaRoute` for automatic DI injection
- `FromDishka[HandlerType]` for handler injection in endpoint params
- Permission checks via `Depends(RequirePermission(codename="catalog:manage"))`
- Mutating endpoints: POST (201), PATCH (200), DELETE (204)
- Read endpoints: GET (200) with `Cache-Control: no-store` header
- Dishka as the DI framework
- Each module has a `dependencies.py` (presentation layer) or `provider.py` (infrastructure layer) with Dishka Provider classes
- Scopes: `APP` for singletons (engine, redis), `REQUEST` for per-request (session, handlers)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Each bounded context is a self-contained module under `backend/src/modules/` with domain, application, infrastructure, and presentation layers
- Strict Dependency Inversion: application layer depends on abstract interfaces (ports); infrastructure provides concrete implementations (adapters)
- CQRS: Commands use domain entities + UnitOfWork + repositories; Queries bypass the domain and read directly from ORM via AsyncSession
- Transactional Outbox pattern: domain events are persisted atomically with business data, then relayed asynchronously via TaskIQ background workers
- Dishka IoC container as the composition root for all dependency injection
- Three separate deployable processes: Web API (FastAPI/ASGI), Background Worker (TaskIQ), Scheduler (TaskIQ Beat)
## System Components
- FastAPI REST API serving the core business logic
- Modules: catalog, identity, user, geo, supplier
- Telegram Bot (aiogram) embedded in the same codebase
- Separate FastAPI microservice for image/media storage and processing
- Mirrors the same architectural patterns (modules, DI, UoW)
- Communicates with the main backend via server-to-server HTTP API
- Next.js 16 application (React 19, Tailwind CSS)
- Proxies API calls through Next.js API routes to the backend
- App Router with file-based routing
- Next.js 16 customer-facing storefront (React 19, Redux Toolkit)
- Telegram Mini App integration for authentication
- App Router with file-based routing
## Layers
- Purpose: HTTP request/response handling, input validation, authorization
- Location: `backend/src/modules/{module}/presentation/`
- Contains: FastAPI routers (`router_*.py`), Pydantic request/response schemas (`schemas.py`), Dishka DI providers (`dependencies.py`), DTO mappers (`mappers.py`)
- Depends on: Application layer (command/query handlers), Shared schemas
- Used by: FastAPI framework (registered in `backend/src/api/router.py`)
- Purpose: Orchestrates business use cases; enforces application-level rules
- Location: `backend/src/modules/{module}/application/`
- Contains: Command handlers (`commands/*.py`), Query handlers (`queries/*.py`), Read models (`queries/read_models.py`), Event consumers (`consumers/*.py`)
- Depends on: Domain layer (entities, interfaces, exceptions), Shared kernel (IUnitOfWork, ILogger)
- Used by: Presentation layer via DI injection
- Pattern: Each command/query is a frozen dataclass; each handler is a class with a `handle()` method
- Purpose: Core business logic, entities, value objects, domain events, repository interfaces
- Location: `backend/src/modules/{module}/domain/`
- Contains: Entities (`entities.py`), Value objects (`value_objects.py`), Domain events (`events.py`), Repository interfaces (`interfaces.py`), Domain exceptions (`exceptions.py`), Constants (`constants.py`)
- Depends on: Shared kernel only (`src/shared/interfaces/entities.py`)
- Used by: Application layer, Infrastructure layer (for interface implementation)
- Rule: Zero infrastructure imports. Domain is pure business logic.
- Purpose: Concrete implementations of domain interfaces (repositories, external clients)
- Location: `backend/src/modules/{module}/infrastructure/`
- Contains: SQLAlchemy ORM models (`models.py`), Repository implementations (`repositories/*.py`), External service clients (e.g., `image_backend_client.py`), DI providers (`provider.py`)
- Depends on: Domain interfaces, SQLAlchemy, external SDKs
- Used by: DI container (wired via Dishka providers)
- Purpose: Cross-cutting abstractions shared by all modules
- Location: `backend/src/shared/`
- Contains: Interface protocols (`interfaces/`), Base exception hierarchy (`exceptions.py`), Pagination helper (`pagination.py`), CamelCase schema base (`schemas.py`), Request context propagation (`context.py`)
- Used by: All layers across all modules
- Purpose: Application wiring, configuration, process entry points
- Location: `backend/src/bootstrap/`
- Contains: App factory (`web.py`), DI container assembly (`container.py`), Configuration (`config.py`), Message broker setup (`broker.py`), Worker entry point (`worker.py`), Scheduler entry point (`scheduler.py`), Bot factory (`bot.py`), Logging setup (`logger.py`)
- Rule: This is the composition root. Only this layer wires concrete implementations to interfaces.
- Purpose: Shared HTTP middleware, exception handlers, auth dependencies
- Location: `backend/src/api/`
- Contains: Root router aggregation (`router.py`), Exception handlers (`exceptions/handlers.py`), Auth dependency (`dependencies/auth.py`), Access logging middleware (`middlewares/logger.py`)
## Data Flow
- Server-side: PostgreSQL (ACID) as single source of truth; Redis for caching (permissions, FSM state)
- Client-side (admin frontend): Server-state via Next.js API routes proxying to backend
- Client-side (main frontend): Redux Toolkit for client state; Next.js API routes for server communication
## Key Abstractions
- Purpose: Base for domain entities that emit events; events are collected in-memory and flushed to Outbox on commit
- Examples: `backend/src/shared/interfaces/entities.py`, `backend/src/modules/catalog/domain/entities.py` (Product, Brand, Category)
- Pattern: Mixin with `add_domain_event()` / `clear_domain_events()` / `domain_events` property; attrs `@dataclass` decorator for entities
- Purpose: Transactional boundary that coordinates commit, rollback, and domain event persistence
- Examples: `backend/src/shared/interfaces/uow.py` (interface), `backend/src/infrastructure/database/uow.py` (implementation)
- Pattern: Async context manager (`async with uow:`); aggregates are registered for event extraction on commit
- Purpose: Generic CRUD port for catalog aggregates (add, get, update, delete)
- Examples: `backend/src/modules/catalog/domain/interfaces.py`
- Pattern: Generic ABC with type parameter; module-specific repos extend with additional query methods
- Purpose: Data Mapper base that converts between ORM models and domain entities
- Examples: `backend/src/modules/catalog/infrastructure/repositories/base.py`
- Pattern: Subclasses declare `model_class` via class argument, implement `_to_domain()` and `_to_orm()` hooks
- Purpose: Single-responsibility use case orchestrators
- Examples: `backend/src/modules/catalog/application/commands/create_product.py`, `backend/src/modules/catalog/application/queries/list_brands.py`
- Pattern: Frozen `@dataclass` for input, handler class with `handle()` method; constructor injection of repositories and UoW via Dishka
- Purpose: DI registration mapping interfaces to implementations at specific scopes
- Examples: `backend/src/modules/catalog/presentation/dependencies.py` (per-module providers), `backend/src/bootstrap/container.py` (composition root)
- Pattern: One or more `Provider` classes per module; `provide(ConcreteClass, scope=Scope.REQUEST, provides=IInterface)`
- Purpose: Declarative route-level authorization via session permission checking
- Examples: `backend/src/modules/identity/presentation/dependencies.py`
- Pattern: Callable class used as FastAPI dependency (`Depends(RequirePermission("catalog:manage"))`); resolves permissions via cache-aside with Redis + recursive CTE fallback
## Entry Points
- Location: `backend/main.py` -> `backend/src/bootstrap/web.py`
- Triggers: Uvicorn ASGI server
- Responsibilities: Creates FastAPI app, wires CORS/middleware/exception handlers/routers, sets up Dishka DI, manages lifespan (broker startup/shutdown)
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker` CLI command
- Responsibilities: Initializes DI container, registers DLQ middleware, imports task modules (consumers), processes queued tasks from RabbitMQ
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler` CLI command
- Responsibilities: Dispatches scheduled tasks (outbox relay every minute, outbox pruning daily at 03:00 UTC)
- Location: `image_backend/main.py` -> `image_backend/src/bootstrap/web.py`
- Triggers: Uvicorn ASGI server (separate process, port 8001)
- Responsibilities: Image upload, processing (resize/crop), storage management
- Location: `backend/src/bot/factory.py`
- Triggers: Webhook or long-polling via aiogram Dispatcher
- Responsibilities: User-facing Telegram bot with FSM, inline keyboards, throttling
## Error Handling
- All expected errors inherit from `AppException` (`backend/src/shared/exceptions.py`) with `status_code`, `error_code`, and `details`
- Subclasses: `NotFoundError` (404), `UnauthorizedError` (401), `ForbiddenError` (403), `ConflictError` (409), `ValidationError` (400), `UnprocessableEntityError` (422)
- Domain modules define their own exception subclasses (e.g., `BrandHasProductsError`, `InvalidStatusTransitionError`) that inherit from the appropriate base
- Centralized exception handlers in `backend/src/api/exceptions/handlers.py` convert all exceptions to a uniform JSON envelope: `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}`
- UnitOfWork catches `IntegrityError` from SQLAlchemy and re-raises as `ConflictError` or `UnprocessableEntityError` based on SQL state code
- Unhandled exceptions are caught by the catch-all handler, logged with full traceback, and returned as a generic 500 response
## Cross-Cutting Concerns
- structlog with contextvars for request-scoped fields (request_id, identity_id, session_id)
- `ILogger` interface (`backend/src/shared/interfaces/logger.py`) injected via Dishka
- Access logging middleware (`backend/src/api/middlewares/logger.py`)
- TaskIQ middleware for background task logging (`backend/src/infrastructure/logging/taskiq_middleware.py`)
- Input: Pydantic schemas in presentation layer with automatic camelCase aliasing via `CamelModel` (`backend/src/shared/schemas.py`)
- Domain: Entity factory methods and `update()` methods perform business rule validation (slug format, i18n completeness, status FSM transitions)
- Database: Constraint-level validation (unique indexes, FK constraints) caught by UoW and re-raised as domain exceptions
- JWT Bearer tokens with `sub` (identity_id) and `sid` (session_id) claims
- `get_auth_context()` dependency in `backend/src/modules/identity/presentation/dependencies.py`
- Token version validation against database (`tv` claim vs `identity.token_version`)
- Telegram authentication via `initData` validation (`backend/src/infrastructure/security/telegram.py`)
- RBAC with recursive role hierarchy
- `RequirePermission` callable dependency checks session permissions via cache-aside resolver
- Redis cache with configurable TTL (default 300s); PostgreSQL recursive CTE fallback
- Permission codenames follow `module:action` pattern (e.g., `catalog:manage`, `catalog:read`)
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing
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
