
<div align="center">

```
 _____ _   _ _____ _____ ____  ____  ____  ___ ____  _____      _    ____ ___
| ____| \ | |_   _| ____|  _ \|  _ \|  _ \|_ _/ ___|| ____|    / \  |  _ \_ _|
|  _| |  \| | | | |  _| | |_) | |_) | |_) || |\___ \|  _|     / _ \ | |_) | |
| |___| |\  | | | | |___|  _ <|  __/|  _ < | | ___) | |___   / ___ \|  __/| |
|_____|_| \_| |_| |_____|_| \_\_|   |_| \_\___|____/|_____| /_/   \_\_|  |___|
```

**Production-grade e-commerce API built with DDD, Clean Architecture, and CQRS.**

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

Enterprise API is an async REST backend for e-commerce platforms. It implements a **modular monolith** with strict bounded contexts — each business domain (catalog, identity, users, storage) lives in its own module with independent layers, communicating only through domain events.

Unlike typical FastAPI CRUD apps, this project enforces **real DDD**: domain entities have zero framework imports, repositories use the Data Mapper pattern (not Active Record), and writes flow through CQRS command handlers with a transactional outbox for reliable event publishing.

Built for teams that want production architecture from day one — not a rewrite later.

---

## ✨ Features

- **Modular Monolith** — four isolated bounded contexts (Catalog, Identity, User, Storage) with enforced architectural boundaries
- **Full CQRS** — dedicated command and query handlers; writes never mix with reads
- **JWT Authentication** — access/refresh token rotation, multi-session management, max 5 sessions per identity
- **RBAC Authorization** — hierarchical roles and permissions with Redis-cached session lookups (300s TTL)
- **Transactional Outbox** — domain events persist atomically with aggregates, then relay asynchronously via [TaskIQ](https://taskiq-python.github.io/) + RabbitMQ
- **Presigned Uploads** — S3-compatible (MinIO) presigned URLs for brand logos with async image processing pipeline
- **Category Trees** — hierarchical categories with `full_slug` propagation, sibling ordering, and bulk subtree renames
- **GDPR Account Deletion** — one-click account deactivation with cascading PII anonymization through domain events
- **88% Test Coverage** — unit, integration, e2e, and architecture fitness tests powered by [testcontainers](https://testcontainers-python.readthedocs.io/)
- **Structured Logging** — JSON-formatted logs via [structlog](https://www.structlog.org/) with request correlation IDs

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

**5. Start the API server:**

```bash
uv run uvicorn src.bootstrap.web:create_app --factory --reload --host 0.0.0.0 --port 8000
```

**6. Open the interactive docs:**

Visit [http://localhost:8000/docs](http://localhost:8000/docs) — register a user, grab a token, and start calling endpoints.

**7. Verify it works:**

```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"dev"}
```

---

## 📦 Installation

### Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| [Python](https://www.python.org/downloads/) | 3.14+ | Runtime |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Package manager |
| [Docker](https://docs.docker.com/get-docker/) | 24.0+ | Infrastructure services |

### From Source

```bash
# Clone the repository
git clone https://github.com/your-org/enterprise-api.git
cd enterprise-api

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
docker build -f deploy/docker/Dockerfile -t enterprise-api .
docker run --env-file .env -p 8000:8000 enterprise-api
```

### Common Issues

| Problem | Fix |
|---|---|
| `asyncpg` fails to install | Install system-level `libpq-dev` (Debian) or `postgresql-devel` (RHEL) |
| `argon2-cffi` build error | Install `libffi-dev` and `build-essential` |
| Docker services not healthy | Run `docker compose ps` — wait for all health checks to pass |
| `alembic upgrade` hangs | Check that PostgreSQL is accepting connections on port 5432 |

---

## 📖 Usage

### Register and Authenticate

```bash
# Register a new identity
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123!"}'
```

```json
{"identityId": "550e8400-e29b-41d4-a716-446655440000"}
```

```bash
# Login to get tokens
curl -X POST http://localhost:8000/api/v1/auth/login \
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

```bash
curl -X POST http://localhost:8000/api/v1/catalog/brands \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nike",
    "slug": "nike",
    "logo": {
      "filename": "nike-logo.png",
      "contentType": "image/png",
      "size": 24576
    }
  }'
```

```json
{
  "brandId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "presignedUploadUrl": "http://localhost:9000/enterprise-bucket/...",
  "objectKey": "brands/7c9e6679.../logo.png"
}
```

### Build a Category Tree

```bash
# Create root category
curl -X POST http://localhost:8000/api/v1/catalog/categories \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Footwear", "slug": "footwear"}'

# Create child category
curl -X POST http://localhost:8000/api/v1/catalog/categories \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Sneakers", "slug": "sneakers", "parentId": "<footwear_id>"}'

# Fetch the full tree
curl http://localhost:8000/api/v1/catalog/categories/tree
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

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register with email + password |
| `POST` | `/auth/login` | Public | Get access/refresh token pair |
| `POST` | `/auth/refresh` | Public | Rotate refresh token |
| `POST` | `/auth/logout` | Bearer | Revoke current session |
| `POST` | `/auth/logout/all` | Bearer | Revoke all sessions |

### Catalog — Brands

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/catalog/brands` | `catalog:manage` | Create brand (with optional logo upload) |
| `GET` | `/catalog/brands` | Public | List brands (paginated) |
| `GET` | `/catalog/brands/{id}` | Public | Get brand by ID |
| `PATCH` | `/catalog/brands/{id}` | `catalog:manage` | Update brand name/slug |
| `DELETE` | `/catalog/brands/{id}` | `catalog:manage` | Delete brand |
| `POST` | `/catalog/brands/{id}/logo/confirm` | `catalog:manage` | Confirm logo upload for processing |

### Catalog — Categories

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/catalog/categories` | `catalog:manage` | Create category |
| `GET` | `/catalog/categories` | Public | List categories (paginated) |
| `GET` | `/catalog/categories/tree` | Public | Full nested category tree |
| `GET` | `/catalog/categories/{id}` | Public | Get category by ID |
| `PATCH` | `/catalog/categories/{id}` | `catalog:manage` | Update category |
| `DELETE` | `/catalog/categories/{id}` | `catalog:manage` | Delete category (leaf only) |

### Admin — IAM

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/roles` | `roles:manage` | List roles with permissions |
| `POST` | `/admin/roles` | `roles:manage` | Create custom role |
| `DELETE` | `/admin/roles/{id}` | `roles:manage` | Delete custom role |
| `GET` | `/admin/permissions` | `roles:manage` | List all permissions |
| `POST` | `/admin/identities/{id}/roles` | `roles:manage` | Assign role to identity |
| `DELETE` | `/admin/identities/{id}/roles/{role_id}` | `roles:manage` | Revoke role |

### User Profile

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/users/me` | `users:read` | Get my profile |
| `PATCH` | `/users/me` | `users:update` | Update my profile |
| `DELETE` | `/users/me` | `users:delete` | Delete account (GDPR) |
| `GET` | `/users/me/sessions` | Bearer | List my active sessions |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check (`{"status": "ok"}`) |

---

## ⚙️ Configuration

All settings load from environment variables or a `.env` file. Copy `.env.example` to get started:

```bash
cp .env.example .env
```

### Application

| Variable | Type | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | `str` | `Enterprise API` | Application display name |
| `VERSION` | `str` | `1.0.0` | Semantic version |
| `ENVIRONMENT` | `str` | `dev` | Runtime mode: `dev`, `test`, `prod` |
| `DEBUG` | `bool` | `False` | Enable debug mode |
| `SECRET_KEY` | `str` | **required** | JWT signing secret |
| `CORS_ORIGINS` | `str` | `[]` | Comma-separated allowed origins |

### Authentication & IAM

| Variable | Type | Default | Description |
|---|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `30` | Refresh token TTL |
| `SESSION_PERMISSIONS_CACHE_TTL` | `int` | `300` | Redis permission cache TTL (seconds) |
| `MAX_ACTIVE_SESSIONS_PER_IDENTITY` | `int` | `5` | Max concurrent sessions per user |

### PostgreSQL

| Variable | Type | Default | Description |
|---|---|---|---|
| `PGHOST` | `str` | **required** | Database host |
| `PGPORT` | `int` | **required** | Database port |
| `PGUSER` | `str` | **required** | Database user |
| `PGPASSWORD` | `str` | **required** | Database password |
| `PGDATABASE` | `str` | **required** | Database name |

### Redis

| Variable | Type | Default | Description |
|---|---|---|---|
| `REDISHOST` | `str` | **required** | Redis host |
| `REDISPORT` | `int` | **required** | Redis port |
| `REDISUSER` | `str` | `default` | Redis username |
| `REDISPASSWORD` | `str` | `None` | Redis password |
| `REDISDATABASE` | `int` | `0` | Redis database index |

### S3 / MinIO

| Variable | Type | Default | Description |
|---|---|---|---|
| `S3_ENDPOINT_URL` | `str` | **required** | S3-compatible endpoint |
| `S3_ACCESS_KEY` | `str` | **required** | Access key |
| `S3_SECRET_KEY` | `str` | **required** | Secret key |
| `S3_REGION` | `str` | **required** | AWS region or `us-east-1` for MinIO |
| `S3_BUCKET_NAME` | `str` | **required** | Default bucket |
| `S3_PUBLIC_BASE_URL` | `str` | **required** | Public URL prefix for assets |

### RabbitMQ

| Variable | Type | Default | Description |
|---|---|---|---|
| `RABBITMQ_URL` | `str` | **required** | AMQP connection URL |

---

## 🏗️ Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI (ASGI Server)                        │
│                                                                     │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│   │  Catalog   │  │ Identity  │  │   User    │  │  Storage  │      │
│   │  Module    │  │  Module   │  │  Module   │  │  Module   │      │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘      │
│         │               │               │               │           │
│   ┌─────┴───────────────┴───────────────┴───────────────┴─────┐    │
│   │              Shared Infrastructure Layer                   │    │
│   │   PostgreSQL  ·  Redis  ·  RabbitMQ  ·  S3/MinIO          │    │
│   └───────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
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

| Pattern | Implementation | Why |
|---|---|---|
| **Data Mapper** | Repositories convert between `attrs` entities and SQLAlchemy ORM models | Domain stays framework-free |
| **CQRS** | Separate command handlers (write) and query handlers (read) | Optimize reads independently from writes |
| **Transactional Outbox** | Domain events persist in `outbox_messages` table, relayed by TaskIQ worker | Guarantee at-least-once event delivery |
| **Dishka DI** | Constructor injection with `APP`, `REQUEST`, `TRANSIENT` scopes | Explicit dependency graphs, no service locators |
| **Unit of Work** | All mutations go through `IUnitOfWork.commit()` | Atomic multi-aggregate transactions |
| **Event-Driven** | Modules communicate via domain events through the outbox | Zero direct cross-module imports |

### Data Flow: Brand Logo Upload

```
Client                API                  Worker              S3
  │                    │                    │                   │
  ├─ POST /brands ────►│                    │                   │
  │                    ├─ Create brand ─────┤                   │
  │                    ├─ Generate presigned URL ──────────────►│
  │◄── presignedUrl ──┤                    │                   │
  │                    │                    │                   │
  ├─ PUT presignedUrl ──────────────────────────────────────────►│
  │                    │                    │                   │
  ├─ POST /confirm ───►│                    │                   │
  │                    ├─ Outbox: BrandLogoConfirmedEvent        │
  │◄── 202 Accepted ──┤                    │                   │
  │                    │                    │                   │
  │                    │  ┌── Relay ───────►│                   │
  │                    │  │                 ├─ Verify object ──►│
  │                    │  │                 ├─ Process image    │
  │                    │  │                 ├─ Update brand     │
  │                    │  │                 │  status=COMPLETED │
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
│   └── logger.py                 # structlog configuration
│
├── infrastructure/               # Cross-cutting concerns
│   ├── cache/                    # Redis client + provider
│   ├── database/                 # SQLAlchemy engine, session, UoW, models
│   ├── logging/                  # DLQ middleware for failed tasks
│   ├── outbox/                   # Event outbox relay + scheduled tasks
│   ├── security/                 # JWT, password hashing, RBAC
│   └── storage/                  # S3/MinIO client factory
│
├── modules/
│   ├── catalog/                  # Brands, categories, products
│   ├── identity/                 # Auth, sessions, roles, permissions
│   ├── user/                     # User profiles
│   └── storage/                  # File management, media processing
│
└── shared/                       # Cross-module interfaces + base classes
    ├── exceptions.py             # Base AppException hierarchy
    ├── schemas.py                # CamelModel (auto camelCase aliases)
    └── interfaces/               # IUnitOfWork, IBlobStorage, ITokenProvider
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

| Marker | Scope | Speed | Dependencies |
|---|---|---|---|
| `unit` | Domain + application logic | ~6s | None |
| `architecture` | Boundary enforcement | ~1s | None |
| `integration` | Real DB + services | ~30s | testcontainers |
| `e2e` | Full HTTP round-trips | ~15s | testcontainers |
| `load` | Stress testing (Locust) | variable | Running server |

### Architecture Fitness Tests

These tests **enforce Clean Architecture boundaries** at CI time:

- Domain layer has zero infrastructure imports
- Application layer imports only from domain
- No direct cross-module imports (modules communicate via events)
- ORM models never appear in domain or application layers

```bash
uv run pytest tests/architecture/ -v
```

---

## 🤝 Contributing

### Development Setup

```bash
# Clone and install
git clone https://github.com/your-org/enterprise-api.git
cd enterprise-api
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
- [SQLAlchemy 2.1](https://www.sqlalchemy.org) — async ORM with Data Mapper
- [Dishka](https://dishka.readthedocs.io) — dependency injection container
- [TaskIQ](https://taskiq-python.github.io) — distributed task queue
- [structlog](https://www.structlog.org) — structured logging
- [Pydantic](https://docs.pydantic.dev) — data validation and settings
- [Alembic](https://alembic.sqlalchemy.org) — database migrations
- [uv](https://docs.astral.sh/uv) — Python package manager
