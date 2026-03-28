# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
loyality/
├── backend/                        # Main Python backend (FastAPI + TaskIQ)
│   ├── alembic/                    # Database migrations
│   │   └── versions/2026/03/       # Migration files (YYYY/MM structure)
│   ├── docs/                       # Backend-specific documentation
│   │   ├── api/                    # API flow docs
│   │   ├── cdek_api/               # CDEK delivery API reference
│   │   ├── russian_post_api/       # Russian Post API reference
│   │   └── yandex_delivery_api/    # Yandex Delivery API reference
│   ├── scripts/                    # Utility scripts
│   ├── seed/                       # Seed data loaders
│   │   ├── attributes/             # Attribute seed data
│   │   ├── brands/                 # Brand seed data
│   │   ├── categories/             # Category seed data
│   │   ├── geo/                    # Country/currency seed data
│   │   └── products/               # Product seed data
│   ├── src/                        # Application source code
│   │   ├── api/                    # HTTP gateway (routers, middleware, exceptions)
│   │   ├── bootstrap/              # App composition root (web, worker, scheduler, config)
│   │   ├── bot/                    # Telegram bot (Aiogram)
│   │   ├── infrastructure/         # Shared infrastructure (DB, cache, security, outbox, logging)
│   │   ├── modules/                # Bounded contexts
│   │   │   ├── catalog/            # Product catalog (brands, categories, attributes, products, SKUs, media)
│   │   │   ├── geo/                # Geography (countries, currencies, languages, subdivisions)
│   │   │   ├── identity/           # IAM (auth, RBAC, sessions, roles, invitations)
│   │   │   ├── supplier/           # Supplier management
│   │   │   └── user/               # User profiles (customers, staff members)
│   │   └── shared/                 # Shared kernel (interfaces, exceptions, pagination)
│   └── tests/                      # Test suite
│       ├── architecture/           # Architectural boundary tests (pytest-archon)
│       ├── e2e/                    # End-to-end API tests
│       ├── factories/              # Test data factories
│       ├── fakes/                  # Fake implementations for unit tests
│       ├── integration/            # Integration tests (DB-backed)
│       ├── load/                   # Load test scenarios
│       └── unit/                   # Unit tests (mirror src/ structure)
├── image_backend/                  # Image processing microservice (FastAPI)
│   ├── alembic/                    # Separate migration chain
│   ├── src/                        # Same Clean Architecture as main backend
│   │   ├── api/                    # HTTP gateway
│   │   ├── bootstrap/              # Composition root
│   │   ├── infrastructure/         # DB, cache, storage adapters
│   │   ├── modules/storage/        # Single bounded context: media storage
│   │   └── shared/                 # Shared kernel
│   └── tests/                      # Unit + integration tests
├── frontend/
│   ├── admin/                      # Admin panel (Next.js 16, JSX, Tailwind)
│   │   ├── src/
│   │   │   ├── app/                # Next.js App Router pages + API routes
│   │   │   ├── assets/icons/       # SVG icons (imported via @svgr/webpack)
│   │   │   ├── components/         # React components
│   │   │   ├── data/               # Static data
│   │   │   ├── hooks/              # Custom React hooks
│   │   │   ├── lib/                # Utilities (api-client, auth, dayjs, etc.)
│   │   │   └── services/           # Service modules (API call wrappers)
│   │   └── public/                 # Static assets
│   └── main/                       # Customer Telegram Mini App (Next.js 16, TSX, Tailwind)
│       ├── app/                    # Next.js App Router pages + API routes
│       ├── components/             # React components
│       │   ├── blocks/             # Feature-specific component groups
│       │   ├── ios/                # iOS-specific fixes
│       │   ├── layout/             # Header, Footer, Layout
│       │   ├── providers/          # Context providers (StoreProvider)
│       │   └── ui/                 # Reusable UI primitives
│       ├── lib/                    # Shared utilities
│       │   ├── auth/               # Cookie helpers, auth logic
│       │   ├── format/             # Formatters (price, date, image URLs)
│       │   ├── hooks/              # Custom hooks
│       │   ├── store/              # Redux store + RTK Query api
│       │   ├── telegram/           # Telegram WebApp SDK hooks + provider
│       │   └── types/              # TypeScript type definitions
│       ├── public/                 # Static assets (fonts, icons, images)
│       └── scripts/                # Build/utility scripts
├── postman/                        # Postman collections and environments
├── docs/                           # Root-level documentation
│   └── superpowers/                # Feature specs and plans
└── .planning/                      # GSD planning documents
    └── codebase/                   # Codebase analysis (this file)
```

## Directory Purposes

**`backend/src/modules/{module}/`** (Bounded Context Module):
- Purpose: Self-contained business capability following Clean Architecture
- Internal structure (consistent across all modules):
  ```
  {module}/
  ├── domain/
  │   ├── entities.py           # Domain entities (attrs dataclasses + AggregateRoot)
  │   ├── value_objects.py      # Enums, value types, validation constants
  │   ├── events.py             # Domain event dataclasses
  │   ├── exceptions.py         # Domain-specific exceptions
  │   ├── interfaces.py         # Repository port interfaces (ABC)
  │   ├── constants.py          # Business rule constants
  │   └── services.py           # Domain services (if needed)
  ├── application/
  │   ├── commands/              # One file per command handler
  │   │   └── create_brand.py   # Contains Command dataclass + Handler class
  │   ├── queries/               # One file per query handler
  │   │   ├── list_brands.py    # Contains Query dataclass + Handler class
  │   │   └── read_models.py    # Pydantic read models for CQRS read side
  │   └── consumers/             # Cross-module event consumers (TaskIQ tasks)
  ├── infrastructure/
  │   ├── models.py              # SQLAlchemy ORM models
  │   ├── repositories/          # Repository implementations (Data Mapper)
  │   │   └── base.py           # Generic BaseRepository with _to_domain/_to_orm
  │   ├── provider.py            # Dishka DI provider (for modules that use it)
  │   └── {service}.py          # External API clients, query services
  ├── presentation/
  │   ├── router_*.py            # FastAPI routers (one per aggregate/resource)
  │   ├── schemas.py             # Pydantic request/response schemas
  │   ├── dependencies.py        # Dishka Provider classes for all handlers
  │   ├── mappers.py             # DTO mapping helpers
  │   └── update_helpers.py      # Partial-update command builders
  └── management/                # CLI/management commands (optional)
      └── create_admin.py        # Bootstrap scripts
  ```
- Key files per module:
  - Catalog: `backend/src/modules/catalog/` -- largest module with 11+ routers, 40+ commands
  - Identity: `backend/src/modules/identity/` -- auth, RBAC, sessions, staff invitations
  - User: `backend/src/modules/user/` -- customer + staff profiles, referral codes
  - Geo: `backend/src/modules/geo/` -- read-only reference data (countries, currencies)
  - Supplier: `backend/src/modules/supplier/` -- supplier CRUD

**`backend/src/infrastructure/`** (Shared Infrastructure):
- Purpose: Cross-cutting infrastructure shared by all modules
- `database/base.py`: SQLAlchemy `DeclarativeBase` definition
- `database/provider.py`: Dishka provider for AsyncEngine, sessionmaker, session, IUnitOfWork
- `database/uow.py`: UnitOfWork implementation (Outbox event extraction + commit)
- `database/registry.py`: ORM model registry for Alembic autogenerate
- `database/models/outbox.py`: OutboxMessage ORM model
- `database/models/failed_task.py`: DLQ failed task ORM model
- `cache/redis.py`: Redis cache service implementation
- `cache/provider.py`: Dishka provider for Redis
- `security/jwt.py`: JWT token encode/decode
- `security/password.py`: Password hashing (bcrypt/argon2)
- `security/authorization.py`: PermissionResolver (cache-aside Redis + recursive CTE)
- `security/telegram.py`: Telegram initData validation
- `outbox/relay.py`: Outbox polling publisher (FOR UPDATE SKIP LOCKED)
- `outbox/tasks.py`: TaskIQ scheduled tasks (relay + pruning) + event handler registry
- `logging/adapter.py`: structlog adapter implementing ILogger
- `logging/dlq_middleware.py`: TaskIQ middleware for dead letter queue persistence

**`backend/src/api/`** (HTTP Gateway):
- Purpose: Cross-cutting HTTP concerns
- `router.py`: Root APIRouter that includes all module routers under `/catalog`, `/auth`, etc.
- `exceptions/handlers.py`: Global exception -> JSON error envelope mapping
- `middlewares/logger.py`: Access logging middleware with correlation ID binding
- `dependencies/`: Shared FastAPI dependencies

**`backend/src/shared/`** (Shared Kernel):
- Purpose: Interfaces and base types used by all modules
- `interfaces/entities.py`: `IBase`, `DomainEvent`, `AggregateRoot`
- `interfaces/uow.py`: `IUnitOfWork` protocol
- `interfaces/logger.py`: `ILogger` protocol
- `interfaces/cache.py`: `ICacheService` protocol
- `interfaces/security.py`: `ITokenProvider`, `IPermissionResolver` protocols
- `interfaces/auth.py`: `AuthContext` dataclass
- `exceptions.py`: `AppException` hierarchy (NotFoundError, ConflictError, etc.)
- `pagination.py`: Generic `paginate()` helper for query handlers
- `schemas.py`: Shared Pydantic schemas
- `context.py`: Request-scoped context variables (request_id)

**`backend/src/bot/`** (Telegram Bot):
- Purpose: Aiogram-based Telegram bot
- `factory.py`: Bot + Dispatcher creation, middleware chain, router registration
- `handlers/`: Message/command handlers organized by feature
- `callbacks/`: Callback query handlers
- `keyboards/`: Inline and reply keyboard builders
- `middlewares/`: Bot-level middleware (logging, throttling, user identification)
- `filters/`: Custom Aiogram filters
- `states/`: FSM state definitions

**`frontend/main/`** (Customer Mini App):
- Purpose: Telegram Mini App for customers (shopping, orders, profiles)
- `app/`: Next.js App Router -- pages and API routes
- `app/api/backend/[...path]/route.ts`: Catch-all proxy to Python backend (key architectural component)
- `app/api/auth/`: Auth API routes (telegram login, refresh, logout)
- `app/api/dadata/`: DaData address suggestion proxy routes
- `components/blocks/`: Feature-grouped components (cart, catalog, favorites, product, profile, search, promo, reviews, telegram)
- `components/ui/`: Reusable primitives (Button, BottomSheet)
- `components/layout/`: Layout components (Header, Footer, Layout)
- `lib/store/`: Redux Toolkit store with RTK Query (`api.ts`, `authSlice.ts`, `store.ts`, `hooks.ts`)
- `lib/telegram/`: Telegram WebApp SDK wrapper with 25+ hooks (useTelegram, useMainButton, useHaptic, etc.)
- `lib/auth/`: Cookie management for auth tokens (`cookie-helpers.ts`, `cookies.ts`)
- `lib/types/`: TypeScript type definitions (`api.ts`, `user.ts`, `catalog.ts`, `auth.ts`, `ui.ts`)
- `lib/format/`: Formatters (`price.ts`, `date.ts`, `product-image.ts`, `brand-image.ts`, `cn.ts`)

**`frontend/admin/`** (Admin Panel):
- Purpose: Internal admin dashboard for managing products, orders, users, settings
- `src/app/admin/`: Admin pages (products, orders, users, reviews, returns, settings)
- `src/app/admin/settings/`: Settings sub-pages (brands, categories, pricing-formulas, promocodes, referrals, roles, staff, suppliers)
- `src/app/admin/products/add/details/[...slug]/`: Product creation wizard
- `src/app/api/`: BFF proxy routes to Python backend (auth, catalog, categories, admin/identities, admin/roles)
- `src/components/admin/`: Admin-specific components (products/, orders/, reviews/, settings/, users/)
- `src/components/ui/`: Shared UI components
- `src/services/`: API call wrappers per resource (`products.js`, `orders.js`, `staff.js`, `categories.js`, `brands.js`, `attributes.js`, `suppliers.js`, `users.js`, `promocodes.js`, `referrals.js`, `reviews.js`)
- `src/lib/api-client.js`: Base fetch wrapper for backend calls (`backendFetch()`)
- `src/lib/auth.js`: Auth utilities
- `src/lib/constants.js`: App constants
- `src/lib/utils.js`: General utilities
- `src/lib/dayjs.js`: dayjs date library configuration
- Note: Uses JSX (not TypeScript) unlike the main frontend

## Key File Locations

**Entry Points:**
- `backend/src/bootstrap/web.py`: FastAPI app factory (`create_app()`)
- `backend/src/bootstrap/worker.py`: TaskIQ worker entry point (critical init order)
- `backend/src/bootstrap/scheduler.py`: TaskIQ Beat scheduler
- `backend/src/bootstrap/config.py`: Pydantic Settings (env vars)
- `backend/src/bootstrap/container.py`: Dishka container assembly (composition root)
- `backend/src/api/router.py`: Root API router (all module routers aggregated here)
- `image_backend/src/bootstrap/web.py`: Image backend app factory
- `frontend/main/app/layout.tsx`: Main frontend root layout
- `frontend/admin/src/app/layout.jsx`: Admin frontend root layout

**Configuration:**
- `backend/src/bootstrap/config.py`: All backend settings (`Settings` class)
- `backend/alembic.ini`: Alembic config
- `image_backend/src/bootstrap/config.py`: Image backend settings
- `frontend/main/package.json`: Main frontend dependencies
- `frontend/admin/package.json`: Admin frontend dependencies
- `frontend/main/middleware.ts`: Next.js edge middleware (security headers, CSRF)

**Core Logic:**
- `backend/src/modules/catalog/domain/entities.py`: Product, Brand, Category, SKU, Variant, Attribute entities
- `backend/src/modules/identity/domain/entities.py`: Identity, Session, Role entities
- `backend/src/modules/user/domain/entities.py`: Customer, StaffMember entities
- `backend/src/infrastructure/database/uow.py`: UnitOfWork with Outbox event persistence
- `backend/src/infrastructure/outbox/relay.py`: Outbox relay polling publisher
- `backend/src/infrastructure/security/authorization.py`: RBAC permission resolver

**Testing:**
- `backend/tests/architecture/test_boundaries.py`: Architectural fitness functions
- `backend/tests/unit/`: Unit tests mirroring `src/` structure
- `backend/tests/integration/`: Integration tests with real DB
- `backend/tests/factories/`: Test data factories
- `backend/tests/fakes/`: Fake implementations for unit testing

## Naming Conventions

**Files (Backend - Python):**
- Modules: `snake_case.py` (e.g., `create_brand.py`, `router_brands.py`)
- One command handler per file: `{verb}_{noun}.py` (e.g., `create_brand.py`, `delete_product.py`, `change_product_status.py`)
- One query handler per file: `{verb}_{noun}.py` (e.g., `list_brands.py`, `get_brand.py`)
- Routers: `router_{resource}.py` (e.g., `router_brands.py`, `router_products.py`)
- ORM models: `models.py` within each module's infrastructure
- Read models: `read_models.py` within each module's `application/queries/`

**Files (Frontend - TypeScript/JSX):**
- Components: `PascalCase.tsx` or `PascalCase.jsx` (e.g., `ProductCard.tsx`, `OrderCard.jsx`)
- Hooks: `camelCase.ts` prefixed with `use` (e.g., `useCart.ts`, `useTelegram.ts`)
- API routes: `route.ts` or `route.js` (Next.js convention)
- Pages: `page.tsx` or `page.jsx` (Next.js convention)
- CSS modules: `{name}.module.css`

**Directories:**
- Backend modules: `snake_case` (e.g., `catalog/`, `identity/`)
- Backend layers: `domain/`, `application/`, `infrastructure/`, `presentation/`
- Frontend components: `PascalCase` for component-specific dirs, `kebab-case` for route segments

**Classes:**
- Domain entities: `PascalCase` (e.g., `Brand`, `Product`, `Identity`)
- Command handlers: `{Verb}{Noun}Handler` (e.g., `CreateBrandHandler`)
- Query handlers: `{Verb}{Noun}Handler` or `List{Noun}Handler` (e.g., `ListBrandsHandler`, `GetBrandHandler`)
- Commands: `{Verb}{Noun}Command` (e.g., `CreateBrandCommand`)
- Queries: `{Verb}{Noun}Query` or `List{Noun}Query` (e.g., `ListBrandsQuery`)
- Repositories: `{Entity}Repository` (e.g., `BrandRepository`)
- Interfaces: `I{Name}` prefix (e.g., `IBrandRepository`, `IUnitOfWork`, `ILogger`)
- DI Providers: `{Feature}Provider` (e.g., `CategoryProvider`, `BrandProvider`)
- Exceptions: descriptive with `Error` suffix (e.g., `BrandSlugConflictError`, `CategoryMaxDepthError`)

## Where to Add New Code

**New Backend Module (Bounded Context):**
1. Create `backend/src/modules/{new_module}/` with `domain/`, `application/`, `infrastructure/`, `presentation/` directories
2. Define entities in `domain/entities.py` inheriting from `AggregateRoot`
3. Define repository interfaces in `domain/interfaces.py` extending `ICatalogRepository[T]` or custom ABC
4. Create command handlers in `application/commands/` (one file per command)
5. Create query handlers in `application/queries/` (one file per query, with `read_models.py`)
6. Implement ORM models in `infrastructure/models.py`
7. Implement repositories in `infrastructure/repositories/`
8. Register DI providers in `presentation/dependencies.py`
9. Create FastAPI routers in `presentation/router_*.py`
10. Add routers to `backend/src/api/router.py`
11. Add DI providers to `backend/src/bootstrap/container.py`
12. Register ORM models in `backend/src/infrastructure/database/registry.py`
13. Add architectural boundary test parameters in `backend/tests/architecture/test_boundaries.py`
14. Generate Alembic migration: `alembic revision --autogenerate -m "description"`

**New Command Handler (Write Operation):**
1. Create `backend/src/modules/{module}/application/commands/{verb}_{noun}.py`
2. Define frozen `@dataclass` Command and Result classes
3. Create Handler class with `__init__(self, repo: IRepo, uow: IUnitOfWork, logger: ILogger)`
4. Implement `async def handle(self, command: Command) -> Result`
5. Register handler in `presentation/dependencies.py` Provider: `provide(HandlerClass, scope=Scope.REQUEST)`
6. Add route in appropriate `presentation/router_*.py` using `FromDishka[HandlerClass]`

**New Query Handler (Read Operation):**
1. Create `backend/src/modules/{module}/application/queries/{verb}_{noun}.py`
2. Define frozen `@dataclass` Query class
3. Create Handler class with `__init__(self, session: AsyncSession, logger: ILogger)` (no UoW)
4. Query ORM models directly via SQLAlchemy `select()`, use `paginate()` helper
5. Return Pydantic read model from `read_models.py`
6. Register in DI provider and add route as above

**New Domain Event + Consumer:**
1. Define event in `backend/src/modules/{source}/domain/events.py` as `@dataclass` inheriting `DomainEvent`
2. Emit event in the source aggregate: `self.add_domain_event(MyEvent(...))`
3. Create consumer in `backend/src/modules/{target}/application/consumers/`
4. Register consumer task import in `backend/src/bootstrap/worker.py`
5. Register event handler in `backend/src/infrastructure/outbox/tasks.py`

**New Frontend Page (Main):**
1. Create `frontend/main/app/{route}/page.tsx`
2. Create feature components in `frontend/main/components/blocks/{feature}/`
3. Add RTK Query endpoints in `frontend/main/lib/store/api.ts` if calling backend
4. Add types in `frontend/main/lib/types/`

**New Frontend Page (Admin):**
1. Create `frontend/admin/src/app/admin/{route}/page.jsx`
2. Create components in `frontend/admin/src/components/admin/{feature}/`
3. Add API proxy route in `frontend/admin/src/app/api/` if needed
4. Add service wrapper in `frontend/admin/src/services/{resource}.js`

**New API Route (Frontend BFF Proxy):**
- Main: `frontend/main/app/api/{path}/route.ts` (TypeScript)
- Admin: `frontend/admin/src/app/api/{path}/route.js` (JavaScript)
- Most backend calls go through the catch-all proxy (`frontend/main/app/api/backend/[...path]/route.ts`), so explicit routes are only needed for auth or special server-side logic

## Special Directories

**`backend/alembic/versions/`:**
- Purpose: Database migration files
- Generated: Yes (via `alembic revision --autogenerate`)
- Committed: Yes
- Structure: `YYYY/MM/` subdirectories

**`backend/seed/`:**
- Purpose: Reference data population scripts (categories, brands, attributes, geo)
- Generated: No (manually maintained)
- Committed: Yes

**`backend/tests/fakes/`:**
- Purpose: In-memory fake implementations of repository interfaces for unit testing
- Generated: No
- Committed: Yes

**`frontend/main/.next/` and `frontend/admin/.next/`:**
- Purpose: Next.js build output and dev cache
- Generated: Yes
- Committed: No (should be in .gitignore)

**`backend/.venv/` and `image_backend/.venv/`:**
- Purpose: Python virtual environments
- Generated: Yes
- Committed: No

**`backend/src/bot/`:**
- Purpose: Telegram bot (Aiogram) -- `factory.py` is implemented, `bootstrap/bot.py` is empty
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-28*
