# Architecture

**Analysis Date:** 2026-03-28

## Pattern Overview

**Overall:** Modular Monolith with Domain-Driven Design (DDD), CQRS, Hexagonal Architecture, and Transactional Outbox

**Key Characteristics:**
- Bounded contexts (modules) with strict layering: domain -> application -> infrastructure -> presentation
- CQRS: Command handlers mutate via repositories + UnitOfWork; query handlers read directly from ORM via AsyncSession
- Hexagonal Architecture: domain defines port interfaces; infrastructure provides adapters
- Transactional Outbox pattern: domain events are written atomically with business data, then relayed asynchronously via TaskIQ/RabbitMQ
- Dishka IoC container wires all dependencies; providers are composed in a single composition root
- Three deployable processes from one codebase: API server (FastAPI), background worker (TaskIQ), scheduler (TaskIQ Beat)
- Two separate backend services: main backend and image_backend (same architectural pattern, independent databases)
- Two Next.js frontends: customer-facing main app and admin panel, both acting as BFF proxies to the backend API

## Layers

**Domain Layer:**
- Purpose: Core business logic, entities, value objects, domain events, and repository port interfaces
- Location: `backend/src/modules/{module}/domain/`
- Contains: `entities.py` (attrs dataclasses extending `AggregateRoot`), `value_objects.py` (enums, frozen dataclasses), `events.py` (dataclass events extending `DomainEvent`), `exceptions.py` (domain-specific `AppException` subclasses), `interfaces.py` (abstract repository contracts)
- Depends on: Only `src/shared/interfaces/` (shared kernel). Zero infrastructure imports.
- Used by: Application layer command handlers

**Application Layer:**
- Purpose: Use-case orchestration via Command and Query handlers (CQRS)
- Location: `backend/src/modules/{module}/application/`
- Contains: `commands/` (one handler + command + result per file), `queries/` (one handler per file returning Pydantic read models), `consumers/` (event consumers for cross-module integration), `read_models.py` (Pydantic models for query responses)
- Depends on: Domain interfaces (ports), `IUnitOfWork`, `ILogger`, `ICacheService`
- Used by: Presentation layer (via Dishka DI injection)

**Infrastructure Layer:**
- Purpose: Concrete implementations of domain ports (repositories, cache, security, outbox)
- Location: `backend/src/modules/{module}/infrastructure/` and `backend/src/infrastructure/`
- Contains: `repositories/` (SQLAlchemy repo implementations), `models.py` (ORM models inheriting from shared `Base`), `provider.py` (Dishka providers)
- Depends on: SQLAlchemy, Redis, asyncpg, domain interfaces
- Used by: Dishka container wires these as implementations of port interfaces

**Presentation Layer:**
- Purpose: HTTP API (FastAPI routers) and Telegram bot handlers
- Location: `backend/src/modules/{module}/presentation/`
- Contains: `router_*.py` (FastAPI route files), `schemas.py` (Pydantic request/response schemas), `dependencies.py` (Dishka DI providers), `mappers.py` (ORM-to-response converters)
- Depends on: Application layer handlers via `FromDishka[HandlerType]`
- Used by: API consumers (frontends, external clients)

**Shared Kernel:**
- Purpose: Cross-cutting interfaces, base types, and utilities shared across all modules
- Location: `backend/src/shared/`
- Contains: `interfaces/entities.py` (`DomainEvent`, `AggregateRoot`), `interfaces/uow.py` (`IUnitOfWork`), `interfaces/cache.py` (`ICacheService`), `interfaces/auth.py` (`AuthContext`), `interfaces/security.py` (token/permission interfaces), `exceptions.py` (exception hierarchy), `pagination.py` (generic paginate helper), `context.py` (request-scoped context vars)

**Bootstrap Layer:**
- Purpose: Composition root -- wires all layers together for each process type
- Location: `backend/src/bootstrap/`
- Contains: `web.py` (FastAPI app factory), `worker.py` (TaskIQ worker entry), `scheduler.py` (TaskIQ Beat entry), `container.py` (Dishka IoC assembly), `config.py` (Pydantic Settings), `broker.py` (RabbitMQ broker), `logger.py` (structlog setup)
- Depends on: All infrastructure providers, all module providers
- Used by: `main.py`, ASGI server, TaskIQ CLI

## Data Flow

**HTTP Request (Command - Write Path):**

1. Client sends request to Next.js frontend
2. Next.js BFF proxy (`frontend/main/app/api/backend/[...path]/route.ts`) forwards with JWT from httpOnly cookie to backend
3. FastAPI middleware chain: `AccessLoggerMiddleware` -> CORS -> route handler
4. `RequirePermission` dependency validates JWT and checks RBAC permissions via `IPermissionResolver`
5. Router function receives Pydantic schema, constructs a `Command` dataclass
6. `FromDishka[CommandHandler]` injects handler with all dependencies (repo, UoW, logger)
7. Handler opens `async with self._uow:`, calls domain entity factory/method, persists via repository
8. Handler calls `uow.register_aggregate(entity)` and `await uow.commit()`
9. `UnitOfWork.commit()` extracts domain events, writes `OutboxMessage` rows atomically, then commits transaction
10. Handler returns `Result` dataclass; router maps to Pydantic response schema

**HTTP Request (Query - Read Path):**

1. Same proxy path through Next.js BFF
2. Query handler receives `AsyncSession` directly (no UoW, no domain entities)
3. Handler builds SQLAlchemy SELECT, optionally uses `paginate()` helper
4. Returns Pydantic `ReadModel` directly from ORM rows

**Async Event Processing (Outbox Relay):**

1. TaskIQ scheduler triggers `outbox_relay_task` every minute
2. `relay_outbox_batch()` polls `outbox_messages` table with `FOR UPDATE SKIP LOCKED`
3. Each event is dispatched to its registered handler via `_EVENT_HANDLERS` registry
4. Handlers (in `application/consumers/`) receive payload and execute cross-module side effects
5. Successfully processed events are marked with `processed_at` timestamp
6. Daily pruning task deletes events older than 7 days

**State Management (Frontend - Main):**
- Redux Toolkit with RTK Query (`@reduxjs/toolkit/query/react`)
- `lib/store/api.ts` configures `createApi` with auto-refresh on 401
- Auth state in `lib/store/authSlice.ts`
- JWT tokens stored in httpOnly cookies (set by Next.js API routes)

**State Management (Frontend - Admin):**
- Server-side data fetching via Next.js API routes
- Custom hooks (`useAuth`, `useProductForm`, `useProductFilters`)
- No Redux -- uses React state and custom hooks
- JWT tokens stored in httpOnly cookies (set by Next.js API routes)

## Key Abstractions

**AggregateRoot:**
- Purpose: Base mixin for all domain aggregates, provides in-memory domain event collection
- Examples: `backend/src/modules/catalog/domain/entities.py` (Brand, Category, Product), `backend/src/modules/identity/domain/entities.py`, `backend/src/modules/supplier/domain/entities.py`
- Pattern: attrs `@dataclass` + `AggregateRoot` mixin. Factory methods (`create()`, `create_root()`, `create_child()`). Guarded fields via `__setattr__` override. Domain events added via `add_domain_event()`.

**DomainEvent:**
- Purpose: Base class for all events written to the Outbox table
- Examples: `backend/src/modules/catalog/domain/events.py` (27 event types covering Brand, Category, Attribute, Product, Variant, SKU)
- Pattern: Dataclass with mandatory `aggregate_type` and `event_type` class-level defaults. Enforced via `__init_subclass__`. Serialized via `dataclasses.asdict()`.

**IUnitOfWork:**
- Purpose: Transactional boundary for write operations, integrates Outbox pattern
- Examples: `backend/src/shared/interfaces/uow.py` (port), `backend/src/infrastructure/database/uow.py` (adapter)
- Pattern: Context manager (`async with uow:`). Command handlers call `register_aggregate()` then `commit()`. Commit extracts events and writes OutboxMessage rows atomically.

**ICatalogRepository[T]:**
- Purpose: Generic CRUD repository contract with generic type parameter
- Examples: `backend/src/modules/catalog/domain/interfaces.py` (IBrandRepository, ICategoryRepository, IProductRepository, etc.)
- Pattern: Abstract base class with `add`, `get`, `update`, `delete`. Module-specific interfaces extend with domain-specific queries (e.g., `check_slug_exists`, `has_products`).

**Command/Query Handlers:**
- Purpose: Application-layer use cases following CQRS
- Examples: `backend/src/modules/catalog/application/commands/create_brand.py`, `backend/src/modules/catalog/application/queries/get_brand.py`
- Pattern: Command handlers depend on repository ports + IUnitOfWork. Query handlers depend on AsyncSession directly. Each handler is a class with a single `handle()` method. One command + result + handler per file.

**Dishka Providers:**
- Purpose: Wire dependencies for each bounded context
- Examples: `backend/src/modules/catalog/presentation/dependencies.py`, `backend/src/modules/identity/infrastructure/provider.py`
- Pattern: Each module exports one or more `Provider` subclasses. All are composed in `backend/src/bootstrap/container.py`. Scopes: `APP` for singletons (engine, sessionmaker), `REQUEST` for per-request (session, UoW, handlers).

## Entry Points

**Backend API Server:**
- Location: `backend/main.py`
- Triggers: `uvicorn main:app` (or Railway deployment)
- Responsibilities: Creates FastAPI app via `src/bootstrap/web.create_app()`. Connects TaskIQ broker on startup. Mounts all module routers under `/api/v1`.

**TaskIQ Background Worker:**
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker`
- Responsibilities: Processes async tasks dispatched via RabbitMQ. Creates its own DI container and DLQ middleware. Imports task modules for registration.

**TaskIQ Scheduler (Beat):**
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler`
- Responsibilities: Dispatches scheduled tasks (outbox relay every minute, outbox pruning daily at 03:00 UTC). Must run as a single instance.

**Image Backend API:**
- Location: `image_backend/main.py`
- Triggers: Separate FastAPI service for image processing and storage
- Responsibilities: Handles image upload, processing, and storage via MinIO (S3-compatible). Uses same DDD/CQRS pattern as main backend.

**Frontend - Customer App:**
- Location: `frontend/main/app/layout.tsx` (Next.js App Router)
- Triggers: `next dev` / `next start`
- Responsibilities: Customer-facing storefront. Proxies API calls to backend via `app/api/backend/[...path]/route.ts`. Uses Redux Toolkit + RTK Query for state management.

**Frontend - Admin Panel:**
- Location: `frontend/admin/src/app/layout.jsx` (Next.js App Router)
- Triggers: `next dev --webpack` / `next start`
- Responsibilities: Admin dashboard for product/order management. Proxies API calls to backend via `src/app/api/` route handlers. Uses vanilla React state + custom hooks.

**Health Check:**
- Location: Inline in `backend/src/bootstrap/web.py` (`/health` endpoint)
- Triggers: HTTP GET /health
- Responsibilities: Returns `{"status": "ok", "environment": "..."}` for load balancer health probes

## Error Handling

**Strategy:** Typed exception hierarchy mapped to HTTP status codes via global exception handlers

**Patterns:**
- All business errors inherit from `AppException` (`backend/src/shared/exceptions.py`) with `message`, `status_code`, `error_code`, and `details`
- Domain modules define specific exceptions (e.g., `BrandSlugConflictError`, `InvalidStatusTransitionError`) in their `domain/exceptions.py`
- Global exception handler in `backend/src/api/exceptions/handlers.py` catches `AppException`, `RequestValidationError`, and `StarletteHTTPException`, returning uniform JSON envelope: `{"error": {"code": ..., "message": ..., "details": ..., "request_id": ...}}`
- `UnitOfWork.commit()` catches `IntegrityError` and translates PostgreSQL sqlstate codes: `23503` (FK violation) -> `UnprocessableEntityError`, others -> `ConflictError`
- Domain entities raise `ValueError` for invariant violations; `AttributeError` for guarded field mutations

**Exception Hierarchy:**
- `AppException` (base, 500)
  - `NotFoundError` (404)
  - `UnauthorizedError` (401)
  - `ForbiddenError` (403)
  - `ConflictError` (409)
  - `ValidationError` (400)
  - `UnprocessableEntityError` (422)

## Cross-Cutting Concerns

**Logging:**
- structlog with JSON output (`backend/src/bootstrap/logger.py`)
- `AccessLoggerMiddleware` logs every HTTP request with timing and correlation ID
- All handlers receive `ILogger` via DI and bind handler name to context
- Context variables propagated via structlog's contextvars integration

**Validation:**
- Input: Pydantic schemas in presentation layer (`schemas.py`)
- Domain: Entity factory methods and `update()` methods validate invariants (slug format, i18n completeness, price constraints)
- Database: Constraint violations caught by UoW and translated to business errors

**Authentication:**
- JWT-based with access + refresh tokens (HS256)
- `get_auth_context()` dependency extracts `AuthContext(identity_id, session_id)` from Bearer token
- Refresh token rotation handled in `backend/src/modules/identity/application/commands/refresh_token.py`
- Telegram authentication supported via `login_telegram.py`
- Frontend stores tokens in httpOnly cookies; Next.js BFF attaches them as Authorization headers

**Authorization (RBAC):**
- `RequirePermission` FastAPI dependency checks permission strings (e.g., `catalog:manage`)
- Permissions resolved via `IPermissionResolver` with TTL-based caching (default 300s)
- Role-based: Identities have roles, roles have permissions
- Session-scoped: permissions are cached per session

**Caching:**
- Redis via `ICacheService` protocol
- Used for session permission caching, category tree caching
- Connection pool managed by Dishka at APP scope

**Database Migrations:**
- Alembic with async engine support
- Single migration file: `backend/alembic/versions/2026/03/27_0911_19_7ce70774f240_init.py`
- All ORM models registered in `backend/src/infrastructure/database/registry.py` for autogenerate

---

*Architecture analysis: 2026-03-28*
