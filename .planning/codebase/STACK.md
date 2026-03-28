# Technology Stack

**Analysis Date:** 2026-03-28

## Languages

**Primary:**
- Python 3.14 - Backend API (`backend/`) and Image microservice (`image_backend/`)
- TypeScript - Main customer-facing frontend (`frontend/main/`)
- JavaScript (ES2017+) - Admin dashboard frontend (`frontend/admin/`)

**Secondary:**
- SQL - Alembic migrations (`backend/alembic/`, `image_backend/alembic/`)
- Shell (bash) - Entrypoint scripts (`backend/scripts/entrypoint.sh`)

## Runtime

**Backend:**
- CPython 3.14 (pinned in `backend/.python-version` and `image_backend/.python-version`)
- Docker base image: `python:3.14-slim-trixie`

**Frontend:**
- Node.js (version not pinned; no `.nvmrc` detected)
- Browser: Telegram WebApp WebView (primary), desktop browsers (admin)

**Package Managers:**
- `uv` (Python) - Used for both backend services; lockfiles present (`backend/uv.lock`, `image_backend/uv.lock`)
- `npm` (JavaScript/TypeScript) - Used for both frontends; lockfiles present (`frontend/admin/package-lock.json`, `frontend/main/package-lock.json`)

## Frameworks

**Core:**
- FastAPI `>=0.115.0` - Backend REST API framework (`backend/src/bootstrap/web.py`, `image_backend/src/bootstrap/web.py`)
- Next.js `^16.1.x` - Both frontend applications (App Router)
- React `19.x` - UI rendering for both frontends
- Aiogram `>=3.26.0` - Telegram bot framework (`backend/src/bot/`)

**ORM & Database:**
- SQLAlchemy `>=2.1.0b1` (async mode) - ORM and query builder for both backends
- Alembic `>=1.18.4` - Database migrations for both backends
- asyncpg `>=0.31.0` - PostgreSQL async driver

**DI Container:**
- Dishka `>=1.9.1` - Async dependency injection container (`backend/src/bootstrap/container.py`)

**Background Tasks:**
- TaskIQ `>=0.12.1` - Task queue framework with RabbitMQ backend
- TaskIQ AioPika `>=0.6.0` - RabbitMQ broker adapter (`backend/src/bootstrap/broker.py`)

**Testing:**
- pytest `>=9.0.2` - Test runner
- pytest-asyncio `>=1.3.0` - Async test support (mode: `auto`)
- pytest-cov `>=7.0.0` - Coverage reporting
- pytest-archon `>=0.0.7` - Architecture fitness functions (backend only)
- polyfactory `>=3.3.0` - Test data factories (backend only)
- testcontainers `>=4.14.1` - Docker-based integration tests (postgres, redis, rabbitmq, minio)
- Locust `>=2.43.3` - Load testing

**Build/Dev:**
- Ruff - Python linting and formatting (target: `py314`, line-length: 88)
- mypy `>=1.19.1` - Static type checking (strict, with pydantic plugin)
- ESLint 9 - JavaScript/TypeScript linting (next core-web-vitals config)
- Prettier `3.x` - Code formatting (admin only; with tailwindcss plugin)

## Key Dependencies

**Critical (Backend):**
- `pydantic-settings` - Environment-based configuration (`backend/src/bootstrap/config.py`)
- `attrs >=25.4.0` - Domain model definitions (immutable value objects)
- `pyjwt[crypto] >=2.12.0` - JWT access token creation/verification (`backend/src/infrastructure/security/jwt.py`)
- `pwdlib[argon2,bcrypt] >=0.3.0` - Password hashing with Argon2id (`backend/src/infrastructure/security/password.py`)
- `structlog >=25.5.0` - Structured JSON logging throughout both backends
- `redis[hiredis] >=7.3.0` - Cache, session storage, FSM state (with hiredis C extension)
- `cachetools >=7.0.5` - In-memory TTL caches (backend only)
- `httpx[http2] >=0.28.1` - Async HTTP client for service-to-service calls (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)

**Critical (Image Backend):**
- `aiobotocore >=3.2.1` - S3-compatible object storage client (`image_backend/src/infrastructure/storage/factory.py`)
- `pillow >=11.0.0` - Image processing (resize, thumbnails, WebP conversion)
- `python-multipart >=0.0.22` - File upload handling

**Critical (Frontend - Main):**
- `@reduxjs/toolkit ^2.11.2` + `react-redux ^9.2.0` - State management with RTK Query for API calls (`frontend/main/lib/store/`)
- `leaflet ^1.9.4` + `leaflet.markercluster ^1.5.3` - Map rendering (pickup points, geo features)
- `lucide-react 0.555.0` - Icon library

**Critical (Frontend - Admin):**
- `dayjs ^1.11.18` - Date/time formatting (`frontend/admin/src/lib/dayjs.js`)
- `clsx ^2.1.1` + `tailwind-merge ^3.4.0` - Conditional CSS class merging
- `@svgr/webpack ^8.1.0` - SVG-as-React-component imports

**CSS/Styling:**
- Tailwind CSS `^4.1.12` - Utility-first CSS (admin uses v4 with `@tailwindcss/postcss`)
- CSS Modules - Used for complex animations/page layouts in admin (`frontend/admin/src/app/admin/layout.module.css`)
- Global CSS imports - Main frontend uses `app/globals.css`

## Configuration

**Backend Environment:**
- Configuration via Pydantic Settings (`backend/src/bootstrap/config.py`, `image_backend/src/bootstrap/config.py`)
- Loads from `.env` file and environment variables
- Validated at startup; app fails fast on missing required vars
- Secrets use `SecretStr` type for safe handling
- Computed fields derive `database_url` and `redis_url` from individual env vars

**Backend Key Settings:**
- `ENVIRONMENT`: `dev | test | prod` (controls docs URL visibility, debug mode)
- `SECRET_KEY`: HS256 JWT signing key
- `API_V1_STR`: `/api/v1` (route prefix)
- Database: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- Redis: `REDISHOST`, `REDISPORT`, `REDISUSER`, `REDISPASSWORD`, `REDISDATABASE`
- RabbitMQ: `RABBITMQ_PRIVATE_URL` (AMQP connection string)
- Telegram: `BOT_TOKEN`, `BOT_ADMIN_IDS`, `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET`
- Service-to-service: `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY`

**Image Backend Key Settings:**
- S3: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL`
- Service auth: `INTERNAL_API_KEY` (API key for backend-to-image calls)
- Processing: `MAX_FILE_SIZE` (50MB), `SSE_TIMEOUT`, `PROCESSING_TIMEOUT`

**Frontend Environment:**
- `BACKEND_URL` - Server-side backend URL (admin, via `frontend/admin/src/lib/api-client.js`)
- `NEXT_PUBLIC_API_BASE_URL` - Client-side API base (main, defaults to `/api/backend`)
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData address suggestions API (main)
- `BROWSER_DEBUG_AUTH_ENABLED` - Debug auth bypass for local dev (main)
- `BACKEND_API_BASE_URL` - Server-side backend URL for BFF proxy (main)

**Build Configuration:**
- `backend/pyproject.toml` - Python project definition, ruff/mypy config
- `backend/alembic.ini` - Migration config (date-based subdirectories, recursive versions)
- `frontend/admin/next.config.js` - Webpack customization, SVG loader, security headers, `@` path alias
- `frontend/main/next.config.ts` - Minimal config, remote image patterns
- `frontend/admin/tailwind.config.js` - Custom `app-*` design tokens, Inter font family
- `frontend/main/tsconfig.json` - Strict mode, `@/*` path alias, ES2017 target

## Platform Requirements

**Development:**
- Docker + Docker Compose - Infrastructure services (`backend/docker-compose.yml`, `image_backend/docker-compose.yml`)
  - PostgreSQL 18 Alpine
  - Redis 8.4 Alpine
  - RabbitMQ 4.2.4 Management Alpine
  - MinIO (S3-compatible object storage)
- Python 3.14 with `uv` package manager
- Node.js with `npm`
- Make (optional, for `backend/Makefile` shortcuts)

**Production:**
- Railway (PaaS) - Both backends deployed via Dockerfile (`backend/railway.toml`, `image_backend/railway.toml`)
- Backend runs: `alembic upgrade head` then `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Image backend runs: `uvicorn main:app --host 0.0.0.0 --port 8001`
- Frontend deployment target: Not explicitly configured (standard Next.js deployment)

## Process Architecture

**Backend runs three separate processes:**
1. **Web (ASGI):** `uvicorn main:app` - HTTP API server (`backend/main.py`)
2. **Worker:** `taskiq worker src.bootstrap.worker:broker` - Background task consumer (`backend/src/bootstrap/worker.py`)
3. **Scheduler (Beat):** `taskiq scheduler src.bootstrap.scheduler:scheduler` - Cron-like task dispatcher (`backend/src/bootstrap/scheduler.py`)

**Image Backend runs two processes:**
1. **Web (ASGI):** `uvicorn main:app` - HTTP API + image processing
2. **Worker:** TaskIQ worker for async image processing tasks

---

*Stack analysis: 2026-03-28*
