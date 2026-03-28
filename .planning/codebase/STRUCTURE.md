# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
loyality/
├── backend/                    # Main Python backend (FastAPI)
│   ├── main.py                 # ASGI entry point -> create_app()
│   ├── pyproject.toml          # Python dependencies (uv), ruff/mypy config
│   ├── uv.lock                 # Dependency lockfile
│   ├── Makefile                # Dev shortcuts (test, lint, migrate)
│   ├── Dockerfile              # Production container image
│   ├── railway.toml            # Railway PaaS deployment config
│   ├── alembic.ini             # Migration config (date-based subdirs)
│   ├── alembic/                # Database migrations
│   │   ├── env.py              # Alembic environment (imports registry)
│   │   └── versions/2026/03/   # Migration scripts (YYYY/MM subdirs)
│   ├── scripts/                # Dev utilities
│   │   └── entrypoint.sh       # Docker entrypoint (migrate + run)
│   ├── seed/                   # Data seeding scripts
│   │   ├── __main__.py         # Entry: python -m seed
│   │   ├── main.py             # Seed orchestrator
│   │   ├── attributes/         # Attribute & value seeding
│   │   ├── brands/             # Brand seeding
│   │   ├── categories/         # Category tree seeding
│   │   ├── geo/                # Countries, currencies, languages
│   │   └── products/           # Product seeding
│   ├── src/                    # Application source code
│   │   ├── api/                # Cross-cutting HTTP layer
│   │   │   ├── router.py       # Root router (mounts all module routers)
│   │   │   ├── dependencies/   # Shared auth dependencies
│   │   │   │   └── auth.py     # JWT extraction dependency
│   │   │   ├── exceptions/     # Centralized exception handlers
│   │   │   │   └── handlers.py # 4 handlers: App, Validation, HTTP, catch-all
│   │   │   └── middlewares/    # Access logging middleware
│   │   │       └── logger.py   # Request/response timing + request ID
│   │   ├── bootstrap/          # Composition root & process entry points
│   │   │   ├── config.py       # Pydantic Settings (env vars, SecretStr)
│   │   │   ├── container.py    # Dishka DI container (18 providers)
│   │   │   ├── web.py          # FastAPI app factory (CORS, DI, lifespan)
│   │   │   ├── worker.py       # TaskIQ worker (critical import order)
│   │   │   ├── scheduler.py    # TaskIQ Beat (outbox relay/pruning)
│   │   │   ├── broker.py       # AioPikaBroker (RabbitMQ) config
│   │   │   ├── bot.py          # Telegram bot factory
│   │   │   └── logger.py       # structlog setup
│   │   ├── bot/                # Telegram bot (aiogram)
│   │   │   ├── factory.py      # Bot & Dispatcher creation
│   │   │   ├── callbacks/      # Callback query handlers
│   │   │   ├── filters/        # Custom message filters
│   │   │   ├── handlers/       # Message/command handlers
│   │   │   ├── keyboards/      # Inline & reply keyboards
│   │   │   ├── middlewares/    # Throttling, logging, user lookup
│   │   │   └── states/         # FSM state groups
│   │   ├── infrastructure/     # Cross-cutting infra (all modules)
│   │   │   ├── cache/          # Redis cache service & Dishka provider
│   │   │   ├── database/       # SQLAlchemy stack
│   │   │   │   ├── base.py     # Shared Base with naming conventions
│   │   │   │   ├── session.py  # Session factory
│   │   │   │   ├── uow.py     # UnitOfWork (outbox event persistence)
│   │   │   │   ├── provider.py # Dishka provider (engine, session, UoW)
│   │   │   │   ├── registry.py # ORM model registry (for Alembic)
│   │   │   │   └── models/     # Cross-cutting ORM models
│   │   │   │       ├── outbox.py    # OutboxMessage table
│   │   │   │       └── failed_task.py # DLQ failed tasks
│   │   │   ├── logging/        # Logging adapters
│   │   │   │   ├── provider.py # ILogger Dishka provider
│   │   │   │   ├── taskiq_middleware.py  # TaskIQ logging middleware
│   │   │   │   └── dlq_middleware.py    # Dead letter queue middleware
│   │   │   ├── outbox/         # Transactional Outbox relay
│   │   │   │   ├── relay.py    # Polls outbox, dispatches events
│   │   │   │   └── tasks.py    # Scheduled tasks + event handler registry
│   │   │   └── security/       # Security infrastructure
│   │   │       ├── jwt.py      # JWT creation/verification
│   │   │       ├── password.py # Argon2id hashing
│   │   │       ├── authorization.py # RBAC permission resolver (Redis + CTE)
│   │   │       ├── telegram.py # Telegram initData validation
│   │   │       └── provider.py # Security Dishka provider
│   │   ├── modules/            # Bounded context modules
│   │   │   ├── catalog/        # Product catalog (largest module)
│   │   │   │   ├── domain/
│   │   │   │   │   ├── entities.py       # Brand, Category, Product, SKU, etc.
│   │   │   │   │   ├── value_objects.py  # Money, BehaviorFlags, enums
│   │   │   │   │   ├── events.py         # 27 domain event types
│   │   │   │   │   ├── interfaces.py     # 11 repository interfaces
│   │   │   │   │   └── exceptions.py     # Domain-specific errors
│   │   │   │   ├── application/
│   │   │   │   │   ├── commands/         # 47 command handler files
│   │   │   │   │   ├── queries/          # 23 query handler files
│   │   │   │   │   └── constants.py      # REQUIRED_LOCALES, defaults
│   │   │   │   ├── infrastructure/
│   │   │   │   │   ├── models.py         # All catalog ORM models
│   │   │   │   │   ├── repositories/     # 11 repository implementations
│   │   │   │   │   │   ├── base.py       # Generic Data Mapper base
│   │   │   │   │   │   ├── brand.py
│   │   │   │   │   │   ├── category.py
│   │   │   │   │   │   ├── product.py
│   │   │   │   │   │   ├── attribute.py
│   │   │   │   │   │   ├── attribute_group.py
│   │   │   │   │   │   ├── attribute_value.py
│   │   │   │   │   │   ├── attribute_template.py
│   │   │   │   │   │   ├── template_attribute_binding.py
│   │   │   │   │   │   ├── product_attribute_value.py
│   │   │   │   │   │   └── media_asset.py
│   │   │   │   │   └── image_backend_client.py  # HTTP client to image service
│   │   │   │   └── presentation/
│   │   │   │       ├── dependencies.py   # 9 Dishka Provider classes
│   │   │   │       ├── schemas.py        # All request/response schemas
│   │   │   │       ├── mappers.py        # DTO mapping functions
│   │   │   │       ├── update_helpers.py # Partial update support
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
│   │   │   ├── geo/            # Geography reference data
│   │   │   │   ├── domain/     # Entities, interfaces
│   │   │   │   ├── application/queries/  # Read-only queries (no commands)
│   │   │   │   ├── infrastructure/       # ORM models, repositories
│   │   │   │   └── presentation/         # router.py, dependencies.py
│   │   │   ├── identity/       # IAM (auth, sessions, roles, permissions)
│   │   │   │   ├── domain/     # Identity, Role, Session, Permission entities
│   │   │   │   ├── application/
│   │   │   │   │   ├── commands/         # 21 command handlers (login, register, roles, etc.)
│   │   │   │   │   ├── queries/          # 14 query handlers
│   │   │   │   │   └── consumers/        # Event consumers (role_events)
│   │   │   │   ├── infrastructure/       # ORM models, repos, provider.py
│   │   │   │   ├── management/           # Admin scripts (create_admin, sync_roles)
│   │   │   │   └── presentation/         # 6 routers (auth, admin, staff, customers, invitation, account)
│   │   │   ├── supplier/       # Supplier management
│   │   │   │   ├── domain/     # Supplier entity, events, exceptions
│   │   │   │   ├── application/
│   │   │   │   │   ├── commands/         # 4 handlers (CRUD + activate/deactivate)
│   │   │   │   │   └── queries/          # Query handlers
│   │   │   │   ├── infrastructure/       # ORM model, repository
│   │   │   │   ├── management/           # sync_suppliers script
│   │   │   │   └── presentation/         # router.py, dependencies.py, schemas.py
│   │   │   └── user/           # User profiles (customer, staff)
│   │   │       ├── domain/     # Profile entities, interfaces
│   │   │       ├── application/
│   │   │       │   ├── commands/         # 4 handlers (create/update customer/staff)
│   │   │       │   ├── queries/          # Query handlers
│   │   │       │   └── consumers/        # identity_events consumer
│   │   │       ├── infrastructure/
│   │   │       │   ├── repositories/     # Profile repos
│   │   │       │   └── services/         # Profile services
│   │   │       └── presentation/         # router.py
│   │   └── shared/             # Shared kernel
│   │       ├── interfaces/     # Abstract protocols
│   │       │   ├── entities.py # IBase, DomainEvent, AggregateRoot
│   │       │   ├── uow.py     # IUnitOfWork
│   │       │   ├── auth.py    # AuthContext
│   │       │   ├── cache.py   # ICacheService
│   │       │   ├── security.py # ITokenProvider, IPermissionResolver
│   │       │   └── logger.py  # ILogger
│   │       ├── exceptions.py  # AppException hierarchy
│   │       ├── pagination.py  # Generic paginate() helper
│   │       ├── schemas.py     # CamelModel base
│   │       └── context.py     # ContextVar request ID propagation
│   └── tests/                  # Test suite
│       ├── conftest.py         # Root fixtures (markers, session scope)
│       ├── architecture/       # Architectural fitness tests (pytest-archon)
│       ├── e2e/                # End-to-end API tests
│       │   └── api/v1/         # API endpoint tests
│       ├── integration/        # Integration tests (real DB via testcontainers)
│       │   ├── conftest.py     # DB fixtures, session factory
│       │   ├── bootstrap/      # Bootstrap integration tests
│       │   └── modules/        # Per-module integration tests
│       │       ├── catalog/    # Catalog repos & command handlers
│       │       ├── identity/   # Identity repos & commands
│       │       └── supplier/   # Supplier repo tests
│       ├── unit/               # Unit tests (no I/O, fakes/mocks)
│       │   ├── conftest.py     # Unit test fixtures
│       │   ├── infrastructure/ # UoW, security, logging tests
│       │   ├── modules/        # Per-module unit tests
│       │   │   ├── catalog/    # Domain, application, infrastructure
│       │   │   ├── identity/   # Domain, application, management
│       │   │   ├── supplier/   # Domain tests
│       │   │   └── user/       # Domain, application tests
│       │   └── shared/         # Shared kernel tests
│       ├── factories/          # Test data creation
│       │   ├── catalog_mothers.py  # Domain entity object mothers
│       │   ├── orm_factories.py    # ORM model factories (polyfactory)
│       │   ├── builders.py         # Builder pattern for complex scenarios
│       │   ├── identity_mothers.py # Identity entity mothers
│       │   └── strategies/         # Polyfactory custom strategies
│       ├── fakes/              # Fake implementations
│       │   ├── fake_uow.py    # In-memory UoW
│       │   ├── fake_repos.py  # In-memory repositories
│       │   └── fake_logger.py # No-op logger
│       ├── load/               # Load tests (Locust)
│       │   └── scenarios/      # Load test scenarios
│       └── utils/              # Test utilities
├── image_backend/              # Image processing microservice
│   ├── main.py                 # ASGI entry point
│   ├── pyproject.toml          # Dependencies (uv)
│   ├── uv.lock                 # Lockfile
│   ├── Dockerfile              # Container image
│   ├── railway.toml            # Deployment config
│   ├── alembic/                # Separate migrations
│   │   └── versions/2026/03/
│   ├── src/
│   │   ├── api/                # HTTP layer (dependencies, exceptions, middlewares)
│   │   ├── bootstrap/          # Config, container, web factory
│   │   ├── infrastructure/     # Cache, database, logging, storage (S3)
│   │   │   └── storage/        # S3-compatible blob storage (aiobotocore)
│   │   ├── modules/storage/    # Single bounded context
│   │   │   ├── domain/         # StorageObject entity, interfaces
│   │   │   ├── application/
│   │   │   │   ├── commands/   # process_image.py
│   │   │   │   ├── consumers/  # Async task consumers
│   │   │   │   └── queries/
│   │   │   └── presentation/   # Router, schemas, SSE endpoint, facade
│   │   └── shared/             # Shared kernel (mirrors backend pattern)
│   └── tests/
│       ├── integration/
│       └── unit/modules/storage/
├── frontend/
│   ├── admin/                  # Admin dashboard (Next.js 16, JSX, no TS)
│   │   ├── next.config.js      # Webpack custom (SVG loader, security headers)
│   │   ├── package.json        # Dependencies
│   │   ├── tailwind.config.js  # Custom design tokens
│   │   ├── src/
│   │   │   ├── app/            # App Router
│   │   │   │   ├── layout.jsx  # Root layout with sidebar
│   │   │   │   ├── page.jsx    # Dashboard page
│   │   │   │   ├── login/      # Login page
│   │   │   │   ├── admin/      # Admin pages (file-based routing)
│   │   │   │   │   ├── products/       # Product management
│   │   │   │   │   ├── orders/         # Order management
│   │   │   │   │   ├── users/          # User management
│   │   │   │   │   ├── reviews/        # Review management
│   │   │   │   │   ├── returns/        # Return management
│   │   │   │   │   └── settings/       # Settings pages
│   │   │   │   │       ├── brands/
│   │   │   │   │       ├── categories/
│   │   │   │   │       ├── suppliers/
│   │   │   │   │       ├── roles/
│   │   │   │   │       ├── staff/
│   │   │   │   │       ├── pricing-formulas/
│   │   │   │   │       ├── promocodes/
│   │   │   │   │       └── referrals/
│   │   │   │   └── api/        # BFF API routes (proxy to backend)
│   │   │   │       ├── auth/   # Auth endpoints (login, logout, me, refresh)
│   │   │   │       ├── catalog/# Catalog endpoints (brands, products, storefront)
│   │   │   │       ├── categories/ # Category CRUD
│   │   │   │       ├── suppliers/  # Supplier CRUD
│   │   │   │       └── admin/  # Admin identity/role management
│   │   │   ├── components/     # React components
│   │   │   │   ├── ui/         # Reusable UI primitives (Modal, Badge, etc.)
│   │   │   │   └── admin/      # Page-specific components
│   │   │   ├── hooks/          # Custom hooks (useAuth, useBodyScrollLock)
│   │   │   ├── lib/            # Utilities (api-client.js, dayjs.js)
│   │   │   ├── services/       # Service layer
│   │   │   ├── data/           # Static data
│   │   │   └── assets/icons/   # SVG icons
│   │   └── public/             # Static assets
│   └── main/                   # Customer storefront (Next.js 16, TypeScript)
│       ├── next.config.ts      # Minimal config
│       ├── package.json        # Dependencies
│       ├── tsconfig.json       # Strict mode, @/* path alias
│       ├── app/                # App Router
│       │   ├── layout.tsx      # Root layout
│       │   ├── page.tsx        # Home page
│       │   ├── api/            # BFF API routes
│       │   │   ├── backend/[...path]/route.ts  # Catch-all proxy to backend
│       │   │   ├── auth/       # Auth (telegram, logout, refresh)
│       │   │   └── dadata/     # DaData address suggestions proxy
│       │   ├── catalog/[category]/  # Category browse
│       │   ├── product/[id]/        # Product detail
│       │   ├── checkout/            # Checkout flow + pickup
│       │   ├── favorites/           # Wishlist + brand favorites
│       │   ├── profile/             # User profile, orders, settings
│       │   ├── search/              # Search results
│       │   ├── poizon/              # Poizon marketplace page
│       │   ├── promo/               # Promotional pages
│       │   └── invite-friends/      # Referral program
│       ├── components/         # React components
│       │   ├── ui/             # Reusable UI primitives
│       │   ├── blocks/         # Feature-specific blocks
│       │   │   ├── cart/       # Cart components
│       │   │   ├── catalog/    # Catalog browse
│       │   │   ├── product/    # Product detail
│       │   │   ├── favorites/  # Wishlist
│       │   │   ├── home/       # Home page blocks
│       │   │   ├── profile/    # Profile sections
│       │   │   ├── search/     # Search UI
│       │   │   ├── promo/      # Promo blocks
│       │   │   └── reviews/    # Review components
│       │   ├── layout/         # Layout components
│       │   ├── providers/      # Context providers
│       │   ├── ios/            # iOS-specific components
│       │   └── telegram/       # Telegram WebApp components
│       ├── lib/                # Utilities and state
│       │   ├── store/          # Redux Toolkit
│       │   │   ├── store.ts    # Store configuration
│       │   │   ├── api.ts      # RTK Query API slice
│       │   │   ├── authSlice.ts # Auth state
│       │   │   └── hooks.ts    # Typed hooks
│       │   ├── auth/           # Auth utilities
│       │   ├── format/         # Formatting utilities
│       │   ├── hooks/          # Custom hooks
│       │   ├── telegram/       # Telegram WebApp SDK helpers
│       │   │   └── hooks/      # Telegram-specific hooks
│       │   └── types/          # TypeScript type definitions
│       ├── scripts/            # Dev scripts
│       └── public/             # Static assets (fonts, icons, images)
├── .planning/                  # GSD planning artifacts
│   ├── codebase/               # Codebase analysis docs
│   ├── phases/                 # Phase plans and research
│   ├── research/               # Research documents
│   └── config.json             # GSD configuration
├── postman/                    # Postman collection & environments
│   ├── collections/
│   ├── environments/
│   └── specs/
└── docs/                       # Project-level documentation
```

## Directory Purposes

### Backend Module Structure

Each module at `backend/src/modules/{module}/` follows an identical four-layer structure:

**`domain/`** -- Pure business logic (zero infrastructure imports)
- `entities.py`: attrs `@dataclass` classes with `create()` factory methods, `update()` methods, `__setattr__` guards for immutable fields
- `value_objects.py`: `StrEnum` enums, frozen `@attrs.frozen` classes
- `events.py`: `DomainEvent` subclasses for Transactional Outbox
- `interfaces.py`: Abstract ABC repository contracts (ports)
- `exceptions.py`: Domain-specific `AppException` subclasses
- `constants.py`: Application-level constants

**`application/`** -- Use case orchestration
- `commands/`: One file per write operation. Each contains: frozen `Command` dataclass, optional `Result` dataclass, `Handler` class with `async def handle()` method
- `queries/`: One file per read operation. Each contains: frozen `Query` dataclass, `Handler` class injecting `AsyncSession` directly
- `queries/read_models.py`: Pydantic read model DTOs returned by query handlers
- `consumers/`: TaskIQ event consumer tasks (react to domain events)
- `constants.py`: Shared constants like `REQUIRED_LOCALES`, `DEFAULT_CURRENCY`

**`infrastructure/`** -- Concrete implementations (adapters)
- `models.py`: SQLAlchemy ORM models (one file per module containing all tables)
- `repositories/`: Repository implementations extending `BaseRepository` or standalone
- `provider.py`: Dishka `Provider` class (used for modules that wire their own DI)
- External clients (e.g., `image_backend_client.py`)

**`presentation/`** -- HTTP API surface
- `router_*.py`: FastAPI routers (one per resource/entity type)
- `schemas.py`: Pydantic `CamelModel` request/response schemas
- `dependencies.py`: Dishka `Provider` classes (one per sub-domain group)
- `mappers.py`: DTO mapping functions
- `update_helpers.py`: Partial update support with Ellipsis sentinel

**`management/`** (optional) -- Admin/CLI scripts
- One-time or infrequent operations like `create_admin.py`, `sync_system_roles.py`
- Exists in: `identity`, `supplier` modules

### Module Sizes

| Module | Commands | Queries | Domain Events | Repository Interfaces | Routers |
|--------|----------|---------|---------------|----------------------|---------|
| `catalog` | 47 | 23 | 27 | 11 | 11 |
| `identity` | 21 | 14 | (uses shared) | (in interfaces.py) | 6 |
| `user` | 4 | (in queries/) | - | (in interfaces.py) | 1 |
| `supplier` | 4 | (in queries/) | (in events.py) | (in interfaces.py) | 1 |
| `geo` | 0 (read-only) | 4 | - | (in interfaces.py) | 1 |

### Infrastructure Layer (Cross-Cutting)

**`backend/src/infrastructure/database/`:**
- `base.py`: Shared SQLAlchemy `Base` with naming conventions (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`)
- `session.py`: Session factory configuration
- `uow.py`: `UnitOfWork` implementation -- coordinates commit, rollback, outbox event extraction
- `provider.py`: Dishka provider for `AsyncEngine` (APP scope), `async_sessionmaker` (APP), `AsyncSession` (REQUEST), `IUnitOfWork` (REQUEST)
- `registry.py`: Imports all ORM models across all modules for Alembic auto-generation
- `models/`: Cross-cutting ORM models (`OutboxMessage`, `FailedTask`)

**`backend/src/infrastructure/security/`:**
- `jwt.py`: JWT creation/verification (HS256, `pyjwt`)
- `password.py`: Password hashing (Argon2id via `pwdlib`)
- `authorization.py`: RBAC permission resolver (Redis cache + recursive CTE fallback)
- `telegram.py`: Telegram `initData` validation
- `provider.py`: Security Dishka provider

**`backend/src/infrastructure/outbox/`:**
- `relay.py`: Polls `outbox_messages` with `SELECT ... FOR UPDATE SKIP LOCKED`, dispatches to registered event handlers
- `tasks.py`: TaskIQ scheduled tasks (`outbox_relay_task` every minute, `outbox_pruning_task` daily) + `_EVENT_HANDLERS` registry

**`backend/src/infrastructure/cache/`:**
- Redis cache service with hiredis C extension
- Dishka provider for cache connections

**`backend/src/infrastructure/logging/`:**
- `provider.py`: `ILogger` Dishka provider
- `taskiq_middleware.py`: Logging middleware for TaskIQ workers
- `dlq_middleware.py`: Dead letter queue -- persists failed tasks to `failed_tasks` table

## Key File Locations

### Entry Points
- `backend/main.py`: Web API ASGI entry point -> calls `create_app()` from `src/bootstrap/web.py`
- `backend/src/bootstrap/worker.py`: TaskIQ worker entry point (run: `taskiq worker src.bootstrap.worker:broker`)
- `backend/src/bootstrap/scheduler.py`: TaskIQ Beat scheduler (run: `taskiq scheduler src.bootstrap.scheduler:scheduler`)
- `image_backend/main.py`: Image backend ASGI entry point
- `frontend/admin/src/app/layout.jsx`: Admin frontend root layout
- `frontend/main/app/layout.tsx`: Main frontend root layout

### Configuration
- `backend/src/bootstrap/config.py`: All environment variables and computed fields (`database_url`, `redis_url`)
- `backend/pyproject.toml`: Python deps, ruff config (rules, line-length 88, target py314), mypy config (strict)
- `backend/alembic.ini`: Alembic migration config (date-based subdirectories, recursive versions)
- `backend/tests/conftest.py`: Root test configuration and pytest markers
- `frontend/admin/next.config.js`: Webpack customization, SVG loader, security headers, `@` path alias
- `frontend/main/next.config.ts`: Minimal config, remote image patterns
- `frontend/main/tsconfig.json`: Strict mode, `@/*` path alias, ES2017 target

### Core Logic (Catalog Focus)
- `backend/src/modules/catalog/domain/entities.py`: 12 domain entities -- Brand, Category, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Attribute, AttributeValue, ProductAttributeValue, SKU, ProductVariant, MediaAsset, Product
- `backend/src/modules/catalog/domain/value_objects.py`: Money, BehaviorFlags, ProductStatus FSM, MediaType, MediaRole, AttributeDataType, AttributeUIType, RequirementLevel, AttributeLevel
- `backend/src/modules/catalog/domain/interfaces.py`: 11 repository interfaces
- `backend/src/modules/catalog/domain/events.py`: 27 domain event types (CatalogEvent base with `__init_subclass__` for required fields)
- `backend/src/modules/catalog/infrastructure/models.py`: All catalog ORM models (brands, categories, products, skus, attributes, media_assets, etc.)

### Testing
- `backend/tests/conftest.py`: Root test configuration, test markers
- `backend/tests/factories/catalog_mothers.py`: Domain entity factories for catalog
- `backend/tests/factories/orm_factories.py`: ORM model factories (polyfactory)
- `backend/tests/factories/builders.py`: Builder pattern for complex test scenarios
- `backend/tests/factories/identity_mothers.py`: Identity entity mothers
- `backend/tests/fakes/`: In-memory fakes (`fake_uow.py`, `fake_repos.py`, `fake_logger.py`)
- `backend/tests/architecture/`: Architectural boundary enforcement tests (pytest-archon)
- `backend/tests/unit/modules/catalog/domain/`: Domain entity unit tests
- `backend/tests/unit/modules/catalog/application/commands/`: Command handler unit tests (with fakes)
- `backend/tests/integration/modules/catalog/infrastructure/repositories/`: Repository integration tests (testcontainers PostgreSQL)

### ORM Model Registry
- `backend/src/infrastructure/database/registry.py`: Central import of all ORM models across modules for Alembic `--autogenerate`
- When adding a new ORM model, it MUST be imported in this file or Alembic will not detect it

## Naming Conventions

### Files
- Python modules: `snake_case.py`
- Command handler files: `verb_noun.py` (e.g., `create_product.py`, `delete_brand.py`, `change_product_status.py`, `generate_sku_matrix.py`)
- Query handler files: `get_noun.py` or `list_nouns.py` (e.g., `get_brand.py`, `list_brands.py`, `get_product_completeness.py`)
- Router files: `router_{resource}.py` (e.g., `router_brands.py`, `router_products.py`) or `router.py` for single-resource modules
- ORM models: `models.py` (one file per module containing all ORM models)
- Pydantic schemas: `schemas.py` (one file per module)
- DI providers: `dependencies.py` (presentation) or `provider.py` (infrastructure)

### Directories
- Modules: `snake_case` matching the bounded context name (`catalog`, `identity`, `user`, `geo`, `supplier`)
- Layer directories: `domain/`, `application/`, `infrastructure/`, `presentation/`
- Sub-layers: `commands/`, `queries/`, `repositories/`, `consumers/`

### Classes
- Domain entities: `PascalCase` bare names (`Product`, `Brand`, `Category`, `SKU`)
- Value objects: Descriptive names (`Money`, `BehaviorFlags`, `ProductStatus`)
- Command dataclasses: `{Verb}{Noun}Command` (`CreateProductCommand`, `UpdateBrandCommand`, `ChangeProductStatusCommand`)
- Result dataclasses: `{Verb}{Noun}Result` (`CreateProductResult`, `UpdateBrandResult`)
- Handler classes: `{Verb}{Noun}Handler` (`CreateProductHandler`, `ListBrandsHandler`)
- Repository interfaces: `I{Noun}Repository` (`IBrandRepository`, `IProductRepository`)
- Repository implementations: `{Noun}Repository` (`BrandRepository`, `ProductRepository`)
- DI providers: `{Noun}Provider` (`BrandProvider`, `CategoryProvider`, `DatabaseProvider`)
- ORM models: `PascalCase` -- bare name if same as entity (`Brand`), suffixed with `Model` if different (`IdentityModel`, `SessionModel`)
- Read models: `{Noun}ReadModel` / `{Noun}ListReadModel` (`BrandReadModel`, `BrandListReadModel`)
- Pydantic schemas: `{Noun}{Action}Request` / `{Noun}Response` (`BrandCreateRequest`, `BrandResponse`)
- Domain exceptions: `{Entity}{Issue}Error` (`BrandSlugConflictError`, `CategoryMaxDepthError`)
- Domain events: `{Entity}{Action}Event` (`BrandCreatedEvent`, `ProductStatusChangedEvent`)

### Enums and Constants
- Enum classes: `PascalCase` (`ProductStatus`, `AttributeDataType`, `MediaRole`)
- Enum values: lowercase strings via `StrEnum` (`ProductStatus.DRAFT = "draft"`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_CATEGORY_DEPTH`, `DEFAULT_CURRENCY`, `GENERAL_GROUP_CODE`)

## Where to Add New Code

### New Bounded Context Module
1. Create `backend/src/modules/{module_name}/` with subdirectories: `domain/`, `application/`, `infrastructure/`, `presentation/`
2. Domain: Create `entities.py` (attrs `@dataclass` with `AggregateRoot` mixin), `interfaces.py` (abstract repos), `exceptions.py` (inherit from `AppException` subclasses), `events.py` (extend `DomainEvent`), `value_objects.py`
3. Infrastructure: Create `models.py` (SQLAlchemy ORM inheriting `Base` from `src.infrastructure.database.base`), `repositories/` directory with implementations
4. Application: Create `commands/` and `queries/` directories with handler files
5. Presentation: Create `router_*.py` (with `DishkaRoute`), `schemas.py` (inherit `CamelModel`), `dependencies.py` (Dishka `Provider` classes)
6. Register ORM models in `backend/src/infrastructure/database/registry.py`
7. Register DI providers in `backend/src/bootstrap/container.py`
8. Register router in `backend/src/api/router.py` with appropriate prefix
9. Create Alembic migration: `cd backend && alembic revision --autogenerate -m "add {module} tables"`

### New Command (Write Operation)
1. Create `backend/src/modules/{module}/application/commands/{verb}_{noun}.py`
2. Define frozen `{Verb}{Noun}Command` dataclass with input fields
3. Define `{Verb}{Noun}Result` dataclass (if handler returns data)
4. Create `{Verb}{Noun}Handler` class:
   - Constructor: inject `I{Noun}Repository`, `IUnitOfWork`, `ILogger` via positional params
   - Bind logger: `self._logger = logger.bind(handler="{Verb}{Noun}Handler")`
   - `async def handle(self, command: Command) -> Result`: open UoW, validate, mutate, commit
5. Register handler in module's `presentation/dependencies.py`: `provide({Handler}, scope=Scope.REQUEST)`
6. Add router endpoint in `presentation/router_{resource}.py` with `FromDishka[Handler]`

### New Query (Read Operation)
1. Create `backend/src/modules/{module}/application/queries/{action}_{noun}.py`
2. Define frozen `{Action}{Noun}Query` dataclass with filter/pagination params
3. Add read model to `application/queries/read_models.py` if new shape needed
4. Create `{Action}{Noun}Handler` class:
   - Constructor: inject `AsyncSession` and `ILogger` (NOT UoW or repos -- CQRS read side)
   - Use `select(OrmModel)` + `paginate()` helper from `backend/src/shared/pagination.py`
   - Return Pydantic read model, not domain entity
5. Register handler in module's `presentation/dependencies.py`
6. Add router endpoint with `Cache-Control: no-store` header

### New Domain Entity
1. Add attrs `@dataclass` to `backend/src/modules/{module}/domain/entities.py`
2. Include `@classmethod create(cls, *, keyword_only_args) -> Self` factory method with validation
3. Add `_UPDATABLE_FIELDS: ClassVar[frozenset[str]]` whitelist
4. Add `update(**kwargs)` method that rejects unknown fields via `TypeError`
5. Add `__setattr__` guard for immutable fields (use `_GUARDED_FIELDS` frozenset pattern)
6. Define repository interface in `domain/interfaces.py` extending `ICatalogRepository[T]`
7. Create SQLAlchemy ORM model in `infrastructure/models.py`
8. Create repository implementation in `infrastructure/repositories/{entity}.py` extending `BaseRepository`
9. Register ORM model in `backend/src/infrastructure/database/registry.py`

### New Domain Event
1. Add `@dataclass` subclass of `CatalogEvent` (or `DomainEvent`) to `domain/events.py`
2. Use `__init_subclass__` params: `required_fields=("entity_id",)`, `aggregate_id_field="entity_id"`
3. Override `aggregate_type` and `event_type` with non-empty string defaults
4. Emit via `aggregate.add_domain_event(MyEvent(...))` in entity methods or command handlers
5. Register handler in `backend/src/infrastructure/outbox/tasks.py` event handler registry
6. Create consumer task in `backend/src/modules/{module}/application/consumers/`
7. Import consumer in `backend/src/bootstrap/worker.py` (after dishka setup, with `# noqa`)

### New Frontend Page (Admin)
1. Create `frontend/admin/src/app/admin/{section}/page.jsx` for the page
2. Create `frontend/admin/src/app/api/{resource}/route.js` for BFF API proxy
3. Create components in `frontend/admin/src/components/admin/{section}/`
4. Use `backendFetch()` from `frontend/admin/src/lib/api-client.js` for server-side API calls

### New Frontend Page (Main)
1. Create `frontend/main/app/{section}/page.tsx` for the page
2. API calls go through catch-all proxy at `app/api/backend/[...path]/route.ts`
3. Create components in `frontend/main/components/blocks/{section}/`
4. Use Redux Toolkit hooks from `frontend/main/lib/store/hooks.ts`

### New Migration
- Generate: `cd backend && alembic revision --autogenerate -m "description"`
- Migrations go to: `backend/alembic/versions/YYYY/MM/` (date-based subdirectories)
- Apply: `cd backend && alembic upgrade head`

## Special Directories

**`backend/src/infrastructure/outbox/`:**
- Purpose: Transactional Outbox pattern (relay, pruning, event handler registry)
- Generated: No
- Committed: Yes

**`backend/alembic/versions/`:**
- Purpose: Database migration scripts (auto-generated + manual)
- Generated: Partially (via `--autogenerate`)
- Committed: Yes

**`backend/seed/`:**
- Purpose: Development/staging data seeding (categories, brands, attributes, products, geo)
- Entry point: `python -m seed` from backend directory
- Generated: No
- Committed: Yes

**`backend/tests/factories/`:**
- Purpose: Test data factories, object mothers, and builders
- Key files: `catalog_mothers.py` (domain), `orm_factories.py` (ORM), `builders.py` (complex scenarios)
- Generated: No
- Committed: Yes

**`backend/.venv/`:**
- Purpose: Python virtual environment (uv)
- Generated: Yes (via `uv sync`)
- Committed: No

**`frontend/*/.next/`:**
- Purpose: Next.js build cache
- Generated: Yes
- Committed: No

**`frontend/*/node_modules/`:**
- Purpose: NPM dependencies
- Generated: Yes
- Committed: No

**`backend/.hypothesis/`:**
- Purpose: Hypothesis property-based testing cache
- Generated: Yes
- Committed: No (but present in repo)

---

*Structure analysis: 2026-03-28*
