# Technology Stack

**Analysis Date:** 2026-03-29

## Languages

**Primary:**
- Python 3.14 - Backend API (`backend/`) and Image microservice (`image_backend/`)
- TypeScript - Customer-facing Telegram Mini App frontend (`frontend/main/`)

**Secondary:**
- JavaScript (ES2017+) - Admin dashboard frontend (`frontend/admin/`), no TypeScript
- SQL - Alembic migration scripts (`backend/alembic/versions/`, `image_backend/alembic/versions/`)
- Shell (bash) - Entrypoint script (`backend/scripts/entrypoint.sh`)

## Runtime

**Environment:**
- CPython 3.14 (pinned in `backend/.python-version` and `image_backend/.python-version`)
- Docker base image: `python:3.14-slim-trixie` (`backend/Dockerfile`, `image_backend/Dockerfile`)
- Node.js (version not pinned; no `.nvmrc` detected)
- Browser target: Telegram WebApp WebView (primary), desktop browsers (admin)

**Package Manager:**
- `uv` (Python) - Both backend services
  - Lockfiles: `backend/uv.lock` (present), `image_backend/uv.lock` (present)
  - Installed from `ghcr.io/astral-sh/uv:latest` in Dockerfiles
- `npm` (JavaScript/TypeScript) - Both frontends
  - Lockfiles: `frontend/main/package-lock.json` (present), `frontend/admin/package-lock.json` (present)

## Frameworks

**Core:**
- FastAPI `>=0.115.0` - REST API for both backends (`backend/src/bootstrap/web.py`, `image_backend/src/bootstrap/web.py`)
- Next.js `^16.1.x` - Both frontend applications using App Router (`frontend/main/package.json`, `frontend/admin/package.json`)
- React `19.x` - UI rendering for both frontends
- Aiogram `>=3.26.0` - Telegram bot framework (`backend/src/bot/factory.py`)
- SQLAlchemy `>=2.1.0b1` (async mode) - ORM and query builder (`backend/pyproject.toml`)
- Alembic `>=1.18.4` - Database migrations (`backend/alembic.ini`, `image_backend/alembic.ini`)
- Dishka `>=1.9.1` - Async dependency injection container (`backend/src/bootstrap/container.py`)
- TaskIQ `>=0.12.1` + TaskIQ AioPika `>=0.6.0` - Background task queue via RabbitMQ (`backend/src/bootstrap/broker.py`)

**Testing:**
- pytest `>=9.0.2` - Test runner (`backend/pyproject.toml`)
- pytest-asyncio `>=1.3.0` - Async test support (mode: `auto`)
- pytest-cov `>=7.0.0` - Coverage reporting
- pytest-archon `>=0.0.7` - Architecture fitness functions
- pytest-randomly `>=4.0.1` - Random test ordering
- pytest-timeout `>=2.4.0` - Test timeout enforcement
- polyfactory `>=3.3.0` - Test data factories
- testcontainers `>=4.14.1` - Docker-based integration tests (postgres, redis, rabbitmq, minio)
- respx `>=0.22.0` - httpx mock library
- hypothesis `>=6.151.9` - Property-based testing
- dirty-equals `>=0.11` - Flexible test assertions
- schemathesis `>=4.14.1` - OpenAPI schema-based fuzzing
- Locust `>=2.43.3` - Load/performance testing

**Build/Dev:**
- Ruff - Python linting and formatting (target: `py314`, line-length: 88, config in `backend/pyproject.toml`)
- mypy `>=1.19.1` - Static type checking (strict mode, pydantic plugin, config in `backend/pyproject.toml`)
- ESLint 9 - JavaScript/TypeScript linting (`eslint-config-next`)
- Prettier `^3.6.2` - Code formatting (admin only, with `prettier-plugin-tailwindcss`)
- Make - Build shortcuts (`backend/Makefile`)

## Key Dependencies

**Critical (Backend):**
- `asyncpg >=0.31.0` - PostgreSQL async driver (the only DB driver)
- `pydantic-settings` - Environment-based configuration (`backend/src/bootstrap/config.py`, `image_backend/src/bootstrap/config.py`)
- `attrs >=25.4.0` - Domain model definitions (immutable value objects and entities)
- `pyjwt[crypto] >=2.12.0` - JWT access token creation/verification (`backend/src/infrastructure/security/jwt.py`)
- `pwdlib[argon2,bcrypt] >=0.3.0` - Password hashing with Argon2id primary, Bcrypt legacy fallback (`backend/src/infrastructure/security/password.py`)
- `structlog >=25.5.0` - Structured JSON logging throughout both backends (`backend/src/bootstrap/logger.py`)
- `redis[hiredis] >=7.3.0` - Cache, session storage, FSM state (with hiredis C extension)
- `httpx[http2] >=0.28.1` - Async HTTP client for service-to-service calls (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)

**Critical (Image Backend):**
- `aiobotocore >=3.2.1` - S3-compatible object storage client (`image_backend/src/infrastructure/storage/factory.py`)
- `pillow >=11.0.0` - Image processing (resize, thumbnails, WebP conversion)
- `python-multipart >=0.0.22` - File upload handling

**Infrastructure:**
- `cachetools >=7.0.5` - In-memory TTL caches (backend only)
- `taskiq-aio-pika >=0.6.0` - RabbitMQ broker adapter for TaskIQ

**Critical (Frontend - Main):**
- `@reduxjs/toolkit ^2.11.2` + `react-redux ^9.2.0` - State management with RTK Query for API calls (`frontend/main/lib/store/api.ts`)
- `leaflet ^1.9.4` + `leaflet.markercluster ^1.5.3` - Map rendering for pickup points
- `lucide-react 0.555.0` - Icon library

**Critical (Frontend - Admin):**
- `dayjs ^1.11.18` - Date/time formatting (`frontend/admin/src/lib/dayjs.js`)
- `clsx ^2.1.1` + `tailwind-merge ^3.4.0` - Conditional CSS class merging
- `@svgr/webpack ^8.1.0` - SVG-as-React-component imports (`frontend/admin/next.config.js`)
- Tailwind CSS `^4.1.12` - Utility-first CSS with `@tailwindcss/postcss` (`frontend/admin/package.json`)

## Configuration

**Environment:**
- Configuration via Pydantic Settings (`backend/src/bootstrap/config.py`, `image_backend/src/bootstrap/config.py`)
- Loads from `.env` file and environment variables; validated at startup (fail-fast)
- Secrets use `SecretStr` type for safe handling
- Computed fields derive `database_url` and `redis_url` from individual env vars
- Three environments: `dev`, `test`, `prod` (controlled by `ENVIRONMENT` var)

**Required Backend Env Vars:**
- `SECRET_KEY` - HS256 JWT signing key (SecretStr)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT` - Redis connection (password optional)
- `RABBITMQ_PRIVATE_URL` - AMQP connection string
- `BOT_TOKEN` - Telegram bot token (SecretStr)
- `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY` - Service-to-service image calls

**Required Image Backend Env Vars:**
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL (separate DB)
- `REDISHOST`, `REDISPORT` - Redis
- `RABBITMQ_PRIVATE_URL` - RabbitMQ
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3 storage
- `INTERNAL_API_KEY` - Service auth key (SecretStr)

**Required Frontend Env Vars (Main):**
- `BACKEND_API_BASE_URL` - Server-side backend URL for BFF proxy
- `NEXT_PUBLIC_API_BASE_URL` - Client-side API base (defaults to `/api/backend`)
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData address suggestion/cleaning API
- `BROWSER_DEBUG_AUTH_ENABLED` - Debug auth bypass for local dev (optional)
- `COOKIE_DOMAIN` - Cookie domain for cross-subdomain auth (optional)

**Required Frontend Env Vars (Admin):**
- `BACKEND_URL` - Server-side backend URL (`frontend/admin/src/lib/api-client.js`)

**Build Config Files:**
- `backend/pyproject.toml` - Python project, ruff, mypy, pytest configuration
- `backend/alembic.ini` - Migration config (date-based subdirectories)
- `image_backend/pyproject.toml` - Image backend Python project config
- `image_backend/alembic.ini` - Image backend migration config
- `frontend/main/tsconfig.json` - TypeScript strict mode, `@/*` path alias, ES2017 target
- `frontend/main/next.config.ts` - Minimal config, remote image patterns
- `frontend/admin/next.config.js` - Webpack customization, SVG loader, security headers, `@` path alias
- `frontend/admin/tailwind.config.js` - Custom `app-*` design tokens

## Platform Requirements

**Development:**
- Docker + Docker Compose - Infrastructure services (`backend/docker-compose.yml`, `image_backend/docker-compose.yml`)
  - PostgreSQL 18 Alpine
  - Redis 8.4 Alpine
  - RabbitMQ 4.2.4 Management Alpine
  - MinIO (latest) - S3-compatible object storage
- Python 3.14 with `uv` package manager
- Node.js with `npm`
- Make (optional, for `backend/Makefile` shortcuts)

**Production:**
- Railway (PaaS) - Both backends deployed via Dockerfile (`backend/railway.toml`, `image_backend/railway.toml`)
- Backend startup: `alembic upgrade head` then `uvicorn main:app --host 0.0.0.0 --port $PORT` (`backend/scripts/entrypoint.sh`)
- Image backend startup: `uvicorn main:app --host 0.0.0.0 --port 8001` (`image_backend/Dockerfile`)
- Frontend deployment target: Not explicitly configured (standard Next.js deployment)

**Process Architecture (Backend):**
- Web API process: FastAPI/ASGI via Uvicorn (`backend/src/bootstrap/web.py`)
- Background Worker: TaskIQ worker consuming RabbitMQ tasks (`backend/src/bootstrap/worker.py`)
- Scheduler (Beat): TaskIQ scheduler dispatching periodic tasks (`backend/src/bootstrap/scheduler.py`)
  - Outbox relay: every minute
  - Outbox pruning: daily at 03:00 UTC

**Make Targets (`backend/Makefile`):**
```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-e2e          # E2E tests only
make test-architecture # Architecture fitness tests
make coverage          # Tests with coverage report
make lint              # Ruff lint check
make format            # Ruff auto-fix + format
make typecheck         # mypy strict checking
```

---

*Stack analysis: 2026-03-29*
