<div align="center">

```
 _____ _   _ _____ _____ ____  ____  ____  ___ ____  _____      _    ____ ___
| ____| \ | |_   _| ____|  _ \|  _ \|  _ \|_ _/ ___|| ____|    / \  |  _ \_ _|
|  _| |  \| | | | |  _| | |_) | |_) | |_) || |\___ \|  _|     / _ \ | |_) | |
| |___| |\  | | | | |___|  _ <|  __/|  _ < | | ___) | |___   / ___ \|  __/| |
|_____|_| \_| |_| |_____|_| \_\_|   |_| \_\___|____/|_____| /_/   \_\_|  |___|
```

**Production-grade e-commerce loyalty platform API built with DDD, Clean Architecture, and CQRS.**

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Test Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)](tests/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff)](https://docs.astral.sh/ruff/)
[![uv](https://img.shields.io/badge/uv-package%20manager-blueviolet?logo=astral)](https://docs.astral.sh/uv/)

</div>

---

## Table of Contents

- [Elevator Pitch](#elevator-pitch)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Configuration](#%EF%B8%8F-configuration)
- [Architecture](#%EF%B8%8F-architecture)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## Elevator Pitch

Enterprise API is an async REST backend for e-commerce loyalty platforms. It implements a **modular monolith** with strict bounded contexts — nine business domains (catalog, identity, user, geo, cart, logistics, supplier, pricing, activity) live in their own modules with independent layers, communicating only through domain events.

Unlike typical FastAPI CRUD apps, this project enforces **real DDD**: domain entities have zero framework imports, repositories use the Data Mapper pattern (not Active Record), and writes flow through CQRS command handlers with a transactional outbox for reliable event publishing.

Built for teams that want production architecture from day one — not a rewrite later.

---

## ✨ Features

- **Modular Monolith** — nine isolated bounded contexts (Catalog, Identity, User, Geo, Cart, Logistics, Supplier, Pricing, Activity) with enforced architectural boundaries
- **Full CQRS** — dedicated command and query handlers; writes never mix with reads
- **Multi-Provider Authentication** — email/password (Argon2id), OIDC, and Telegram Mini App with access/refresh token rotation (max 5 sessions per identity)
- **RBAC Authorization** — hierarchical roles and permissions with Redis-cached session lookups (300s TTL), resolved via recursive CTE
- **Transactional Outbox** — domain events persist atomically with aggregates; the relay processes them in per-event transactions with `FOR UPDATE SKIP LOCKED` for concurrent workers, dispatched via TaskIQ + RabbitMQ. IAM events (identity registered/deactivated, role changes, linked account) have wired consumers; catalog/cart/pricing/logistics/supplier events are persisted for audit/future subscription
- **Presigned Uploads & Media Pipeline** — image processing extracted into a dedicated `image_backend/` microservice (server-to-server X-API-Key)
- **Catalog with Variants & Templates** — products → variants → SKUs, attribute templates with per-category bindings, EAV product attribute values, full-text search vector
- **Storefront APIs** — separate routers for product detail, listings, search + suggest, trending, and personalized "for you" feed (co-view recommendations)
- **Pricing Engine** — versioned formula AST (draft → published → archived) with pure-domain Decimal evaluator, scoped variables (global / supplier / category / range / product_input), pricing contexts with rounding modes, and preview endpoint
- **Cart with Guest Support** — cart aggregate with FSM (ACTIVE / FROZEN / MERGED / ORDERED), anonymous-token sessions for guests, and cart merge on login
- **Logistics** — Shipment aggregate with local FSM and append-only carrier tracking events, multi-provider abstraction (CDEK, Russian Post, Yandex Delivery)
- **Activity Tracking & Recommendations** — fire-and-forget Redis hot path (LPUSH + ZINCRBY pipeline) flushed to a partitioned PostgreSQL table; product co-view scores power "similar products" and "for you" feed
- **Geo Reference Data** — ISO 3166-1/2 countries and subdivisions, districts (OKTMO/FIAS for RU), ISO 4217 currencies, IETF BCP 47 languages with multi-language translations
- **Telegram Bot** — [Aiogram 3](https://docs.aiogram.dev/) bot with inline keyboards, FSM states, throttling, and user identification middleware
- **GDPR Account Deletion** — one-click account deactivation with cascading PII anonymization through domain events
- **Staff Management** — invitation workflow with token-based acceptance, role assignment, and separate PII storage
- **High Test Coverage** — unit, integration, e2e, and architecture fitness tests powered by [testcontainers](https://testcontainers-python.readthedocs.io/)
- **Structured Logging** — JSON-formatted logs via [structlog](https://www.structlog.org/) with request correlation IDs propagated through the outbox

---

## 🚀 Quick Start

Get the API running locally in under 5 minutes.

**1. Start infrastructure services:**

```bash
docker compose up -d
```

**2. Install dependencies:**

```bash
uv sync
```

**3. Configure environment:**

```bash
cp .env.example .env
```

**4. Run database migrations:**

```bash
uv run alembic upgrade head
```

uv run python -m seed.main                         # all steps (server must be running)
uv run python -m seed.main --step roles,admin,geo  # DB-only (no server needed)
uv run python -m seed.main --step brands,products  # API-only

**5. Start the API server:**

```bash
uv run uvicorn src.bootstrap.web:create_app --factory --reload --host 0.0.0.0 --port 8080
```

**6. Open the interactive docs:**

Visit [http://localhost:8080/docs](http://localhost:8080/docs) — register a user, grab a token, and start calling endpoints.

**7. Verify it works:**

```bash
curl http://localhost:8080/health
# {"status":"ok","environment":"dev"}
```

---

## 📦 Installation

### Prerequisites

| Dependency                                                    | Version | Purpose                 |
| ------------------------------------------------------------- | ------- | ----------------------- |
| [Python](https://www.python.org/downloads/)                   | 3.14+   | Runtime                 |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest  | Package manager         |
| [Docker](https://docs.docker.com/get-docker/)                 | 24.0+   | Infrastructure services |

### From Source

```bash
# Clone the repository
git clone https://github.com/sanjar-x/loyality.git
cd loyality/backend

# Install all dependencies (including dev tools)
uv sync

# Copy environment config
cp .env.example .env

# Start PostgreSQL, Redis, RabbitMQ, MinIO
docker compose up -d

# Apply database migrations
uv run alembic upgrade head
```

### Docker (Production)

```bash
docker build -f deploy/docker/Dockerfile -t loyality-api .
docker run --env-file .env -p 8080:8080 loyality-api
```

### Common Issues

| Problem                     | Fix                                                                    |
| --------------------------- | ---------------------------------------------------------------------- |
| `asyncpg` fails to install  | Install system-level `libpq-dev` (Debian) or `postgresql-devel` (RHEL) |
| `argon2-cffi` build error   | Install `libffi-dev` and `build-essential`                             |
| Docker services not healthy | Run `docker compose ps` — wait for all health checks to pass           |
| `alembic upgrade` hangs     | Check that PostgreSQL is accepting connections on port 5432            |

---

## 📖 Usage

### Register and Authenticate

```bash
# Register a new identity
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123!"}'
```

```json
{ "identityId": "550e8400-e29b-41d4-a716-446655440000" }
```

```bash
# Login to get tokens
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123!"}'
```

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "dGhpcyBpcyBhIHJlZnJl..."
}
```

### Create a Brand (Protected Endpoint)

The logo is uploaded via `image_backend/` first; backend only stores the resolved URL and storage object id.

```bash
curl -X POST http://localhost:8080/api/v1/catalog/brands \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nike",
    "slug": "nike",
    "logoUrl": "https://cdn.example.com/brands/nike.webp",
    "logoStorageObjectId": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  }'
```

```json
{
  "brandId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Build a Category Tree

```bash
# Create root category
curl -X POST http://localhost:8080/api/v1/catalog/categories \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Footwear", "slug": "footwear"}'

# Create child category
curl -X POST http://localhost:8080/api/v1/catalog/categories \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Sneakers", "slug": "sneakers", "parentId": "<footwear_id>"}'

# Fetch the full tree
curl http://localhost:8080/api/v1/catalog/categories/tree
```

```json
[
  {
    "id": "...",
    "name": "Footwear",
    "slug": "footwear",
    "fullSlug": "footwear",
    "level": 0,
    "sortOrder": 0,
    "children": [
      {
        "id": "...",
        "name": "Sneakers",
        "slug": "sneakers",
        "fullSlug": "footwear/sneakers",
        "level": 1,
        "sortOrder": 0,
        "children": []
      }
    ]
  }
]
```

### Start the Background Worker

The worker processes domain events (logo processing, RBAC cache invalidation, PII anonymization):

```bash
uv run taskiq worker src.bootstrap.worker:broker
```

---

## 📡 API Reference

All endpoints are served under `/api/v1`. Interactive docs available at `/docs` (dev/test only).

### Authentication

| Method | Endpoint           | Auth   | Description                         |
| ------ | ------------------ | ------ | ----------------------------------- |
| `POST` | `/auth/register`   | Public | Register with email + password      |
| `POST` | `/auth/login`      | Public | Get access/refresh token pair       |
| `POST` | `/auth/telegram`   | Public | Authenticate via Telegram init data |
| `POST` | `/auth/refresh`    | Public | Rotate refresh token                |
| `POST` | `/auth/logout`     | Bearer | Revoke current session              |
| `POST` | `/auth/logout/all` | Bearer | Revoke all sessions                 |

### Catalog — Brands

| Method   | Endpoint                  | Auth             | Description                                   |
| -------- | ------------------------- | ---------------- | --------------------------------------------- |
| `POST`   | `/catalog/brands`         | `catalog:manage` | Create brand (logo URL + storageObjectId opt) |
| `POST`   | `/catalog/brands/bulk`    | `catalog:manage` | Bulk-create brands                            |
| `GET`    | `/catalog/brands`         | Public           | List brands (paginated)                       |
| `GET`    | `/catalog/brands/{id}`    | Public           | Get brand by ID                               |
| `PATCH`  | `/catalog/brands/{id}`    | `catalog:manage` | Update brand name/slug/logo                   |
| `DELETE` | `/catalog/brands/{id}`    | `catalog:manage` | Delete brand                                  |

### Catalog — Categories

| Method   | Endpoint                   | Auth             | Description                 |
| -------- | -------------------------- | ---------------- | --------------------------- |
| `POST`   | `/catalog/categories`      | `catalog:manage` | Create category             |
| `GET`    | `/catalog/categories`      | Public           | List categories (paginated) |
| `GET`    | `/catalog/categories/tree` | Public           | Full nested category tree   |
| `GET`    | `/catalog/categories/{id}` | Public           | Get category by ID          |
| `PATCH`  | `/catalog/categories/{id}` | `catalog:manage` | Update category             |
| `DELETE` | `/catalog/categories/{id}` | `catalog:manage` | Delete category (leaf only) |

### Admin — Identity Management

| Method   | Endpoint                                 | Auth                | Description               |
| -------- | ---------------------------------------- | ------------------- | ------------------------- |
| `GET`    | `/admin/identities`                      | `identities:manage` | List all identities       |
| `GET`    | `/admin/identities/{id}`                 | `identities:manage` | Get identity detail       |
| `POST`   | `/admin/identities/{id}/deactivate`      | `identities:manage` | Deactivate identity       |
| `POST`   | `/admin/identities/{id}/reactivate`      | `identities:manage` | Reactivate identity       |
| `POST`   | `/admin/identities/{id}/roles`           | `roles:manage`      | Assign role to identity   |
| `DELETE` | `/admin/identities/{id}/roles/{role_id}` | `roles:manage`      | Revoke role from identity |

### Admin — Roles & Permissions

| Method   | Endpoint                        | Auth           | Description                         |
| -------- | ------------------------------- | -------------- | ----------------------------------- |
| `GET`    | `/admin/roles`                  | `roles:manage` | List roles with permissions         |
| `POST`   | `/admin/roles`                  | `roles:manage` | Create custom role                  |
| `GET`    | `/admin/roles/{id}`             | `roles:manage` | Get role detail with permissions    |
| `PATCH`  | `/admin/roles/{id}`             | `roles:manage` | Update role name/description        |
| `DELETE` | `/admin/roles/{id}`             | `roles:manage` | Delete custom role                  |
| `PUT`    | `/admin/roles/{id}/permissions` | `roles:manage` | Set role permissions (full replace) |
| `GET`    | `/admin/permissions`            | `roles:manage` | List all permissions (grouped)      |

### Admin — Staff

| Method   | Endpoint                        | Auth           | Description              |
| -------- | ------------------------------- | -------------- | ------------------------ |
| `GET`    | `/admin/staff`                  | `staff:manage` | List staff members       |
| `GET`    | `/admin/staff/{id}`             | `staff:manage` | Get staff member detail  |
| `POST`   | `/admin/staff/{id}/deactivate`  | `staff:manage` | Deactivate staff member  |
| `POST`   | `/admin/staff/{id}/reactivate`  | `staff:manage` | Reactivate staff member  |
| `GET`    | `/admin/staff/invitations`      | `staff:manage` | List pending invitations |
| `POST`   | `/admin/staff/invitations`      | `staff:invite` | Invite staff member      |
| `DELETE` | `/admin/staff/invitations/{id}` | `staff:manage` | Revoke invitation        |

### Admin — Customers

| Method | Endpoint                           | Auth               | Description         |
| ------ | ---------------------------------- | ------------------ | ------------------- |
| `GET`  | `/admin/customers`                 | `customers:read`   | List customers      |
| `GET`  | `/admin/customers/{id}`            | `customers:read`   | Get customer detail |
| `POST` | `/admin/customers/{id}/deactivate` | `customers:manage` | Deactivate customer |
| `POST` | `/admin/customers/{id}/reactivate` | `customers:manage` | Reactivate customer |

### Profile & Account

| Method   | Endpoint               | Auth             | Description             |
| -------- | ---------------------- | ---------------- | ----------------------- |
| `GET`    | `/profile/me`          | `profile:read`   | Get my profile          |
| `PATCH`  | `/profile/me`          | `profile:update` | Update my profile       |
| `DELETE` | `/profile/me`          | `profile:delete` | Delete account (GDPR)   |
| `PUT`    | `/profile/me/password` | Bearer           | Change password         |
| `GET`    | `/profile/me/sessions` | Bearer           | List my active sessions |

### Invitations

| Method | Endpoint                        | Auth   | Description             |
| ------ | ------------------------------- | ------ | ----------------------- |
| `GET`  | `/invitations/{token}/validate` | Public | Validate invitation     |
| `POST` | `/invitations/{token}/accept`   | Public | Accept staff invitation |

### Geo

| Method | Endpoint                             | Auth   | Description                      |
| ------ | ------------------------------------ | ------ | -------------------------------- |
| `GET`  | `/geo/countries`                     | Public | List countries with translations |
| `GET`  | `/geo/countries/{code}/subdivisions` | Public | List subdivisions of a country   |
| `GET`  | `/geo/countries/{code}/currencies`   | Public | List currencies of a country     |
| `GET`  | `/geo/currencies`                    | Public | List all currencies              |
| `GET`  | `/geo/languages`                     | Public | List supported languages         |

### Catalog — Storefront (Public)

| Method | Endpoint                                    | Auth   | Description                                |
| ------ | ------------------------------------------- | ------ | ------------------------------------------ |
| `GET`  | `/catalog/storefront/products`              | Public | List products (filters, paginated)         |
| `GET`  | `/catalog/storefront/products/{slug}`       | Public | Product detail page (PDP) by slug          |
| `GET`  | `/catalog/storefront/search`                | Public | Full-text product search                   |
| `GET`  | `/catalog/storefront/search/suggest`        | Public | Search autocomplete                        |
| `GET`  | `/catalog/storefront/trending`              | Public | Trending products (Redis sorted sets)      |
| `GET`  | `/catalog/storefront/for-you`               | Public | Personalized feed (co-view recommendations)|

### Cart

| Method   | Endpoint                  | Auth          | Description                              |
| -------- | ------------------------- | ------------- | ---------------------------------------- |
| `GET`    | `/cart`                   | Bearer/Guest  | Get current cart (resolves by token)     |
| `POST`   | `/cart/items`             | Bearer/Guest  | Add SKU to cart                          |
| `PATCH`  | `/cart/items/{itemId}`    | Bearer/Guest  | Update quantity                          |
| `DELETE` | `/cart/items/{itemId}`    | Bearer/Guest  | Remove item                              |
| `POST`   | `/cart/clear`             | Bearer/Guest  | Clear all items                          |
| `POST`   | `/cart/freeze`            | Bearer        | Freeze cart for checkout                 |

### Pricing (Admin)

| Method  | Endpoint                                 | Auth             | Description                                    |
| ------- | ---------------------------------------- | ---------------- | ---------------------------------------------- |
| `*`     | `/pricing/variables`                     | `pricing:manage` | CRUD pricing variables                         |
| `*`     | `/pricing/contexts`                      | `pricing:manage` | Manage pricing contexts (currency, rounding)   |
| `*`     | `/pricing/contexts/{id}/values`          | `pricing:manage` | Set global variable values per context         |
| `*`     | `/pricing/contexts/{id}/formula`         | `pricing:manage` | Draft/publish/rollback formula versions        |
| `POST`  | `/pricing/preview`                       | `pricing:manage` | Preview computed price for a product           |
| `*`     | `/pricing/profiles`                      | `pricing:manage` | Per-product input variable values              |
| `*`     | `/pricing/category-settings`             | `pricing:manage` | Category-scoped variable values                |
| `*`     | `/pricing/supplier-settings`             | `pricing:manage` | Supplier-scoped variable values                |
| `*`     | `/pricing/supplier-type-mappings`        | `pricing:manage` | Supplier-type → context mappings               |

### Logistics

| Method | Endpoint                              | Auth                | Description                            |
| ------ | ------------------------------------- | ------------------- | -------------------------------------- |
| `POST` | `/logistics/quotes`                   | Bearer              | Get delivery quotes from carriers      |
| `POST` | `/logistics/shipments`                | `logistics:manage`  | Create shipment from selected quote    |
| `GET`  | `/logistics/shipments/{id}`           | `logistics:manage`  | Get shipment with tracking events      |
| `POST` | `/logistics/shipments/{id}/book`      | `logistics:manage`  | Book shipment with carrier             |
| `POST` | `/logistics/shipments/{id}/cancel`    | `logistics:manage`  | Cancel shipment                        |
| `POST` | `/logistics/webhooks/{provider}`      | Webhook secret      | Carrier tracking webhook               |

### Suppliers (Admin)

| Method | Endpoint                            | Auth               | Description           |
| ------ | ----------------------------------- | ------------------ | --------------------- |
| `*`    | `/suppliers`                        | `suppliers:manage` | CRUD suppliers        |
| `POST` | `/suppliers/{id}/activate`          | `suppliers:manage` | Activate supplier     |
| `POST` | `/suppliers/{id}/deactivate`        | `suppliers:manage` | Deactivate supplier   |

### Activity (Admin)

| Method | Endpoint                          | Auth              | Description                         |
| ------ | --------------------------------- | ----------------- | ----------------------------------- |
| `GET`  | `/admin/activity/trending`        | `analytics:read`  | Trending products (daily/weekly)    |
| `GET`  | `/admin/activity/search/popular`  | `analytics:read`  | Popular search queries              |
| `GET`  | `/admin/activity/history`         | `analytics:read`  | Activity history (partitioned PG)   |

### System

| Method | Endpoint  | Description                       |
| ------ | --------- | --------------------------------- |
| `GET`  | `/health` | Health check (`{"status": "ok"}`) |

---

## ⚙️ Configuration

All settings load from environment variables or a `.env` file. Copy `.env.example` to get started:

```bash
cp .env.example .env
```

### Application

| Variable       | Type   | Default          | Description                         |
| -------------- | ------ | ---------------- | ----------------------------------- |
| `PROJECT_NAME` | `str`  | `Enterprise API` | Application display name            |
| `VERSION`      | `str`  | `1.0.0`          | Semantic version                    |
| `ENVIRONMENT`  | `str`  | `dev`            | Runtime mode: `dev`, `test`, `prod` |
| `DEBUG`        | `bool` | `False`          | Enable debug mode                   |
| `SECRET_KEY`   | `str`  | **required**     | JWT signing secret                  |
| `CORS_ORIGINS` | `str`  | `[]`             | Comma-separated allowed origins     |

### Authentication & IAM

| Variable                           | Type  | Default | Description                          |
| ---------------------------------- | ----- | ------- | ------------------------------------ |
| `ACCESS_TOKEN_EXPIRE_MINUTES`      | `int` | `15`    | Access token TTL                     |
| `REFRESH_TOKEN_EXPIRE_DAYS`        | `int` | `30`    | Refresh token TTL                    |
| `SESSION_PERMISSIONS_CACHE_TTL`    | `int` | `300`   | Redis permission cache TTL (seconds) |
| `MAX_ACTIVE_SESSIONS_PER_IDENTITY` | `int` | `5`     | Max concurrent sessions per user     |

### PostgreSQL

| Variable     | Type  | Default      | Description       |
| ------------ | ----- | ------------ | ----------------- |
| `PGHOST`     | `str` | **required** | Database host     |
| `PGPORT`     | `int` | **required** | Database port     |
| `PGUSER`     | `str` | **required** | Database user     |
| `PGPASSWORD` | `str` | **required** | Database password |
| `PGDATABASE` | `str` | **required** | Database name     |

### Redis

| Variable        | Type  | Default      | Description          |
| --------------- | ----- | ------------ | -------------------- |
| `REDISHOST`     | `str` | **required** | Redis host           |
| `REDISPORT`     | `int` | **required** | Redis port           |
| `REDISUSER`     | `str` | `default`    | Redis username       |
| `REDISPASSWORD` | `str` | `None`       | Redis password       |
| `REDISDATABASE` | `int` | `0`          | Redis database index |

### S3 / MinIO

| Variable             | Type  | Default      | Description                         |
| -------------------- | ----- | ------------ | ----------------------------------- |
| `S3_ENDPOINT_URL`    | `str` | **required** | S3-compatible endpoint              |
| `S3_ACCESS_KEY`      | `str` | **required** | Access key                          |
| `S3_SECRET_KEY`      | `str` | **required** | Secret key                          |
| `S3_REGION`          | `str` | **required** | AWS region or `us-east-1` for MinIO |
| `S3_BUCKET_NAME`     | `str` | **required** | Default bucket                      |
| `S3_PUBLIC_BASE_URL` | `str` | **required** | Public URL prefix for assets        |

### RabbitMQ

| Variable               | Type  | Default      | Description         |
| ---------------------- | ----- | ------------ | ------------------- |
| `RABBITMQ_PRIVATE_URL` | `str` | **required** | AMQP connection URL |

### Telegram Bot

| Variable                             | Type        | Default      | Description                           |
| ------------------------------------ | ----------- | ------------ | ------------------------------------- |
| `BOT_TOKEN`                          | `str`       | **required** | Bot token from @BotFather             |
| `BOT_ADMIN_IDS`                      | `list[int]` | `[]`         | Telegram IDs of bot administrators    |
| `BOT_WEBHOOK_URL`                    | `str`       | `""`         | Webhook URL for incoming updates      |
| `BOT_WEBHOOK_SECRET`                 | `str`       | `""`         | Webhook secret for request validation |
| `THROTTLE_RATE`                      | `float`     | `0.5`        | Rate limit interval (seconds)         |
| `TELEGRAM_INIT_DATA_MAX_AGE`         | `int`       | `300`        | Init data validity window (seconds)   |
| `TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS` | `int`       | `7`          | Telegram refresh token TTL (days)     |

### Session Timeouts

| Variable                                   | Type  | Default | Description                               |
| ------------------------------------------ | ----- | ------- | ----------------------------------------- |
| `SESSION_IDLE_TIMEOUT_MINUTES`             | `int` | `30`    | Idle session timeout (minutes)            |
| `SESSION_ABSOLUTE_LIFETIME_HOURS`          | `int` | `24`    | Absolute session lifetime (hours)         |
| `TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES`    | `int` | `1440`  | Telegram session idle timeout (minutes)   |
| `TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS` | `int` | `168`   | Telegram session lifetime (hours, 7 days) |

---

## 🏗️ Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI (ASGI Server)                                 │
│ ┌─────────┐ ┌─────────┐ ┌──────┐ ┌─────┐ ┌──────┐ ┌───────────┐ ┌────────┐ ┌───────┐ │
│ │ Catalog │ │ Identity│ │ User │ │ Geo │ │ Cart │ │ Logistics │ │Supplier│ │Pricing│ │
│ └────┬────┘ └────┬────┘ └──┬───┘ └──┬──┘ └──┬───┘ └─────┬─────┘ └───┬────┘ └───┬───┘ │
│      │           │         │        │       │           │           │          │     │
│      └───────────┴────┬────┴────────┴───────┴───────────┴───────────┴────────┬─┘     │
│                       │                              ┌────────────┐         │        │
│                       │                              │  Activity  │─────────┘        │
│                       │                              └─────┬──────┘                  │
│   ┌───────────────────┴────────────────────────────────────┴─────────────────────┐   │
│   │                       Shared Infrastructure Layer                            │   │
│   │           PostgreSQL  ·  Redis  ·  RabbitMQ  ·  S3/MinIO                     │   │
│   └──────────────────────────────────────────────────────────────────────────────┘   │
│   ┌──────────────────────────────────────────────────────────────────────────────┐   │
│   │                          Telegram Bot (Aiogram 3)                            │   │
│   └──────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                            ▲
                                            │ X-API-Key (delete only)
                                            ▼
                        ┌───────────────────────────────────────────┐
                        │  image_backend/  (FastAPI + Pillow + S3)  │
                        └───────────────────────────────────────────┘
```

### Module Internal Structure (Clean Architecture)

```
Each bounded context follows this layering:

    ┌──────────────────────────────┐
    │      Presentation Layer      │  ← Pydantic schemas, FastAPI routers
    ├──────────────────────────────┤
    │      Application Layer       │  ← Command/Query handlers, services
    ├──────────────────────────────┤
    │        Domain Layer          │  ← Entities, value objects, events, interfaces
    ├──────────────────────────────┤
    │     Infrastructure Layer     │  ← ORM models, repository impls, providers
    └──────────────────────────────┘

    Dependencies flow INWARD: Presentation → Application → Domain ← Infrastructure
```

### Key Architecture Decisions

| Pattern                  | Implementation                                                             | Why                                      |
| ------------------------ | -------------------------------------------------------------------------- | ---------------------------------------- |
| **Data Mapper**          | Repositories convert between `attrs` entities and SQLAlchemy ORM models    | Domain stays framework-free              |
| **CQRS**                 | Separate command handlers (write) and query handlers (read)                | Optimize reads independently from writes |
| **Transactional Outbox** | Domain events persist in `outbox_messages` table, relayed by TaskIQ worker | Guarantee at-least-once event delivery   |
| **Dishka DI**            | Constructor injection with `APP`, `REQUEST` scopes                         | Explicit dependency graphs               |
| **Unit of Work**         | All mutations go through `IUnitOfWork.commit()`                            | Atomic multi-aggregate transactions      |
| **Event-Driven**         | Modules communicate via domain events through the outbox                   | Zero direct cross-module imports         |
| **NIST RBAC**            | Hierarchical roles → permissions, cached in Redis with CTE fallback        | Fine-grained access control              |
| **Dead Letter Queue**    | Failed tasks persisted in `failed_tasks` table via DLQ middleware          | No silent task failures                  |

### Data Flow: Media Upload (3-step)

Image processing lives in the separate `image_backend/` microservice. The main backend only references media through `storage_object_id`.

```
Client                BFF Proxy             image_backend          S3
  │                    │                        │                   │
  ├─ POST /media/upload ───────────────────────►│                   │
  │                    │  X-API-Key             ├── reserve slot ──►│
  │◄────── presignedUrl + storageObjectId ──────┤                   │
  │                                                                 │
  ├─ PUT presignedUrl ─────────────────────────────────────────────►│
  │                                                                 │
  ├─ POST /media/{id}/confirm ─────────────────►│                   │
  │                                             ├─ enqueue task     │
  │◄─────── 202 Accepted ───────────────────────┤                   │
  │                                             │                   │
  │                                  ┌─ Worker ─┤                   │
  │                                  │          ├─ verify object ─► │
  │                                  │          ├─ Pillow resize    │
  │                                  │          ├─ upload variants ►│
  │                                  │          │  (thumb/med/large)│
  │                                  │          │                   │
  ├─ GET /media/{id}/status (SSE) ──►│          │                   │
  │◄────── COMPLETED ────────────────┘          │                   │
  │                                                                 │
  ├─ Backend stores storage_object_id with the entity (brand, product media)
```

### Project Structure

```
src/
├── api/                          # HTTP layer — routers, middleware, exceptions
│   ├── dependencies/             # Auth dependency (JWT extraction)
│   ├── exceptions/               # Centralized error handlers
│   └── middlewares/              # Access logging middleware
│
├── bootstrap/                    # Composition root
│   ├── config.py                 # Pydantic Settings (env vars)
│   ├── container.py              # Dishka DI container assembly
│   ├── web.py                    # FastAPI app factory + lifespan
│   ├── worker.py                 # TaskIQ worker entrypoint
│   ├── bot.py                    # Telegram bot initialization
│   ├── scheduler.py              # Periodic task scheduler
│   └── logger.py                 # structlog configuration
│
├── bot/                          # Telegram bot (Aiogram 3)
│   ├── factory.py                # Bot/Dispatcher factory
│   ├── handlers/                 # /start, /help, navigation, errors
│   ├── keyboards/                # Inline + reply keyboards
│   ├── middlewares/              # Logging, throttling, user identification
│   ├── filters/                  # Admin check filter
│   ├── callbacks/                # Callback query handlers
│   └── states/                   # FSM states
│
├── infrastructure/               # Cross-cutting concerns
│   ├── cache/                    # Redis client + provider
│   ├── database/                 # SQLAlchemy engine, session, UoW, outbox/DLQ models
│   ├── logging/                  # Structlog adapter, TaskIQ + DLQ middleware
│   ├── outbox/                   # Event outbox relay (FOR UPDATE SKIP LOCKED)
│   ├── security/                 # JWT, Argon2id passwords, RBAC resolver, Telegram auth
│   └── storage/                  # S3/MinIO client factory
│
├── modules/
│   ├── catalog/                  # Brands, categories, products, variants, SKUs, attributes, templates, media
│   ├── identity/                 # Auth (LOCAL/OIDC/Telegram), sessions, roles, permissions, invitations
│   ├── user/                     # Customer + StaffMember profiles (PII storage)
│   ├── geo/                      # Countries, subdivisions, districts, currencies, languages
│   ├── cart/                     # Cart aggregate, items, checkout snapshots (FSM)
│   ├── logistics/                # Shipments, tracking events, carrier providers
│   ├── supplier/                 # Suppliers (cross-border / local)
│   ├── pricing/                  # Variables, formula AST, contexts, profiles, settings
│   └── activity/                 # User activity tracking, trending, co-view recommendations
│
└── shared/                       # Cross-module interfaces + base classes
    ├── exceptions.py             # Base AppException hierarchy
    ├── schemas.py                # CamelModel (auto camelCase aliases)
    ├── pagination.py             # Pagination primitives
    └── interfaces/               # IUnitOfWork, IBlobStorage, ITokenProvider, ILogger, ...
```

---

## 🧪 Testing

### Run Tests

```bash
# All unit + architecture tests (fast, no containers needed)
uv run pytest tests/unit/ tests/architecture/ -v

# Integration tests (requires running Docker services)
uv run pytest tests/integration/ -v

# End-to-end API tests
uv run pytest tests/e2e/ -v

# Everything with coverage report
uv run pytest tests/ --cov=src --cov-report=html
```

### Test Categories

| Marker         | Scope                      | Speed    | Dependencies   |
| -------------- | -------------------------- | -------- | -------------- |
| `unit`         | Domain + application logic | ~6s      | None           |
| `architecture` | Boundary enforcement       | ~1s      | None           |
| `integration`  | Real DB + services         | ~30s     | testcontainers |
| `e2e`          | Full HTTP round-trips      | ~15s     | testcontainers |
| `load`         | Stress testing (Locust)    | variable | Running server |

### Architecture Fitness Tests

These tests **enforce Clean Architecture boundaries** at CI time across all nine modules:

- Domain layer has zero infrastructure or framework imports (attrs + stdlib only)
- Application commands MUST NOT import infrastructure (queries and consumers exempt — CQRS read-side; `geo.commands` exempt — reference-data)
- No direct cross-module imports — modules communicate via domain events through the outbox
- Whitelisted exceptions: presentation→identity for auth/permission deps; `cart.infrastructure.adapters.catalog_adapter` (anti-corruption); `identity.management.*` (admin CLI)
- Shared kernel (`src/shared/`) MUST NOT import any business module

```bash
uv run pytest tests/architecture/ -v
```

---

## 🤝 Contributing

### Development Setup

```bash
# Clone and install
git clone https://github.com/sanjar-x/loyality.git
cd loyality/backend
uv sync

# Start infrastructure
docker compose up -d

# Copy env and run migrations
cp .env.example .env
uv run alembic upgrade head

# Verify everything works
uv run pytest tests/unit/ tests/architecture/ -v
```

### Before Submitting a PR

```bash
# Lint and format
uv run ruff check --fix .
uv run ruff format .

# Type check
uv run mypy .

# Run all tests
uv run pytest tests/unit/ tests/architecture/ -v
```

### Code Style

- **Ruff** for linting and formatting (line length: 100, target: Python 3.14)
- **mypy** strict mode with Pydantic plugin
- **Google-style docstrings** on all public modules, classes, and functions
- Follow the layer order: domain first, then application, infrastructure, presentation

### Creating Database Migrations

```bash
uv run alembic revision --autogenerate -m "add_new_table"
uv run alembic upgrade head
```

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

### Built With

- [FastAPI](https://fastapi.tiangolo.com) — async web framework
- [SQLAlchemy 2.x](https://www.sqlalchemy.org) — async ORM with Data Mapper
- [Dishka](https://dishka.readthedocs.io) — dependency injection container
- [TaskIQ](https://taskiq-python.github.io) — distributed task queue
- [Aiogram 3](https://docs.aiogram.dev) — Telegram bot framework
- [structlog](https://www.structlog.org) — structured logging
- [Pydantic](https://docs.pydantic.dev) — data validation and settings
- [Alembic](https://alembic.sqlalchemy.org) — database migrations
- [pwdlib](https://pypi.org/project/pwdlib/) — Argon2id + bcrypt password hashing
- [uv](https://docs.astral.sh/uv) — Python package manager
