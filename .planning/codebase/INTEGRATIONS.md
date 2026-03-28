# External Integrations

**Analysis Date:** 2026-03-28

## Architecture Overview

Four deployable units with clearly defined communication paths:

```
[Telegram Client]
    |
    v
[Frontend Main]  ----BFF proxy----> [Backend API]
  (Next.js)        /api/backend/*     (FastAPI)
    |                                    |
    +-- /api/dadata/* --> [DaData API]   +-- httpx --> [Image Backend]
    |                                    |              (FastAPI)
    +-- /api/auth/* (cookie mgmt)        +-- outbox --> [RabbitMQ] --> [Workers]
                                         |
[Frontend Admin] ----server fetch----> [Backend API]
  (Next.js)        via BACKEND_URL
```

## APIs & External Services

**DaData (Russian address standardization):**
- Purpose: Address suggestion and geocoding for delivery/pickup features
- Endpoints:
  - Suggest: `https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address`
  - Clean: `https://cleaner.dadata.ru/api/v1/clean/address`
- Auth: Token-based (`Authorization: Token <token>`) + optional `X-Secret` header
- Env vars: `DADATA_TOKEN`, `DADATA_SECRET`
- Proxy routes (BFF pattern -- secrets never reach the browser):
  - `frontend/main/app/api/dadata/suggest/address/route.ts`
  - `frontend/main/app/api/dadata/clean/address/route.ts`
- Params: `query` (string), `count` (1-10, default 5), bounded from `city` to `settlement`

**Telegram Bot API:**
- Purpose: Bot for user interaction (commands, inline keyboards, FSM flows)
- SDK: Aiogram `>=3.26.0`
- Auth: `BOT_TOKEN` env var
- Bot factory: `backend/src/bot/factory.py`
- Handlers: `backend/src/bot/handlers/` (common, nav, errors, registry)
- Keyboards: `backend/src/bot/keyboards/` (inline, reply)
- Callbacks: `backend/src/bot/callbacks/base.py`
- FSM storage: Redis-backed
- Webhook mode: optional (`BOT_WEBHOOK_URL`, `BOT_WEBHOOK_SECRET`)
- Throttle: configurable rate (`THROTTLE_RATE`, default 0.5s)

**Telegram Mini App (WebApp API):**
- Purpose: Customer-facing web application embedded in Telegram
- Client SDK: `window.Telegram.WebApp` (injected by Telegram client at runtime)
- Core wrapper: `frontend/main/lib/telegram/core.ts`
- Hooks library: `frontend/main/lib/telegram/hooks/` (30+ hooks covering all WebApp APIs)
  - `useTelegram.ts`, `useBackButton.ts`, `useMainButton.ts`, `useHaptic.ts`, `useViewport.ts`, `usePopup.ts`, `useQrScanner.ts`, `useBiometric.ts`, `useCloudStorage.ts`, `useFullscreen.ts`, etc.
- Types: `frontend/main/lib/telegram/types.ts`, `frontend/main/lib/types/telegram-globals.d.ts`
- Auth flow:
  1. Mini App loads, captures `initData` from `window.Telegram.WebApp`
  2. Frontend POSTs to `/api/auth/telegram` (Next.js BFF route)
  3. BFF forwards `Authorization: tma <initData>` to `backend /api/v1/auth/telegram`
  4. Backend validates initData HMAC-SHA256 via `backend/src/infrastructure/security/telegram.py`
  5. Backend creates/finds identity, returns JWT access + refresh tokens
  6. BFF sets HTTP-only cookies (`access_token`, `refresh_token`)
- Route: `frontend/main/app/api/auth/telegram/route.ts`
- Debug mode: `BROWSER_DEBUG_AUTH=true` allows auth without Telegram client (dev only)

## Inter-Service Communication

**Backend -> Image Backend (HTTP, server-to-server):**
- Purpose: Media asset lifecycle management (upload orchestration, deletion)
- Transport: httpx `AsyncClient`
- Auth: `X-API-Key` header (env var: `IMAGE_BACKEND_API_KEY` on backend, `INTERNAL_API_KEY` on image_backend)
- Base URL: env var `IMAGE_BACKEND_URL` (default: `http://localhost:8001`)
- Image Backend API prefix: `/api/v1/media/`
- Endpoints consumed:
  - `POST /media/upload` - Reserve upload slot, get presigned PUT URL
  - `POST /media/{id}/reupload` - Replace image, keep same ID
  - `POST /media/{id}/confirm` - Trigger background processing
  - `GET /media/{id}/status` - SSE stream for processing status
  - `GET /media/{id}` - Get metadata
  - `DELETE /media/{id}` - Delete files + record
  - `POST /media/external` - Import from external URL
- Auth validation: `image_backend/src/api/dependencies/auth.py` (HMAC-safe comparison, disableable in dev)

**Frontend Main -> Backend (HTTP BFF Proxy):**
- Purpose: All client API requests proxied through Next.js server (cookie-to-bearer conversion)
- Proxy route: `frontend/main/app/api/backend/[...path]/route.ts`
- Methods: GET, POST, PUT, PATCH, DELETE (all proxied)
- Auth injection: Reads `access_token` from HTTP-only cookie, sets `Authorization: Bearer` header upstream
- Timeout: 25 seconds (AbortController)
- Header filtering: Only forwards `accept`, `content-type`, `accept-language`
- Response header forwarding: `content-type`, `content-length`, `content-disposition`, `cache-control`, `x-total-count`
- Error handling: Returns 502 with generic message (never leaks upstream URLs/IPs)

**Frontend Main -> Backend (Auth routes):**
- `/api/auth/telegram` - Telegram initData login (`frontend/main/app/api/auth/telegram/route.ts`)
- `/api/auth/refresh` - Token refresh (`frontend/main/app/api/auth/refresh/route.ts`)
- `/api/auth/logout` - Session logout (`frontend/main/app/api/auth/logout/route.ts`)
- RTK Query auto-reauth: On 401, refreshes tokens via `/api/auth/refresh` with mutex to prevent stampede (`frontend/main/lib/store/api.ts`)

**Frontend Admin -> Backend (Server-Side Fetch):**
- Purpose: Server-side data fetching + mutation for admin panel
- Client: `frontend/admin/src/lib/api-client.js` (`backendFetch()` helper)
- Auth: Cookie-based JWT, middleware refresh in `frontend/admin/src/proxy.js`
- Base URL: env var `BACKEND_URL` (e.g., `http://127.0.0.1:8000`)
- Login: `frontend/admin/src/app/api/auth/login/route.js` -> `POST /api/v1/auth/login`
- Token refresh: `frontend/admin/src/proxy.js` middleware on `/admin/:path*`
- API routes proxy pattern: `frontend/admin/src/app/api/` mirrors backend routes

**Async Event Processing (Outbox -> RabbitMQ -> TaskIQ Workers):**
- Pattern: Transactional Outbox with Polling Publisher
- Outbox table: `outbox_messages` in PostgreSQL (backend DB)
- Relay: `backend/src/infrastructure/outbox/relay.py`
  - Uses `FOR UPDATE SKIP LOCKED` for concurrent relay workers
  - Per-event transaction isolation
- Broker config: `backend/src/bootstrap/broker.py`
  - Exchange: `taskiq_rpc_exchange`
  - Queue: `taskiq_background_jobs`
  - QoS prefetch: 10
- Event handlers registered via `register_event_handler()` in `backend/src/infrastructure/outbox/relay.py`
- Task consumers:
  - `backend/src/infrastructure/outbox/tasks.py` - Relay + pruning scheduled tasks
  - `backend/src/modules/identity/application/consumers/role_events.py` - Permission cache invalidation
  - `backend/src/modules/user/application/consumers/identity_events.py` - Profile creation on registration
- Scheduled tasks (via TaskIQ Beat / `backend/src/bootstrap/scheduler.py`):
  - Outbox relay: every minute
  - Outbox pruning: daily at 03:00 UTC (deletes processed records >7 days old)
- DLQ: Failed tasks persisted to `failed_tasks` table via `backend/src/infrastructure/logging/dlq_middleware.py`

## Data Storage

**PostgreSQL 18:**
- Separate databases per service:
  - Backend: env var `PGDATABASE` (default: `enterprise`)
  - Image Backend: env var `PGDATABASE` (default: `image_backend`)
- Driver: `postgresql+asyncpg` (async)
- Connection config: individual PG* env vars (not a connection URL)
- ORM: SQLAlchemy 2.1 async
- Migrations: Alembic with date-based subdirectory structure
  - Backend: `backend/alembic/`
  - Image Backend: `image_backend/alembic/`
- Key tables (backend): `outbox_messages`, `failed_tasks`, plus module-specific tables
- Key tables (image_backend): `storage_files`, `failed_tasks`

**Redis 8.4:**
- Shared instance, separated by database number:
  - Backend: DB 0 (general cache, permission caching, bot FSM)
  - Image Backend: DB 1 (SSE pub/sub, processing state)
- Connection: `redis[hiredis]` async client
- Docker config: 256MB max, `allkeys-lru` eviction policy
- Use cases:
  - Permission caching (TTL 300s, invalidated via async events)
  - Bot FSM state/data storage
  - Image processing SSE pub/sub
  - General key-value caching (`backend/src/infrastructure/cache/redis.py`)
- Error handling: Cache failures logged but never propagate (graceful degradation)

**S3-Compatible Object Storage (MinIO dev / AWS S3 prod):**
- Used by: Image Backend only
- Client: `aiobotocore` via `image_backend/src/infrastructure/storage/factory.py`
- Service: `image_backend/src/modules/storage/infrastructure/service.py` (S3StorageService)
- Pattern: Ephemeral single-use S3 clients (context-manager, TCP torn down per operation)
- Bucket: env var `S3_BUCKET_NAME` (default: `media-bucket`)
- Public URL: env var `S3_PUBLIC_BASE_URL`
- Key layout:
  - `raw/{storage_object_id}/{filename}` - Original uploads
  - `public/{storage_object_id}.webp` - Processed main image
  - `public/{storage_object_id}_{suffix}.webp` - Variants (thumb, md, lg)
- Operations: streaming upload (multipart 5MB parts), download, presigned URLs (PUT + GET), batch delete, copy, HEAD
- Presigned URL TTL: 300 seconds (configurable via `PRESIGNED_URL_TTL`)
- Max file size: 50MB (configurable via `MAX_FILE_SIZE`)
- External import max: 10MB per file

**RabbitMQ 4.2.4:**
- Purpose: Message broker for TaskIQ background tasks
- Exchange: `taskiq_rpc_exchange` (auto-declared)
- Queue: `taskiq_background_jobs` (auto-declared)
- Connection: AMQP URL via `RABBITMQ_PRIVATE_URL`
- Management UI: port 15672 (dev)

## Authentication & Identity

**Auth Provider:** Custom IAM (Identity & Access Management)
- Module: `backend/src/modules/identity/`
- Security infrastructure: `backend/src/infrastructure/security/`

**Authentication Methods:**
1. **Email/password** (admin panel login)
   - Endpoint: `POST /api/v1/auth/login`
   - Password hashing: Argon2id primary, Bcrypt legacy fallback
   - Implementation: `backend/src/infrastructure/security/password.py`
2. **Telegram Mini App** (customer login)
   - Endpoint: `POST /api/v1/auth/telegram`
   - HMAC-SHA256 validation of Telegram `initData`
   - Implementation: `backend/src/infrastructure/security/telegram.py`
   - Uses aiogram's `safe_parse_webapp_init_data()` + custom freshness check

**Token Strategy:**
- Access token: JWT (HS256), 15-minute expiry
  - Claims: `sub` (identity_id), `exp`, `iat`, `jti`
  - Implementation: `backend/src/infrastructure/security/jwt.py`
- Refresh token: Opaque (`secrets.token_urlsafe(32)`), SHA-256 hash stored in DB
  - Standard expiry: 30 days
  - Telegram expiry: 7 days
  - Rotation on use (old token invalidated)
- Auth dependency: `backend/src/api/dependencies/auth.py` (extracts identity_id from JWT, binds to structlog context)

**Session Management (configured in `backend/src/bootstrap/config.py`):**
- Max active sessions per identity: 5
- Session idle timeout: 30 min (standard), 1440 min / 24h (Telegram)
- Session absolute lifetime: 24h (standard), 168h / 7 days (Telegram)

**RBAC:**
- Cache-aside permission resolver
  - Primary: Redis cache per session (TTL 300s)
  - Fallback: CTE-based PostgreSQL query
  - Implementation: `backend/src/infrastructure/security/authorization.py`
  - Invalidation: async event via outbox when role assignment changes

**Frontend Cookie Management:**
- Frontend Main:
  - HTTP-only cookies: `access_token` (15min), `refresh_token` (30 days)
  - SameSite=Lax, Secure in production
  - Auto-refresh: RTK Query baseQuery with 401 retry + single-flight mutex
  - Cookie helpers: `frontend/main/lib/auth/cookie-helpers.ts`
- Frontend Admin:
  - Same cookie pattern
  - Middleware refresh: `frontend/admin/src/proxy.js` (checks JWT exp, refreshes server-side)
  - Cookie helpers: `frontend/admin/src/lib/auth.js`

## Monitoring & Observability

**Structured Logging:**
- Framework: structlog `>=25.5.0`
- Dev mode: Colored console output with call-site info (filename, function, line number)
- Production: JSON lines to stdout (for log aggregator ingestion)
- Config: `backend/src/bootstrap/logger.py`
- Processors: contextvars merge, logger name, log level, timestamps (ISO UTC), stack info, unicode decoder
- Access logging: Custom middleware `backend/src/api/middlewares/logger.py`
- TaskIQ logging: `backend/src/infrastructure/logging/taskiq_middleware.py`
- Correlation IDs: bound via `structlog.contextvars.bind_contextvars()`

**Error Tracking:**
- No external error tracking service detected (no Sentry, Datadog, Bugsnag, etc.)

**DLQ (Dead Letter Queue):**
- Failed TaskIQ tasks persisted to `failed_tasks` PostgreSQL table
- Uses dedicated DB engine (not Dishka request-scoped session)
- Implementation: `backend/src/infrastructure/logging/dlq_middleware.py`
- Model: `backend/src/infrastructure/database/models/failed_task.py`

## CI/CD & Deployment

**Backend + Image Backend:**
- Platform: Railway
- Build: Dockerfile-based (configured in `railway.toml`)
- Backend entrypoint: `backend/scripts/entrypoint.sh`
  1. Runs `alembic upgrade head` (auto-migrate on deploy)
  2. Starts `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Image Backend: Direct CMD `uvicorn main:app --host 0.0.0.0 --port 8001`

**Frontend Main:**
- Platform: Netlify
- Build: `npm run build`
- Plugin: `@netlify/plugin-nextjs`
- Config: `frontend/main/netlify.toml`

**Frontend Admin:**
- Deployment target not explicitly configured (no netlify.toml, vercel.json, etc.)
- Standard Next.js build output (`next build --webpack`)

**CI Pipeline:**
- Not detected (no `.github/workflows/`, `.gitlab-ci.yml`, Jenkinsfile, or similar)

## Security Headers

**Frontend Admin (`frontend/admin/next.config.js`):**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy`: self + unsafe-inline/eval for scripts/styles, blob/data for images
- `Strict-Transport-Security`: max-age=63072000; includeSubDomains; preload
- `Permissions-Policy`: camera=(), microphone=(), geolocation=()
- `poweredByHeader: false` (removes X-Powered-By)

**Frontend Main (`frontend/main/middleware.ts`):**
- Edge middleware CSRF protection: Origin header validation on POST `/api/auth/*`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN` (allows Telegram iframe embedding)
- `Referrer-Policy: strict-origin-when-cross-origin`

**Image Backend:**
- API-key authentication on all endpoints (`X-API-Key` header or `api_key` query param for SSE)
- HMAC-safe key comparison (`hmac.compare_digest`)
- Auth disableable when `INTERNAL_API_KEY` is empty (dev convenience)

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot webhook (optional): `BOT_WEBHOOK_URL` + `BOT_WEBHOOK_SECRET`
- Image Backend media endpoints (API-key protected): `POST /api/v1/media/*`

**Outgoing:**
- None detected (all async processing is internal via outbox + RabbitMQ)

## Environment Configuration Summary

**Required env vars (Backend):**
- `SECRET_KEY` - JWT signing (critical, no default)
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

**Required env vars (Frontend Admin):**
- `BACKEND_URL` - Backend server URL for server-side fetch

**Secrets storage:**
- Development: `.env` files (gitignored)
- Templates: `.env.example` committed in `backend/` and `image_backend/`, `.env.local.example` in `frontend/admin/`, `.env.example` in `frontend/main/`
- Production: Railway environment variables (Python services), Netlify env vars (frontend main)

---

*Integration audit: 2026-03-28*
