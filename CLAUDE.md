# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

E-commerce — async REST API built with FastAPI, following DDD / Clean Architecture / CQRS / Modular Monolith patterns. Python 3.14+, managed with `uv`.

## Commands

```bash
# Run dev server
uv run uvicorn main:app --reload

# Start infrastructure (PostgreSQL 18, Redis 8, RabbitMQ 4.2, MinIO)
docker compose up -d

# Run all tests (always use uv, never bare pytest)
uv run pytest tests/ -v

# Run by layer
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run pytest tests/e2e/ -v
uv run pytest tests/architecture/ -v

# Single test file / test function
uv run pytest tests/unit/test_brand.py -v
uv run pytest tests/unit/test_brand.py::test_create_brand -v

# Lint & format
uv run ruff check .
uv run ruff check --fix . && uv run ruff format .

# Type check
uv run mypy .

# Coverage
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Alembic migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

## Architecture

### Module Structure (Modular Monolith)

Each module in `src/modules/` is an independent bounded context with four layers:

```
src/modules/<module>/
├── domain/          # Entities, value objects, domain exceptions, repository interfaces (Protocols)
├── application/     # Commands and queries (CQRS handlers), services, TaskIQ tasks
├── infrastructure/  # SQLAlchemy ORM models, repository implementations (Data Mapper pattern)
└── presentation/    # FastAPI routers, Pydantic schemas, DI dependencies
```

**Active modules:** `catalog` (brands, categories, products), `storage` (file management via S3/MinIO), `order` (stub).

### Dependency Flow (Clean Architecture)

`presentation → application → domain ← infrastructure`

Domain layer has zero framework imports. Infrastructure implements domain interfaces. Never import from infrastructure into domain or application.

### Cross-Cutting Infrastructure (`src/infrastructure/`)

- `database/` — AsyncSession factory, UnitOfWork (`IUnitOfWork` Protocol: commit/rollback/flush), DeclarativeBase, Dishka provider
- `cache/` — RedisService (set/get/delete with TTL), cache-aside pattern (category tree: TTL 300s)
- `security/` — JWT tokens, bcrypt password hashing, permissions
- `storage/` — S3 client factory (aiobotocore)

### Key Patterns

- **DI:** Dishka IoC container. Providers registered in `src/bootstrap/container.py`. Use `@inject` + `FromDishka` type hints.
- **Unit of Work:** All write operations go through `IUnitOfWork` async context manager.
- **Data Mapper:** Repositories map between ORM models and domain entities. ORM never leaks into domain.
- **StorageFacade:** Cross-module file operations go through `src/modules/storage/presentation/facade.py`, not direct repository access.
- **Task Queue:** TaskIQ + RabbitMQ (aio-pika). Worker entry point: `src/bootstrap/worker.py`. Init order matters: container → tasks.
- **FSM:** `MediaProcessingStatus` enum governs logo upload lifecycle (PENDING_UPLOAD → PROCESSING → COMPLETED/FAILED).
- **Pessimistic Locking:** `SELECT FOR UPDATE` via `get_for_update()` for concurrent-safe state transitions.

### Bootstrap (`src/bootstrap/`)

- `config.py` — Pydantic `Settings` (DB, Redis, S3, JWT, CORS)
- `container.py` — Dishka container setup
- `web.py` — FastAPI app factory (lifespan, middleware, routers)
- `broker.py` — TaskIQ AioPikaBroker
- `logger.py` — Structlog JSON config

### Testing

- Tests use **testcontainers** for real PostgreSQL, Redis, MinIO, and RabbitMQ
- `pytest-asyncio` with `asyncio_mode = auto` and session-scoped event loop
- Test factories in `tests/factories/`
- Architecture boundary tests via `pytest-archon` in `tests/architecture/`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.architecture`

### Alembic Migrations

- Async mode with date-based version organization (`alembic/versions/YYYY/MM/`)
- Config reads from `src/bootstrap/config.py` Settings
- Type comparison and server defaults enabled

