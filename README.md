# Loyality — Loyalty Marketplace Platform

Production-grade e-commerce marketplace built as a **modular monolith** with Clean Architecture, CQRS, and domain-driven design. The platform aggregates local and cross-border suppliers into a single storefront with integrated logistics, dynamic pricing, and a loyalty program.

**Solo-developed** from architecture to deployment.

---

## Codebase at a Glance

| Metric | Value |
|--------|-------|
| Commits | 750+ |
| Backend source files | 442 |
| Lines of code (backend modules) | 82,600+ |
| Bounded contexts | 9 |
| Domain entities (`attrs.define`) | 49 |
| Value objects | 84 |
| Domain events | 111 |
| CQRS command handlers | 121 |
| CQRS query handlers | 90 |
| Protocol interfaces (domain + shared) | 35 |
| ORM models (Data Mapper) | 64 |
| Repository implementations | 84 |
| Pydantic schemas | 264 |
| API endpoints | 74 |
| Alembic migrations | 25 |
| Test files | 151 |
| Test functions | 1,731 |
| Enum types | 25 |
| DI provider classes (Dishka) | 19 |
| Deployable services | 3 |
| Frontend apps | 2 |

---

## Architecture

```
                          ┌────────────────────────────────────────────────────────────────────────────┐
                          │                                                                            │
    ┌──────────────┐      │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐ ┌─────┐ ┌─────────┐        │
    │  Frontend    │──────│─▶│ Catalog │ │Identity │ │Pricing  │ │ Cart │ │ Geo │ │Supplier │        │
    │  Next.js 16  │      │  └─────────┘ └─────────┘ └─────────┘ └──────┘ └─────┘ └─────────┘        │
    │  (Main)      │      │  ┌──────────┐ ┌─────────┐ ┌──────────┐                                    │
    └──────────────┘      │  │Logistics │ │  User   │ │ Activity │    Backend (FastAPI, Python 3.14)   │
                          │  └──────────┘ └─────────┘ └──────────┘                                    │
    ┌──────────────┐      │       │              │            │                                        │
    │  Frontend    │──────│─▶     └──────────────┴────────────┘                                        │
    │  Next.js 16  │      │       │                                                                    │
    │  (Admin)     │      │  ┌────┴──────────────────────────────────────────────────────────────────┐  │
    └──────────────┘      │  │  Shared: PostgreSQL 18 · Redis 8 · RabbitMQ 4 · S3/MinIO            │  │
                          │  └──────────────────────────────────────────────────────────────────────┘  │
    ┌──────────────┐      │       │                                                                    │
    │ Telegram Bot │──────│─▶     │  X-API-Key                                                        │
    │  Aiogram 3   │      │       ▼                                                                    │
    └──────────────┘      │  ┌───────────────────────────────────┐                                    │
                          │  │  Image Backend (FastAPI + Pillow)  │                                    │
                          │  └───────────────────────────────────┘                                    │
                          └────────────────────────────────────────────────────────────────────────────┘
```

Three deployable services, two frontends, one Telegram bot — deployed on Railway (backends) and Netlify (frontends).

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.14, FastAPI, async SQLAlchemy 2.1, Alembic, Dishka DI, TaskIQ + RabbitMQ |
| **Image Service** | FastAPI, Pillow, aiobotocore, presigned upload pipeline |
| **Frontend (Customer)** | Next.js 16, TypeScript, React 19, Redux Toolkit, RTK Query |
| **Frontend (Admin)** | Next.js 16, JSX, Tailwind CSS 4 |
| **Telegram Bot** | Aiogram 3, FSM states, inline keyboards |
| **Infrastructure** | PostgreSQL 18, Redis 8.4, RabbitMQ 4.2, MinIO (S3), Docker Compose |
| **Quality** | Ruff, mypy, pytest (unit / integration / e2e / architecture fitness tests) |
| **Deploy** | Railway (backends), Netlify (frontends) |

---

## What Demonstrates Senior-Level Engineering

### 1. Domain-Driven Design — Not Just Folder Structure

This is not "DDD" where you rename folders to `domain/` and call it a day. The domain layer is **genuinely framework-free**: 49 entities built with `attrs.define`, 84 value objects, 111 typed domain events — zero imports from FastAPI, SQLAlchemy, or any infrastructure framework.

- **Aggregate roots** with factory methods (`Entity.create(...)`) and encapsulated invariants
- **Data Mapper pattern** — 64 ORM models are completely separate from 49 domain entities; repositories handle the conversion. No Active Record, no `Base.query`
- **Domain events** are first-class citizens: collected in-memory on aggregates, flushed atomically via transactional outbox
- **35 Protocol interfaces** define contracts between layers — domain depends on abstractions, infrastructure implements them

### 2. CQRS — 121 Commands, 90 Queries, Strict Separation

Every write operation follows the same structure: frozen dataclass command → handler class with constructor-injected deps → `async with uow` → aggregate mutation → domain event → `uow.commit()`.

- **121 command handler files** (writes) and **90 query handler files** (reads) — not a single endpoint that mixes both
- Queries read directly from ORM (performance) while commands go through domain entities (correctness) — a deliberate CQRS tradeoff, not laziness
- Commands may compose queries (read-your-writes) but never the reverse

### 3. Transactional Outbox — Reliable Event-Driven Communication

Modules don't call each other. Period. They communicate through domain events persisted atomically in the same transaction as the aggregate change.

- **111 domain event types** across 9 modules — persisted to `outbox_messages` table within `UnitOfWork.commit()`
- Outbox relay polls with `FOR UPDATE SKIP LOCKED` — multiple workers can run in parallel without blocking
- Each event processed in its own transaction — one failure doesn't block the queue
- `correlation_id` propagated from HTTP request context through the outbox for end-to-end tracing
- Processed records pruned after 7 days

### 4. Architecture Fitness Tests — Boundaries Enforced in CI

Not just a convention documented in a wiki — architectural rules are **executable tests** that break the build:

```
tests/architecture/test_boundaries.py
```

Parametrized across all 9 modules, these tests enforce:
- Domain layer MUST NOT import application, infrastructure, presentation, or any framework
- Application commands MUST NOT import infrastructure (with documented, whitelisted exceptions for CQRS read-side and reference-data module)
- Modules MUST NOT import each other's internals — every cross-module exception is whitelisted and justified
- Shared kernel (`src/shared/`) MUST NOT import any business module

### 5. 9 Bounded Contexts — Real Module Isolation

Each module is a self-contained vertical slice with 4 layers (`domain → application → infrastructure → presentation`), its own DI provider, its own ORM models, its own router files.

| Module | What makes it non-trivial |
|--------|--------------------------|
| **catalog** | Multi-variant products with EAV attributes, attribute templates with per-category bindings, full-text search vector (tsvector), storefront with keyset pagination, trending/for-you feed |
| **identity** | 3 auth providers (email/Argon2id, OIDC, Telegram HMAC-SHA256), JWT access+refresh with rotation, max 5 concurrent sessions, hierarchical RBAC resolved via recursive CTE, Redis-cached permissions (300s TTL) |
| **pricing** | Versioned formula AST (draft → published → archived), pure-domain Decimal evaluator (no floating-point), 5-level variable scoping (global → supplier-type → category → range → product), pricing contexts with rounding modes |
| **logistics** | Shipment aggregate with FSM (6 states, cancel/return branches), append-only tracking events, multi-carrier abstraction (CDEK + Yandex Delivery), OAuth2 token management with force-refresh, webhook ingestion |
| **cart** | Cart aggregate with FSM (ACTIVE → FROZEN → MERGED → ORDERED), anonymous guest tokens, cart merge on login, checkout snapshots |
| **supplier** | Supplier types (local/cross-border), onboarding workflow, type-based pricing context mapping |
| **user** | PII-isolated storage, GDPR account deletion cascading via domain events |
| **geo** | ISO 3166-1/2, OKTMO/FIAS districts, ISO 4217 currencies, BCP 47 languages with multi-language translations |
| **activity** | Fire-and-forget Redis hot path (LPUSH + ZINCRBY pipeline), flush to partitioned PostgreSQL, co-view matrix for recommendations |

### 6. Real Third-Party Integrations — Not Mocked APIs

**CDEK** (carrier) — full lifecycle through their REST API:
- Rate calculation, order creation, intake scheduling, delivery slot booking, tracking webhook processing, return registration
- OAuth2 client credentials flow with token caching and force-refresh on 401

**Yandex Delivery** — rate quotes, pickup point search with caching, delivery scheduling

Both providers sit behind a **provider-agnostic `IShippingProvider` interface** — adding a new carrier means implementing one adapter, not touching any business logic.

### 7. Pricing Engine — Not CRUD, a Formula Evaluator

The pricing module is a domain-level formula evaluation engine:
- Formula AST stored in PostgreSQL, versioned with draft/published/archived lifecycle
- Pure-domain `Decimal` evaluator — no floating-point arithmetic anywhere in pricing
- Variables resolved through 5-level scope chain: global → supplier-type → category → range → product-level inputs
- Preview endpoint lets admins simulate price changes before publishing
- SKU-level autonomous recompute triggered by domain events (ADR-005)

### 8. Testing Maturity — 1,731 Tests Across 4 Levels

| Level | Files | Tests | What it proves |
|-------|-------|-------|---------------|
| **Unit** | 92 | ~1,400 | Domain entities, value objects, command/query handlers, mappers, validators |
| **Integration** | 35 | ~200 | Repositories against real PostgreSQL, Redis operations, outbox relay |
| **E2E** | 23 | ~100 | Full HTTP request → response cycles through FastAPI |
| **Architecture** | 1 | 30+ | Parametrized boundary checks across all 9 modules |

Test infrastructure:
- **Builder pattern factories** in `tests/factories/` — 11 factory/builder files for domain entities and ORM models
- **22 parametrized test suites** — edge cases covered systematically, not ad-hoc
- **DB isolation** — each test gets a nested transaction (savepoint), rolled back after completion
- **Session-scoped Alembic** — migrations run once per session via subprocess
- **Redis flushed per test** in integration/e2e
- **30s timeout per test** — no hanging tests in CI

### 9. Security — Not an Afterthought

- **Argon2id** password hashing (not bcrypt) via pwdlib
- **JWT** with HS256, access/refresh token rotation, max 5 sessions per identity
- **RBAC** with hierarchical roles resolved via recursive CTE, permissions cached in Redis (300s TTL)
- **Telegram Mini App** auth via HMAC-SHA256 validation
- **GDPR** — one-click account deactivation with cascading PII anonymization through domain events
- **Correlation IDs** — request-scoped, propagated through outbox events for audit trail
- **Staff invitations** — token-based workflow with expiry validation

### 10. Infrastructure & Observability

- **Structured logging** — JSON-formatted via structlog with request correlation IDs
- **Dead Letter Queue** — failed TaskIQ tasks persisted in `failed_tasks` table, not silently dropped
- **Transactional outbox relay** — concurrent-safe with `FOR UPDATE SKIP LOCKED`, auto-prunes processed events
- **Background worker** — TaskIQ + RabbitMQ for async event processing
- **Presigned upload pipeline** — 3-step media flow through dedicated image microservice (reserve → upload → confirm → async resize to WebP variants)
- **Seed system** — step-based runner with dependency ordering (roles → admin → geo → brands → categories → products)

### 11. Code Organization — Consistent Conventions

Not just "it works" — it's systematically organized:

- **39 router files** following `router_<scope>.py` naming convention
- **264 Pydantic schemas** — request/response DTOs in `presentation/schemas.py`
- **DI providers always in `infrastructure/provider.py`** — wiring is an infrastructure concern
- **Naming is enforced**: entities, commands, handlers, repositories, providers all follow the same patterns across 9 modules
- **Error handling** — uniform JSON envelope `{"error": {"code", "message", "details", "request_id"}}` with 6 exception types mapped to HTTP codes

---

## Project Structure

```
loyality/
├── backend/                   # Main API — FastAPI, Clean Architecture
│   ├── src/
│   │   ├── modules/           # 9 bounded contexts (442 source files)
│   │   ├── infrastructure/    # Cross-cutting: DB, cache, security, outbox
│   │   ├── api/               # HTTP layer, middleware, auth
│   │   ├── bot/               # Telegram bot (Aiogram 3)
│   │   ├── bootstrap/         # Composition root, DI container, config
│   │   └── shared/            # Shared kernel: interfaces, exceptions, pagination
│   ├── tests/                 # 151 test files, 1,731 test functions
│   ├── alembic/               # 25 database migrations
│   └── seed/                  # Reference data seeding
│
├── image_backend/             # Image processing microservice (73 source files)
│   ├── src/                   # Presigned upload → Pillow resize → WebP variants
│   └── tests/
│
├── frontend/
│   ├── main/                  # Customer-facing — Next.js 16, TypeScript, React 19
│   └── admin/                 # Admin panel — Next.js 16, Tailwind CSS 4
│
└── docker-compose.yml         # PostgreSQL 18, Redis 8.4, RabbitMQ 4.2, MinIO
```

---

## Quick Start

```bash
# 1. Infrastructure
cd backend && docker compose up -d

# 2. Dependencies
uv sync

# 3. Environment
cp .env.example .env

# 4. Database
uv run alembic upgrade head

# 5. Run
uv run uvicorn src.bootstrap.web:create_app --factory --reload --port 8080

# 6. Open interactive API docs
open http://localhost:8080/docs
```

See [`backend/README.md`](backend/README.md) for full API reference with 74 endpoints documented.

---

## License

MIT
