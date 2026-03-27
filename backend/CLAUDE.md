# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

E-commerce loyalty platform backend — a **modular monolith** with strict DDD bounded contexts. Python 3.14, FastAPI, SQLAlchemy 2.x async, PostgreSQL 18, Redis, RabbitMQ (TaskIQ), Dishka DI.

## Commands

```bash
# Infrastructure (must be running for integration/e2e tests)
docker compose up -d                    # PostgreSQL, Redis, RabbitMQ, MinIO

# Dependencies
uv sync                                 # Install all deps (including dev)

# Run server
uv run uvicorn src.bootstrap.web:create_app --factory --reload --host 0.0.0.0 --port 8000

# Run background worker (processes domain events via Outbox)
uv run taskiq worker src.bootstrap.worker:broker

# Database migrations
uv run alembic upgrade head             # Apply all migrations
uv run alembic revision --autogenerate -m "description"  # Create new migration

# Tests (pytest.ini has --cov=src by default)
uv run pytest tests/ -v                 # All tests
uv run pytest tests/unit/ -v            # Unit only (no I/O)
uv run pytest tests/integration/ -v     # Integration (needs Docker services)
uv run pytest tests/e2e/ -v             # E2E HTTP round-trips
uv run pytest tests/architecture/ -v    # Boundary fitness functions
uv run pytest tests/unit/modules/catalog/domain/test_brand.py -v  # Single file
uv run pytest -k "test_create_brand" -v # Single test by name

# Linting & formatting
uv run ruff check .                     # Lint
uv run ruff check --fix . && uv run ruff format .  # Auto-fix + format
uv run mypy .                           # Type checking
```

## Architecture

### Module Structure (4-Layer Clean Architecture)

Each bounded context in `src/modules/{module}/` follows this strict layer hierarchy:

```
domain/          Pure business logic. Uses attrs @dataclass + AggregateRoot mixin.
                 ZERO framework imports (enforced by architecture tests).
application/
  commands/      Write-side CQRS handlers. One file per command (frozen dataclass + Handler).
                 Depends only on domain interfaces + shared kernel.
  queries/       Read-side CQRS handlers. MAY import ORM models directly for performance.
                 Returns Pydantic read models, not domain entities.
  consumers/     Cross-module event consumers (TaskIQ tasks). MAY wire infrastructure.
infrastructure/
  models.py      SQLAlchemy ORM models (completely separate from domain entities).
  repositories/  Data Mapper implementations: explicit _to_domain() / _to_orm() conversion.
presentation/
  router_*.py    FastAPI routers. Uses Dishka DI (FromDishka[HandlerType]).
  schemas.py     Pydantic request/response schemas.
  dependencies.py Dishka Provider classes registering repos + handlers.
```

**Modules**: `catalog`, `identity`, `user`, `geo`, `supplier`

### Cross-Cutting Layers

- `src/shared/` — Shared kernel: `AppException` hierarchy, `AggregateRoot`, `DomainEvent`, `IUnitOfWork`, protocol interfaces (`ITokenProvider`, `IPasswordHasher`, `IPermissionResolver`, `ICacheService`, `ILogger`), `paginate()` helper
- `src/infrastructure/` — Cross-module infra: database engine/session/UoW, Redis cache, JWT/password security, Outbox relay, structlog adapter
- `src/bootstrap/` — Composition root: `config.py` (Pydantic Settings from `.env`), `container.py` (Dishka IoC), `web.py` (FastAPI factory), `broker.py` (TaskIQ/RabbitMQ), `worker.py`
- `src/api/` — Global router aggregation, JWT auth dependency, error handlers, access-log middleware

### Key Patterns

**Data Mapper**: Domain entities (`attrs`) and ORM models (`SQLAlchemy`) are separate classes. Repositories translate between them. Never use Active Record.

**CQRS**: Commands go through domain repos + UoW + domain entities. Queries use `AsyncSession` + ORM directly. Architecture tests explicitly exempt `*.application.queries.*` from the "no infrastructure imports" rule.

**Transactional Outbox**: Aggregates accumulate events via `add_domain_event()`. `UoW.commit()` extracts events and writes `OutboxMessage` rows atomically. A TaskIQ cron relay (`FOR UPDATE SKIP LOCKED`) dispatches them to consumers. This is how modules communicate — no direct cross-module imports.

**DI (Dishka)**: `Scope.APP` for singletons (engine, Redis, settings). `Scope.REQUEST` for per-request (session, UoW, repos, handlers). Routers use `DishkaRoute` route class + `FromDishka[T]` annotations.

**Command Handler pattern**:
```python
async with self._uow:
    entity = Entity.create(...)
    await self._repo.add(entity)
    self._uow.register_aggregate(entity)
    await self._uow.commit()
```

### Module Isolation Rules (enforced by `tests/architecture/test_boundaries.py`)

1. **Domain** must not import application, infrastructure, presentation, or any framework (sqlalchemy, fastapi, dishka, pydantic, redis, taskiq)
2. **Application commands** must not import infrastructure or presentation
3. **Infrastructure** must not import presentation
4. **Cross-module**: only presentation→presentation is allowed (for auth deps like `RequirePermission`); everything else goes through domain events
5. **Shared kernel** must not import any module

### Domain Entity Conventions

- Use `attrs.define` (not Pydantic, not stdlib dataclasses)
- Extend `AggregateRoot` for root entities
- Factory methods: `Entity.create(...)`, `Entity.create_root()`, `Entity.create_child()`
- `_UPDATABLE_FIELDS: ClassVar[frozenset[str]]` whitelist for `update(**kwargs)`
- Soft-delete via `deleted_at` timestamp
- Optimistic locking via `version` column

### Exception Hierarchy

All expected errors extend `AppException` from `src/shared/exceptions.py`:
- `NotFoundError` (404), `UnauthorizedError` (401), `ForbiddenError` (403)
- `ConflictError` (409), `ValidationError` (400), `UnprocessableEntityError` (422)

Domain modules define specific subclasses (e.g., `BrandSlugConflictError(ConflictError)`).

### Test Structure

Tests mirror source: `tests/{tier}/modules/{module}/{layer}/`. Tiers:
- `architecture/` — pytest-archon boundary rules
- `unit/` — Pure domain logic, mocked dependencies
- `integration/` — Real DB via Docker services (not testcontainers — requires `docker compose up -d`)
- `e2e/` — HTTP round-trips via `httpx.AsyncClient` with `ASGITransport`

Test isolation uses **nested transactions** (savepoints) — each test auto-rollbacks. Session-scoped event loop and Dishka container shared across all tests.

### Alembic Migrations

All ORM models must be imported in `src/infrastructure/database/registry.py` for autogenerate to detect them. Migration env at `alembic/env.py` uses async engine with `NullPool`.
