# External Integrations

**Analysis Date:** 2026-03-28

## Architecture Overview

The system is a **microservice architecture** with four deployable units:

1. **Backend API** (`backend/`) - Core business logic, identity, catalog, geo, supplier modules
2. **Image Backend** (`image_backend/`) - Image processing microservice (upload, resize, WebP conversion)
3. **Frontend Main** (`frontend/main/`) - Customer-facing Telegram Mini App (Next.js)
4. **Frontend Admin** (`frontend/admin/`) - Admin panel (Next.js)

## APIs & External Services

**DaData (Russian address standardization):**
- Purpose: Address suggestion and cleaning for geo features
- Endpoints used:
  - `https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address` (Suggest API)
  - `https://cleaner.dadata.ru/api/v1/clean/address` (Cleaner API)
- Auth: Token-based (`Authorization: Token <token>` header + `X-Secret` header for Cleaner)
- Env vars: `DADATA_TOKEN`, `DADATA_SECRET`
- Proxy routes (BFF pattern, secrets never exposed to client):
  - `frontend/main/app/api/dadata/suggest/address/route.ts`
  - `frontend/main/app/api/dadata/clean/address/route.ts`

**Telegram Bot API (via Aiogram):**
- Purpose: Telegram bot for user interaction
- SDK: Aiogram `>=3.26.0`
- Auth: `BOT_TOKEN` env var
- Bot factory: `backend/src/bot/factory.py`
- Middleware chain: logging -> user identification -> throttling
- FSM storage: Redis-backed (`aiogram.fsm.storage.redis.RedisStorage`)
- Commands: `/start`, `/help`, `/cancel`

**Telegram Mini App (WebApp API):**
- Purpose: Customer-facing web app embedded in Telegram
- Client SDK: `window.Telegram.WebApp` (injected by Telegram client)
- Core wrapper: `frontend/main/lib/telegram/core.ts`
- Context provider: `frontend/main/lib/telegram/TelegramProvider.tsx`
- Auth flow:
  1. Mini App captures `initData` from `window.Telegram.WebApp`
  2. Frontend POSTs to `/api/auth/telegram` (Next.js BFF route)
  3. BFF forwards `Authorization: tma <initData>` to `backend /api/v1/auth/telegram`
  4. Backend validates initData HMAC, creates/finds identity, returns JWT tokens
  5. BFF sets HTTP-only cookies (`access_token`, `refresh_token`)
- Route: `frontend/main/app/api/auth/telegram/route.ts`
- Backend handler: `backend/src/modules/identity/presentation/router_auth.py`

## Inter-Service Communication

**Backend -> Image Backend (HTTP):**
- Purpose: Server-to-server media management (delete operations)
- Client: `backend/src/modules/catalog/infrastructure/image_backend_client.py`
- Transport: httpx AsyncClient
- Auth: `X-API-Key` header (env var: `IMAGE_BACKEND_API_KEY`)
- Base URL: env var `IMAGE_BACKEND_URL` (default: `http://localhost:8001`)
- Operations: DELETE `/api/v1/media/{storage_object_id}` (best-effort, fire-and-forget)

**Frontend Main -> Backend (HTTP Proxy / BFF):**
- Purpose: All client API requests proxied through Next.js server
- Proxy route: `frontend/main/app/api/backend/[...path]/route.ts`
- Pattern: Catch-all route forwards all methods (GET, POST, PUT, PATCH, DELETE)
- Auth injection: Reads `access_token` from HTTP-only cookie, sets `Authorization: Bearer` header
- Timeout: 25 seconds
- Base URL: env var `BACKEND_API_BASE_URL`

**Frontend Admin -> Backend (HTTP, Server-Side):**
- Purpose: Server-side data fetching for admin panel
- Client: `frontend/admin/src/lib/api-client.js` (`backendFetch()` helper)
- Auth: Cookie-based JWT (via `frontend/admin/src/lib/auth.js`)
- Base URL: env var `BACKEND_URL`
- Pattern: Next.js Server Actions / API routes proxy to backend

**Async Event Processing (Outbox -> RabbitMQ -> TaskIQ Workers):**
- Purpose: Reliable async event processing between bounded contexts
- Pattern: Transactional Outbox with Polling Publisher
- Outbox table: `outbox_messages` in PostgreSQL
- Relay: `backend/src/infrastructure/outbox/relay.py` (polls every minute via TaskIQ Beat)
- Events handled:
  - `identity_registered` -> creates user profile (Customer/StaffMember)
  - `identity_deactivated` -> anonymizes customer data (GDPR)
  - `role_assignment_changed` -> invalidates Redis permission cache
- Task definitions:
  - `backend/src/infrastructure/outbox/tasks.py` - relay and pruning tasks
  - `backend/src/modules/identity/application/consumers/role_events.py` - permission cache invalidation
  - `backend/src/modules/user/application/consumers/identity_events.py` - profile creation/anonymization
- Scheduled tasks:
  - Outbox relay: every minute (`* * * * *`)
  - Outbox pruning: daily at 03:00 UTC (`0 3 * * *`), deletes processed records older than 7 days

## Data Storage

**Databases:**
- PostgreSQL 18 (separate databases per service)
  - Backend DB: env var `PGDATABASE` (default: `enterprise`)
  - Image Backend DB: env var `PGDATABASE` (default: `image_backend`)
  - Driver: `postgresql+asyncpg` (async)
  - Connection pool: `AsyncAdaptedQueuePool`, 15 connections, +10 overflow
  - Config: `backend/src/infrastructure/database/provider.py`
  - Migrations: Alembic with date-based subdirectories (`backend/alembic/`, `image_backend/alembic/`)

**Caching:**
- Redis 8.4
  - Backend: DB 0 (default), used for permission caching, general cache
  - Image Backend: DB 1, used for processing state
  - Bot FSM: Shares backend Redis, key prefix `fsm:`
  - Connection: `redis[hiredis]` async client, 100 max connections
  - Config: `backend/src/infrastructure/cache/provider.py`
  - Eviction policy: `allkeys-lru` (256MB max, configured in docker-compose)

**File/Object Storage:**
- S3-compatible (MinIO in development, AWS S3 or compatible in production)
  - Used by: Image Backend only
  - Client: `aiobotocore` via `image_backend/src/infrastructure/storage/factory.py`
  - Pattern: Ephemeral S3 clients per operation (context-manager based)
  - Bucket: env var `S3_BUCKET_NAME` (default: `media-bucket`)
  - Public URL: env var `S3_PUBLIC_BASE_URL`

**Message Broker:**
- RabbitMQ 4.2.4
  - Exchange: `taskiq_rpc_exchange` (declared automatically)
  - Queue: `taskiq_background_jobs` (default), plus `outbox_relay`, `outbox_pruning`, `iam_events`
  - QoS prefetch: 10
  - Config: `backend/src/bootstrap/broker.py`

## Authentication & Identity

**Auth Provider:** Custom IAM (Identity & Access Management)
- Module: `backend/src/modules/identity/`
- Presentation: `backend/src/modules/identity/presentation/router_auth.py`

**Authentication Methods:**
1. Email/password registration and login
   - Password hashing: Argon2id (primary) with Bcrypt legacy fallback
   - Implementation: `backend/src/infrastructure/security/password.py`
2. Telegram Mini App (`tma` scheme)
   - HMAC validation of Telegram `initData`
   - Handler: `backend/src/modules/identity/application/commands/login_telegram.py`

**Token Strategy:**
- Access token: JWT (HS256), 15-minute expiry
  - Payload: custom claims + `exp`, `iat`, `jti`
  - Implementation: `backend/src/infrastructure/security/jwt.py`
- Refresh token: Opaque (secrets.token_urlsafe), SHA-256 hash stored in DB
  - Backend expiry: 30 days (standard), 7 days (Telegram)
  - Rotation on use (old token invalidated)

**Session Management:**
- Max active sessions per identity: 5
- Session idle timeout: 30 minutes (standard), 1440 minutes (Telegram)
- Session absolute lifetime: 24 hours (standard), 168 hours (Telegram)
- Permission caching: Redis with TTL (300s default), invalidated via async events

**RBAC:**
- Permission resolver with cache-aside strategy
  - Primary: Redis cache per session
  - Fallback: CTE-based PostgreSQL query
  - Implementation: `backend/src/infrastructure/security/authorization.py`

**Frontend Cookie Management:**
- Frontend Main: HTTP-only cookies (`access_token`, `refresh_token`), SameSite=Lax
  - Cookie helper: `frontend/main/lib/auth/cookie-helpers.ts`
  - Auto-refresh: RTK Query baseQuery with 401 retry + mutex (`frontend/main/lib/store/api.ts`)
- Frontend Admin: HTTP-only cookies, same pattern
  - Cookie helper: `frontend/admin/src/lib/auth.js`

## Monitoring & Observability

**Structured Logging:**
- Framework: structlog `>=25.5.0`
- Dev: Colored console output with call-site info (file, function, line)
- Production: JSON lines to stdout (for log aggregator ingestion)
- Config: `backend/src/bootstrap/logger.py`
- Access logging: Custom middleware (`backend/src/api/middlewares/logger.py`)
- TaskIQ middleware: `backend/src/infrastructure/logging/taskiq_middleware.py`

**Error Tracking:**
- Not detected (no Sentry, Datadog, or similar SDK)

**DLQ (Dead Letter Queue):**
- Failed TaskIQ tasks persisted to database
- Implementation: `backend/src/infrastructure/logging/dlq_middleware.py`
- Model: `backend/src/infrastructure/database/models/failed_task.py`

## CI/CD & Deployment

**Backend + Image Backend:**
- Platform: Railway
- Build: Dockerfile-based (`railway.toml` -> `Dockerfile`)
- Entrypoint: `backend/scripts/entrypoint.sh` (runs `alembic upgrade head`, then `uvicorn`)
- Image Backend: Direct `uvicorn main:app --host 0.0.0.0 --port 8001`

**Frontend Main:**
- Platform: Netlify
- Build: `npm run build`
- Plugin: `@netlify/plugin-nextjs`
- Config: `frontend/main/netlify.toml`

**Frontend Admin:**
- Deployment target not explicitly configured (standard Next.js build)

**CI Pipeline:**
- Not detected (no `.github/workflows/`, `.gitlab-ci.yml`, or similar)

## Security Headers

**Frontend Admin (`frontend/admin/next.config.js`):**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` (self + unsafe-inline/eval for scripts/styles)
- `Strict-Transport-Security` (HSTS with preload)
- `Permissions-Policy` (camera, microphone, geolocation disabled)

**Frontend Main (`frontend/main/middleware.ts`):**
- Edge middleware with CSRF protection for auth routes (Origin check)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN` (Telegram iframe embedding)
- `Referrer-Policy: strict-origin-when-cross-origin`

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot webhook (optional, configured via `BOT_WEBHOOK_URL` and `BOT_WEBHOOK_SECRET`)
- Image Backend: API-key authenticated endpoints for media operations

**Outgoing:**
- None detected (all async processing is internal via outbox + message broker)

## Environment Configuration

**Required env vars (Backend):**
- `SECRET_KEY` - JWT signing (critical)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL
- `REDISHOST`, `REDISPORT` - Redis
- `RABBITMQ_PRIVATE_URL` - RabbitMQ AMQP URL
- `BOT_TOKEN` - Telegram Bot token

**Required env vars (Image Backend):**
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL
- `REDISHOST`, `REDISPORT` - Redis
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` - S3
- `RABBITMQ_PRIVATE_URL` - RabbitMQ

**Required env vars (Frontend Main):**
- `BACKEND_API_BASE_URL` - Backend server URL for BFF proxy

**Optional env vars:**
- `DADATA_TOKEN`, `DADATA_SECRET` - DaData integration
- `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY` - Image Backend connectivity
- `COOKIE_DOMAIN` - Auth cookie domain for cross-subdomain sharing
- `BROWSER_DEBUG_AUTH_ALLOWED_HOSTS` - Debug auth in non-Telegram browsers

**Secrets location:**
- `.env` files (gitignored, local development)
- `.env.example` files committed as templates (`backend/.env.example`, `image_backend/.env.example`)
- Railway environment variables (production)
- Netlify environment variables (frontend production)

---

*Integration audit: 2026-03-28*
