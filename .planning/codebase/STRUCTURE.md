# Codebase Structure

**Analysis Date:** 2026-03-29

## Directory Layout

```
loyality/
├── backend/                        # Main API (Python, FastAPI, DDD)
│   ├── main.py                     # ASGI entry point (imports create_app)
│   ├── pyproject.toml              # Python project config (ruff, mypy, deps)
│   ├── uv.lock                     # uv lockfile
│   ├── Makefile                    # Dev shortcuts (test, lint, migrate)
│   ├── Dockerfile                  # Production Docker image
│   ├── railway.toml                # Railway PaaS deployment config
│   ├── alembic.ini                 # Migration config (date-based dirs)
│   ├── alembic/                    # Database migrations
│   │   └── versions/2026/03/       # Date-structured migration files
│   ├── seed/                       # Seed data scripts
│   │   ├── attributes/             # Attribute seed data
│   │   ├── brands/                 # Brand seed data
│   │   ├── categories/             # Category seed data
│   │   ├── geo/                    # Geo reference seed data
│   │   └── products/               # Product seed data
│   ├── scripts/                    # Shell scripts (entrypoint.sh)
│   ├── docs/                       # API docs, requirements, research
│   ├── src/                        # Application source code
│   │   ├── api/                    # Cross-cutting API layer
│   │   │   ├── router.py           # Root router (aggregates all modules)
│   │   │   ├── dependencies/       # Shared auth dependencies
│   │   │   │   └── auth.py         # JWT auth context extraction
│   │   │   ├── exceptions/         # Global exception handlers
│   │   │   │   └── handlers.py     # 4 exception handlers (app, validation, http, catch-all)
│   │   │   └── middlewares/        # ASGI middleware
│   │   │       └── logger.py       # Access logging + request ID + timing
│   │   ├── bootstrap/              # Composition root
│   │   │   ├── config.py           # Pydantic Settings (env vars)
│   │   │   ├── container.py        # Dishka IoC container assembly
│   │   │   ├── web.py              # FastAPI app factory
│   │   │   ├── broker.py           # TaskIQ/RabbitMQ broker config
│   │   │   ├── worker.py           # TaskIQ worker entry point
│   │   │   ├── scheduler.py        # TaskIQ Beat scheduler
│   │   │   ├── bot.py              # Telegram bot factory
│   │   │   └── logger.py           # structlog setup
│   │   ├── bot/                    # Telegram bot (aiogram)
│   │   │   ├── callbacks/          # Callback query handlers
│   │   │   ├── filters/            # Message filters
│   │   │   ├── handlers/           # Message handlers
│   │   │   ├── keyboards/          # Inline keyboard builders
│   │   │   ├── middlewares/        # Bot-specific middleware
│   │   │   └── states/             # FSM state definitions
│   │   ├── infrastructure/         # Shared infrastructure implementations
│   │   │   ├── cache/              # Redis cache provider
│   │   │   │   ├── provider.py     # Dishka provider (Redis + ICache)
│   │   │   │   └── redis.py        # Redis client wrapper
│   │   │   ├── database/           # SQLAlchemy infrastructure
│   │   │   │   ├── base.py         # DeclarativeBase with naming conventions
│   │   │   │   ├── provider.py     # Dishka provider (engine, session, UoW)
│   │   │   │   ├── registry.py     # ORM model registry (all models for Alembic)
│   │   │   │   ├── session.py      # Session helpers
│   │   │   │   ├── uow.py          # UnitOfWork implementation (outbox integration)
│   │   │   │   └── models/         # Cross-cutting ORM models
│   │   │   │       ├── outbox.py   # OutboxMessage model
│   │   │   │       └── failed_task.py  # DLQ FailedTask model
│   │   │   ├── logging/            # Logging infrastructure
│   │   │   │   ├── provider.py     # ILogger Dishka provider
│   │   │   │   ├── taskiq_middleware.py  # TaskIQ logging middleware
│   │   │   │   └── dlq_middleware.py    # Dead letter queue middleware
│   │   │   ├── outbox/             # Transactional Outbox relay
│   │   │   │   ├── relay.py        # Outbox polling + event dispatch
│   │   │   │   └── tasks.py        # Scheduled TaskIQ tasks (relay, pruning)
│   │   │   └── security/           # Auth infrastructure
│   │   │       ├── authorization.py # Permission resolver (Redis + CTE)
│   │   │       ├── jwt.py          # JWT token creation/verification
│   │   │       ├── password.py     # Argon2/bcrypt password hashing
│   │   │       ├── provider.py     # Security Dishka provider
│   │   │       └── telegram.py     # Telegram initData validation
│   │   ├── modules/                # Bounded contexts
│   │   │   ├── catalog/            # EAV Catalog (largest module)
│   │   │   │   ├── application/
│   │   │   │   │   ├── commands/   # 48 command handlers
│   │   │   │   │   ├── queries/    # 25 query handlers + read_models.py
│   │   │   │   │   └── constants.py # Cache keys, locales, defaults
│   │   │   │   ├── domain/
│   │   │   │   │   ├── entities/   # 16 entity files (subdirectory)
│   │   │   │   │   ├── value_objects.py
│   │   │   │   │   ├── events.py
│   │   │   │   │   ├── exceptions.py
│   │   │   │   │   ├── interfaces.py
│   │   │   │   │   └── constants.py
│   │   │   │   ├── infrastructure/
│   │   │   │   │   ├── models.py    # All catalog ORM models (single file)
│   │   │   │   │   ├── repositories/ # 14 repository implementations
│   │   │   │   │   │   ├── base.py  # Generic Data Mapper base
│   │   │   │   │   │   ├── brand.py
│   │   │   │   │   │   ├── category.py
│   │   │   │   │   │   ├── product.py
│   │   │   │   │   │   ├── attribute.py
│   │   │   │   │   │   ├── attribute_group.py
│   │   │   │   │   │   ├── attribute_value.py
│   │   │   │   │   │   ├── attribute_template.py
│   │   │   │   │   │   ├── media_asset.py
│   │   │   │   │   │   ├── product_attribute_value.py
│   │   │   │   │   │   └── template_attribute_binding.py
│   │   │   │   │   └── image_backend_client.py  # HTTP client to image service
│   │   │   │   └── presentation/
│   │   │   │       ├── dependencies.py  # 8 Dishka Provider classes
│   │   │   │       ├── schemas.py       # All Pydantic schemas (42KB)
│   │   │   │       ├── mappers.py       # DTO mapping helpers
│   │   │   │       ├── update_helpers.py # Partial update command builder
│   │   │   │       ├── router_brands.py
│   │   │   │       ├── router_categories.py
│   │   │   │       ├── router_products.py
│   │   │   │       ├── router_variants.py
│   │   │   │       ├── router_skus.py
│   │   │   │       ├── router_attributes.py
│   │   │   │       ├── router_attribute_values.py
│   │   │   │       ├── router_attribute_templates.py
│   │   │   │       ├── router_product_attributes.py
│   │   │   │       ├── router_media.py
│   │   │   │       └── router_storefront.py
│   │   │   ├── identity/           # IAM bounded context
│   │   │   │   ├── application/
│   │   │   │   │   ├── commands/   # Auth, role, session commands
│   │   │   │   │   ├── queries/    # Permission, staff, customer queries
│   │   │   │   │   └── consumers/  # Role event consumers
│   │   │   │   ├── domain/
│   │   │   │   │   ├── entities.py  # Identity, Role, Permission, Session, etc.
│   │   │   │   │   ├── events.py
│   │   │   │   │   ├── exceptions.py
│   │   │   │   │   ├── interfaces.py
│   │   │   │   │   ├── value_objects.py
│   │   │   │   │   └── seed.py      # Default roles/permissions seed data
│   │   │   │   ├── infrastructure/
│   │   │   │   │   ├── models.py    # 12 ORM models
│   │   │   │   │   ├── repositories/
│   │   │   │   │   └── provider.py  # IdentityProvider
│   │   │   │   ├── management/      # CLI management commands
│   │   │   │   └── presentation/
│   │   │   │       ├── dependencies.py  # get_auth_context, RequirePermission
│   │   │   │       ├── schemas.py
│   │   │   │       ├── router_auth.py
│   │   │   │       ├── router_admin.py
│   │   │   │       ├── router_staff.py
│   │   │   │       ├── router_customers.py
│   │   │   │       ├── router_account.py
│   │   │   │       └── router_invitation.py
│   │   │   ├── user/               # User profile context
│   │   │   │   ├── application/
│   │   │   │   │   ├── commands/   # create_customer, create_staff_member, update_profile, anonymize
│   │   │   │   │   ├── queries/
│   │   │   │   │   └── consumers/  # identity_events (auto-create profiles)
│   │   │   │   ├── domain/
│   │   │   │   │   ├── entities.py  # Customer, StaffMember
│   │   │   │   │   ├── exceptions.py
│   │   │   │   │   ├── interfaces.py
│   │   │   │   │   └── services.py
│   │   │   │   ├── infrastructure/
│   │   │   │   │   ├── models.py
│   │   │   │   │   ├── repositories/
│   │   │   │   │   ├── services/
│   │   │   │   │   └── provider.py
│   │   │   │   └── presentation/
│   │   │   │       ├── router.py
│   │   │   │       └── schemas.py
│   │   │   ├── geo/                # Geography reference data
│   │   │   │   ├── application/
│   │   │   │   │   └── queries/    # Read-only queries
│   │   │   │   ├── domain/
│   │   │   │   │   ├── value_objects.py
│   │   │   │   │   ├── interfaces.py
│   │   │   │   │   └── exceptions.py
│   │   │   │   ├── infrastructure/
│   │   │   │   │   ├── models.py    # 10 ORM models (country, subdivision, currency, language)
│   │   │   │   │   └── repositories/
│   │   │   │   └── presentation/
│   │   │   │       ├── dependencies.py
│   │   │   │       └── router.py
│   │   │   └── supplier/           # Supplier management
│   │   │       ├── application/
│   │   │       │   ├── commands/
│   │   │       │   └── queries/
│   │   │       ├── domain/
│   │   │       │   ├── entities.py
│   │   │       │   ├── events.py
│   │   │       │   ├── exceptions.py
│   │   │       │   ├── interfaces.py
│   │   │       │   ├── constants.py
│   │   │       │   └── value_objects.py
│   │   │       ├── infrastructure/
│   │   │       │   ├── models.py
│   │   │       │   └── repositories/
│   │   │       ├── management/     # CLI commands
│   │   │       └── presentation/
│   │   │           ├── dependencies.py
│   │   │           ├── router.py
│   │   │           └── schemas.py
│   │   └── shared/                 # Shared kernel
│   │       ├── context.py          # ContextVar for request_id
│   │       ├── exceptions.py       # AppException hierarchy
│   │       ├── pagination.py       # Generic paginate() helper
│   │       ├── schemas.py          # CamelModel base
│   │       └── interfaces/         # Port protocols
│   │           ├── auth.py         # AuthContext dataclass
│   │           ├── cache.py        # ICache protocol
│   │           ├── entities.py     # IBase, DomainEvent, AggregateRoot
│   │           ├── logger.py       # ILogger protocol
│   │           ├── security.py     # ITokenProvider, IPermissionResolver
│   │           └── uow.py          # IUnitOfWork ABC
│   └── tests/                      # Test suite
│       ├── conftest.py             # Root fixtures
│       ├── architecture/           # Architecture fitness functions (pytest-archon)
│       ├── unit/                   # Unit tests (fakes, no DB)
│       │   ├── infrastructure/     # Infrastructure unit tests
│       │   │   ├── database/
│       │   │   ├── logging/
│       │   │   ├── outbox/
│       │   │   └── security/
│       │   ├── modules/            # Per-module unit tests
│       │   │   ├── catalog/
│       │   │   │   ├── application/commands/
│       │   │   │   ├── domain/
│       │   │   │   └── infrastructure/
│       │   │   ├── identity/
│       │   │   ├── supplier/
│       │   │   └── user/
│       │   └── shared/
│       ├── integration/            # Integration tests (real DB via testcontainers)
│       │   ├── bootstrap/
│       │   └── modules/
│       │       ├── catalog/
│       │       │   ├── application/commands/
│       │       │   └── infrastructure/repositories/
│       │       ├── identity/
│       │       └── supplier/
│       ├── e2e/                    # End-to-end API tests (full HTTP stack)
│       │   └── api/v1/catalog/
│       ├── load/                   # Load tests (Locust)
│       │   └── scenarios/
│       ├── factories/              # Test data factories (polyfactory, builders, mothers)
│       │   ├── strategies/         # Hypothesis strategies
│       │   └── *.py                # ModelFactory, Mothers, Builder classes
│       ├── fakes/                  # In-memory fake implementations
│       └── utils/                  # Test utilities
├── image_backend/                  # Image processing microservice
│   ├── main.py                     # ASGI entry point
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   ├── railway.toml
│   ├── alembic/                    # Separate migrations
│   ├── src/
│   │   ├── api/                    # Same structure as main backend
│   │   │   ├── dependencies/
│   │   │   ├── exceptions/
│   │   │   └── middlewares/
│   │   ├── bootstrap/              # Config, container, web, logger
│   │   ├── infrastructure/
│   │   │   ├── cache/
│   │   │   ├── database/
│   │   │   ├── logging/
│   │   │   └── storage/            # S3-compatible storage (aiobotocore)
│   │   ├── modules/
│   │   │   └── storage/            # Single module
│   │   │       ├── application/
│   │   │       │   ├── commands/   # process_image
│   │   │       │   └── consumers/
│   │   │       ├── domain/
│   │   │       │   ├── entities.py
│   │   │       │   ├── exceptions.py
│   │   │       │   ├── interfaces.py
│   │   │       │   └── value_objects.py
│   │   │       └── presentation/
│   │   │           ├── dependencies.py
│   │   │           ├── facade.py   # High-level orchestration
│   │   │           ├── router.py
│   │   │           ├── schemas.py
│   │   │           ├── sse.py      # Server-Sent Events for processing status
│   │   │           └── tasks.py    # Background processing tasks
│   │   └── shared/
│   │       └── interfaces/
│   └── tests/
│       ├── integration/
│       └── unit/
├── frontend/
│   ├── admin/                      # Admin panel (Next.js 16, JSX, no TS)
│   │   ├── next.config.js
│   │   ├── tailwind.config.js
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── app/                # Next.js App Router
│   │   │   │   ├── admin/          # Admin pages
│   │   │   │   │   ├── products/
│   │   │   │   │   ├── orders/
│   │   │   │   │   ├── settings/   # brands, categories, roles, staff, suppliers, etc.
│   │   │   │   │   ├── users/
│   │   │   │   │   ├── returns/
│   │   │   │   │   └── reviews/
│   │   │   │   ├── api/            # BFF proxy routes
│   │   │   │   │   ├── auth/       # login, logout, me, refresh
│   │   │   │   │   ├── admin/      # identities, roles, permissions
│   │   │   │   │   ├── catalog/    # brands, products, storefront
│   │   │   │   │   ├── categories/ # tree, CRUD
│   │   │   │   │   └── suppliers/
│   │   │   │   └── login/
│   │   │   ├── components/
│   │   │   │   ├── ui/             # Reusable UI primitives (Modal, Badge, etc.)
│   │   │   │   └── admin/          # Admin domain components
│   │   │   │       ├── products/
│   │   │   │       ├── orders/
│   │   │   │       ├── settings/
│   │   │   │       └── users/
│   │   │   ├── hooks/              # Custom React hooks
│   │   │   ├── lib/                # Utilities
│   │   │   │   ├── api-client.js   # backendFetch() helper
│   │   │   │   ├── auth.js         # Auth helpers
│   │   │   │   ├── constants.js
│   │   │   │   ├── dayjs.js        # Date formatting
│   │   │   │   └── utils.js
│   │   │   ├── services/           # API service modules
│   │   │   │   ├── products.js
│   │   │   │   ├── categories.js
│   │   │   │   ├── brands.js
│   │   │   │   ├── suppliers.js
│   │   │   │   ├── attributes.js
│   │   │   │   └── ...
│   │   │   ├── assets/icons/
│   │   │   └── data/               # Static data
│   │   └── public/
│   └── main/                       # Customer app (Next.js 16, TS, Telegram Mini App)
│       ├── next.config.ts
│       ├── tsconfig.json
│       ├── package.json
│       ├── app/                    # Next.js App Router (no src/ prefix)
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   ├── globals.css
│       │   ├── api/                # BFF routes
│       │   │   ├── auth/           # telegram, refresh, logout
│       │   │   ├── backend/        # Catch-all proxy to FastAPI
│       │   │   │   └── [...path]/route.ts
│       │   │   └── dadata/         # DaData address suggestions
│       │   ├── catalog/[category]/ # Category browsing
│       │   ├── product/[id]/       # Product detail page
│       │   ├── checkout/           # Checkout flow + pickup search
│       │   ├── favorites/          # Favorites + brand favorites
│       │   ├── profile/            # User profile, orders, settings
│       │   ├── search/             # Product search
│       │   └── promo/              # Promotional pages
│       ├── components/
│       │   ├── ui/                 # UI primitives
│       │   ├── blocks/             # Feature blocks (cart, catalog, product, etc.)
│       │   ├── layout/             # Layout components
│       │   ├── providers/          # Context providers
│       │   └── ios/                # iOS-specific components
│       ├── lib/
│       │   ├── auth/               # Cookie helpers, auth logic
│       │   ├── store/              # Redux Toolkit + RTK Query
│       │   │   ├── store.ts
│       │   │   ├── api.ts          # RTK Query base API with token refresh
│       │   │   ├── authSlice.ts
│       │   │   └── hooks.ts
│       │   ├── format/             # Formatting utilities
│       │   ├── hooks/              # Custom hooks
│       │   ├── telegram/           # Telegram WebApp integration
│       │   │   └── hooks/
│       │   └── types/              # TypeScript type definitions
│       └── public/                 # Static assets (fonts, icons, images)
└── docker-compose.yml              # (per-service in backend/ and image_backend/)
```

## Directory Purposes

**`backend/src/modules/{module}/`:**
- Purpose: Self-contained bounded context with 4-layer hexagonal structure
- Contains: `domain/`, `application/`, `infrastructure/`, `presentation/` subdirectories
- Key pattern: Each module is isolated; cross-module communication happens only through domain events (via Outbox) or shared kernel interfaces

**`backend/src/shared/`:**
- Purpose: Shared kernel providing cross-cutting abstractions
- Contains: Interface protocols, base exception hierarchy, pagination helper, CamelModel schema base, request context propagation
- Key files: `interfaces/uow.py`, `interfaces/entities.py`, `exceptions.py`, `schemas.py`

**`backend/src/bootstrap/`:**
- Purpose: Composition root -- wires all concrete implementations to interfaces
- Contains: App factory, DI container assembly, config, broker, worker, scheduler, bot, logging
- Key files: `container.py` (DI assembly), `web.py` (FastAPI factory), `config.py` (env vars)

**`backend/src/api/`:**
- Purpose: Cross-cutting HTTP concerns shared by all modules
- Contains: Root router, exception handlers, auth dependencies, access logging middleware
- Key files: `router.py` (aggregates all module routers), `exceptions/handlers.py`

**`backend/src/infrastructure/`:**
- Purpose: Shared infrastructure implementations (not module-specific)
- Contains: Database (engine, session, UoW, base model, ORM registry), cache (Redis), security (JWT, passwords, Telegram auth, RBAC), logging, outbox relay

**`backend/tests/`:**
- Purpose: Comprehensive test suite organized by test type
- Structure: `unit/` (fakes, no DB), `integration/` (real DB via testcontainers), `e2e/` (full HTTP API), `architecture/` (fitness functions), `load/` (Locust), `factories/` (test data), `fakes/` (in-memory impls)

**`frontend/admin/src/app/api/`:**
- Purpose: BFF (Backend For Frontend) proxy routes
- Pattern: Each API route proxies requests to the FastAPI backend using `backendFetch()` from `frontend/admin/src/lib/api-client.js`

**`frontend/main/app/api/backend/[...path]/`:**
- Purpose: Catch-all proxy route that forwards all `/api/backend/*` requests to the FastAPI backend
- Handles: Cookie-to-header JWT forwarding, timeout management, error translation

## Key File Locations

**Entry Points:**
- `backend/main.py`: ASGI entry point, creates FastAPI app
- `backend/src/bootstrap/web.py`: FastAPI app factory (middleware, routers, DI, lifespan)
- `backend/src/bootstrap/worker.py`: TaskIQ worker entry point (DI, DLQ, task imports)
- `backend/src/bootstrap/scheduler.py`: TaskIQ Beat scheduler
- `image_backend/main.py`: Image service entry point

**Configuration:**
- `backend/src/bootstrap/config.py`: Pydantic Settings (all env vars)
- `backend/pyproject.toml`: Python project config (ruff, mypy rules, dependencies)
- `backend/alembic.ini`: Migration config
- `frontend/admin/next.config.js`: Admin Next.js config
- `frontend/main/next.config.ts`: Main Next.js config
- `frontend/main/tsconfig.json`: TypeScript strict config

**Core Business Logic (Catalog):**
- `backend/src/modules/catalog/domain/entities/product.py`: Product aggregate root (largest entity, 23KB)
- `backend/src/modules/catalog/domain/entities/category.py`: Category tree with materialized path
- `backend/src/modules/catalog/domain/entities/brand.py`: Brand aggregate
- `backend/src/modules/catalog/domain/interfaces.py`: All catalog repository interfaces (18KB)
- `backend/src/modules/catalog/domain/value_objects.py`: Enums, Money, validation helpers
- `backend/src/modules/catalog/domain/exceptions.py`: All catalog domain exceptions (23KB)
- `backend/src/modules/catalog/domain/events.py`: All catalog domain events (16KB)

**Infrastructure:**
- `backend/src/infrastructure/database/uow.py`: UnitOfWork with Outbox integration
- `backend/src/infrastructure/database/base.py`: SQLAlchemy DeclarativeBase
- `backend/src/infrastructure/database/registry.py`: ORM model registry (all models)
- `backend/src/modules/catalog/infrastructure/models.py`: All catalog ORM models (single file)
- `backend/src/modules/catalog/infrastructure/repositories/base.py`: Generic Data Mapper base

**DI Wiring:**
- `backend/src/bootstrap/container.py`: Composition root (assembles all providers)
- `backend/src/modules/catalog/presentation/dependencies.py`: 8 Dishka Provider classes for catalog (20KB)
- `backend/src/infrastructure/database/provider.py`: Engine, session, UoW providers

**Authentication/Authorization:**
- `backend/src/modules/identity/presentation/dependencies.py`: `get_auth_context()`, `RequirePermission`
- `backend/src/infrastructure/security/jwt.py`: JWT creation/verification
- `backend/src/infrastructure/security/authorization.py`: Permission resolver (Redis + CTE)
- `backend/src/infrastructure/security/telegram.py`: Telegram initData validation

**API Schemas:**
- `backend/src/modules/catalog/presentation/schemas.py`: All catalog Pydantic schemas (42KB)
- `backend/src/modules/identity/presentation/schemas.py`: Identity schemas (14KB)
- `backend/src/shared/schemas.py`: CamelModel base class

**Testing:**
- `backend/tests/conftest.py`: Root test fixtures
- `backend/tests/factories/`: Test data factories (ModelFactory, Mothers, Builder patterns)
- `backend/tests/fakes/`: In-memory fake repositories/services

**Frontend State Management:**
- `frontend/main/lib/store/api.ts`: RTK Query base API with token refresh
- `frontend/main/lib/store/store.ts`: Redux store configuration
- `frontend/admin/src/lib/api-client.js`: Server-side API client for admin BFF

## Naming Conventions

**Files (Python):**
- `snake_case.py` for all files
- Domain: `entities.py`, `value_objects.py`, `exceptions.py`, `interfaces.py`, `events.py`, `constants.py`
- Commands: action-named `create_brand.py`, `update_category.py`, `delete_product.py`, `generate_sku_matrix.py`
- Queries: read-named `list_brands.py`, `get_category.py`, `get_category_tree.py`
- Routers: `router_{resource}.py` (e.g., `router_brands.py`, `router_storefront.py`)
- ORM models: `models.py` (single file per module)
- Schemas: `schemas.py` (single file per module)
- Repositories: named after aggregate `brand.py`, `category.py`, `product.py`
- DI providers: `dependencies.py` (presentation) or `provider.py` (infrastructure)

**Files (JavaScript/TypeScript):**
- React components: `PascalCase.jsx` / `PascalCase.tsx`
- Utilities: `kebab-case.ts` / `camelCase.js`
- Next.js routes: `route.js` / `route.ts`, `page.jsx` / `page.tsx`, `layout.jsx` / `layout.tsx`
- Services: `camelCase.js` (e.g., `products.js`, `categories.js`)

**Directories:**
- Backend modules: `snake_case` (e.g., `catalog`, `identity`, `user`, `geo`, `supplier`)
- Backend layers: `application`, `domain`, `infrastructure`, `presentation`
- Frontend components: `kebab-case` or `camelCase` directories
- Frontend routes: Next.js file-based routing with `[param]` dynamic segments

## Where to Add New Code

**New Backend Module (Bounded Context):**
1. Create directory: `backend/src/modules/{module_name}/`
2. Create 4 subdirectories: `domain/`, `application/`, `infrastructure/`, `presentation/`
3. Domain layer: `entities.py`, `interfaces.py`, `exceptions.py`, `value_objects.py`, `events.py`
4. Application layer: `commands/` and `queries/` subdirectories
5. Infrastructure layer: `models.py`, `repositories/`, `provider.py`
6. Presentation layer: `router_{resource}.py`, `schemas.py`, `dependencies.py`
7. Register the module's router in `backend/src/api/router.py`
8. Register the module's DI providers in `backend/src/bootstrap/container.py`
9. Register ORM models in `backend/src/infrastructure/database/registry.py`
10. Create Alembic migration: `alembic revision --autogenerate -m "add {module} tables"`

**New Command Handler (Catalog):**
1. Create file: `backend/src/modules/catalog/application/commands/{action}_{entity}.py`
2. Define frozen `@dataclass` for `{Action}{Entity}Command` and `{Action}{Entity}Result`
3. Define handler class `{Action}{Entity}Handler` with `__init__` accepting repos, UoW, logger
4. Implement `async def handle(self, command: Command) -> Result`
5. Register handler in `backend/src/modules/catalog/presentation/dependencies.py` (appropriate Provider class)
6. Add endpoint in the relevant router file

**New Query Handler (Catalog):**
1. Create file: `backend/src/modules/catalog/application/queries/{action}_{entity}.py`
2. Define frozen `@dataclass` for `{Action}{Entity}Query`
3. Define handler class `{Action}{Entity}Handler` with `__init__` accepting `AsyncSession` and `ILogger`
4. Query ORM models directly (no repository), return Pydantic read models
5. Add read model to `backend/src/modules/catalog/application/queries/read_models.py`
6. Register handler in DI provider, add endpoint in router

**New Domain Entity (Catalog):**
1. Create file: `backend/src/modules/catalog/domain/entities/{entity_name}.py`
2. Use `@attr.dataclass` with `AggregateRoot` mixin for aggregate roots
3. Implement `create()` factory method, `update()` method, `validate_deletable()` guard
4. Add guarded fields with `__setattr__` pattern (DDD-01)
5. Add to `backend/src/modules/catalog/domain/entities/__init__.py` exports
6. Define interface in `backend/src/modules/catalog/domain/interfaces.py`
7. Create ORM model in `backend/src/modules/catalog/infrastructure/models.py`
8. Create repository in `backend/src/modules/catalog/infrastructure/repositories/`

**New Admin Page:**
1. Create route: `frontend/admin/src/app/admin/{feature}/page.jsx`
2. Create BFF proxy: `frontend/admin/src/app/api/{feature}/route.js`
3. Create service: `frontend/admin/src/services/{feature}.js`
4. Create components: `frontend/admin/src/components/admin/{feature}/`

**New Customer Page:**
1. Create route: `frontend/main/app/{feature}/page.tsx`
2. API calls go through catch-all proxy at `frontend/main/app/api/backend/[...path]/route.ts`
3. Create components: `frontend/main/components/blocks/{feature}/`
4. Add RTK Query endpoints in `frontend/main/lib/store/api.ts`

**New Test (Backend):**
- Unit test: `backend/tests/unit/modules/{module}/application/commands/test_{handler}.py`
- Integration test: `backend/tests/integration/modules/{module}/infrastructure/repositories/test_{repo}.py`
- E2E test: `backend/tests/e2e/api/v1/{module}/test_{feature}.py`
- Test factory: `backend/tests/factories/{entity}_factory.py` or update existing mothers/builders

## Special Directories

**`backend/seed/`:**
- Purpose: Database seed scripts for reference data (brands, categories, attributes, geo)
- Generated: No (hand-maintained)
- Committed: Yes

**`backend/alembic/versions/`:**
- Purpose: Database migrations organized by date (YYYY/MM)
- Generated: Yes (via `alembic revision --autogenerate`)
- Committed: Yes

**`backend/tests/factories/`:**
- Purpose: Test data generation using polyfactory `ModelFactory`, Object Mothers, and Builders
- Generated: No
- Committed: Yes

**`backend/tests/fakes/`:**
- Purpose: In-memory fake implementations of repository interfaces for unit tests
- Generated: No
- Committed: Yes

**`frontend/admin/src/app/api/`:**
- Purpose: BFF proxy routes (Next.js API routes forwarding to FastAPI backend)
- Generated: No
- Committed: Yes

**`backend/src/infrastructure/database/registry.py`:**
- Purpose: Central import of all ORM models so Alembic can discover schema changes
- Must be updated: Every time a new ORM model is added to any module

---

*Structure analysis: 2026-03-29*
