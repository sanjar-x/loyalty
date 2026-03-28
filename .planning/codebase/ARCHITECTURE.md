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
- Telegram Bot (aiogram) embedded in the same codebase (`backend/src/bot/`)

**Image Backend (`image_backend/`):**
- Separate FastAPI microservice for image/media storage and processing
- Mirrors the same architectural patterns (modules, DI, UoW)
- Single bounded context: `storage` (`image_backend/src/modules/storage/`)
- Communicates with the main backend via server-to-server HTTP API with API key auth

**Admin Frontend (`frontend/admin/`):**
- Next.js 16 application (React 19, JSX, Tailwind CSS)
- Proxies API calls through Next.js API routes to the backend (BFF pattern)
- App Router with file-based routing under `src/app/`

**Main Frontend (`frontend/main/`):**
- Next.js 16 customer-facing storefront (React 19, TypeScript, Redux Toolkit)
- Telegram Mini App integration for authentication
- App Router with file-based routing under `app/`
- Catch-all proxy route at `app/api/backend/[...path]/route.ts` forwards to backend

## Layers

### Presentation Layer

- **Purpose:** HTTP request/response handling, input validation, authorization
- **Location:** `backend/src/modules/{module}/presentation/`
- **Contains:**
  - FastAPI routers (`router_*.py`) -- one per resource/entity
  - Pydantic request/response schemas (`schemas.py`)
  - Dishka DI providers (`dependencies.py`) -- wires interfaces to implementations
  - DTO mappers (`mappers.py`) -- converts between schemas and commands
  - Update helpers (`update_helpers.py`) -- partial update support with Ellipsis sentinel
- **Depends on:** Application layer (command/query handlers), Shared schemas
- **Used by:** FastAPI framework (registered in `backend/src/api/router.py`)

**Router Pattern:**
```python
# backend/src/modules/catalog/presentation/router_brands.py
brand_router = APIRouter(prefix="/brands", tags=["Brands"], route_class=DishkaRoute)

@brand_router.post("", status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))])
async def create_brand(
    request: BrandCreateRequest,
    handler: FromDishka[CreateBrandHandler],
) -> BrandCreateResponse:
    command = CreateBrandCommand(name=request.name, slug=request.slug)
    result = await handler.handle(command)
    return BrandCreateResponse(id=result.brand_id)
```

### Application Layer

- **Purpose:** Orchestrates business use cases; enforces application-level rules
- **Location:** `backend/src/modules/{module}/application/`
- **Contains:**
  - Command handlers (`commands/*.py`) -- one file per write operation
  - Query handlers (`queries/*.py`) -- one file per read operation
  - Read models (`queries/read_models.py`) -- Pydantic DTOs for query results
  - Event consumers (`consumers/*.py`) -- react to domain events via TaskIQ
- **Depends on:** Domain layer (entities, interfaces, exceptions), Shared kernel (IUnitOfWork, ILogger)
- **Used by:** Presentation layer via DI injection
- **Pattern:** Each command/query is a frozen dataclass; each handler is a class with a `handle()` method

**Command Handler Pattern:**
```python
# backend/src/modules/catalog/application/commands/create_brand.py
@dataclass(frozen=True)
class CreateBrandCommand:
    name: str
    slug: str

@dataclass(frozen=True)
class CreateBrandResult:
    brand_id: uuid.UUID

class CreateBrandHandler:
    def __init__(self, brand_repo: IBrandRepository, uow: IUnitOfWork, logger: ILogger):
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateBrandHandler")

    async def handle(self, command: CreateBrandCommand) -> CreateBrandResult:
        async with self._uow:
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)
            brand = Brand.create(name=command.name, slug=command.slug)
            brand = await self._brand_repo.add(brand)
            brand.add_domain_event(BrandCreatedEvent(...))
            self._uow.register_aggregate(brand)
            await self._uow.commit()
        self._logger.info("Brand created", brand_id=str(brand.id))
        return CreateBrandResult(brand_id=brand.id)
```

**Query Handler Pattern (CQRS Read Side):**
```python
# backend/src/modules/catalog/application/queries/list_brands.py
@dataclass(frozen=True)
class ListBrandsQuery:
    offset: int = 0
    limit: int = 20

class ListBrandsHandler:
    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session  # Direct ORM access, no UoW/repos
        self._logger = logger.bind(handler="ListBrandsHandler")

    async def handle(self, query: ListBrandsQuery) -> BrandListReadModel:
        base = select(OrmBrand).order_by(OrmBrand.name)
        items, total = await paginate(self._session, base, ...)
        return BrandListReadModel(items=items, total=total, ...)
```

### Domain Layer

- **Purpose:** Core business logic, entities, value objects, domain events, repository interfaces
- **Location:** `backend/src/modules/{module}/domain/`
- **Contains:**
  - Entities (`entities.py`) -- attrs `@dataclass` classes with factory methods and invariant validation
  - Value objects (`value_objects.py`) -- StrEnum enums, frozen attrs classes (Money, BehaviorFlags)
  - Domain events (`events.py`) -- DomainEvent subclasses emitted on state changes
  - Repository interfaces (`interfaces.py`) -- abstract ABC repository contracts
  - Domain exceptions (`exceptions.py`) -- module-specific error subclasses
  - Constants (`constants.py`) -- application-level constants (locales, defaults)
- **Depends on:** Shared kernel only (`src/shared/interfaces/entities.py`)
- **Used by:** Application layer, Infrastructure layer (for interface implementation)
- **Rule:** Zero infrastructure imports. Domain is pure business logic.

**Entity Pattern (attrs + AggregateRoot):**
```python
# backend/src/modules/catalog/domain/entities.py
@dataclass
class Brand(AggregateRoot):
    id: uuid.UUID
    name: str
    slug: str

    # DDD-01: guard slug against direct mutation
    def __setattr__(self, name, value):
        if name in _BRAND_GUARDED_FIELDS and getattr(self, "_Brand__initialized", False):
            raise AttributeError(f"Cannot set '{name}' directly. Use update().")
        super().__setattr__(name, value)

    @classmethod
    def create(cls, name: str, slug: str, ...) -> Brand:
        _validate_slug(slug, "Brand")
        return cls(id=_generate_id(), name=name.strip(), slug=slug, ...)

    def update(self, name=None, slug=None, ...):
        if slug is not None:
            object.__setattr__(self, "slug", slug)  # Bypass guard
```

**Product Aggregate with FSM:**
```python
# Product status transitions enforced by class-level dict
_ALLOWED_TRANSITIONS = {
    ProductStatus.DRAFT: {ProductStatus.ENRICHING},
    ProductStatus.ENRICHING: {ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW},
    ProductStatus.READY_FOR_REVIEW: {ProductStatus.ENRICHING, ProductStatus.PUBLISHED},
    ProductStatus.PUBLISHED: {ProductStatus.ARCHIVED},
    ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
}
```
Product owns ProductVariant children (which own SKU children). SKU uniqueness is enforced via SHA-256 `variant_hash` computed from `(variant_id, variant_attributes)`.

### Infrastructure Layer

- **Purpose:** Concrete implementations of domain interfaces (repositories, external clients)
- **Location:** `backend/src/modules/{module}/infrastructure/`
- **Contains:**
  - SQLAlchemy ORM models (`models.py`)
  - Repository implementations (`repositories/*.py`)
  - External service clients (e.g., `image_backend_client.py`)
  - DI providers (`provider.py`)
- **Depends on:** Domain interfaces, SQLAlchemy, external SDKs
- **Used by:** DI container (wired via Dishka providers)

**Data Mapper Repository Pattern:**
```python
# backend/src/modules/catalog/infrastructure/repositories/base.py
class BaseRepository[EntityType, ModelType: IBase](ICatalogRepository[EntityType]):
    model: type[ModelType]

    def __init_subclass__(cls, model_class=None, **kwargs):
        if model_class:
            cls.model = model_class

    def __init__(self, session: AsyncSession):
        self._session = session

    @abstractmethod
    def _to_domain(self, orm: ModelType) -> EntityType: ...
    @abstractmethod
    def _to_orm(self, entity: EntityType, orm=None) -> ModelType: ...

    async def add(self, entity): ...      # ORM -> flush -> domain
    async def get(self, entity_id): ...   # session.get -> domain
    async def update(self, entity): ...   # merge -> flush -> domain
    async def delete(self, entity_id): ...
```

Concrete repos inherit with `model_class=` class argument:
```python
class BrandRepository(BaseRepository[DomainBrand, Brand], model_class=Brand):
    def _to_domain(self, orm): ...
    def _to_orm(self, entity, orm=None): ...
```

### Shared Kernel

- **Purpose:** Cross-cutting abstractions shared by all modules
- **Location:** `backend/src/shared/`
- **Contains:**
  - `interfaces/entities.py`: `IBase` protocol, `DomainEvent` base, `AggregateRoot` mixin
  - `interfaces/uow.py`: `IUnitOfWork` abstract class
  - `interfaces/auth.py`: `AuthContext` dataclass
  - `interfaces/cache.py`: `ICacheService` protocol
  - `interfaces/security.py`: `ITokenProvider`, `IPermissionResolver` protocols
  - `interfaces/logger.py`: `ILogger` protocol
  - `exceptions.py`: `AppException` hierarchy (NotFound 404, Unauthorized 401, Forbidden 403, Conflict 409, Validation 400, UnprocessableEntity 422)
  - `pagination.py`: Generic `paginate()` helper for CQRS queries
  - `schemas.py`: `CamelModel` base with automatic snake_case -> camelCase aliasing
  - `context.py`: Request ID propagation via `ContextVar`

### Bootstrap Layer

- **Purpose:** Application wiring, configuration, process entry points
- **Location:** `backend/src/bootstrap/`
- **Contains:**
  - `web.py`: `create_app()` FastAPI factory (CORS, middleware, routers, DI, health check, lifespan)
  - `container.py`: `create_container()` assembles all Dishka providers into single `AsyncContainer`
  - `config.py`: `Settings` class (Pydantic Settings, loads from `.env`, `SecretStr` for secrets)
  - `broker.py`: `AioPikaBroker` (RabbitMQ) configuration with logging middleware
  - `worker.py`: TaskIQ worker initialization (critical import order: container -> dishka -> tasks)
  - `scheduler.py`: TaskIQ Beat scheduler with outbox relay (every minute) and pruning (daily 03:00 UTC)
  - `bot.py`: Telegram bot factory
  - `logger.py`: structlog configuration
- **Rule:** This is the composition root. Only this layer wires concrete implementations to interfaces.

### API Layer (Cross-Cutting)

- **Purpose:** Shared HTTP middleware, exception handlers, auth dependencies
- **Location:** `backend/src/api/`
- **Contains:**
  - `router.py`: Root router aggregation -- imports all module routers and mounts them with prefixes
  - `exceptions/handlers.py`: Four exception handlers registered on FastAPI: `AppException` -> structured JSON, `RequestValidationError` -> 422, `HTTPException` -> JSON envelope, `Exception` -> 500 catch-all
  - `dependencies/auth.py`: Shared JWT extraction dependency
  - `middlewares/logger.py`: Access logging with request/response timing and request ID propagation

## Data Flow

### Command (Write) Flow

1. HTTP request hits FastAPI router endpoint in `presentation/router_*.py`
2. Router validates input via Pydantic schema (`CamelModel` subclass), checks authorization via `Depends(RequirePermission(codename="..."))`
3. Router constructs a frozen `Command` dataclass from the validated request
4. Router calls `handler.handle(command)` on the Dishka-injected command handler (`FromDishka[Handler]`)
5. Command handler opens `async with self._uow:` (Unit of Work context)
6. Handler validates business rules via repository lookups (FK existence, slug uniqueness, deletion guards)
7. Handler calls domain entity factory method (e.g., `Product.create(...)`) or mutates existing entity via `entity.update()`
8. Handler persists via repository (`repo.add()` or `repo.update()`) which internally calls `_to_orm()` + `session.flush()`
9. Handler registers aggregate with UoW: `self._uow.register_aggregate(entity)`
10. Handler calls `await self._uow.commit()` which atomically:
    - Calls `_collect_and_persist_outbox_events()` to extract domain events from all registered aggregates
    - Maps each `DomainEvent` to an `OutboxMessage` ORM instance with serialized payload and correlation ID
    - Calls `session.commit()` -- business data and outbox records in one transaction
11. On `IntegrityError`: UoW rolls back and re-raises as `ConflictError` (unique constraint) or `UnprocessableEntityError` (FK violation, sqlstate 23503)
12. Router maps the handler result to a Pydantic response schema

### Query (Read) Flow

1. HTTP request hits FastAPI router endpoint
2. Router validates pagination/filter params via `Query()`, checks authorization
3. Router constructs a frozen `Query` dataclass
4. Router calls `handler.handle(query)` on the DI-injected query handler
5. Query handler queries ORM directly via `AsyncSession` (bypasses domain layer entirely)
6. Handler uses `paginate()` helper from `backend/src/shared/pagination.py` with a mapper function
7. `paginate()` executes count query + offset/limit query, maps ORM rows to read models
8. Router maps read model to response schema, sets `Cache-Control: no-store` header

### Async Event Flow (Outbox Pattern)

1. `OutboxMessage` rows are written atomically during command commit (see write flow step 10)
2. TaskIQ Scheduler (Beat) triggers `outbox_relay_task` every minute (`backend/src/infrastructure/outbox/tasks.py`)
3. Relay polls `outbox_messages` table with `SELECT ... FOR UPDATE SKIP LOCKED` (`backend/src/infrastructure/outbox/relay.py`)
4. Each event is dispatched to a registered handler from `_EVENT_HANDLERS` registry keyed by `event_type`
5. Event handler dispatches a TaskIQ background task
6. TaskIQ worker process executes the consumer task with DI-injected dependencies
7. Processed outbox records are pruned daily at 03:00 UTC via `outbox_pruning_task`

**Active event consumers:**
- `backend/src/modules/identity/application/consumers/role_events.py` -- reacts to role hierarchy changes
- `backend/src/modules/user/application/consumers/identity_events.py` -- creates user profile on identity registration

**Note:** Catalog domain events (27 event types) are recorded to Outbox but no consumer processes them yet -- planned for Elasticsearch sync.

### State Management

- **Server-side:** PostgreSQL (ACID) as single source of truth; Redis for caching (permissions TTL 300s, FSM state)
- **Admin frontend:** Server-state via Next.js API routes proxying to backend (no client-side state management library)
- **Main frontend:** Redux Toolkit (`frontend/main/lib/store/`) for client state; RTK Query for API calls; Next.js API routes for BFF proxy

## Key Abstractions

### AggregateRoot / DomainEvent
- **Purpose:** Base for domain entities that emit events; events are collected in-memory and flushed to Outbox on commit
- **Files:** `backend/src/shared/interfaces/entities.py`
- **Pattern:** Mixin with `add_domain_event()` / `clear_domain_events()` / `domain_events` property; combined with attrs `@dataclass` for entity fields
- **DomainEvent base** enforces `aggregate_type` and `event_type` override via `__init_subclass__`; serialized via `dataclasses.asdict()`

### IUnitOfWork
- **Purpose:** Transactional boundary that coordinates commit, rollback, and domain event persistence
- **Interface:** `backend/src/shared/interfaces/uow.py`
- **Implementation:** `backend/src/infrastructure/database/uow.py`
- **Pattern:** Async context manager; `register_aggregate()` to track entities; `commit()` extracts events and writes `OutboxMessage` rows atomically

### ICatalogRepository[T]
- **Purpose:** Generic CRUD port for catalog aggregates
- **File:** `backend/src/modules/catalog/domain/interfaces.py`
- **Methods:** `add()`, `get()`, `update()`, `delete()`
- **Pattern:** Generic ABC with type parameter; module-specific repos extend with additional query methods (e.g., `check_slug_exists()`, `get_for_update()`, `has_products()`)
- **Catalog repos:** `IBrandRepository`, `ICategoryRepository`, `IProductRepository`, `IAttributeRepository`, `IAttributeGroupRepository`, `IAttributeValueRepository`, `IAttributeTemplateRepository`, `ITemplateAttributeBindingRepository`, `IProductAttributeValueRepository`, `IMediaAssetRepository`, `IImageBackendClient`

### BaseRepository[EntityType, ModelType]
- **Purpose:** Data Mapper base that converts between ORM models and domain entities
- **File:** `backend/src/modules/catalog/infrastructure/repositories/base.py`
- **Pattern:** Subclasses declare `model_class` via class argument, implement `_to_domain()` and `_to_orm()` hooks
- **Features:** Generic `_field_exists()` helper for uniqueness checks; `_translate_integrity_error()` hook for domain exception mapping; `get_for_update()` with `SELECT FOR UPDATE`

### Command / Query Handler
- **Purpose:** Single-responsibility use case orchestrators
- **Examples:** `backend/src/modules/catalog/application/commands/` (47 command handlers), `backend/src/modules/catalog/application/queries/` (23 query handlers)
- **Catalog command handlers include:** CRUD for brands, categories, attributes, attribute values, attribute templates, template bindings, products, variants, SKUs, media assets, plus bulk operations (bulk_create_brands, bulk_create_categories, bulk_create_attributes, bulk_add_attribute_values, bulk_assign_product_attributes), matrix generation (generate_sku_matrix), and reordering operations

### Dishka Provider
- **Purpose:** DI registration mapping interfaces to implementations at specific scopes
- **Composition root:** `backend/src/bootstrap/container.py` -- assembles 18 providers
- **Module providers:** `backend/src/modules/catalog/presentation/dependencies.py` contains 8 Provider classes: `CategoryProvider`, `BrandProvider`, `AttributeGroupProvider`, `AttributeProvider`, `AttributeValueProvider`, `AttributeTemplateProvider`, `StorefrontCatalogProvider`, `ProductProvider`, `MediaAssetProvider`
- **Scope:** `Scope.APP` for singletons (engine, redis, settings); `Scope.REQUEST` for per-request (session, handlers, repos)

### RequirePermission
- **Purpose:** Declarative route-level authorization via session permission checking
- **File:** `backend/src/modules/identity/presentation/dependencies.py`
- **Pattern:** Callable class used as FastAPI dependency: `Depends(RequirePermission(codename="catalog:manage"))`
- **Mechanism:** Resolves permissions via cache-aside with Redis (TTL 300s) + recursive CTE fallback for RBAC hierarchy

### CamelModel
- **Purpose:** Pydantic base for all request/response schemas
- **File:** `backend/src/shared/schemas.py`
- **Pattern:** `ConfigDict(populate_by_name=True, alias_generator=to_camel)` -- auto-converts `snake_case` Python fields to `camelCase` JSON

## Entry Points

**Web API (ASGI):**
- Location: `backend/main.py` -> `backend/src/bootstrap/web.py` -> `create_app()`
- Triggers: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Responsibilities: Creates FastAPI app, wires CORS/middleware/exception handlers/routers, sets up Dishka DI, manages lifespan (broker startup/shutdown)
- Health check: `GET /health` returns `{"status": "ok", "environment": "..."}`

**Background Worker:**
- Location: `backend/src/bootstrap/worker.py`
- Triggers: `taskiq worker src.bootstrap.worker:broker`
- Responsibilities: Initializes DI container -> registers DLQ middleware -> imports task modules (consumers) -> processes queued tasks from RabbitMQ
- Critical: Import order is enforced (container -> dishka -> tasks); task imports use `# noqa` to prevent auto-formatter reordering

**Scheduler (Beat):**
- Location: `backend/src/bootstrap/scheduler.py`
- Triggers: `taskiq scheduler src.bootstrap.scheduler:scheduler`
- Responsibilities: Dispatches outbox relay every minute, outbox pruning daily at 03:00 UTC
- Requirement: Exactly ONE scheduler instance (multiple instances cause duplicate dispatches)

**Image Backend API:**
- Location: `image_backend/main.py` -> `image_backend/src/bootstrap/web.py`
- Triggers: Uvicorn ASGI server (separate process, port 8001)
- Responsibilities: Image upload, processing (resize/crop/WebP), S3 storage management
- Auth: API key via `INTERNAL_API_KEY` header

**Telegram Bot:**
- Location: `backend/src/bot/factory.py`
- Triggers: Webhook or long-polling via aiogram Dispatcher
- Responsibilities: User-facing Telegram bot with FSM, inline keyboards, throttling

## Error Handling

**Strategy:** Typed exception hierarchy with centralized HTTP mapping

**Exception Hierarchy (`backend/src/shared/exceptions.py`):**
```
AppException (base, default 500)
├── NotFoundError (404)
├── UnauthorizedError (401)
├── ForbiddenError (403)
├── ConflictError (409)
├── ValidationError (400)
└── UnprocessableEntityError (422)
```

**Domain Exception Naming:** `{Entity}{Issue}Error` -- e.g., `BrandHasProductsError`, `InvalidStatusTransitionError`, `CategoryMaxDepthError`, `DuplicateVariantCombinationError`

**Domain Exception Contract:**
```python
class BrandSlugConflictError(ConflictError):
    def __init__(self, slug: str):
        super().__init__(
            message=f"Brand with slug '{slug}' already exists",
            error_code="BRAND_SLUG_CONFLICT",
            details={"slug": slug},
        )
```

**Handler Chain (`backend/src/api/exceptions/handlers.py`):**
1. `AppException` -> structured JSON with `error_code`, `message`, `details`, `request_id`
2. `RequestValidationError` (Pydantic) -> 422 with per-field error details
3. `HTTPException` (Starlette) -> JSON envelope with HTTP status
4. `Exception` (catch-all) -> 500 with generic message, full traceback logged

**UoW Integrity Error Mapping (`backend/src/infrastructure/database/uow.py`):**
- sqlstate `23503` (foreign key violation) -> `UnprocessableEntityError`
- Other integrity errors -> `ConflictError`

**Response Envelope:**
```json
{
  "error": {
    "code": "BRAND_SLUG_CONFLICT",
    "message": "Brand with slug 'nike' already exists",
    "details": {"slug": "nike"},
    "request_id": "abc-123-def"
  }
}
```

## Cross-Cutting Concerns

**Logging:**
- structlog with contextvars for request-scoped fields (request_id, identity_id, session_id)
- `ILogger` interface (`backend/src/shared/interfaces/logger.py`) injected via Dishka
- Handler pattern: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Access logging middleware (`backend/src/api/middlewares/logger.py`)
- TaskIQ middleware for background task logging (`backend/src/infrastructure/logging/taskiq_middleware.py`)
- DLQ middleware for failed task persistence (`backend/src/infrastructure/logging/dlq_middleware.py`)

**Validation (Three Layers):**
- Input: Pydantic schemas in presentation layer with `CamelModel` aliasing
- Domain: Entity `create()` and `update()` methods perform business rule validation (slug format via `SLUG_RE`, i18n completeness via `REQUIRED_LOCALES`, status FSM transitions, search_weight range 1-10)
- Database: Constraint-level validation (unique indexes, FK constraints, check constraints) caught by UoW and re-raised as domain exceptions

**Authentication:**
- JWT Bearer tokens with `sub` (identity_id) and `sid` (session_id) claims
- `get_auth_context()` dependency in `backend/src/modules/identity/presentation/dependencies.py`
- Token version validation against database (`tv` claim vs `identity.token_version`)
- Telegram authentication via `initData` validation (`backend/src/infrastructure/security/telegram.py`)

**Authorization:**
- RBAC with recursive role hierarchy
- `RequirePermission` callable dependency checks session permissions via cache-aside resolver
- Redis cache with TTL 300s; PostgreSQL recursive CTE fallback
- Permission codenames follow `module:action` pattern: `catalog:manage`, `catalog:read`, `identity:manage`, `supplier:manage`

**Request Context:**
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing
- Request ID included in all error responses

**Database Configuration (`backend/src/infrastructure/database/provider.py`):**
- Connection pool: `pool_size=15`, `max_overflow=10`, `pool_timeout=30s`, `pool_recycle=3600s`
- Session: `autoflush=False`, `expire_on_commit=False`
- Server settings: `statement_timeout=30000`, `idle_in_transaction_session_timeout=60000`, timezone UTC
- Isolation level: `READ COMMITTED`
- Naming conventions for constraints in `backend/src/infrastructure/database/base.py`: `ix_`, `uq_`, `ck_`, `fk_`, `pk_` prefixes

---

*Architecture analysis: 2026-03-28*
