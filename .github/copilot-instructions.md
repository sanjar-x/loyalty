# Loyality — Copilot Instructions

Loyalty marketplace: modular monolith with three deployable services and two frontends.

## Components

| Component | Path | Tech | Port |
|---|---|---|---|
| Backend | `backend/` | FastAPI, Python 3.14, Clean Architecture | 8080 |
| Image Backend | `image_backend/` | FastAPI, Python 3.14, Pillow, aiobotocore | 8080 |
| Frontend Main | `frontend/main/` | Next.js 16, TypeScript, React 19, TanStack Query, Zustand | 3000 |
| Frontend Admin | `frontend/admin/` | Next.js 16, JSX (no TypeScript), Tailwind CSS 4 | 3000 |
| Telegram Bot | `backend/src/bot/` | Aiogram 3, FSM states | — |

Each component has its own `CLAUDE.md` with detailed architecture — read it when working in that directory.

## Infrastructure

```bash
# From backend/ or image_backend/:
docker compose up -d    # Postgres 18, Redis 8.4, RabbitMQ 4.2, MinIO
```

## Commands

### Backend (`backend/`)

```bash
uv sync                          # Dependencies (uv, NOT pip)
uv run uvicorn main:app --reload --port 8080

# Tests (docker compose required for non-unit tests)
make test                        # all tests
make test-unit                   # domain-only, no I/O
make test-integration            # real DB
make test-e2e                    # HTTP round-trips
make test-architecture           # Clean Architecture boundary enforcement
uv run pytest tests/path/to/test_file.py::test_name -v  # single test

# Lint & format
make lint                        # ruff check
make format                      # ruff check --fix + ruff format
make typecheck                   # mypy

# Migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### Frontend Main (`frontend/main/`)

```bash
pnpm install
pnpm dev                         # next dev (port 3000)
pnpm build
pnpm lint                        # eslint --max-warnings=0
pnpm typecheck                   # tsc --noEmit
pnpm vitest                      # unit tests
pnpm playwright test             # e2e tests
```

### Frontend Admin (`frontend/admin/`)

```bash
npm install
npm run dev                      # next dev --webpack (port 3000)
npm run build                    # next build --webpack
npm run lint                     # eslint .
npm run format                   # prettier --write .
```

Uses `--webpack` because `@svgr/webpack` requires webpack instead of Turbopack.

### Image Backend (`image_backend/`)

```bash
uv sync
uv run uvicorn main:app --reload --port 8080
uv run alembic upgrade head
```

## Architecture

### Cross-Service Communication

```
Frontend Main ──cookie──▸ BFF proxy ──Bearer──▸ Backend API (/api/v1/*)
Frontend Admin ──cookie──▸ BFF proxy ──Bearer──▸ Backend API (/api/v1/*)
                           BFF proxy ──API-Key──▸ Image Backend (/api/v1/media/*)
Backend ──X-API-Key──▸ Image Backend (delete only)
Telegram Bot ──direct──▸ Backend API
```

Auth: JWT (HS256) + RBAC (admin → manager → customer). Telegram Mini App: HMAC-SHA256.
Error envelope: `{"error": {"code", "message", "details", "request_id"}}`.

### Backend — Clean Architecture + Modular Monolith

Each module in `src/modules/{catalog,identity,user,geo,supplier}/` has 4 layers:

- **domain/** — `attrs` entities inheriting `AggregateRoot`, value objects, domain events, interfaces (Protocols). Zero framework imports.
- **application/** — `commands/` (CQRS write), `queries/` (CQRS read, may use ORM directly), `consumers/` (event handlers).
- **infrastructure/** — SQLAlchemy models (Data Mapper pattern), repository implementations, Dishka providers.
- **presentation/** — FastAPI routers, Pydantic schemas.

**Layer rules** (enforced by architecture tests):
- Domain must not import application/infrastructure/presentation or any framework
- Application commands must not import infrastructure (queries and consumers are exempt — CQRS read-side)
- Modules must not import each other's domain/application/infrastructure
- `src/shared/` is the shared kernel — must not import any module

**Command/Handler pattern** for all write operations:

```python
@dataclass(frozen=True)
class CreateFooCommand:
    name: str

class CreateFooHandler:
    def __init__(self, repo: IFooRepository, uow: IUnitOfWork, logger: ILogger) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateFooHandler")

    async def handle(self, command: CreateFooCommand) -> CreateFooResult:
        async with self._uow:
            entity = Foo.create(...)
            entity = await self._repo.add(entity)
            entity.add_domain_event(FooCreatedEvent(...))
            self._uow.register_aggregate(entity)
            await self._uow.commit()
        return CreateFooResult(foo_id=entity.id)
```

**DI (Dishka)**: inject via `FromDishka[Type]` in router parameters. Container in `src/bootstrap/container.py`.

**Transactional Outbox**: domain events collected on `AggregateRoot`, serialized to `outbox_messages` on `uow.commit()`, relayed to RabbitMQ by TaskIQ scheduler.

### Frontend Main — Feature-Sliced Architecture

TypeScript, React 19, Next.js 16 App Router, TanStack React Query, Zustand, Tailwind CSS 4, `ky` HTTP client.

- **Features**: `src/features/{auth,cart,catalog,favorites,orders,product,search,telegram,...}/` — each feature is self-contained
- **Data fetching**: TanStack React Query with centralized query keys in `src/lib/query-keys.ts`
- **HTTP**: `ky`-based clients — `api-client.ts` (client-side, BFF proxy) and `api-server.ts` (server-side, direct)
- **State**: Zustand stores in `src/stores/`
- **BFF proxy**: `src/app/api/` routes forward to backend, managing auth cookies server-side
- **Testing**: Vitest (unit) + Playwright (e2e) + MSW (API mocking)
- **Path alias**: `@/*` → `src/*`
- **Package manager**: pnpm

### Frontend Admin — BFF + Service Layer

JavaScript/JSX (no TypeScript), Next.js 16 App Router, Tailwind CSS 4, CSS Modules.

- **Data flow**: `services/*.js` (client) → `app/api/` routes (BFF) → `backendFetch()` / `imageBackendFetch()` (server-side)
- **Auth**: `useAuth()` hook + `AuthProvider` context. JWT in httpOnly cookies.
- **Class merging**: always use `cn()` from `@/lib/utils` — never `clsx()` directly
- **SVG icons**: import from `src/assets/icons/*.svg` as React components via `@svgr/webpack`
- **i18n**: product data uses `{ru, en}` objects. Use `i18n(obj)` to extract, `buildI18nPayload(ru, en)` to construct
- **Design tokens**: custom `app-*` color palette in `tailwind.config.js` — use these instead of raw Tailwind colors
- **Path alias**: `@/*` → `src/*`
- **Package manager**: npm

### Image Backend

Single-module Clean Architecture service. Handles image upload via presigned S3 URLs (MinIO), then processes variants (thumbnail, medium, large, WebP) via TaskIQ workers. Auth: X-API-Key header (server-to-server).

## Key Conventions

- **Backend entities**: `attrs.define` classes + `AggregateRoot`, factory methods (`Entity.create()`). ORM models are separate (Data Mapper).
- **Backend exceptions**: use hierarchy from `src/shared/exceptions.py` — `NotFoundError`, `ConflictError`, `ValidationError`, etc.
- **Backend DB naming**: `ix_`, `uq_`, `ck_`, `fk_`, `pk_` prefixes. Alembic migrations auto-formatted by ruff.
- **Backend config**: Pydantic Settings in `src/bootstrap/config.py`, reads `.env` file.
- **Backend tests**: markers `@pytest.mark.unit/integration/e2e/architecture`. Builder-pattern factories in `tests/factories/`. Each test gets a rolled-back savepoint.
- **Both frontends**: BFF pattern — browser never calls backend directly. Auth tokens in httpOnly cookies.
- **Product status FSM**: `draft → enriching → ready_for_review → published → archived`.
