# Architecture

**Analysis Date:** 2026-03-29

## Pattern Overview

**Overall:** DDD Modular Monolith with Hexagonal Architecture + CQRS

**Key Characteristics:**
- Bounded contexts as self-contained modules under `backend/src/modules/` with strict 4-layer structure (presentation, application, domain, infrastructure)
- Strict Dependency Inversion: application layer depends on abstract interfaces (ports); infrastructure provides concrete implementations (adapters)
- CQRS split: Commands flow through domain entities + UnitOfWork + repositories; Queries bypass domain and read directly from ORM via `AsyncSession`
- Transactional Outbox pattern: domain events are persisted atomically with business data in the same DB transaction, then relayed asynchronously via TaskIQ workers
- Dishka IoC container as the single composition root for all dependency injection
- Three separate deployable processes sharing the same codebase: Web API (FastAPI/ASGI), Background Worker (TaskIQ), Scheduler (TaskIQ Beat)
- A separate Image Backend microservice mirrors the same architectural patterns

## Layers

**Presentation Layer:**
- Purpose: HTTP request/response handling, input validation via Pydantic schemas, route-level authorization
- Location: `backend/src/modules/{module}/presentation/`
- Contains: FastAPI routers (`router_*.py`), Pydantic request/response schemas (`schemas.py`), Dishka DI providers (`dependencies.py`), DTO mappers (`mappers.py`), update helpers (`update_helpers.py`)
- Depends on: Application layer (command/query handlers), Shared schemas (`src/shared/schemas.py`)
- Used by: FastAPI framework (registered in `backend/src/api/router.py`)
- Pattern: Each router file defines one `APIRouter` with prefix and tags, uses `DishkaRoute` for automatic DI injection, `FromDishka[HandlerType]` for handler injection in endpoint params
- Auth: `Depends(RequirePermission(codename="catalog:manage"))` for permission checks

**Application Layer:**
- Purpose: Orchestrate business use cases; enforce application-level rules
- Location: `backend/src/modules/{module}/application/`
- Contains:
  - Command handlers: `commands/*.py` (one command + handler per file)
  - Query handlers: `queries/*.py` (one query + handler per file)
  - Read models: `queries/read_models.py`
  - Event consumers: `consumers/*.py` (TaskIQ task handlers)
  - Constants: `constants.py` (cache keys, domain constants)
- Depends on: Domain layer (entities, interfaces, exceptions), Shared kernel (`IUnitOfWork`, `ILogger`)
- Used by: Presentation layer via Dishka DI injection
- Pattern: Each command/query is a frozen `@dataclass`; each handler is a class with an `async def handle()` method; constructor injection of repositories and UoW

**Domain Layer:**
- Purpose: Core business logic, entities, value objects, domain events, repository interfaces (ports)
- Location: `backend/src/modules/{module}/domain/`
- Contains:
  - Entities: `entities.py` or `entities/*.py` (catalog uses subdirectory)
  - Value objects: `value_objects.py`
  - Domain events: `events.py`
  - Repository interfaces: `interfaces.py`
  - Domain exceptions: `exceptions.py`
  - Constants: `constants.py`
- Depends on: Shared kernel only (`src/shared/interfaces/entities.py`)
- Used by: Application layer, Infrastructure layer (for interface implementation)
- Rule: Zero infrastructure imports. Domain is pure business logic.

**Infrastructure Layer:**
- Purpose: Concrete implementations of domain interfaces (repositories, external clients)
- Location: `backend/src/modules/{module}/infrastructure/`
- Contains:
  - ORM models: `models.py` (single file per module)
  - Repository implementations: `repositories/*.py`
  - External service clients: e.g., `image_backend_client.py`
  - DI providers: `provider.py`
- Depends on: Domain interfaces, SQLAlchemy, external SDKs
- Used by: DI container (wired via Dishka providers)
- Pattern: Data Mapper via `BaseRepository` that converts between ORM models and domain entities

**Shared Kernel:**
- Purpose: Cross-cutting abstractions shared by all modules
- Location: `backend/src/shared/`
- Contains:
  - Interface protocols: `interfaces/` (IUnitOfWork, ILogger, IBase, AggregateRoot, DomainEvent, ITokenProvider, IPermissionResolver, ICache, AuthContext)
  - Base exception hierarchy: `exceptions.py` (AppException -> NotFoundError, UnauthorizedError, ForbiddenError, ConflictError, ValidationError, UnprocessableEntityError)
  - Pagination helper: `pagination.py`
  - CamelCase schema base: `schemas.py` (CamelModel)
  - Request context propagation: `context.py` (ContextVar for request_id)
- Used by: All layers across all modules

**Bootstrap (Composition Root):**
- Purpose: Application wiring, configuration, process entry points
- Location: `backend/src/bootstrap/`
- Contains:
  - App factory: `web.py` (creates FastAPI app, wires middleware/handlers/routers)
  - DI container assembly: `container.py` (composes all module-level providers)
  - Configuration: `config.py` (Pydantic Settings, validated at startup)
  - Message broker: `broker.py` (AioPikaBroker with RabbitMQ)
  - Worker entry point: `worker.py` (TaskIQ worker with DI, DLQ, task imports)
  - Scheduler entry point: `scheduler.py` (TaskIQ Beat with schedule sources)
  - Bot factory: `bot.py` (aiogram Dispatcher)
  - Logging setup: `logger.py` (structlog configuration)
- Rule: Only this layer wires concrete implementations to interfaces.

**API Cross-Cutting Layer:**
- Purpose: Shared HTTP middleware, exception handlers, auth dependencies
- Location: `backend/src/api/`
- Contains:
  - Root router aggregation: `router.py` (includes all module routers with prefixes)
  - Exception handlers: `exceptions/handlers.py` (4 handlers: AppException, RequestValidationError, HTTPException, catch-all)
  - Auth dependency: `dependencies/auth.py`
  - Access logging middleware: `middlewares/logger.py`

## Data Flow

**Command Flow (Write Side):**
1. HTTP request hits FastAPI router in presentation layer (`router_brands.py`)
2. Router validates input via Pydantic schema, checks permissions via `RequirePermission`
3. Router constructs a frozen `@dataclass` Command and calls `handler.handle(command)`
4. Handler (injected via Dishka) opens UoW context: `async with self._uow:`
5. Handler calls repository methods (via interface) to check invariants (e.g., slug uniqueness)
6. Handler calls entity factory method (e.g., `Brand.create(...)`) for domain validation
7. Handler calls `repo.add(entity)` which maps domain entity to ORM model via `_to_orm()`
8. Handler calls `entity.add_domain_event(...)` then `uow.register_aggregate(entity)`
9. `uow.commit()` extracts events from aggregates, persists them as `OutboxMessage` rows atomically with business data, then commits the transaction
10. Handler returns a frozen `@dataclass` Result
11. Router maps Result to Pydantic Response and returns HTTP response

**Query Flow (Read Side):**
1. HTTP request hits FastAPI router
2. Router constructs a frozen `@dataclass` Query (offset, limit, filters)
3. Handler (injected via Dishka) receives `AsyncSession` directly (no UoW, no repository)
4. Handler builds SQLAlchemy `select()` against ORM models directly
5. Handler uses `paginate()` helper for offset/limit queries
6. Handler maps ORM rows to Pydantic read models via mapper functions
7. Router returns the read model as HTTP response

**Event Flow (Outbox Relay):**
1. Scheduler dispatches `outbox_relay_task` every minute via TaskIQ Beat
2. Worker picks up the task from RabbitMQ queue
3. Relay queries `outbox_messages` for unprocessed events (status = pending)
4. For each event, relay dispatches a TaskIQ task to the appropriate consumer
5. Consumer processes the event (e.g., `identity_events.py` creates a user profile when identity is created)
6. Relay marks the event as processed; pruning task cleans up old events daily at 03:00 UTC

**Frontend-to-Backend Flow (Main App):**
1. Client-side RTK Query calls `/api/backend/{path}` (Next.js API route)
2. Next.js catch-all route (`frontend/main/app/api/backend/[...path]/route.ts`) proxies to FastAPI backend
3. Proxy reads JWT from httpOnly cookie, attaches as `Authorization: Bearer` header
4. FastAPI processes the request through the command/query flow above
5. Response is proxied back through Next.js to the client

**Frontend-to-Backend Flow (Admin App):**
1. Admin server components or API routes call `backendFetch(path)` from `frontend/admin/src/lib/api-client.js`
2. Each Next.js API route (e.g., `frontend/admin/src/app/api/catalog/brands/route.js`) acts as a BFF proxy
3. Cookie-based auth tokens are forwarded to the backend

**State Management:**
- Server-side: PostgreSQL (ACID) as single source of truth; Redis for caching (permissions, storefront attributes, category tree)
- Client-side (main frontend): Redux Toolkit + RTK Query with automatic token refresh
- Client-side (admin frontend): Server-state via Next.js API routes, no global state manager

## Key Abstractions

**AggregateRoot + DomainEvent:**
- Purpose: Base for domain entities that emit events; events are collected in-memory and flushed to Outbox on commit
- Examples: `backend/src/shared/interfaces/entities.py`
- Concrete entities: `backend/src/modules/catalog/domain/entities/brand.py`, `backend/src/modules/catalog/domain/entities/product.py`, `backend/src/modules/catalog/domain/entities/category.py`
- Pattern: `AggregateRoot` mixin with `add_domain_event()` / `clear_domain_events()` / `domain_events` property; entities use `attrs @dataclass` decorator

**IUnitOfWork:**
- Purpose: Transactional boundary that coordinates commit, rollback, and domain event persistence
- Interface: `backend/src/shared/interfaces/uow.py`
- Implementation: `backend/src/infrastructure/database/uow.py`
- Pattern: Async context manager (`async with uow:`); aggregates are registered for event extraction on commit; catches `IntegrityError` and maps to domain exceptions

**ICatalogRepository[T]:**
- Purpose: Generic CRUD port for catalog aggregates (add, get, update, delete)
- Interface: `backend/src/modules/catalog/domain/interfaces.py`
- Pattern: Generic ABC with type parameter; module-specific repos extend with additional query methods (e.g., `check_slug_exists`, `get_for_update`, `has_products`)

**BaseRepository[EntityType, ModelType]:**
- Purpose: Data Mapper base that converts between ORM models and domain entities
- Implementation: `backend/src/modules/catalog/infrastructure/repositories/base.py`
- Pattern: Subclasses declare `model_class` via class argument, implement `_to_domain()` and `_to_orm()` hooks; provides generic `add`, `get`, `update`, `delete`, `get_for_update`, `_field_exists` methods

**Command/Query Handlers:**
- Purpose: Single-responsibility use case orchestrators
- Command examples: `backend/src/modules/catalog/application/commands/create_brand.py`, `backend/src/modules/catalog/application/commands/create_product.py`
- Query examples: `backend/src/modules/catalog/application/queries/list_brands.py`, `backend/src/modules/catalog/application/queries/storefront.py`
- Pattern: Frozen `@dataclass` for input (Command/Query), handler class with `async def handle()` method; constructor injection of repos, UoW, logger via Dishka

**Dishka Providers:**
- Purpose: DI registration mapping interfaces to implementations at specific scopes
- Examples: `backend/src/modules/catalog/presentation/dependencies.py`, `backend/src/infrastructure/database/provider.py`, `backend/src/bootstrap/container.py`
- Pattern: One or more `Provider` classes per module; `provide(ConcreteClass, scope=Scope.REQUEST, provides=IInterface)`; scopes: APP (singletons), REQUEST (per-request)

**RequirePermission:**
- Purpose: Declarative route-level RBAC authorization
- Location: `backend/src/modules/identity/presentation/dependencies.py`
- Pattern: Callable class used as FastAPI dependency; resolves permissions via cache-aside with Redis + PostgreSQL recursive CTE fallback; permission codenames follow `module:action` pattern (e.g., `catalog:manage`, `catalog:read`)

**CamelModel:**
- Purpose: Base Pydantic schema with automatic snake_case-to-camelCase aliasing
- Location: `backend/src/shared/schemas.py`
- Pattern: All presentation-layer request/response schemas inherit from `CamelModel`

## Entry Points

**Web API (FastAPI):**
- Location: `backend/main.py` -> `backend/src/bootstrap/web.py`
- Triggers: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Responsibilities: Creates FastAPI app via `create_app()`, wires CORS middleware, access logging middleware, exception handlers, API router (all modules under `/api/v1`), health check endpoint, Dishka DI container, TaskIQ broker startup/shutdown in lifespan

**Background Worker (TaskIQ):**
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker`
- Responsibilities: Initializes DI container, registers DLQ middleware (persists failed tasks to DB), imports task modules (outbox relay, role events consumer, identity events consumer), processes queued tasks from RabbitMQ
- Critical ordering: DI setup must happen before task imports (tasks register via `@broker.task()` decorator at import time)

**Scheduler (TaskIQ Beat):**
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler`
- Responsibilities: Dispatches `outbox_relay_task` every minute, `outbox_pruning_task` daily at 03:00 UTC
- Constraint: Exactly one instance must run to avoid duplicate dispatches

**Image Backend:**
- Location: `image_backend/main.py` -> `image_backend/src/bootstrap/web.py`
- Triggers: `uvicorn main:app --host 0.0.0.0 --port 8001`
- Responsibilities: Image upload, processing (resize/crop/WebP conversion), S3-compatible storage, SSE for processing status

**Telegram Bot:**
- Location: `backend/src/bot/factory.py`
- Triggers: Webhook or long-polling via aiogram Dispatcher
- Responsibilities: User-facing Telegram bot with FSM, inline keyboards, throttling

## Error Handling

**Strategy:** Layered exception hierarchy with global catch-all

**Exception Hierarchy:**
- `AppException` (base, `backend/src/shared/exceptions.py`) -> status_code, error_code, message, details
  - `NotFoundError` (404)
  - `UnauthorizedError` (401)
  - `ForbiddenError` (403)
  - `ConflictError` (409)
  - `ValidationError` (400)
  - `UnprocessableEntityError` (422)
- Domain modules define their own exceptions inheriting from the appropriate base (e.g., `BrandHasProductsError`, `InvalidStatusTransitionError`, `CategoryMaxDepthError` in `backend/src/modules/catalog/domain/exceptions.py`)

**Global Exception Handlers** (`backend/src/api/exceptions/handlers.py`):
1. `AppException` -> JSON envelope with error code, message, details, request_id
2. `RequestValidationError` (Pydantic) -> 422 with per-field error details
3. `StarletteHTTPException` -> JSON envelope (for framework 404/405 errors)
4. `Exception` (catch-all) -> 500 with generic message, full traceback logged

**UoW-Level Error Translation:**
- `IntegrityError` with sqlstate `23503` (FK violation) -> `UnprocessableEntityError`
- Other `IntegrityError` -> `ConflictError`

**Domain Validation Pattern:**
- Entity factory methods (`create()`, `create_root()`, `create_child()`) validate invariants (slug format, i18n completeness, max depth) and raise `ValueError` or domain-specific exceptions
- `__setattr__` guard pattern (DDD-01) prevents direct mutation of guarded fields (e.g., `slug`, `status`)

**JSON Error Envelope:**
```json
{
  "error": {
    "code": "BRAND_SLUG_CONFLICT",
    "message": "Brand with slug 'nike' already exists",
    "details": {"slug": "nike"},
    "request_id": "abc123"
  }
}
```

## Cross-Cutting Concerns

**Logging:**
- structlog with contextvars for request-scoped fields (request_id, correlation_id, ip, method, path, identity_id, session_id)
- `ILogger` protocol (`backend/src/shared/interfaces/logger.py`) injected via Dishka
- Access logging middleware (`backend/src/api/middlewares/logger.py`) emits one structured log per HTTP request with timing
- Handlers bind their own name: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Log levels: `info` for success, `warning` for 4xx, `error` for 5xx

**Validation:**
- Input: Pydantic schemas in presentation layer with automatic camelCase aliasing via `CamelModel`
- Domain: Entity factory methods and `update()` methods validate business rules
- Database: Constraint-level validation (unique indexes, FK constraints) caught by UoW and re-raised as domain exceptions
- i18n fields: Must include `ru` and `en` locales (enforced by `validate_i18n_completeness()`)

**Authentication:**
- JWT Bearer tokens with `sub` (identity_id), `sid` (session_id), `tv` (token_version) claims
- `get_auth_context()` dependency in `backend/src/modules/identity/presentation/dependencies.py`
- Token version validation against database per request (`tv` claim vs `identity.token_version`)
- Telegram authentication via `initData` validation (`backend/src/infrastructure/security/telegram.py`)

**Authorization (RBAC):**
- `RequirePermission` callable dependency checks session permissions
- Cache-aside pattern: Redis cache with TTL -> PostgreSQL recursive CTE fallback
- Permission codenames: `module:action` (e.g., `catalog:manage`, `catalog:read`)

**Request Tracing:**
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing
- Response headers include `X-Process-Time-Ms` and `X-Request-ID`

**Caching:**
- Redis for: permission resolution, storefront attribute queries, category tree
- Cache keys defined in `backend/src/modules/catalog/application/constants.py`
- Pattern: cache-aside (check cache -> miss -> query DB -> populate cache)
- TTL: 1 hour for storefront caches, 300s for permissions

## Bounded Contexts (Modules)

**catalog** (largest, focus of current milestone):
- Location: `backend/src/modules/catalog/`
- Entities: Brand, Category, Product (aggregate root with ProductVariant + SKU children), Attribute, AttributeGroup, AttributeValue, AttributeTemplate, TemplateAttributeBinding, MediaAsset, ProductAttributeValue
- Commands: 48 command handlers covering full CRUD + bulk operations + status FSM + SKU matrix generation
- Queries: 25 query handlers including storefront-specific queries (filterable, card, comparison, form attributes)
- EAV pattern: Products have dynamic attributes via ProductAttributeValue join table; categories define attribute templates
- Routers: 11 router files (`router_brands.py`, `router_categories.py`, `router_products.py`, `router_variants.py`, `router_skus.py`, `router_attributes.py`, `router_attribute_values.py`, `router_attribute_templates.py`, `router_product_attributes.py`, `router_media.py`, `router_storefront.py`)

**identity:**
- Location: `backend/src/modules/identity/`
- Entities: Identity, Role, Permission, Session, LinkedAccount, LocalCredentials, StaffInvitation
- Handles: Authentication (JWT, Telegram), RBAC, staff management, customer management
- Routers: `router_auth.py`, `router_admin.py`, `router_staff.py`, `router_customers.py`, `router_account.py`, `router_invitation.py`

**user:**
- Location: `backend/src/modules/user/`
- Entities: Customer, StaffMember (Profile)
- Handles: User profile CRUD, customer creation/anonymization
- Event consumers: Listens for identity events to auto-create profiles

**geo:**
- Location: `backend/src/modules/geo/`
- Contains: Country, Subdivision, Currency, Language reference data
- Read-only: Queries only, no commands (seed data)

**supplier:**
- Location: `backend/src/modules/supplier/`
- Entities: Supplier
- Handles: Supplier CRUD for the marketplace

**storage (image_backend):**
- Location: `image_backend/src/modules/storage/`
- Entities: StorageObject
- Handles: Image upload, processing (resize, WebP conversion), S3 storage
- Pattern: Same hexagonal architecture as main backend

---

*Architecture analysis: 2026-03-29*
