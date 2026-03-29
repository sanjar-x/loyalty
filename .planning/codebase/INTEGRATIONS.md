# External Integrations

**Analysis Date:** 2026-03-29

## APIs & External Services

**Address Data (DaData):**
- DaData Suggestions API - Address autocomplete for city/settlement selection
  - Endpoint: `https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address`
  - Client: Next.js API route BFF proxy (`frontend/main/app/api/dadata/suggest/address/route.ts`)
  - Auth: `DADATA_TOKEN` (Authorization header), `DADATA_SECRET` (X-Secret header, optional for suggestions)
- DaData Cleaner API - Address standardization/cleaning
  - Endpoint: `https://cleaner.dadata.ru/api/v1/clean/address`
  - Client: Next.js API route BFF proxy (`frontend/main/app/api/dadata/clean/address/route.ts`)
  - Auth: `DADATA_TOKEN` (Authorization header), `DADATA_SECRET` (X-Secret header, required)

**Image Processing (Internal Microservice):**
- Image Backend - Upload, resize, thumbnail generation, WebP conversion
  - Client: `backend/src/modules/catalog/infrastructure/image_backend_client.py` (httpx async)
  - Auth: `IMAGE_BACKEND_API_KEY` via `X-API-Key` header
  - Config: `IMAGE_BACKEND_URL` (default `http://localhost:8001`)
  - Operations: DELETE `/api/v1/media/{storage_object_id}` (best-effort, fire-and-forget)
  - Timeout: 10 seconds
  - Interface: `IImageBackendClient` in `backend/src/modules/catalog/domain/interfaces.py`

**Telegram Bot API:**
- Aiogram Bot - Customer-facing Telegram bot with FSM, inline keyboards, throttling
  - Client: `backend/src/bot/factory.py` (aiogram Bot + Dispatcher)
  - Auth: `BOT_TOKEN` (SecretStr)
  - FSM Storage: Redis-backed (`aiogram.fsm.storage.redis.RedisStorage`)
  - Delivery: Webhook or long-polling via aiogram Dispatcher
  - Webhook config: `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET`
  - Middleware chain: Logging -> UserIdentify -> Throttling (`backend/src/bot/middlewares/`)
  - DI: Dishka integrated via `setup_dishka(container, router=dp)`

## Data Storage

**Databases:**
- PostgreSQL 18 (Alpine) - Primary RDBMS for both services
  - Backend connection: Computed `database_url` from `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
  - Driver: `asyncpg >=0.31.0` (async)
  - ORM: SQLAlchemy 2.1 async mode
  - Pool config (`backend/src/infrastructure/database/provider.py`):
    - `pool_size=15`, `max_overflow=10`, `pool_timeout=30s`
    - `pool_pre_ping=True`, `pool_recycle=3600s`, `pool_use_lifo=True`
    - `statement_timeout=30000ms`, `idle_in_transaction_session_timeout=60000ms`
    - Isolation level: `READ COMMITTED`
  - Migrations: Alembic with date-based subdirectories (`backend/alembic/`, `image_backend/alembic/`)
  - Image backend has separate PostgreSQL database (same connection pattern)

**Caching:**
- Redis 8.4 (Alpine) - Cache, session storage, bot FSM state
  - Connection: Computed `redis_url` from `REDISHOST`, `REDISPORT`, `REDISUSER`, `REDISPASSWORD`, `REDISDATABASE`
  - Client: `redis.asyncio` with hiredis C extension (`backend/src/infrastructure/cache/provider.py`)
  - Pool config: `max_connections=100`, `socket_timeout=5.0s`, `socket_connect_timeout=2.0s`
  - Cache service: `RedisService` implementing `ICacheService` (`backend/src/infrastructure/cache/redis.py`)
  - Uses:
    - Session permissions cache (TTL: 300s configurable via `SESSION_PERMISSIONS_CACHE_TTL`)
    - Bot FSM state storage (TTL configurable via `FSM_STATE_TTL`, `FSM_DATA_TTL`)
    - In-memory TTL caches via `cachetools` for hot paths

**File/Object Storage:**
- MinIO (S3-compatible) - Image and media asset storage
  - Client: `aiobotocore` S3 client via `S3ClientFactory` (`image_backend/src/infrastructure/storage/factory.py`)
  - Config: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL`
  - Client config: `max_pool_connections=1` (ephemeral per-operation), `connect_timeout=5s`, `read_timeout=60s`, `retries=3`
  - Dev: MinIO container on `localhost:9000` (API) / `localhost:9001` (console)
  - Prod: Likely AWS S3 or S3-compatible service (configurable via endpoint URL)

**Message Broker:**
- RabbitMQ 4.2.4 (Management Alpine) - Async task queue
  - Connection: `RABBITMQ_PRIVATE_URL` (AMQP connection string)
  - Client: TaskIQ AioPikaBroker (`backend/src/bootstrap/broker.py`)
  - Exchange: `taskiq_rpc_exchange` (declared)
  - Queue: `taskiq_background_jobs` (declared), QoS prefetch: 10
  - Dev: Container on `localhost:5672` (AMQP) / `localhost:15672` (management UI)

## Authentication & Identity

**Auth Provider: Custom (Multi-Strategy)**

**Strategy 1 - Telegram Mini App Auth:**
- Implementation: HMAC-SHA256 validation of Telegram `initData` (`backend/src/infrastructure/security/telegram.py`)
- Uses aiogram's `safe_parse_webapp_init_data()` for cryptographic verification
- Additional checks: freshness (max age configurable, default 300s), user presence
- Frontend flow: Client sends `initData` -> Next.js BFF (`frontend/main/app/api/auth/telegram/route.ts`) -> Backend `/api/v1/auth/telegram`
- Auth header format: `Authorization: tma <initData>`

**Strategy 2 - JWT Bearer Token Auth:**
- Implementation: `JwtTokenProvider` (`backend/src/infrastructure/security/jwt.py`)
- Algorithm: HS256, signing key from `SECRET_KEY` env var
- Access token: JWT with `sub` (identity_id), `sid` (session_id), `tv` (token_version), `exp`, `iat`, `jti` claims
- Access token TTL: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token: Opaque `secrets.token_urlsafe(32)`, SHA-256 hash stored in DB
- Refresh token TTL: 30 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- Token version validation: `tv` claim checked against `identity.token_version` in DB

**Strategy 3 - Debug Auth (Dev Only):**
- Implementation: Mock tokens for local browser development (`frontend/main/lib/auth/debug.ts`)
- Enabled via `BROWSER_DEBUG_AUTH_ENABLED` env var
- Restricted to localhost, 127.0.0.1, ::1, *.local hosts
- Falls back to mock mode if backend unreachable

**Password Hashing:**
- Implementation: `Argon2PasswordHasher` (`backend/src/infrastructure/security/password.py`)
- Primary: Argon2id (OWASP recommended)
- Legacy: Bcrypt verification + transparent migration via `needs_rehash()`

**Authorization (RBAC):**
- Recursive role hierarchy with permission inheritance
- `RequirePermission` callable dependency (`backend/src/modules/identity/presentation/dependencies.py`)
- Permission resolution: Redis cache-aside (TTL 300s) -> PostgreSQL recursive CTE fallback
- Permission codenames: `module:action` pattern (e.g., `catalog:manage`, `catalog:read`)
- Session management: Max 5 active sessions per identity, idle timeout, absolute lifetime

**Cookie Management (Frontend):**
- Access token cookie: `access_token`, HttpOnly, Secure (prod), SameSite=Lax, 15 min max-age
- Refresh token cookie: `refresh_token`, HttpOnly, Secure (prod), SameSite=Lax, 7 day max-age
- Implementation: `frontend/main/lib/auth/cookie-helpers.ts`, `frontend/admin/src/lib/auth.js`
- Auto-refresh: RTK Query base query with 401 retry logic (`frontend/main/lib/store/api.ts`)

**Service-to-Service Auth:**
- Backend -> Image Backend: `X-API-Key` header (`IMAGE_BACKEND_API_KEY`)
- Image Backend validates via `INTERNAL_API_KEY`

## Monitoring & Observability

**Structured Logging:**
- Framework: structlog (`backend/src/bootstrap/logger.py`)
- Dev mode: Colored console output with call-site info (file, function, line)
- Prod mode: JSON lines to stdout for log aggregator ingestion
- Context propagation: `structlog.contextvars.merge_contextvars` for request-scoped fields
- ILogger interface: `backend/src/shared/interfaces/logger.py` (injected via Dishka)
- Access logging: Custom middleware (`backend/src/api/middlewares/logger.py`)
- TaskIQ logging: Custom middleware (`backend/src/infrastructure/logging/taskiq_middleware.py`)

**Error Tracking:**
- No external error tracking service detected (Sentry, Datadog, etc.)
- Errors logged via structlog with full traceback

**Request Tracing:**
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing

**Health Checks:**
- Backend: `GET /health` returns `{"status": "ok", "environment": "..."}` (`backend/src/bootstrap/web.py`)
- Docker: PostgreSQL `pg_isready`, Redis `PING`, RabbitMQ `rabbitmq-diagnostics ping`, MinIO curl health

## CI/CD & Deployment

**Hosting:**
- Railway (PaaS) - Both backends (`backend/railway.toml`, `image_backend/railway.toml`)
- Builder: Dockerfile-based deployment
- Backend start: `alembic upgrade head` then Uvicorn on `$PORT` (`backend/scripts/entrypoint.sh`)
- Image backend start: Uvicorn on port 8001 (`image_backend/Dockerfile`)
- Frontend deployment: Not explicitly configured (standard Next.js, likely Vercel given `VERCEL_ENV` reference in `frontend/main/lib/auth/cookie-helpers.ts`)

**CI Pipeline:**
- No CI configuration files detected (`.github/workflows/`, `.gitlab-ci.yml`, etc.)

**Docker Configuration:**
- `backend/docker-compose.yml` - PostgreSQL, Redis, RabbitMQ, MinIO (dev infrastructure)
- `image_backend/docker-compose.yml` - Identical infrastructure services
- `backend/Dockerfile` - Multi-stage with uv for Python dependency management
- `image_backend/Dockerfile` - Same pattern as backend

## BFF Proxy Pattern

**Main Frontend (Telegram Mini App):**
- All backend API calls proxied through Next.js API routes to hide backend URL from client
- Catch-all proxy: `frontend/main/app/api/backend/[...path]/route.ts`
  - Forwards GET, POST, PUT, PATCH, DELETE
  - Injects `Authorization: Bearer <token>` from HttpOnly cookies
  - 25-second timeout
  - Filters headers for security (no Origin/Referer forwarding)
- Auth routes: `frontend/main/app/api/auth/telegram/route.ts`, `frontend/main/app/api/auth/refresh/route.ts`, `frontend/main/app/api/auth/logout/route.ts`
- DaData routes: `frontend/main/app/api/dadata/suggest/address/route.ts`, `frontend/main/app/api/dadata/clean/address/route.ts`

**Admin Frontend:**
- Direct server-side fetch via `backendFetch()` (`frontend/admin/src/lib/api-client.js`)
- Uses `BACKEND_URL` env var for server-side calls
- Cookie-based auth with JWT decode for expiry checks (`frontend/admin/src/lib/auth.js`)

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot webhook: Configurable via `BOT_WEBHOOK_URL` + `BOT_WEBHOOK_SECRET`
- Internal webhook: `INTERNAL_WEBHOOK_SECRET` for service-to-service event delivery

**Outgoing:**
- Transactional Outbox pattern (`backend/src/infrastructure/outbox/`)
  - Domain events persisted atomically with business data
  - Relay task polls outbox table every minute (`backend/src/infrastructure/outbox/tasks.py`)
  - Events dispatched to TaskIQ tasks for async processing
  - Registered event handlers:
    - `identity_registered` -> Create user profile (Customer or StaffMember)
    - `identity_deactivated` -> Anonymize customer data (GDPR)
    - `role_assignment_changed` -> Invalidate permissions cache
  - Pruning: Processed records older than 7 days deleted daily at 03:00 UTC
  - Dead Letter Queue: DLQ middleware persists failed tasks to database (`backend/src/infrastructure/logging/dlq_middleware.py`)

## API Modules (Backend Routes)

All routes registered under `/api/v1` prefix (`backend/src/api/router.py`):

**Catalog Module (`/api/v1/catalog/`):**
- Categories, Brands, Attributes, Attribute Values, Attribute Templates
- Products, Variants, SKUs, Product Attributes, Media
- Storefront (public read endpoints)

**Identity Module (`/api/v1/`):**
- Auth (login, telegram, refresh, logout)
- Admin (identity management)
- Staff admin, Customer admin
- Invitations
- Account (self-service)

**User Module (`/api/v1/`):**
- Profile management

**Geo Module (`/api/v1/geo/`):**
- Countries, Currencies, Languages, Subdivisions (public, cacheable 1hr)

**Supplier Module (`/api/v1/`):**
- Supplier management

## Environment Configuration Summary

**`.env` files exist** - Both backends load from `.env` via Pydantic Settings. Never read or commit contents.

**Required for backend startup:**
| Var | Purpose |
|-----|---------|
| `SECRET_KEY` | JWT signing key |
| `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` | PostgreSQL |
| `REDISHOST`, `REDISPORT` | Redis |
| `RABBITMQ_PRIVATE_URL` | RabbitMQ AMQP URL |
| `BOT_TOKEN` | Telegram bot token |

**Required for image_backend startup:**
| Var | Purpose |
|-----|---------|
| `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` | PostgreSQL |
| `REDISHOST`, `REDISPORT` | Redis |
| `RABBITMQ_PRIVATE_URL` | RabbitMQ |
| `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` | S3 storage |

**Required for frontend/main:**
| Var | Purpose |
|-----|---------|
| `BACKEND_API_BASE_URL` | Server-side backend URL |
| `DADATA_TOKEN` | DaData API token |

**Required for frontend/admin:**
| Var | Purpose |
|-----|---------|
| `BACKEND_URL` | Server-side backend URL |

---

*Integration audit: 2026-03-29*
