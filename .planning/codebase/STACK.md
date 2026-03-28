# Technology Stack

**Analysis Date:** 2026-03-28

## Overview

Multi-service monorepo with four deployable units:

| Service | Language | Framework | Default Port |
|---------|----------|-----------|-------------|
| `backend/` | Python 3.14 | FastAPI | 8000 |
| `image_backend/` | Python 3.14 | FastAPI | 8001 |
| `frontend/admin/` | JavaScript (JSX) | Next.js 16 | 3000 |
| `frontend/main/` | TypeScript (TSX) | Next.js 16 | 3001 |

## Languages

**Primary:**
- Python 3.14 - Both backend services (`backend/`, `image_backend/`)
- TypeScript - Customer-facing frontend (`frontend/main/`)
- JavaScript (JSX, no TypeScript) - Admin dashboard (`frontend/admin/`)

**Secondary:**
- SQL - Alembic migrations, raw queries in outbox relay (`backend/src/infrastructure/outbox/relay.py`)
- CSS Modules - Component-scoped styles in `frontend/main/` (70+ module files)
- Shell - Entrypoint scripts (`backend/scripts/entrypoint.sh`)

## Runtime

**Python Services:**
- CPython 3.14 (pinned in `.python-version` files)
- Docker base: `python:3.14-slim-trixie`
- ASGI server: Uvicorn with `standard` extras (uvloop + httptools)

**Frontend Services:**
- Node.js (no version pinned; no `.nvmrc` or `.node-version`)
- Next.js 16 App Router (both admin and main)

## Package Managers

**Python:**
- **uv** (Astral) - Both Python services
- Lockfile: `uv.lock` present in `backend/` and `image_backend/`
- Workspace: `backend/pyproject.toml` declares `[tool.uv.workspace]`
- Docker installs via: `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`

**JavaScript/TypeScript:**
- **npm** - Both frontend apps
- Lockfile: `package-lock.json` in `frontend/admin/` and `frontend/main/`

## Frameworks

**Core Web:**
- FastAPI `>=0.115.0` - REST API for both Python services
  - Entry: `backend/main.py`, `image_backend/main.py`
  - App factory: `backend/src/bootstrap/web.py`, `image_backend/src/bootstrap/web.py`
- Next.js `^16.1.x` - React meta-framework for both frontends
  - Admin config: `frontend/admin/next.config.js` (webpack mode)
  - Main config: `frontend/main/next.config.ts`
- React `19.x` - UI library

**Telegram:**
- Aiogram `>=3.26.0` - Telegram Bot framework (backend only)
  - Bot factory: `backend/src/bot/factory.py`
  - initData HMAC validation: `backend/src/infrastructure/security/telegram.py`

**ORM / Database:**
- SQLAlchemy `>=2.1.0b1` (async mode) - Both Python services
  - Driver: `asyncpg >=0.31.0`
- Alembic `>=1.18.4` - Migrations
  - Config: `backend/alembic.ini`, `image_backend/alembic.ini`
  - File template: date-based subdirectories (`%%(year)d/%%(month).2d/...`)
  - Recursive version locations enabled

**Dependency Injection:**
- Dishka `>=1.9.1` - Async DI container for both Python services
  - Container: `backend/src/bootstrap/container.py`, `image_backend/src/bootstrap/container.py`
  - FastAPI integration: `dishka.integrations.fastapi`
  - TaskIQ integration: `dishka.integrations.taskiq`

**Domain Modeling:**
- attrs `>=25.4.0` - Immutable value objects and domain entities

**Background Tasks:**
- TaskIQ `>=0.12.1` - Distributed task queue
  - Broker: `taskiq-aio-pika >=0.6.0` (RabbitMQ AMQP)
  - Config: `backend/src/bootstrap/broker.py`, `image_backend/src/bootstrap/broker.py`
  - Worker: `backend/src/bootstrap/worker.py`, `image_backend/src/bootstrap/worker.py`
  - Scheduler (Beat): `backend/src/bootstrap/scheduler.py`

**State Management (Frontend):**
- Redux Toolkit + RTK Query - `frontend/main/` only
  - Store: `frontend/main/lib/store/store.ts`
  - API layer with auto-reauth: `frontend/main/lib/store/api.ts`
  - Tag types: `User`, `Products`, `Product`, `Categories`, `Brands`
- No state management library in `frontend/admin/` (React hooks + fetch)

**Testing:**
- pytest `>=9.0.2` - Both Python services
  - Config: `backend/pytest.ini`, both `pyproject.toml [tool.pytest.ini_options]`
  - pytest-asyncio `>=1.3.0` (asyncio_mode = "auto", session-scoped loop)
  - pytest-cov `>=7.0.0` (auto-coverage via `--cov=src`)
  - pytest-archon `>=0.0.7` - Architecture fitness tests (backend only)
- Testcontainers `>=4.14.1` - Integration tests with real infra (backend only)
  - Containers: postgres, redis, rabbitmq, minio
- Polyfactory `>=3.3.0` - Test data factories (backend only)
- Locust `>=2.43.3` - Load testing (backend only)

**Linting / Formatting (Python):**
- Ruff - Linter + formatter
  - Config: `[tool.ruff]` in both `pyproject.toml`
  - Target: `py314`, line-length: 88
  - Rules: `E, F, W, I, UP, B, SIM, RUF`
  - Ignored: `E501, RUF001-003, B008, UP042, UP046`
  - isort: `known-first-party = ["src"]`
- mypy `>=1.19.1` - Static type checking
  - Config: `[tool.mypy]` in `backend/pyproject.toml`
  - Plugin: `pydantic.mypy`
  - `disallow_untyped_defs = true` (except tests)

**Linting / Formatting (JavaScript/TypeScript):**
- ESLint 9 - Linting
  - Admin: `frontend/admin/eslint.config.mjs` (next core-web-vitals)
  - Main: `frontend/main/eslint.config.mjs` (next core-web-vitals)
- Prettier `^3.6.2` - Formatting (admin only)
  - Config: `frontend/admin/.prettierrc`
  - Semi: true, singleQuote: true, trailingComma: "all"
  - Plugin: `prettier-plugin-tailwindcss`

## Key Dependencies

**Critical (Backend):**
- `pydantic-settings` - Env config validation (`backend/src/bootstrap/config.py`)
- `structlog >=25.5.0` - Structured logging (JSON prod, colored dev)
- `pyjwt[crypto] >=2.12.0` - JWT signing/verification (`backend/src/infrastructure/security/jwt.py`)
- `pwdlib[argon2,bcrypt] >=0.3.0` - Password hashing (`backend/src/infrastructure/security/password.py`)
- `httpx[http2] >=0.28.1` - Async HTTP client for server-to-server calls
- `cachetools >=7.0.5` - In-memory caching
- `redis[hiredis] >=7.3.0` - Async Redis with C extension

**Critical (Image Backend):**
- `aiobotocore >=3.2.1` - S3-compatible storage (`image_backend/src/infrastructure/storage/factory.py`)
- `pillow >=11.0.0` - Image processing (resize, WebP, thumbnails)
- `python-multipart >=0.0.22` - Multipart upload handling
- `pydantic-settings >=2.0.0` - Env config
- `python-dotenv >=1.2.2` - .env file loading

**Critical (Frontend Main):**
- `@reduxjs/toolkit ^2.11.2` + `react-redux ^9.2.0` - State + API layer
- `leaflet ^1.9.4` + `leaflet.markercluster ^1.5.3` - Maps for pickup points
- `lucide-react 0.555.0` - Icon library (pinned exact version)
- `clsx ^2.1.1` - Conditional class merging

**Critical (Frontend Admin):**
- `clsx ^2.1.1` + `tailwind-merge ^3.4.0` - Class merging via `cn()` utility
- `dayjs ^1.11.18` - Date formatting (`frontend/admin/src/lib/dayjs.js`)
- `@svgr/webpack ^8.1.0` - SVG-as-React-component imports

## CSS / Styling

**Frontend Admin (`frontend/admin/`):**
- Tailwind CSS `^4.1.12` (v4) with PostCSS plugin `@tailwindcss/postcss`
- Custom `app-*` design token palette in `frontend/admin/tailwind.config.js`
- Convention: always use `cn()` from `@/lib/utils` (wraps clsx + twMerge), never raw `clsx()`
- PostCSS config: `frontend/admin/postcss.config.js`
- Content path: `./src/**/*.{js,jsx,mdx}`

**Frontend Main (`frontend/main/`):**
- **CSS Modules exclusively** -- no Tailwind CSS
- Self-hosted Inter font family (400/500/600/700 weights, WOFF2)
- Global styles: `frontend/main/app/globals.css`
- PostCSS config present but empty plugins: `frontend/main/postcss.config.mjs`

## Configuration

**Environment Variables (Backend -- `backend/.env.example`):**
- `PROJECT_NAME`, `VERSION`, `ENVIRONMENT`, `DEBUG` - App metadata
- `SECRET_KEY` - JWT signing (critical)
- `CORS_ORIGINS` - Comma-separated allowed origins
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL
- `REDISHOST`, `REDISPORT`, `REDISUSER`, `REDISPASSWORD`, `REDISDATABASE` - Redis
- `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY` - Image Backend connectivity
- `RABBITMQ_URL`, `RABBITMQ_PRIVATE_URL` - RabbitMQ
- `BOT_TOKEN`, `BOT_ADMIN_IDS`, `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET` - Telegram Bot
- `THROTTLE_RATE`, `FSM_STATE_TTL`, `FSM_DATA_TTL` - Bot throttling/FSM

**Environment Variables (Image Backend -- `image_backend/.env.example`):**
- `PROJECT_NAME`, `VERSION`, `ENVIRONMENT`, `DEBUG` - App metadata
- `CORS_ORIGINS` - Allowed origins
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL
- `REDISHOST`, `REDISPORT`, `REDISUSER`, `REDISPASSWORD`, `REDISDATABASE` - Redis
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3/MinIO
- `RABBITMQ_PRIVATE_URL` - RabbitMQ
- `INTERNAL_API_KEY` - Service-to-service auth key

**Environment Variables (Frontend Main -- `frontend/main/.env.example`):**
- `BACKEND_API_BASE_URL` - Backend base URL for BFF proxy
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData address API
- `COOKIE_DOMAIN` - Auth cookie domain
- `BROWSER_DEBUG_AUTH`, `NEXT_PUBLIC_BROWSER_DEBUG_AUTH` - Dev-only mock auth

**Environment Variables (Frontend Admin -- `frontend/admin/.env.local.example`):**
- `BACKEND_URL` - Backend base URL for server-side calls

**Config loading:**
- Python services: Pydantic `BaseSettings` loading from `.env` file
  - Backend: `backend/src/bootstrap/config.py`
  - Image Backend: `image_backend/src/bootstrap/config.py`
- Frontend: `process.env.*` (Next.js built-in env handling)

**Build Config Files:**
- `backend/pyproject.toml` - Python project metadata + tool config
- `image_backend/pyproject.toml` - Same
- `backend/Dockerfile`, `image_backend/Dockerfile` - Docker builds
- `backend/railway.toml`, `image_backend/railway.toml` - Railway deployment
- `frontend/main/netlify.toml` - Netlify deployment
- `frontend/admin/next.config.js`, `frontend/main/next.config.ts` - Next.js config

## Platform Requirements

**Development:**
- Python 3.14 + uv
- Node.js + npm
- Docker + Docker Compose (for infrastructure services)
- Git

**Local Infrastructure (docker-compose):**
- PostgreSQL 18 Alpine (`backend/docker-compose.yml`)
- Redis 8.4 Alpine (256MB max, allkeys-lru eviction)
- RabbitMQ 4.2.4 Management Alpine
- MinIO (S3-compatible object storage)

**Production:**
- Railway - Both Python services (Dockerfile-based deploy)
- Netlify - Frontend Main (`frontend/main/netlify.toml`, `@netlify/plugin-nextjs`)
- Frontend Admin - Deployment target not explicitly configured

## Run Commands

```bash
# ---------- Backend API ----------
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# ---------- Backend Worker ----------
cd backend
uv run taskiq worker src.bootstrap.worker:broker

# ---------- Backend Scheduler ----------
cd backend
uv run taskiq scheduler src.bootstrap.scheduler:scheduler

# ---------- Image Backend API ----------
cd image_backend
uv run uvicorn main:app --host 0.0.0.0 --port 8001

# ---------- Frontend Admin ----------
cd frontend/admin
npm run dev

# ---------- Frontend Main ----------
cd frontend/main
npm run dev

# ---------- Infrastructure ----------
cd backend
docker compose up -d

# ---------- Testing (Backend) ----------
make test              # all tests
make test-unit         # unit only
make test-integration  # integration with testcontainers
make test-e2e          # end-to-end API tests
make test-architecture # architecture fitness functions
make lint              # ruff check
make format            # ruff fix + format
make typecheck         # mypy
```

---

*Stack analysis: 2026-03-28*
