# Architecture

**Analysis Date:** 2026-03-28

## Pattern Overview

**Overall:** Modular Monolith with Hexagonal (Ports & Adapters) Architecture per module, CQRS (Command-Query Responsibility Segregation), and Transactional Outbox for eventual consistency.

**Key Characteristics:**
- Each bounded context is a self-contained module under `backend/src/modules/` with domain, application, infrastructure, and presentation layers
- Strict Dependency Inversion: application layer depends on abstract interfaces (ports); infrastructure provides concrete implementations (adapters)
- CQRS: Commands use domain entities + UnitOfWork + repositories; Queries bypass the domain and read directly from ORM via AsyncSession
- Transactional Outbox pattern: domain events are persisted atomically with business data, then relayed asynchronously via TaskIQ background workers
- Dishka IoC container as the composition root for all dependency injection
- Three separate deployable processes: Web API (FastAPI/ASGI), Background Worker (TaskIQ), Scheduler (TaskIQ Beat)

## System Components

**Main Backend (`backend/`):**
- FastAPI REST API serving the core business logic
- Modules: catalog, identity, user, geo, supplier
- Telegram Bot (aiogram) embedded in the same codebase

**Image Backend (`image_backend/`):**
- Separate FastAPI microservice for image/media storage and processing
- Mirrors the same architectural patterns (modules, DI, UoW)
- Communicates with the main backend via server-to-server HTTP API

**Admin Frontend (`frontend/admin/`):**
- Next.js 16 application (React 19, Tailwind CSS)
- Proxies API calls through Next.js API routes to the backend
- App Router with file-based routing

**Main Frontend (`frontend/main/`):**
- Next.js 16 customer-facing storefront (React 19, Redux Toolkit)
- Telegram Mini App integration for authentication
- App Router with file-based routing

## Layers

**Presentation Layer (Routers):**
- Purpose: HTTP request/response handling, input validation, authorization
- Location: `backend/src/modules/{module}/presentation/`
- Contains: FastAPI routers (`router_*.py`), Pydantic request/response schemas (`schemas.py`), Dishka DI providers (`dependencies.py`), DTO mappers (`mappers.py`)
- Depends on: Application layer (command/query handlers), Shared schemas
- Used by: FastAPI framework (registered in `backend/src/api/router.py`)

**Application Layer (Commands & Queries):**
- Purpose: Orchestrates business use cases; enforces application-level rules
- Location: `backend/src/modules/{module}/application/`
- Contains: Command handlers (`commands/*.py`), Query handlers (`queries/*.py`), Read models (`queries/read_models.py`), Event consumers (`consumers/*.py`)
- Depends on: Domain layer (entities, interfaces, exceptions), Shared kernel (IUnitOfWork, ILogger)
- Used by: Presentation layer via DI injection
- Pattern: Each command/query is a frozen dataclass; each handler is a class with a `handle()` method

**Domain Layer:**
- Purpose: Core business logic, entities, value objects, domain events, repository interfaces
- Location: `backend/src/modules/{module}/domain/`
- Contains: Entities (`entities.py`), Value objects (`value_objects.py`), Domain events (`events.py`), Repository interfaces (`interfaces.py`), Domain exceptions (`exceptions.py`), Constants (`constants.py`)
- Depends on: Shared kernel only (`src/shared/interfaces/entities.py`)
- Used by: Application layer, Infrastructure layer (for interface implementation)
- Rule: Zero infrastructure imports. Domain is pure business logic.

**Infrastructure Layer:**
- Purpose: Concrete implementations of domain interfaces (repositories, external clients)
- Location: `backend/src/modules/{module}/infrastructure/`
- Contains: SQLAlchemy ORM models (`models.py`), Repository implementations (`repositories/*.py`), External service clients (e.g., `image_backend_client.py`), DI providers (`provider.py`)
- Depends on: Domain interfaces, SQLAlchemy, external SDKs
- Used by: DI container (wired via Dishka providers)

**Shared Kernel:**
- Purpose: Cross-cutting abstractions shared by all modules
- Location: `backend/src/shared/`
- Contains: Interface protocols (`interfaces/`), Base exception hierarchy (`exceptions.py`), Pagination helper (`pagination.py`), CamelCase schema base (`schemas.py`), Request context propagation (`context.py`)
- Used by: All layers across all modules

**Bootstrap Layer:**
- Purpose: Application wiring, configuration, process entry points
- Location: `backend/src/bootstrap/`
- Contains: App factory (`web.py`), DI container assembly (`container.py`), Configuration (`config.py`), Message broker setup (`broker.py`), Worker entry point (`worker.py`), Scheduler entry point (`scheduler.py`), Bot factory (`bot.py`), Logging setup (`logger.py`)
- Rule: This is the composition root. Only this layer wires concrete implementations to interfaces.

**API Layer (Cross-Cutting):**
- Purpose: Shared HTTP middleware, exception handlers, auth dependencies
- Location: `backend/src/api/`
- Contains: Root router aggregation (`router.py`), Exception handlers (`exceptions/handlers.py`), Auth dependency (`dependencies/auth.py`), Access logging middleware (`middlewares/logger.py`)

## Data Flow

**Command (Write) Flow:**

1. HTTP request hits FastAPI router endpoint in `presentation/router_*.py`
2. Router validates input via Pydantic schema, checks authorization via `RequirePermission` dependency
3. Router constructs a frozen `Command` dataclass from the request
4. Router calls `handler.handle(command)` on the DI-injected command handler
5. Command handler opens `async with self._uow:` (Unit of Work context)
6. Handler validates business rules via repository lookups (FK existence, slug uniqueness)
7. Handler calls domain entity factory method (e.g., `Product.create(...)`) or mutates existing entity
8. Handler persists via repository (`repo.add()` or `repo.update()`)
9. Handler registers aggregate with UoW: `self._uow.register_aggregate(entity)`
10. Handler calls `await self._uow.commit()` which atomically: flushes ORM changes, extracts domain events from registered aggregates, persists `OutboxMessage` rows, commits the database transaction
11. Router maps the result to a Pydantic response schema

**Query (Read) Flow:**

1. HTTP request hits FastAPI router endpoint
2. Router validates pagination/filter params, checks authorization
3. Router constructs a frozen `Query` dataclass
4. Router calls `handler.handle(query)` on the DI-injected query handler
5. Query handler queries ORM directly via `AsyncSession` (bypasses domain layer)
6. Handler uses `paginate()` helper with a mapper function to convert ORM rows to read models
7. Router maps read model to response schema

**Async Event Flow (Outbox Pattern):**

1. `OutboxMessage` rows are written atomically during command commit (see write flow step 10)
2. TaskIQ Scheduler (Beat) triggers `outbox_relay_task` every minute (`backend/src/infrastructure/outbox/tasks.py`)
3. Relay polls `outbox_messages` table with `FOR UPDATE SKIP LOCKED` (`backend/src/infrastructure/outbox/relay.py`)
4. Each event is dispatched to a registered handler in `_EVENT_HANDLERS` map
5. Event handler dispatches a TaskIQ background task (e.g., `create_profile_on_identity_registered`)
6. TaskIQ worker process executes the consumer task with DI-injected dependencies
7. Processed outbox records are pruned daily at 03:00 UTC

**State Management:**
- Server-side: PostgreSQL (ACID) as single source of truth; Redis for caching (permissions, FSM state)
- Client-side (admin frontend): Server-state via Next.js API routes proxying to backend
- Client-side (main frontend): Redux Toolkit for client state; Next.js API routes for server communication

## Key Abstractions

**AggregateRoot / DomainEvent:**
- Purpose: Base for domain entities that emit events; events are collected in-memory and flushed to Outbox on commit
- Examples: `backend/src/shared/interfaces/entities.py`, `backend/src/modules/catalog/domain/entities.py` (Product, Brand, Category)
- Pattern: Mixin with `add_domain_event()` / `clear_domain_events()` / `domain_events` property; attrs `@dataclass` decorator for entities

**IUnitOfWork:**
- Purpose: Transactional boundary that coordinates commit, rollback, and domain event persistence
- Examples: `backend/src/shared/interfaces/uow.py` (interface), `backend/src/infrastructure/database/uow.py` (implementation)
- Pattern: Async context manager (`async with uow:`); aggregates are registered for event extraction on commit

**ICatalogRepository[T]:**
- Purpose: Generic CRUD port for catalog aggregates (add, get, update, delete)
- Examples: `backend/src/modules/catalog/domain/interfaces.py`
- Pattern: Generic ABC with type parameter; module-specific repos extend with additional query methods

**BaseRepository[EntityType, ModelType]:**
- Purpose: Data Mapper base that converts between ORM models and domain entities
- Examples: `backend/src/modules/catalog/infrastructure/repositories/base.py`
- Pattern: Subclasses declare `model_class` via class argument, implement `_to_domain()` and `_to_orm()` hooks

**Command / Query Handler:**
- Purpose: Single-responsibility use case orchestrators
- Examples: `backend/src/modules/catalog/application/commands/create_product.py`, `backend/src/modules/catalog/application/queries/list_brands.py`
- Pattern: Frozen `@dataclass` for input, handler class with `handle()` method; constructor injection of repositories and UoW via Dishka

**Dishka Provider:**
- Purpose: DI registration mapping interfaces to implementations at specific scopes
- Examples: `backend/src/modules/catalog/presentation/dependencies.py` (per-module providers), `backend/src/bootstrap/container.py` (composition root)
- Pattern: One or more `Provider` classes per module; `provide(ConcreteClass, scope=Scope.REQUEST, provides=IInterface)`

**RequirePermission:**
- Purpose: Declarative route-level authorization via session permission checking
- Examples: `backend/src/modules/identity/presentation/dependencies.py`
- Pattern: Callable class used as FastAPI dependency (`Depends(RequirePermission("catalog:manage"))`); resolves permissions via cache-aside with Redis + recursive CTE fallback

## Entry Points

**Web API (ASGI):**
- Location: `backend/main.py` -> `backend/src/bootstrap/web.py`
- Triggers: Uvicorn ASGI server
- Responsibilities: Creates FastAPI app, wires CORS/middleware/exception handlers/routers, sets up Dishka DI, manages lifespan (broker startup/shutdown)

**Background Worker:**
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker` CLI command
- Responsibilities: Initializes DI container, registers DLQ middleware, imports task modules (consumers), processes queued tasks from RabbitMQ

**Scheduler (Beat):**
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler` CLI command
- Responsibilities: Dispatches scheduled tasks (outbox relay every minute, outbox pruning daily at 03:00 UTC)

**Image Backend API:**
- Location: `image_backend/main.py` -> `image_backend/src/bootstrap/web.py`
- Triggers: Uvicorn ASGI server (separate process, port 8001)
- Responsibilities: Image upload, processing (resize/crop), storage management

**Telegram Bot:**
- Location: `backend/src/bot/factory.py`
- Triggers: Webhook or long-polling via aiogram Dispatcher
- Responsibilities: User-facing Telegram bot with FSM, inline keyboards, throttling

## Error Handling

**Strategy:** Typed exception hierarchy with centralized HTTP mapping

**Patterns:**
- All expected errors inherit from `AppException` (`backend/src/shared/exceptions.py`) with `status_code`, `error_code`, and `details`
- Subclasses: `NotFoundError` (404), `UnauthorizedError` (401), `ForbiddenError` (403), `ConflictError` (409), `ValidationError` (400), `UnprocessableEntityError` (422)
- Domain modules define their own exception subclasses (e.g., `BrandHasProductsError`, `InvalidStatusTransitionError`) that inherit from the appropriate base
- Centralized exception handlers in `backend/src/api/exceptions/handlers.py` convert all exceptions to a uniform JSON envelope: `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}`
- UnitOfWork catches `IntegrityError` from SQLAlchemy and re-raises as `ConflictError` or `UnprocessableEntityError` based on SQL state code
- Unhandled exceptions are caught by the catch-all handler, logged with full traceback, and returned as a generic 500 response

## Cross-Cutting Concerns

**Logging:**
- structlog with contextvars for request-scoped fields (request_id, identity_id, session_id)
- `ILogger` interface (`backend/src/shared/interfaces/logger.py`) injected via Dishka
- Access logging middleware (`backend/src/api/middlewares/logger.py`)
- TaskIQ middleware for background task logging (`backend/src/infrastructure/logging/taskiq_middleware.py`)

**Validation:**
- Input: Pydantic schemas in presentation layer with automatic camelCase aliasing via `CamelModel` (`backend/src/shared/schemas.py`)
- Domain: Entity factory methods and `update()` methods perform business rule validation (slug format, i18n completeness, status FSM transitions)
- Database: Constraint-level validation (unique indexes, FK constraints) caught by UoW and re-raised as domain exceptions

**Authentication:**
- JWT Bearer tokens with `sub` (identity_id) and `sid` (session_id) claims
- `get_auth_context()` dependency in `backend/src/modules/identity/presentation/dependencies.py`
- Token version validation against database (`tv` claim vs `identity.token_version`)
- Telegram authentication via `initData` validation (`backend/src/infrastructure/security/telegram.py`)

**Authorization:**
- RBAC with recursive role hierarchy
- `RequirePermission` callable dependency checks session permissions via cache-aside resolver
- Redis cache with configurable TTL (default 300s); PostgreSQL recursive CTE fallback
- Permission codenames follow `module:action` pattern (e.g., `catalog:manage`, `catalog:read`)

**Request Context:**
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing

---

*Architecture analysis: 2026-03-28*
