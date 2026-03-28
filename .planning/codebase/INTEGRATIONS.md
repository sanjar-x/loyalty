# External Integrations

**Analysis Date:** 2026-03-28

## APIs & External Services

**Telegram Bot API:**
- Purpose: Telegram bot for user interaction (commands, inline keyboards, FSM flows)
- SDK: `aiogram >=3.26.0`
- Auth: `BOT_TOKEN` env var (SecretStr in `backend/src/bootstrap/config.py`)
- Implementation: `backend/src/bot/factory.py` creates Bot + Dispatcher
- Middleware chain: LoggingMiddleware -> UserIdentifyMiddleware -> ThrottlingMiddleware
- FSM storage: Redis-backed via `aiogram.fsm.storage.redis.RedisStorage` (separate connection, not from DI)
- Commands: `/start`, `/help`, `/cancel` (set in `backend/src/bot/factory.py`)
- Webhook support: `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET` env vars (polling mode available as fallback)
- Handlers: `backend/src/bot/handlers/` (common.py, errors.py, nav.py)
- Keyboards: `backend/src/bot/keyboards/` (inline.py, reply.py)
- Throttling: `THROTTLE_RATE` (default 0.5s per message)

**Telegram Mini App (WebApp) Auth:**
- Purpose: Authenticate Telegram users in the main customer frontend
- Flow: Frontend sends `initData` -> Next.js BFF (`frontend/main/app/api/auth/telegram/route.ts`) -> Backend IAM (`POST /api/v1/auth/telegram`)
- Validation: HMAC-SHA256 via `aiogram.utils.web_app.safe_parse_webapp_init_data` (`backend/src/infrastructure/security/telegram.py`)
- Freshness check: `TELEGRAM_INIT_DATA_MAX_AGE` (default 300 seconds) -- aiogram does NOT check freshness, custom logic adds it
- Token flow: Backend returns JWT accessToken + opaque refreshToken -> BFF sets HttpOnly cookies
- Exceptions: `InvalidInitDataError`, `InitDataExpiredError`, `InitDataMissingUserError` (all in `backend/src/modules/identity/domain/exceptions.py`)
- Parsed data: `TelegramUserData` value object with telegram_id, first_name, last_name, username, language_code, is_premium, photo_url, allows_write_to_pm, start_param
- Frontend SDK: `frontend/main/lib/telegram/` (extensive custom hooks wrapping `window.Telegram.WebApp`)
- Debug mode: `BROWSER_DEBUG_AUTH_ENABLED` allows localhost auth without real Telegram (`frontend/main/app/api/auth/telegram/route.ts`)

**DaData (Address Suggestions):**
- Purpose: Russian address autocomplete for city/settlement lookup
- API: `https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address`
- Suggest proxy: `frontend/main/app/api/dadata/suggest/address/route.ts` (server-side, POST only)
- Clean proxy: `frontend/main/app/api/dadata/clean/address/route.ts` (server-side)
- Auth: `DADATA_TOKEN` env var (Token-based Authorization header), optional `DADATA_SECRET` (X-Secret header)
- Scope: Suggestions bounded from `city` to `settlement` level
- Rate limiting: count capped at 1-10 (default 5) per request

**Image Backend (Internal Microservice):**
- Purpose: Image upload, resize, thumbnail generation, WebP conversion
- Protocol: HTTP REST (server-to-server)
- Client: `backend/src/modules/catalog/infrastructure/image_backend_client.py` (httpx AsyncClient with 10s timeout)
- Auth: API key via `X-API-Key` header
- Base URL: `IMAGE_BACKEND_URL` env var (default `http://localhost:8001`)
- API key: `IMAGE_BACKEND_API_KEY` env var (SecretStr)
- Operations: DELETE `/api/v1/media/{storage_object_id}` (best-effort cleanup -- errors logged but not raised)
- Image backend validates: `INTERNAL_API_KEY` on incoming requests
- Client lifecycle: Async context manager with explicit `aclose()`

## Data Storage

**PostgreSQL (Primary Database):**
- Version: 18 Alpine (Docker)
- Separate databases: one for backend, one for image backend (each has own `PGDATABASE`)
- Driver: `asyncpg` (async, binary protocol)
- ORM: SQLAlchemy 2.1+ async mode
- Connection pool config (`backend/src/infrastructure/database/provider.py`):
  - Pool class: `AsyncAdaptedQueuePool`
  - Pool size: 15, max overflow: 10
  - Pool timeout: 30s, recycle: 3600s
  - Pool LIFO: true, pre-ping: true
- Connection settings via `connect_args`:
  - `application_name`: "enterprise_api"
  - `statement_timeout`: 30000ms
  - `idle_in_transaction_session_timeout`: 60000ms
  - `timezone`: UTC
- Isolation level: READ COMMITTED
- Session config: `autoflush=False`, `expire_on_commit=False`
- Migrations: Alembic with date-based subdirectory pattern (`%%(year)d/%%(month).2d/%%(day).2d_...`)
- Recursive version locations enabled
- Post-write hook: ruff format via uv
- UoW pattern: `backend/src/infrastructure/database/uow.py` wraps session with outbox event persistence

**Database Models (Backend):**
- Catalog: `Product`, `ProductVariant`, `SKU`, `Category`, `Brand`, `Attribute`, `AttributeGroup`, `AttributeValue`, `AttributeTemplate`, `TemplateAttributeBinding`, `ProductAttributeValue`, `SKUAttributeValueLink`, `MediaAsset` (`backend/src/modules/catalog/infrastructure/models.py`)
- Identity/IAM: `IdentityModel`, `RoleModel`, `PermissionModel`, `SessionModel`, `LinkedAccountModel`, `LocalCredentialsModel`, `RoleHierarchyModel`, `RolePermissionModel`, `IdentityRoleModel`, `SessionRoleModel`, `StaffInvitationModel`, `StaffInvitationRoleModel` (`backend/src/modules/identity/infrastructure/models.py`)
- Geo: `CountryModel`, `CountryTranslationModel`, `CurrencyModel`, `CurrencyTranslationModel`, `LanguageModel`, `SubdivisionModel`, `SubdivisionTranslationModel`, `SubdivisionCategoryModel`, `SubdivisionCategoryTranslationModel`, `CountryCurrencyModel` (`backend/src/modules/geo/infrastructure/models.py`)
- User: `CustomerModel`, `StaffMemberModel` (`backend/src/modules/user/infrastructure/models.py`)
- Supplier: `Supplier` (`backend/src/modules/supplier/infrastructure/models.py`)
- Infrastructure: `OutboxMessage`, `FailedTask` (`backend/src/infrastructure/database/models/`)

**Redis (Cache + Session Store):**
- Version: 8.4 Alpine (Docker), allkeys-lru eviction, 256mb max memory
- Driver: `redis-py` async with `hiredis` C extension
- Connection pool: max 100 connections, socket timeout 5s, connect timeout 2s, decode_responses=False
- Provider: `backend/src/infrastructure/cache/provider.py` (app-scoped singleton)
- Implementation: `backend/src/infrastructure/cache/redis.py` (RedisService -> ICacheService)
- Uses:
  - Permission cache (cache-aside pattern, TTL from `SESSION_PERMISSIONS_CACHE_TTL`, default 300s)
  - Aiogram FSM state storage (separate connection in `backend/src/bot/factory.py`, key prefix "fsm:")
  - General caching via `ICacheService` interface

**S3/MinIO (Object Storage):**
- Purpose: Image file storage (upload, serve, presigned URLs)
- Dev provider: MinIO (latest Docker image)
- Production: Any S3-compatible provider
- Client: `aiobotocore` via `S3ClientFactory` (`image_backend/src/infrastructure/storage/factory.py`)
- Config: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY` (SecretStr), `S3_SECRET_KEY` (SecretStr), `S3_REGION`, `S3_BUCKET_NAME`
- Public URL: `S3_PUBLIC_BASE_URL` (for generating public-facing image URLs)
- Presigned URL TTL: `PRESIGNED_URL_TTL` (default 300s)
- Ephemeral client pattern: each operation gets its own short-lived client (pool_size=1)
- Retry: 3 attempts, standard mode; timeouts: connect 5s, read 60s

**RabbitMQ (Message Broker):**
- Version: 4.2.4 Management Alpine (Docker)
- Client: TaskIQ via `taskiq-aio-pika` (`AioPikaBroker`)
- Exchange: `taskiq_rpc_exchange` (declared, direct)
- Queue: `taskiq_background_jobs` (declared)
- QoS prefetch: 10
- Connection: `RABBITMQ_PRIVATE_URL` env var (AMQP URL)
- Configuration: `backend/src/bootstrap/broker.py`
- Middleware: `LoggingTaskiqMiddleware` for structured task logging
- Management console: port 15672 (dev only)

## Authentication & Identity

**Auth Provider: Custom IAM (Identity & Access Management)**
- Implementation: Full custom RBAC system in `backend/src/modules/identity/`
- Identity types: Staff (email/password), Customer (Telegram), Linked accounts

**Authentication Flows:**

1. **Telegram Mini App Auth** (customers):
   - Client sends `initData` string from Telegram WebApp SDK
   - BFF proxy: `frontend/main/app/api/auth/telegram/route.ts` -> `POST /api/v1/auth/telegram`
   - Auth header: `Authorization: tma <initData>`
   - Backend validates HMAC-SHA256 signature using bot token (`backend/src/infrastructure/security/telegram.py`)
   - Freshness validated: age must be 0..`TELEGRAM_INIT_DATA_MAX_AGE` seconds
   - Returns JWT access token (15min) + opaque refresh token (7 days for Telegram users)
   - Tokens stored in HttpOnly cookies by BFF via `setTokenCookies()`

2. **Email/Password Auth** (staff/admin):
   - Login: `POST /api/v1/auth/login` -> returns JWT access + refresh tokens
   - Tokens stored in HttpOnly cookies by admin BFF
   - Cookie management: admin frontend API routes

3. **Token Refresh:**
   - Frontend BFF: `POST /api/auth/refresh` route
   - Main frontend: RTK Query auto-refresh with mutex pattern prevents token stampede (`frontend/main/lib/store/api.ts`)
   - On 401 response: coalesces concurrent refresh calls into single request, retries original request on success, dispatches `sessionExpired()` on failure
   - Backend: validates refresh token hash (SHA-256) against database

4. **Debug Auth** (dev only):
   - Enabled by `BROWSER_DEBUG_AUTH_ENABLED` env var
   - Only works on localhost/127.0.0.1/::1 or hosts in `BROWSER_DEBUG_AUTH_ALLOWED_HOSTS`
   - Tries backend first; falls back to mock tokens if backend unreachable
   - Never available in production (`isProduction()` guard)

**Authorization:**
- RBAC with recursive role hierarchy (`RoleHierarchyModel`)
- Permission resolver with cache-aside pattern
- Permissions cached in Redis with configurable TTL (`SESSION_PERMISSIONS_CACHE_TTL`, default 300s)
- Fallback: PostgreSQL recursive CTE query
- Session-based: `SessionModel` with `SessionRoleModel` for per-session role snapshots
- Session limits: `MAX_ACTIVE_SESSIONS_PER_IDENTITY=5`, idle timeout 30min, absolute lifetime 24h
- Telegram sessions: longer timeouts (idle 1440min, absolute 168h)
- Permission codenames: `module:action` pattern (e.g., `catalog:manage`, `catalog:read`)
- Route-level: `Depends(RequirePermission(codename="catalog:manage"))`

**Password Hashing:**
- Algorithm: Argon2id (primary), Bcrypt (legacy fallback)
- Library: `pwdlib[argon2,bcrypt]`
- Implementation: `backend/src/infrastructure/security/password.py`
- `needs_rehash()` detects legacy Bcrypt hashes for transparent migration
- New passwords always hashed with Argon2id

**JWT:**
- Algorithm: HS256
- Library: PyJWT
- Access token TTL: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Claims: `exp`, `iat`, `jti` (UUID4), `sub` (identity_id), `sid` (session_id), `tv` (token_version)
- Token version validation: `tv` claim compared against `identity.token_version` in database
- Refresh token: opaque `secrets.token_urlsafe(32)`, stored as SHA-256 hash in database
- Implementation: `backend/src/infrastructure/security/jwt.py`

## Monitoring & Observability

**Structured Logging:**
- Library: `structlog >=25.5.0`
- Configuration: `backend/src/bootstrap/logger.py`
- Dev mode: Colored console output with call-site info (filename, func_name, lineno)
- Production mode: JSON lines to stdout for log aggregator ingestion
- Shared processors: contextvars merge, logger name, log level, timestamps (ISO UTC), stack info, unicode decode
- Third-party loggers (uvicorn, FastAPI) redirected through structlog pipeline
- `uvicorn.access` silenced (app provides its own access logging middleware)
- Access logging middleware: `backend/src/api/middlewares/logger.py`
- TaskIQ logging middleware: `backend/src/infrastructure/logging/taskiq_middleware.py`
- Context vars: `request_id`, `identity_id`, `session_id` bound per request

**Error Tracking:**
- No external error tracking service detected (no Sentry, Datadog, etc.)
- DLQ middleware: Failed TaskIQ tasks persisted to `FailedTask` database table (`backend/src/infrastructure/logging/dlq_middleware.py`)
- DLQ uses dedicated SQLAlchemy engine (pool_size=2, max_overflow=1) to avoid Dishka scope conflicts

**Health Checks:**
- Backend: `GET /health` returns `{"status": "ok", "environment": "..."}` (`backend/src/bootstrap/web.py`)
- Image backend: Same pattern
- Docker healthchecks configured for all services:
  - PostgreSQL: `pg_isready -U postgres -d postgres`
  - Redis: `redis-cli -a password ping | grep PONG`
  - RabbitMQ: `rabbitmq-diagnostics -q ping`
  - MinIO: `curl -f http://localhost:9000/minio/health/live`

**Request Tracing:**
- `X-Request-ID` header propagated via `ContextVar` (`backend/src/shared/context.py`)
- Correlation ID attached to outbox events and TaskIQ task labels for end-to-end tracing
- Error responses include `request_id` in the JSON envelope

## CI/CD & Deployment

**Hosting:**
- Railway (PaaS) for both Python backends
  - `backend/railway.toml` - Dockerfile builder
  - `image_backend/railway.toml` - Dockerfile builder
- Frontend deployment target: Not explicitly configured

**CI Pipeline:**
- No CI configuration detected (no `.github/workflows/`, no `.gitlab-ci.yml`)

**Docker:**
- Backend Dockerfile: `backend/Dockerfile` (single-stage, `uv` copied from `ghcr.io/astral-sh/uv:latest`)
- Image backend Dockerfile: `image_backend/Dockerfile` (same pattern)
- Docker Compose: `backend/docker-compose.yml`, `image_backend/docker-compose.yml` (identical infrastructure for local dev)
- Both compose files define shared bridge network `dev_net`
- All services have memory limits: postgres 1024M, redis 512M, rabbitmq 512M, minio 512M

## Event-Driven Architecture

**Outbox Pattern:**
- Purpose: Reliable domain event publishing (transactional outbox)
- Table: `outbox_messages` (id, aggregate_type, aggregate_id, event_type, payload, correlation_id, processed_at)
- Event collection: UoW collects events from registered aggregates at commit time (`backend/src/infrastructure/database/uow.py`)
- Serialization: Recursive serialization of UUID, datetime, nested lists/dicts to JSON-compatible format
- Relay: Polls every minute via TaskIQ Beat (`backend/src/infrastructure/outbox/tasks.py`)
  - Batch size: 100 per cycle
  - Timeout: 55 seconds (shorter than 1-minute cron interval)
  - Queue: `outbox_relay`, routing key: `infrastructure.outbox.relay`
- Pruning: Daily at 03:00 UTC, deletes records older than 7 days
  - Queue: `outbox_pruning`, routing key: `infrastructure.outbox.pruning`
  - Timeout: 120 seconds, max_retries: 1

**Domain Events (currently wired):**
- `identity_registered` -> Creates customer/staff profile (`backend/src/modules/user/application/consumers/identity_events.py`)
- `identity_deactivated` -> Anonymizes customer data (GDPR) (`backend/src/modules/user/application/consumers/identity_events.py`)
- `role_assignment_changed` -> Invalidates permission cache (`backend/src/modules/identity/application/consumers/role_events.py`)

**TaskIQ Queues:**
- `taskiq_background_jobs` - Default job queue
- `outbox_relay` - Outbox polling
- `outbox_pruning` - Outbox cleanup

## Frontend BFF Proxy

**Main Frontend (`frontend/main/app/api/backend/[...path]/route.ts`):**
- Catch-all proxy: All HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Injects `Authorization: Bearer <access_token>` from HttpOnly cookies
- Timeout: 25 seconds (AbortController)
- Filters upstream request headers (allowlist: accept, content-type, accept-language)
- Safe response header forwarding (content-type, content-length, content-disposition, cache-control, x-total-count)
- Path encoding: Normalizes percent-escapes to avoid double-encoding
- Trailing slash handling: Forces trailing slash for POST/PUT/PATCH to `/api/v1` (DRF compatibility)
- Error handling: Returns 502 on upstream failure; sanitized error messages (never exposes internal URLs/IPs/ports)
- Debug info logged server-side only in non-production mode

**Admin Frontend (`frontend/admin/src/lib/api-client.js`):**
- Simple `backendFetch()` wrapper around `fetch()`
- Uses `BACKEND_URL` env var for server-side API calls
- Default headers: `Content-Type: application/json`
- Returns `{ ok, status, data }` tuple

## Environment Configuration

**Required env vars (Backend):**
- `SECRET_KEY` - JWT signing secret (SecretStr)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT` - Redis connection (REDISPASSWORD optional)
- `RABBITMQ_PRIVATE_URL` - RabbitMQ AMQP URL
- `BOT_TOKEN` - Telegram bot token (SecretStr)

**Required env vars (Image Backend):**
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT` - Redis connection
- `RABBITMQ_PRIVATE_URL` - RabbitMQ AMQP URL
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3 storage

**Required env vars (Frontend - Main):**
- `BACKEND_API_BASE_URL` - Backend server URL for BFF proxy
- `DADATA_TOKEN` - DaData API token (server-side only)

**Required env vars (Frontend - Admin):**
- `BACKEND_URL` - Backend server URL

**Env file locations:**
- `backend/.env` (present, gitignored)
- `backend/.env.example` (committed, safe reference)
- `image_backend/.env.example` (committed, safe reference)
- `frontend/main/.env.example` (committed, safe reference)
- `frontend/main/.env.local` (present, gitignored)
- `frontend/admin/.env.local` (present, gitignored)
- `frontend/admin/.env.local.example` (committed, safe reference)

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot webhook: `BOT_WEBHOOK_URL` (optional; polling mode available as fallback)
- Internal webhook: `INTERNAL_WEBHOOK_SECRET` configured but usage not yet widespread

**Outgoing:**
- Backend -> Image Backend: DELETE calls for media cleanup (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)
- Frontend -> DaData: Address suggestion/cleaning requests (proxied through Next.js BFF)
- Frontend -> Telegram WebApp: SDK callbacks via `window.Telegram.WebApp` methods

---

*Integration audit: 2026-03-28*
