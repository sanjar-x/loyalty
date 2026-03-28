# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
loyality/
├── backend/                    # Main backend API (Python/FastAPI)
│   ├── main.py                 # ASGI entry point
│   ├── pyproject.toml          # Dependencies and tool config
│   ├── Makefile                # Dev commands (test, lint, format)
│   ├── Dockerfile              # Production container
│   ├── docker-compose.yml      # Local infrastructure (Postgres, Redis, RabbitMQ, MinIO)
│   ├── alembic/                # Database migrations
│   │   ├── alembic.ini
│   │   └── versions/2026/03/   # Migration files
│   ├── seed/                   # Data seeding scripts
│   │   ├── attributes/
│   │   ├── brands/
│   │   ├── categories/
│   │   ├── geo/
│   │   └── products/
│   ├── scripts/                # Utility scripts
│   ├── src/                    # Application source code
│   │   ├── api/                # Cross-cutting API concerns
│   │   │   ├── router.py       # Root router aggregating all modules
│   │   │   ├── dependencies/   # Shared FastAPI dependencies (auth.py)
│   │   │   ├── exceptions/     # Global exception handlers
│   │   │   └── middlewares/    # HTTP middleware (access logger)
│   │   ├── bootstrap/          # Composition root
│   │   │   ├── web.py          # FastAPI app factory
│   │   │   ├── worker.py       # TaskIQ worker entry
│   │   │   ├── scheduler.py    # TaskIQ Beat entry
│   │   │   ├── container.py    # Dishka IoC assembly
│   │   │   ├── config.py       # Pydantic Settings
│   │   │   ├── broker.py       # RabbitMQ broker config
│   │   │   ├── logger.py       # structlog setup
│   │   │   └── bot.py          # Telegram bot entry (empty)
│   │   ├── bot/                # Telegram bot (aiogram)
│   │   │   ├── factory.py
│   │   │   ├── callbacks/
│   │   │   ├── filters/
│   │   │   ├── handlers/
│   │   │   ├── keyboards/
│   │   │   ├── middlewares/
│   │   │   └── states/
│   │   ├── infrastructure/     # Shared infrastructure adapters
│   │   │   ├── cache/          # Redis cache (provider.py, redis.py)
│   │   │   ├── database/       # SQLAlchemy setup
│   │   │   │   ├── base.py     # Declarative base with naming conventions
│   │   │   │   ├── registry.py # ORM model registry for Alembic
│   │   │   │   ├── provider.py # Dishka DB provider (engine, session, UoW)
│   │   │   │   ├── uow.py     # UnitOfWork with Outbox integration
│   │   │   │   └── models/    # Shared ORM models (outbox, failed_task)
│   │   │   ├── logging/       # structlog provider + TaskIQ middleware
│   │   │   ├── outbox/        # Outbox relay + pruning + tasks
│   │   │   └── security/      # JWT, password hashing, authorization, Telegram auth
│   │   ├── modules/           # Bounded contexts
│   │   │   ├── catalog/       # Product catalog (brands, categories, attributes, products, SKUs, media)
│   │   │   ├── identity/      # Authentication, RBAC, sessions, staff invitations
│   │   │   ├── user/          # Customer and staff member profiles
│   │   │   ├── supplier/      # Supplier management
│   │   │   └── geo/           # Countries, currencies, languages, subdivisions
│   │   └── shared/            # Shared kernel
│   │       ├── interfaces/    # Port definitions (entities, UoW, cache, auth, security, logger)
│   │       ├── exceptions.py  # Exception hierarchy
│   │       ├── pagination.py  # Generic paginate helper
│   │       ├── schemas.py     # Shared Pydantic schemas
│   │       └── context.py     # Request-scoped context variables
│   └── tests/                 # Test suite
│       ├── conftest.py        # Global fixtures
│       ├── architecture/      # Architectural fitness functions
│       ├── unit/              # Domain-layer pure logic tests
│       ├── integration/       # Application + infrastructure tests
│       ├── e2e/               # HTTP round-trip tests
│       ├── load/              # Locust load tests
│       ├── factories/         # Test data factories (polyfactory)
│       └── fakes/             # Fake implementations for testing
│
├── image_backend/              # Image processing microservice (Python/FastAPI)
│   ├── main.py                 # ASGI entry point
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── alembic/                # Separate migration chain
│   ├── src/                    # Same layered structure as backend
│   │   ├── api/
│   │   ├── bootstrap/
│   │   ├── infrastructure/
│   │   ├── modules/
│   │   │   └── storage/       # Single bounded context
│   │   │       ├── domain/
│   │   │       ├── application/
│   │   │       │   ├── commands/
│   │   │       │   ├── consumers/
│   │   │       │   └── queries/
│   │   │       ├── infrastructure/
│   │   │       └── presentation/
│   │   └── shared/
│   └── tests/
│       ├── integration/
│       └── unit/
│
├── frontend/
│   ├── admin/                  # Admin panel (Next.js, JSX)
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── app/            # Next.js App Router
│   │   │   │   ├── layout.jsx
│   │   │   │   ├── admin/      # Admin pages
│   │   │   │   │   ├── products/
│   │   │   │   │   ├── orders/
│   │   │   │   │   ├── returns/
│   │   │   │   │   ├── reviews/
│   │   │   │   │   ├── users/
│   │   │   │   │   └── settings/
│   │   │   │   ├── api/        # BFF proxy routes
│   │   │   │   │   ├── auth/
│   │   │   │   │   ├── admin/
│   │   │   │   │   ├── catalog/
│   │   │   │   │   ├── categories/
│   │   │   │   │   └── suppliers/
│   │   │   │   └── login/
│   │   │   ├── components/
│   │   │   │   ├── admin/      # Feature-specific components
│   │   │   │   └── ui/         # Reusable UI components (Badge, Modal, Pagination, etc.)
│   │   │   ├── services/       # API service modules (brands.js, products.js, etc.)
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── lib/            # Utilities (api-client.js, auth.js, constants.js)
│   │   │   ├── data/           # Static data
│   │   │   └── assets/
│   │   └── public/
│   │
│   └── main/                   # Customer-facing app (Next.js, TypeScript)
│       ├── package.json
│       ├── app/                # Next.js App Router
│       │   ├── layout.tsx
│       │   ├── api/            # BFF proxy + auth routes
│       │   │   ├── backend/[...path]/route.ts  # Catch-all backend proxy
│       │   │   ├── auth/
│       │   │   └── dadata/
│       │   ├── catalog/
│       │   ├── product/
│       │   ├── checkout/
│       │   ├── favorites/
│       │   ├── profile/
│       │   ├── search/
│       │   ├── invite-friends/
│       │   └── promo/
│       ├── components/
│       │   ├── blocks/         # Feature-specific (cart, catalog, product, profile, etc.)
│       │   ├── ui/             # Reusable (BottomSheet, Button)
│       │   ├── layout/         # Layout components
│       │   ├── providers/      # React context providers
│       │   └── ios/            # iOS-specific components
│       ├── lib/
│       │   ├── auth/           # Cookie helpers
│       │   ├── store/          # Redux store (api.ts, authSlice.ts, store.ts)
│       │   ├── hooks/          # Custom hooks
│       │   ├── format/         # Formatting utilities
│       │   ├── telegram/       # Telegram Mini App integration
│       │   └── types/          # TypeScript type definitions
│       └── public/
│
├── docs/                       # Project-level documentation
└── postman/                    # Postman API collections
```

## Directory Purposes

**`backend/src/modules/{module}/`:**
- Purpose: Each module is a DDD bounded context with four internal layers
- Contains: `domain/` (entities, VOs, events, exceptions, interfaces), `application/` (commands, queries, consumers), `infrastructure/` (ORM models, repos, providers), `presentation/` (routers, schemas, dependencies)
- Key files vary by module; every module has `domain/entities.py`, `domain/interfaces.py`, `presentation/router*.py`

**`backend/src/bootstrap/`:**
- Purpose: Composition root -- the only place where all layers meet
- Contains: App factories, DI container assembly, configuration, broker/scheduler setup
- Key files: `web.py` (creates FastAPI app), `container.py` (assembles all providers), `config.py` (env settings)

**`backend/src/infrastructure/`:**
- Purpose: Shared infrastructure services used across all modules
- Contains: Database engine/session/UoW, Redis cache, outbox relay, security (JWT, passwords, RBAC), logging
- Key files: `database/uow.py` (UnitOfWork with outbox), `database/base.py` (shared ORM base), `outbox/relay.py` (event publisher)

**`backend/src/shared/`:**
- Purpose: Shared kernel with cross-cutting interfaces and utilities
- Contains: Port definitions (IUnitOfWork, ICacheService, ITokenProvider, IPermissionResolver), exception hierarchy, pagination, context vars
- Key files: `interfaces/entities.py` (AggregateRoot, DomainEvent), `exceptions.py` (AppException hierarchy)

**`frontend/admin/src/app/api/`:**
- Purpose: BFF (Backend-for-Frontend) proxy layer. Each route handler calls the backend API server-side, managing auth cookies.
- Contains: Next.js API route handlers that forward requests to the Python backend with JWT tokens from httpOnly cookies
- Key files: `auth/login/route.js`, `catalog/products/route.js`

**`frontend/main/app/api/backend/[...path]/`:**
- Purpose: Catch-all BFF proxy for the customer-facing app
- Contains: Single `route.ts` that proxies any path to the backend, attaching the JWT from cookies
- Key files: `route.ts`

## Key File Locations

**Entry Points:**
- `backend/main.py`: ASGI entry point, imports `create_app()` from bootstrap
- `backend/src/bootstrap/web.py`: FastAPI application factory (composition root)
- `backend/src/bootstrap/worker.py`: TaskIQ worker entry point
- `backend/src/bootstrap/scheduler.py`: TaskIQ scheduler entry point
- `image_backend/main.py`: Image backend ASGI entry point
- `frontend/admin/src/app/layout.jsx`: Admin panel root layout
- `frontend/main/app/layout.tsx`: Customer app root layout

**Configuration:**
- `backend/src/bootstrap/config.py`: All backend settings (Pydantic Settings, env-based)
- `backend/pyproject.toml`: Python dependencies, pytest, ruff, mypy config
- `backend/docker-compose.yml`: Local infrastructure services
- `backend/alembic.ini`: Alembic configuration
- `frontend/admin/package.json`: Admin frontend dependencies
- `frontend/main/package.json`: Main frontend dependencies

**Core Logic (by module):**
- `backend/src/modules/catalog/domain/entities.py`: Brand, Category, AttributeTemplate, Attribute, Product, ProductVariant, SKU, MediaAsset entities
- `backend/src/modules/catalog/domain/interfaces.py`: All catalog repository port interfaces
- `backend/src/modules/identity/domain/entities.py`: Identity, Session, Role, Permission entities
- `backend/src/modules/identity/domain/interfaces.py`: Identity repository ports
- `backend/src/modules/user/domain/entities.py`: Customer, StaffMember entities
- `backend/src/modules/supplier/domain/entities.py`: Supplier entity
- `backend/src/modules/geo/domain/entities.py`: Country, Currency, Language entities

**API Routing:**
- `backend/src/api/router.py`: Root router aggregating all module routers
- `backend/src/modules/catalog/presentation/router_products.py`: Product CRUD endpoints
- `backend/src/modules/identity/presentation/router_auth.py`: Authentication endpoints
- `backend/src/modules/identity/presentation/router_admin.py`: Admin RBAC endpoints

**Testing:**
- `backend/tests/conftest.py`: Global fixtures (testcontainers, DB setup)
- `backend/tests/unit/`: Domain-layer tests (no I/O)
- `backend/tests/integration/`: Application + infrastructure tests with real DB
- `backend/tests/e2e/`: HTTP round-trip tests
- `backend/tests/architecture/`: Architectural fitness functions (boundary enforcement)
- `backend/tests/factories/`: Test data factories (polyfactory)
- `backend/tests/fakes/`: Fake repository implementations

**Database:**
- `backend/src/infrastructure/database/base.py`: Shared `Base` declarative class
- `backend/src/infrastructure/database/registry.py`: ORM model registry for Alembic
- `backend/src/infrastructure/database/uow.py`: UnitOfWork implementation
- `backend/alembic/versions/2026/03/27_0911_19_7ce70774f240_init.py`: Initial migration

## Naming Conventions

**Files (Backend - Python):**
- Snake_case for all Python files: `create_brand.py`, `router_products.py`
- One command handler per file named after the action: `create_brand.py`, `update_category.py`, `delete_product.py`
- One query handler per file: `get_brand.py`, `list_products.py`
- Router files prefixed with `router_`: `router_products.py`, `router_brands.py`
- Domain files follow DDD conventions: `entities.py`, `value_objects.py`, `events.py`, `exceptions.py`, `interfaces.py`

**Files (Frontend - Admin - JSX):**
- PascalCase for components: `Badge.jsx`, `Modal.jsx`, `SearchInput.jsx`
- camelCase for hooks: `useAuth.jsx`, `useProductForm.js`
- camelCase for services: `brands.js`, `products.js`
- camelCase for lib utilities: `api-client.js`, `auth.js`

**Files (Frontend - Main - TypeScript):**
- PascalCase for components: `BottomSheet.tsx`, `Button.tsx`
- CSS Modules co-located: `Button.module.css`
- camelCase for store files: `authSlice.ts`, `api.ts`
- kebab-case for utility dirs: `cookie-helpers`

**Directories (Backend):**
- Plural for collections: `commands/`, `queries/`, `repositories/`, `models/`
- Singular for bounded contexts: `catalog/`, `identity/`, `user/`, `geo/`, `supplier/`
- Layer names: `domain/`, `application/`, `infrastructure/`, `presentation/`

**Directories (Frontend):**
- kebab-case for route segments: `invite-friends/`, `add-to-home/`
- Plural for collection dirs: `components/`, `hooks/`, `services/`
- Feature-based grouping in `components/blocks/`: `cart/`, `catalog/`, `product/`

## Where to Add New Code

**New Backend Bounded Context (Module):**
1. Create directory: `backend/src/modules/{module_name}/`
2. Add four layer directories: `domain/`, `application/`, `infrastructure/`, `presentation/`
3. Domain layer: Create `entities.py`, `interfaces.py`, `events.py`, `exceptions.py`, `value_objects.py`
4. Application layer: Create `commands/` and `queries/` directories
5. Infrastructure layer: Create `models.py` (ORM), `repositories/` directory, `provider.py` (Dishka)
6. Presentation layer: Create `router.py`, `schemas.py`, `dependencies.py`
7. Register ORM models in `backend/src/infrastructure/database/registry.py`
8. Add Dishka provider to `backend/src/bootstrap/container.py`
9. Include router in `backend/src/api/router.py`

**New Command Handler (Write Operation):**
1. Create file: `backend/src/modules/{module}/application/commands/{action}_{entity}.py`
2. Define frozen dataclass `{Action}{Entity}Command` with input fields
3. Define frozen dataclass `{Action}{Entity}Result` with output fields
4. Define handler class `{Action}{Entity}Handler` with `__init__` (inject repos, UoW, logger) and `async handle()` method
5. Register handler in the module's `presentation/dependencies.py` Dishka provider
6. Create router endpoint in `presentation/router_{entity}.py`

**New Query Handler (Read Operation):**
1. Create file: `backend/src/modules/{module}/application/queries/{action}_{entity}.py`
2. Define read model in `queries/read_models.py` if not existing
3. Define handler class with `__init__` (inject AsyncSession, logger) and `async handle()` method
4. Handler queries ORM models directly (no domain entities, no UoW)
5. Register in Dishka provider and add router endpoint

**New Frontend Page (Admin):**
1. Create directory: `frontend/admin/src/app/admin/{page_name}/`
2. Add `page.jsx` for the route
3. Create components in `frontend/admin/src/components/admin/{feature}/`
4. Add API proxy route if needed in `frontend/admin/src/app/api/`
5. Add service module in `frontend/admin/src/services/{feature}.js`

**New Frontend Page (Main - Customer):**
1. Create directory: `frontend/main/app/{page_name}/`
2. Add `page.tsx` for the route
3. Create feature components in `frontend/main/components/blocks/{feature}/`
4. Add RTK Query endpoints in `frontend/main/lib/store/api.ts`
5. Add types in `frontend/main/lib/types/`

**New Domain Event:**
1. Define event dataclass in `backend/src/modules/{module}/domain/events.py`
2. Set `aggregate_type` and `event_type` class defaults
3. Emit via `entity.add_domain_event(MyEvent(...))` in entity method or command handler
4. For cross-module consumption: create consumer in `backend/src/modules/{target_module}/application/consumers/`
5. Register consumer task in `backend/src/bootstrap/worker.py`

**Utilities / Shared Code:**
- Backend shared helpers: `backend/src/shared/`
- Backend shared interfaces: `backend/src/shared/interfaces/`
- Frontend admin shared components: `frontend/admin/src/components/ui/`
- Frontend main shared components: `frontend/main/components/ui/`
- Frontend main hooks: `frontend/main/lib/hooks/`

## Special Directories

**`backend/alembic/`:**
- Purpose: Database migration scripts (auto-generated by Alembic)
- Generated: Yes (via `alembic revision --autogenerate`)
- Committed: Yes

**`backend/seed/`:**
- Purpose: Data seeding scripts for development (attributes, brands, categories, geo, products)
- Generated: No (manually curated)
- Committed: Yes

**`backend/tests/factories/`:**
- Purpose: Test data factories using polyfactory for generating domain entities
- Generated: No
- Committed: Yes

**`backend/tests/fakes/`:**
- Purpose: In-memory fake implementations of repository interfaces for unit testing
- Generated: No
- Committed: Yes

**`frontend/*/public/`:**
- Purpose: Static assets (icons, images, fonts) served directly by Next.js
- Generated: No
- Committed: Yes

**`frontend/*/.next/`:**
- Purpose: Next.js build output
- Generated: Yes
- Committed: No (gitignored)

**`postman/`:**
- Purpose: Postman API collections for manual testing
- Generated: No
- Committed: Yes

**`backend/src/infrastructure/database/models/`:**
- Purpose: Shared ORM models not belonging to any bounded context (outbox_messages, failed_tasks)
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-28*
