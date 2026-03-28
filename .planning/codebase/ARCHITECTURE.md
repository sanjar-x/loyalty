# Architecture

**Analysis Date:** 2026-03-28

## Pattern Overview

**Overall:** Modular Monolith with Clean/Hexagonal Architecture (Ports & Adapters), CQRS, and Transactional Outbox for async event-driven cross-module communication.

**Key Characteristics:**
- Three deployable services: Main Backend (FastAPI), Image Backend (FastAPI), Telegram Bot (Aiogram) -- all in one repo
- Two frontend apps: Customer-facing Telegram Mini App (Next.js) and Admin Panel (Next.js)
- Domain-Driven Design with bounded contexts as modules: `catalog`, `identity`, `user`, `geo`, `supplier`
- Strict architectural boundary enforcement via pytest-archon tests (`backend/tests/architecture/test_boundaries.py`)
- Dependency injection via Dishka (async DI container)
- CQRS: commands go through domain entities + repositories + UoW; queries hit ORM models directly for performance
- Transactional Outbox pattern for reliable cross-module event delivery via RabbitMQ + TaskIQ

## Layers

**Domain Layer:**
- Purpose: Core business logic, entities, value objects, domain events, exception definitions, repository port interfaces
- Location: `backend/src/modules/{module}/domain/`
- Contains: `entities.py`, `value_objects.py`, `events.py`, `exceptions.py`, `interfaces.py`, `constants.py`
- Depends on: `src/shared/interfaces/entities.py` (AggregateRoot, DomainEvent base classes) only. Zero framework imports enforced.
- Used by: Application layer (command handlers reference domain entities and interfaces)

**Application Layer:**
- Purpose: Use-case orchestration via Command Handlers and Query Handlers (CQRS)
- Location: `backend/src/modules/{module}/application/`
- Contains: `commands/` (one file per command handler), `queries/` (one file per query handler), `consumers/` (cross-module event handlers)
- Depends on: Domain interfaces (ports), `src/shared/interfaces/uow.py`, `src/shared/interfaces/logger.py`
- Used by: Presentation layer (routers invoke handlers via DI)
- Note: Query handlers intentionally import ORM models directly for read-side performance; consumers wire infrastructure for event processing -- both excluded from boundary rules

**Infrastructure Layer:**
- Purpose: Concrete implementations of domain ports (repositories, external clients, security, caching, database)
- Location: `backend/src/modules/{module}/infrastructure/` and `backend/src/infrastructure/`
- Contains: `repositories/`, `models.py` (SQLAlchemy ORM), `provider.py` (Dishka DI wiring), external API clients
- Depends on: Domain interfaces, SQLAlchemy, Redis, external SDKs
- Used by: DI container (wired in `presentation/dependencies.py` or `infrastructure/provider.py`)

**Presentation Layer:**
- Purpose: HTTP API routers, request/response schemas, DI provider registration
- Location: `backend/src/modules/{module}/presentation/`
- Contains: `router_*.py` (FastAPI routers), `schemas.py` (Pydantic models), `dependencies.py` (Dishka Providers), `mappers.py`
- Depends on: Application layer handlers, Dishka, FastAPI
- Used by: `backend/src/api/router.py` (aggregates all module routers)

**Shared Kernel:**
- Purpose: Cross-cutting abstractions shared by all modules
- Location: `backend/src/shared/`
- Contains: `interfaces/` (IUnitOfWork, AggregateRoot, DomainEvent, IBase, ILogger, ICacheService, ITokenProvider, IPermissionResolver, AuthContext), `exceptions.py` (AppException hierarchy), `pagination.py`, `schemas.py`, `context.py` (request-scoped context vars)
- Depends on: Nothing module-specific. Enforced by architecture tests.
- Used by: All modules

**Bootstrap Layer:**
- Purpose: Application composition root -- wires together DI container, ASGI app, broker, scheduler
- Location: `backend/src/bootstrap/`
- Contains: `web.py` (FastAPI factory), `container.py` (Dishka container assembly), `broker.py` (TaskIQ/RabbitMQ), `worker.py` (TaskIQ worker entry), `scheduler.py` (TaskIQ Beat), `config.py` (Pydantic Settings), `logger.py` (structlog setup), `bot.py` (Telegram bot -- currently empty)
- Depends on: All layers (composition root)

**API Gateway Layer:**
- Purpose: Cross-cutting HTTP concerns (exception handlers, middleware, dependencies)
- Location: `backend/src/api/`
- Contains: `router.py` (root router aggregator), `exceptions/handlers.py` (global exception -> JSON mapping), `middlewares/` (access logging), `dependencies/`

## Data Flow

**HTTP Request (Command - Write Side):**

1. Client sends HTTP request to FastAPI endpoint
2. `AccessLoggerMiddleware` logs request, binds correlation ID via `structlog.contextvars`
3. FastAPI route handler receives request, `RequirePermission` dependency validates JWT + RBAC permissions via cache-aside Redis lookup
4. Route handler maps Pydantic request schema to a frozen `@dataclass` Command
5. Dishka injects the appropriate `CommandHandler` with its dependencies (repository, UoW, logger)
6. Handler opens `async with self._uow:` transactional context
7. Handler invokes domain entity factory/method, calls repository to persist, registers aggregate with UoW
8. `uow.commit()` extracts domain events from registered aggregates, writes them as `OutboxMessage` rows atomically with business data, then commits the SQLAlchemy session
9. Route handler maps result to Pydantic response schema

**HTTP Request (Query - Read Side):**

1. Same auth/middleware chain as commands
2. Route handler maps query params to a frozen `@dataclass` Query
3. Dishka injects `QueryHandler` with `AsyncSession` (no UoW, no repositories)
4. Handler builds SQLAlchemy `select()` against ORM models directly, uses `paginate()` helper
5. Results mapped to Pydantic read models and returned

**Async Event Processing (Outbox -> TaskIQ -> Consumer):**

1. TaskIQ Scheduler (Beat) triggers `outbox_relay_task` every minute (`backend/src/infrastructure/outbox/tasks.py`)
2. Relay fetches unprocessed `outbox_messages` with `SELECT FOR UPDATE SKIP LOCKED` (`backend/src/infrastructure/outbox/relay.py`)
3. For each event, relay looks up registered handler by `event_type` and dispatches via TaskIQ `.kiq()`
4. TaskIQ worker picks up the task from RabbitMQ queue
5. Consumer function (e.g. `backend/src/modules/user/application/consumers/identity_events.py`) executes with Dishka-injected dependencies
6. Failed tasks are persisted to `failed_tasks` table via `DLQMiddleware` (`backend/src/infrastructure/logging/dlq_middleware.py`)

**State Management (Frontend - Main):**
- Redux Toolkit with RTK Query (`frontend/main/lib/store/api.ts`)
- API proxy: Next.js catch-all route (`frontend/main/app/api/backend/[...path]/route.ts`) proxies all `/api/backend/*` requests to the Python backend, injecting access token from httpOnly cookies
- Auth tokens stored in httpOnly cookies, managed via Next.js API routes (`/api/auth/telegram`, `/api/auth/refresh`, `/api/auth/logout`)
- Automatic 401 -> refresh -> retry flow with mutex to prevent token stampede

**State Management (Frontend - Admin):**
- No client-side state library; server-side rendering with Next.js App Router
- Backend API client: `frontend/admin/src/lib/api-client.js` -- simple `fetch` wrapper calling `BACKEND_URL` directly
- API routes in `frontend/admin/src/app/api/` act as BFF (Backend for Frontend) proxy to Python backend
- Auth via httpOnly cookies with token refresh

## Key Abstractions

**AggregateRoot (Mixin):**
- Purpose: Base mixin for domain entities that collect domain events in-memory
- Location: `backend/src/shared/interfaces/entities.py`
- Pattern: `attrs.define` class inherits from `AggregateRoot`, calls `self.add_domain_event(...)`, UoW extracts events on commit
- Examples: `backend/src/modules/catalog/domain/entities.py` (Brand, Category, Product), `backend/src/modules/identity/domain/entities.py`

**DomainEvent (Dataclass):**
- Purpose: Immutable event record written to the Outbox table on commit
- Location: `backend/src/shared/interfaces/entities.py`
- Pattern: `@dataclass` with `aggregate_type` and `event_type` class-level defaults (enforced by `__init_subclass__`). Serialized via `dataclasses.asdict()`.
- Examples: `backend/src/modules/identity/domain/events.py`, `backend/src/modules/catalog/domain/events.py`

**IUnitOfWork:**
- Purpose: Transactional boundary that flushes domain events to Outbox atomically
- Interface: `backend/src/shared/interfaces/uow.py`
- Implementation: `backend/src/infrastructure/database/uow.py`
- Pattern: Context manager (`async with uow:`). Command handlers call `uow.register_aggregate(entity)` then `uow.commit()`.

**ICatalogRepository[T] (Generic Repository Port):**
- Purpose: Generic CRUD contract for catalog aggregates with type parameter
- Location: `backend/src/modules/catalog/domain/interfaces.py`
- Pattern: `class IBrandRepository(ICatalogRepository[DomainBrand])` with additional domain-specific methods
- Implementations: `backend/src/modules/catalog/infrastructure/repositories/` -- use `BaseRepository` Data Mapper pattern

**BaseRepository[EntityType, ModelType] (Data Mapper):**
- Purpose: Generic CRUD implementation mapping between domain entities and ORM models
- Location: `backend/src/modules/catalog/infrastructure/repositories/base.py`
- Pattern: Subclasses declare `model_class=OrmModel` in class args, implement `_to_domain()` and `_to_orm()` hooks

**Dishka DI Provider:**
- Purpose: Registers repository implementations and handler classes into the IoC container
- Pattern: Each module defines `Provider` subclasses in `presentation/dependencies.py` or `infrastructure/provider.py`. Providers use `CompositeDependencySource = provide(HandlerClass, scope=Scope.REQUEST)`. All assembled in `backend/src/bootstrap/container.py`.
- Example: `backend/src/modules/catalog/presentation/dependencies.py`

**RequirePermission (RBAC Guard):**
- Purpose: FastAPI dependency that enforces a permission codename on the session
- Location: `backend/src/modules/identity/presentation/dependencies.py`
- Pattern: `Depends(RequirePermission(codename="catalog:manage"))` on route declarations. Resolves permissions via cache-aside Redis + recursive CTE fallback.

**AppException Hierarchy:**
- Purpose: Typed exception tree mapping to HTTP status codes
- Location: `backend/src/shared/exceptions.py`
- Hierarchy: `AppException` -> `NotFoundError(404)`, `UnauthorizedError(401)`, `ForbiddenError(403)`, `ConflictError(409)`, `ValidationError(400)`, `UnprocessableEntityError(422)`
- Pattern: Caught by `backend/src/api/exceptions/handlers.py` and mapped to uniform JSON error envelope

## Entry Points

**FastAPI Web Server:**
- Location: `backend/src/bootstrap/web.py` -> `create_app()`
- Triggers: ASGI server (Uvicorn)
- Responsibilities: Assembles middleware, exception handlers, routers, DI container; exposes `/health` endpoint

**TaskIQ Worker:**
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker`
- Responsibilities: Processes async tasks from RabbitMQ (outbox relay events, cross-module consumers). Critical initialization order documented in module docstring.

**TaskIQ Scheduler (Beat):**
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler`
- Responsibilities: Periodically dispatches `outbox_relay_task` (every minute) and `outbox_pruning_task` (daily 03:00 UTC). Must run exactly one instance.

**Telegram Bot:**
- Location: `backend/src/bot/factory.py`
- Triggers: Bot webhook or polling
- Responsibilities: Aiogram-based Telegram bot with FSM, Redis-backed state storage, Dishka DI integration

**Image Backend:**
- Location: `image_backend/src/bootstrap/web.py`
- Triggers: ASGI server (Uvicorn), separate service on port 8001
- Responsibilities: Handles media upload, image processing, blob storage. Has its own DI container, database, and TaskIQ worker. Follows same Clean Architecture pattern as main backend.

**Frontend - Customer Mini App:**
- Location: `frontend/main/app/layout.tsx`
- Triggers: Next.js dev/build (`next dev`)
- Responsibilities: Telegram Mini App with TelegramProvider, Redux store, auth bootstrap. Proxies API requests through `/api/backend/[...path]` catch-all route.

**Frontend - Admin Panel:**
- Location: `frontend/admin/src/app/layout.jsx`
- Triggers: Next.js dev/build (`next dev --webpack`)
- Responsibilities: Admin dashboard for products, orders, users, settings. BFF API routes proxy to Python backend.

**Alembic Migrations:**
- Location: `backend/alembic/env.py`, `image_backend/alembic/env.py`
- Triggers: `alembic upgrade head`, `alembic revision --autogenerate`
- Responsibilities: Schema migrations for both databases. All ORM models imported in `backend/src/infrastructure/database/registry.py`.

**Seed Data:**
- Location: `backend/seed/` (attributes, brands, categories, geo, products)
- Triggers: Manual script execution
- Responsibilities: Populates reference data (countries, categories, attributes)

## Error Handling

**Strategy:** Exception hierarchy mapped to HTTP status codes via global exception handlers.

**Patterns:**
- Domain layer raises typed exceptions from `{module}/domain/exceptions.py` (e.g. `BrandSlugConflictError`, `InvalidStatusTransitionError`)
- Domain exceptions typically inherit from `src/shared/exceptions.py` hierarchy (`NotFoundError`, `ConflictError`, etc.)
- UoW catches `IntegrityError` and translates to `ConflictError` or `UnprocessableEntityError` based on sqlstate
- All exceptions caught by `backend/src/api/exceptions/handlers.py` and rendered as uniform JSON envelope: `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}`
- Unhandled exceptions logged with full traceback, returned as generic 500

## Cross-Cutting Concerns

**Logging:** structlog with bound context variables (request_id, identity_id, session_id). Configured in `backend/src/bootstrap/logger.py`. Access logging via `AccessLoggerMiddleware`. TaskIQ tasks logged via `LoggingTaskiqMiddleware`.

**Validation:** Pydantic v2 schemas at the presentation layer for HTTP request validation. Domain entities validate via factory methods and value objects (e.g. `SLUG_RE` regex, `validate_i18n_completeness()`). Architecture tests enforce domain purity.

**Authentication:** JWT access tokens (short-lived, 15 min) + refresh tokens (30 days). Telegram auth via `initData` validation. Token version check against DB on every request. Auth context extracted in `get_auth_context()` dependency.

**Authorization:** RBAC with recursive role hierarchy. Permissions resolved via `PermissionResolver` (cache-aside: Redis -> recursive CTE fallback). Applied as `Depends(RequirePermission(codename="..."))` on routes.

**Caching:** Redis for permission cache, Telegram bot FSM state. Cache-aside pattern with configurable TTL (default 300s for permissions).

**Correlation/Tracing:** Request ID generated in middleware, bound to structlog context vars, propagated to outbox events and TaskIQ task labels for end-to-end tracing.

---

*Architecture analysis: 2026-03-28*
