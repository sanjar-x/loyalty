# Technology Stack

**Analysis Date:** 2026-03-28

## Languages

**Primary:**
- Python 3.14 - Backend API (`backend/`) and Image Backend microservice (`image_backend/`)
- TypeScript - Customer-facing Telegram Mini App frontend (`frontend/main/`)

**Secondary:**
- JavaScript (ES2017+) - Admin panel frontend (`frontend/admin/`), uses JSX without TypeScript
- SQL - Alembic migrations (`backend/alembic/`, `image_backend/alembic/`)
- Shell - Entrypoint scripts (`backend/scripts/entrypoint.sh`)

## Runtime

**Backend:**
- CPython 3.14 (Docker base: `python:3.14-slim-trixie`)
- ASGI server: Uvicorn with standard extras (libuv event loop, httptools)

**Frontend:**
- Node.js (version managed by each Next.js project)
- Next.js runtime (React Server Components + Edge middleware)

**Package Managers:**
- `uv` (Astral) - Python dependency management for both `backend/` and `image_backend/`
  - Lockfile: `uv.lock` present in both services
  - Workspace mode enabled in `backend/pyproject.toml` (`[tool.uv.workspace]`)
- `npm` - JavaScript/TypeScript dependency management for both frontends
  - Lockfile: `package-lock.json` present in both `frontend/admin/` and `frontend/main/`

## Frameworks

**Core:**
- FastAPI `>=0.115.0` - Web framework for both Python services (`backend/main.py`, `image_backend/main.py`)
- Next.js `^16.1.x` - React framework for both frontends (`frontend/admin/package.json`, `frontend/main/package.json`)
- React `19.x` - UI library for both frontends
- Aiogram `>=3.26.0` - Telegram Bot framework (`backend/src/bot/`)

**ORM / Database:**
- SQLAlchemy `>=2.1.0b1` (async mode) - ORM for both Python services
- Alembic `>=1.18.4` - Database migrations for both services
- asyncpg `>=0.31.0` - PostgreSQL async driver

**DI / Architecture:**
- Dishka `>=1.9.1` - Async dependency injection container (both Python services)
- attrs `>=25.4.0` - Domain model immutable value objects

**Background Tasks:**
- TaskIQ `>=0.12.1` - Distributed task queue framework
- taskiq-aio-pika `>=0.6.0` - RabbitMQ broker backend for TaskIQ

**Testing:**
- pytest `>=9.0.2` - Test runner (both services)
- pytest-asyncio `>=1.3.0` - Async test support
- pytest-cov `>=7.0.0` - Coverage reporting
- pytest-archon `>=0.0.7` - Architecture fitness functions (backend only)
- polyfactory `>=3.3.0` - Test data factories (backend only)
- testcontainers `>=4.14.1` - Dockerized test dependencies (PostgreSQL, Redis, RabbitMQ, MinIO)
- Locust `>=2.43.3` - Load testing (backend only)

**Build/Dev:**
- Ruff - Linter and formatter (target: Python 3.14, line-length: 88)
  - Config: `backend/pyproject.toml` `[tool.ruff]`, `image_backend/pyproject.toml` `[tool.ruff]`
- mypy `>=1.19.1` - Static type checker (with Pydantic plugin)
  - Config: `backend/pyproject.toml` `[tool.mypy]`
- ESLint 9 - JavaScript/TypeScript linting (both frontends)
- Prettier `>=3.6.2` - Code formatting (admin frontend)
  - Plugin: `prettier-plugin-tailwindcss`
- Docker - Containerization (`backend/Dockerfile`, `image_backend/Dockerfile`)

## Key Dependencies

**Critical (Backend):**
- `pydantic-settings` - Environment-based configuration (`backend/src/bootstrap/config.py`)
- `pyjwt[crypto]` `>=2.12.0` - JWT access token creation and verification (`backend/src/infrastructure/security/jwt.py`)
- `pwdlib[argon2,bcrypt]` `>=0.3.0` - Password hashing with Argon2id primary, Bcrypt legacy fallback (`backend/src/infrastructure/security/password.py`)
- `structlog` `>=25.5.0` - Structured logging (JSON in prod, colored console in dev) (`backend/src/bootstrap/logger.py`)
- `redis[hiredis]` `>=7.3.0` - Cache, FSM storage for Telegram bot, permission caching
- `httpx[http2]` `>=0.28.1` - Async HTTP client for server-to-server calls (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)

**Critical (Image Backend):**
- `aiobotocore` `>=3.2.1` - S3-compatible object storage client (`image_backend/src/infrastructure/storage/factory.py`)
- `pillow` `>=11.0.0` - Image processing (resize, thumbnail, WebP conversion)
- `python-multipart` `>=0.0.22` - File upload handling

**Critical (Frontend Main):**
- `@reduxjs/toolkit` `^2.11.2` - State management with RTK Query for API calls (`frontend/main/lib/store/api.ts`)
- `react-redux` `^9.2.0` - React bindings for Redux
- `leaflet` `^1.9.4` + `leaflet.markercluster` `^1.5.3` - Map rendering (`frontend/main/`)
- `lucide-react` `0.555.0` - Icon library

**Critical (Frontend Admin):**
- `dayjs` `^1.11.18` - Date manipulation
- `clsx` `^2.1.1` + `tailwind-merge` `^3.4.0` - Conditional class merging
- `@svgr/webpack` `^8.1.0` - SVG as React components

**CSS/Styling:**
- Tailwind CSS `^4.1.12` - Utility-first CSS (admin frontend)
- PostCSS `^8.5.6` - CSS processing (both frontends)

## Configuration

**Environment:**
- Backend: Pydantic Settings (`BaseSettings`) loading from `.env` file (`backend/src/bootstrap/config.py`)
- Image Backend: Same pattern (`image_backend/src/bootstrap/config.py`)
- Frontend Main: `process.env.BACKEND_API_BASE_URL`, `process.env.DADATA_TOKEN`, `process.env.DADATA_SECRET`
- Frontend Admin: `process.env.BACKEND_URL` for server-side API calls (`frontend/admin/src/lib/api-client.js`)
- `.env` file present in `backend/` (gitignored)
- `.env.example` present in `backend/` and `image_backend/`

**Key Environment Variables (Backend):**
- `SECRET_KEY` - JWT signing key
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT`, `REDISPASSWORD`, `REDISDATABASE` - Redis connection
- `RABBITMQ_PRIVATE_URL` - RabbitMQ AMQP URL
- `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY` - Image Backend service URL
- `BOT_TOKEN`, `BOT_ADMIN_IDS`, `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET` - Telegram Bot
- `CORS_ORIGINS` - Comma-separated allowed origins

**Key Environment Variables (Image Backend):**
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3/MinIO
- `INTERNAL_API_KEY` - Service-to-service authentication key
- `RABBITMQ_PRIVATE_URL` - RabbitMQ for task queue

**Key Environment Variables (Frontend Main):**
- `BACKEND_API_BASE_URL` - Backend API base URL for server-side proxy
- `NEXT_PUBLIC_API_BASE_URL` - Client-side API base (defaults to `/api/backend`)
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData address API
- `COOKIE_DOMAIN` - Auth cookie domain

**Build:**
- `backend/Dockerfile` - Multi-stage with uv, copies lockfile first for caching
- `image_backend/Dockerfile` - Same pattern
- `backend/railway.toml`, `image_backend/railway.toml` - Railway deployment config (Dockerfile builder)
- `frontend/main/netlify.toml` - Netlify deployment config with `@netlify/plugin-nextjs`
- `backend/Makefile` - Dev commands: `make test`, `make lint`, `make format`, `make typecheck`, `make coverage`

## Platform Requirements

**Development:**
- Docker + Docker Compose for local infrastructure (PostgreSQL 18, Redis 8.4, RabbitMQ 4.2.4, MinIO)
  - Config: `backend/docker-compose.yml` (shared by both Python services)
- Python 3.14+ with `uv` package manager
- Node.js with `npm` for frontend development

**Production:**
- Railway (backend and image_backend) - Dockerfile-based deployment
- Netlify (frontend/main) - Next.js with `@netlify/plugin-nextjs`
- Frontend admin: deployment target not explicitly configured (Next.js build output)

**Infrastructure Services (Production):**
- PostgreSQL 18 - Primary database (separate databases per service)
- Redis 8.4 - Caching, session storage, FSM state
- RabbitMQ 4.2.4 - Message broker for async tasks
- S3-compatible storage (MinIO in dev) - Media file storage

---

*Stack analysis: 2026-03-28*
