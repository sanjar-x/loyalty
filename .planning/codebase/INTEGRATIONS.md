# External Integrations

**Analysis Date:** 2026-03-28

## APIs & External Services

**Telegram Bot API:**
- Purpose: Telegram bot for user interaction (commands, inline keyboards, FSM flows)
- SDK: `aiogram >=3.26.0`
- Auth: `BOT_TOKEN` env var (SecretStr in `backend/src/bootstrap/config.py`)
- Implementation: `backend/src/bot/factory.py` creates Bot + Dispatcher
- Middleware chain: LoggingMiddleware -> UserIdentifyMiddleware -> ThrottlingMiddleware
- FSM storage: Redis-backed via `aiogram.fsm.storage.redis.RedisStorage`
- Commands: `/start`, `/help`, `/cancel` (set in `backend/src/bot/factory.py`)
- Webhook support: `BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET` env vars
- Handlers: `backend/src/bot/handlers/` (common, errors, nav)
- Keyboards: `backend/src/bot/keyboards/` (inline, reply)

**Telegram Mini App (WebApp) Auth:**
- Purpose: Authenticate Telegram users in the main customer frontend
- Flow: Frontend sends `initData` -> Next.js BFF (`frontend/main/app/api/auth/telegram/route.ts`) -> Backend IAM (`/api/v1/auth/telegram`)
- Validation: HMAC-SHA256 via `aiogram.utils.web_app.safe_parse_webapp_init_data` (`backend/src/infrastructure/security/telegram.py`)
- Freshness: `TELEGRAM_INIT_DATA_MAX_AGE` (default 300 seconds)
- Token flow: Backend returns JWT accessToken + opaque refreshToken -> BFF sets HttpOnly cookies
- Frontend SDK: `frontend/main/lib/telegram/` (custom hooks wrapping `window.Telegram.WebApp`)
- Script: `https://telegram.org/js/telegram-web-app.js` loaded in `frontend/main/app/layout.tsx`

**DaData (Address Suggestions):**
- Purpose: Russian address autocomplete for city/settlement lookup
- API: `https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address`
- Implementation: `frontend/main/app/api/dadata/suggest/address/route.ts` (server-side proxy)
- Also: `frontend/main/app/api/dadata/clean/address/route.ts` (address cleaning)
- Auth: `DADATA_TOKEN` env var (Token-based Authorization header), optional `DADATA_SECRET` (X-Secret header)
- Scope: Suggestions bounded from `city` to `settlement`

**Image Backend (Internal Microservice):**
- Purpose: Image upload, resize, thumbnail generation, WebP conversion
- Protocol: HTTP REST (server-to-server)
- Client: `backend/src/modules/catalog/infrastructure/image_backend_client.py` (httpx AsyncClient)
- Auth: API key via `X-API-Key` header
- Base URL: `IMAGE_BACKEND_URL` env var (default `http://localhost:8001`)
- API key: `IMAGE_BACKEND_API_KEY` env var
- Operations: DELETE `/api/v1/media/{storage_object_id}` (best-effort cleanup)
- Image backend validates: `INTERNAL_API_KEY` in `image_backend/src/api/dependencies/auth.py`

## Data Storage

**PostgreSQL (Primary Database):**
- Version: 18 Alpine (Docker)
- Separate databases: `enterprise` (backend), `image_backend` (image service)
- Driver: `asyncpg` (async, binary protocol)
- ORM: SQLAlchemy 2.1+ async mode with `DeclarativeBase`
- Connection pool: `AsyncAdaptedQueuePool` (size=15, max_overflow=10, recycle=3600s)
- Connection settings: `statement_timeout=30s`, `idle_in_transaction_session_timeout=60s`, timezone=UTC
- Naming conventions: `backend/src/infrastructure/database/base.py` (ix_, uq_, ck_, fk_, pk_ prefixes)
- Migrations: Alembic with date-based subdirectories (`backend/alembic/versions/2026/03/`)
- UoW pattern: `backend/src/infrastructure/database/uow.py` (IUnitOfWork interface)
- Isolation: READ COMMITTED

**Database Models (Backend):**
- Catalog: `Product`, `ProductVariant`, `SKU`, `Category`, `Brand`, `Attribute`, `AttributeGroup`, `AttributeValue`, `AttributeTemplate`, `TemplateAttributeBinding`, `ProductAttributeValue`, `SKUAttributeValueLink`, `MediaAsset` (`backend/src/modules/catalog/infrastructure/models.py`)
- Identity/IAM: `IdentityModel`, `RoleModel`, `PermissionModel`, `SessionModel`, `LinkedAccountModel`, `LocalCredentialsModel`, `RoleHierarchyModel`, `RolePermissionModel`, `IdentityRoleModel`, `SessionRoleModel`, `StaffInvitationModel`, `StaffInvitationRoleModel` (`backend/src/modules/identity/infrastructure/models.py`)
- Geo: `CountryModel`, `CountryTranslationModel`, `CurrencyModel`, `CurrencyTranslationModel`, `LanguageModel`, `SubdivisionModel`, `SubdivisionTranslationModel`, `SubdivisionCategoryModel`, `SubdivisionCategoryTranslationModel`, `CountryCurrencyModel` (`backend/src/modules/geo/infrastructure/models.py`)
- User: `CustomerModel`, `StaffMemberModel` (`backend/src/modules/user/infrastructure/models.py`)
- Supplier: `Supplier` (`backend/src/modules/supplier/infrastructure/models.py`)
- Infrastructure: `OutboxMessage`, `FailedTask` (`backend/src/infrastructure/database/models/`)

**Redis (Cache + Session Store):**
- Version: 8.4 Alpine (Docker)
- Driver: `redis-py` async with `hiredis` C extension
- Connection pool: max 100 connections, socket timeout 5s, connect timeout 2s
- Provider: `backend/src/infrastructure/cache/provider.py`
- Implementation: `backend/src/infrastructure/cache/redis.py` (RedisService -> ICacheService)
- Uses:
  - Permission cache (cache-aside pattern, TTL from `SESSION_PERMISSIONS_CACHE_TTL`)
  - Aiogram FSM state storage (separate connection in `backend/src/bot/factory.py`)
  - General caching via `ICacheService` interface
- Backend uses DB 0; Image backend uses DB 1

**S3/MinIO (Object Storage):**
- Purpose: Image file storage (upload, serve)
- Provider: MinIO (dev), S3-compatible in production
- Client: `aiobotocore` via `S3ClientFactory` (`image_backend/src/infrastructure/storage/factory.py`)
- Config: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`
- Public URL: `S3_PUBLIC_BASE_URL` (for generating public-facing image URLs)
- Ephemeral client pattern: each operation gets its own short-lived client
- Retry: 3 attempts, standard mode; timeouts: connect 5s, read 60s

**RabbitMQ (Message Broker):**
- Version: 4.2.4 Management Alpine (Docker)
- Client: TaskIQ via `taskiq-aio-pika` (`AioPikaBroker`)
- Exchange: `taskiq_rpc_exchange` (declared, direct)
- Queue: `taskiq_background_jobs` (declared, QoS prefetch=10)
- Connection: `RABBITMQ_PRIVATE_URL` env var (AMQP URL)
- Configuration: `backend/src/bootstrap/broker.py`
- Management console: port 15672

## Authentication & Identity

**Auth Provider: Custom IAM (Identity & Access Management)**
- Implementation: Full custom RBAC system in `backend/src/modules/identity/`
- Identity types: Staff (email/password), Customer (Telegram), Linked accounts

**Authentication Flows:**
1. **Telegram Mini App Auth** (customers):
   - Client sends `initData` string from Telegram WebApp SDK
   - BFF proxy: `frontend/main/app/api/auth/telegram/route.ts` -> `POST /api/v1/auth/telegram`
   - Backend validates HMAC-SHA256 signature using bot token
   - Returns JWT access token (15min) + opaque refresh token (7 days for Telegram users)
   - Tokens stored in HttpOnly cookies by BFF

2. **Email/Password Auth** (staff/admin):
   - Login: `POST /api/v1/auth/login` -> returns JWT access + refresh tokens
   - Tokens stored in HttpOnly cookies by admin BFF
   - Cookie management: `frontend/admin/src/lib/auth.js`

3. **Token Refresh:**
   - Frontend: `POST /api/auth/refresh` (BFF route)
   - RTK Query auto-refresh: `frontend/main/lib/store/api.ts` (mutex pattern prevents token stampede)
   - Backend: validates refresh token hash against database

**Authorization:**
- RBAC with role hierarchy (`RoleHierarchyModel`)
- Permission resolver: `backend/src/infrastructure/security/authorization.py`
- Cache-aside: Permissions cached in Redis with configurable TTL
- Session-based: `SessionModel` with `SessionRoleModel` for per-session role snapshots
- Session limits: `MAX_ACTIVE_SESSIONS_PER_IDENTITY=5`, idle timeout 30min, absolute lifetime 24h
- Telegram sessions: longer timeouts (idle 1440min, absolute 168h)

**Password Hashing:**
- Algorithm: Argon2id (primary), bcrypt (fallback)
- Library: `pwdlib[argon2,bcrypt]`
- Implementation: `backend/src/infrastructure/security/password.py`

**JWT:**
- Algorithm: HS256
- Library: PyJWT
- Access token TTL: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Claims: `exp`, `iat`, `jti` (UUID)
- Implementation: `backend/src/infrastructure/security/jwt.py`

## Monitoring & Observability

**Structured Logging:**
- Library: `structlog >=25.5.0`
- Adapter: `backend/src/infrastructure/logging/adapter.py` (StructlogAdapter -> ILogger)
- Access logging middleware: `backend/src/api/middlewares/logger.py`
- TaskIQ logging middleware: `backend/src/infrastructure/logging/taskiq_middleware.py`
- Context vars: `correlation_id`, `event_id`, `event_type` bound per request/task

**Error Tracking:**
- No external error tracking service detected (no Sentry, Datadog, etc.)
- DLQ middleware: Failed TaskIQ tasks persisted to `FailedTask` table (`backend/src/infrastructure/logging/dlq_middleware.py`)

**Health Checks:**
- Backend: `GET /health` returns `{"status": "ok", "environment": "..."}` (`backend/src/bootstrap/web.py`)
- Image backend: Same pattern (`image_backend/src/bootstrap/web.py`)
- Docker healthchecks: PostgreSQL (`pg_isready`), Redis (`redis-cli ping`), RabbitMQ (`rabbitmq-diagnostics ping`), MinIO (`curl /minio/health/live`)

## CI/CD & Deployment

**Hosting:**
- Railway (PaaS) for both Python backends
  - `backend/railway.toml` - Dockerfile builder
  - `image_backend/railway.toml` - Dockerfile builder
- Frontend deployment target: Not explicitly configured (likely Vercel or Railway)

**CI Pipeline:**
- No CI configuration detected (no `.github/workflows/`, no `.gitlab-ci.yml`)

**Docker:**
- Backend Dockerfile: `backend/Dockerfile` (multi-stage with `uv` for fast installs)
- Image backend Dockerfile: `image_backend/Dockerfile`
- Docker Compose: `backend/docker-compose.yml` (shared infrastructure for local dev)

## Event-Driven Architecture

**Outbox Pattern:**
- Purpose: Reliable domain event publishing (transactional outbox)
- Table: `outbox_messages` (event_type, payload, correlation_id, processed_at)
- Relay: Polls every minute via TaskIQ Beat (`backend/src/infrastructure/outbox/tasks.py`)
- Concurrency: `FOR UPDATE SKIP LOCKED` for parallel relay workers
- Pruning: Daily at 03:00 UTC, deletes records older than 7 days

**Domain Events:**
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
- Timeout: 25 seconds
- Filters upstream headers (allowlist: accept, content-type, accept-language)
- Safe response header forwarding (content-type, content-length, cache-control, x-total-count)
- Error handling: Returns 502 on upstream failure with sanitized error messages

**Admin Frontend (`frontend/admin/src/lib/api-client.js`):**
- Simple `backendFetch()` wrapper around `fetch()`
- Uses `BACKEND_URL` env var for server-side API calls
- Auth cookies managed via `frontend/admin/src/lib/auth.js`

## Environment Configuration

**Required env vars (Backend):**
- `SECRET_KEY` - JWT signing secret
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT` - Redis connection
- `RABBITMQ_PRIVATE_URL` - RabbitMQ AMQP URL
- `BOT_TOKEN` - Telegram bot token

**Required env vars (Image Backend):**
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `REDISHOST`, `REDISPORT` - Redis connection
- `RABBITMQ_PRIVATE_URL` - RabbitMQ AMQP URL
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3 storage

**Required env vars (Frontend - Main):**
- `BACKEND_API_BASE_URL` - Backend server URL for BFF proxy
- `DADATA_TOKEN` - DaData API token (server-side only)

**Required env vars (Frontend - Admin):**
- `BACKEND_URL` - Backend server URL for API calls

**Env file locations:**
- `backend/.env` (present, gitignored)
- `backend/.env.example` (committed, safe reference)
- `image_backend/.env.example` (committed, safe reference)

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot webhook: `BOT_WEBHOOK_URL` (optional; polling mode available as fallback)
- Internal webhook: `INTERNAL_WEBHOOK_SECRET` configured but usage not yet widespread

**Outgoing:**
- Backend -> Image Backend: DELETE calls for media cleanup (`backend/src/modules/catalog/infrastructure/image_backend_client.py`)
- Frontend -> DaData: Address suggestion/cleaning requests (proxied through BFF)
- Frontend -> Telegram WebApp: SDK callbacks via `window.Telegram.WebApp` methods

---

*Integration audit: 2026-03-28*
