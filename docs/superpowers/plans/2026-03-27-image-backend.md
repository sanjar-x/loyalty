# ImageBackend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ImageBackend microservice from scratch — presigned upload, background image processing (resize/WebP), SSE status streaming, external URL import.

**Architecture:** Clean Architecture (Hexagonal) with strict bottom-up layering. Domain has zero infrastructure dependencies. Infrastructure implements ports. Presentation wires HTTP + background tasks. DI via Dishka.

**Tech Stack:** Python 3.14, FastAPI, Dishka (DI), TaskIQ + RabbitMQ (background jobs), Pillow (image processing), aiobotocore (S3), PostgreSQL + SQLAlchemy (metadata), Redis (SSE pub/sub), Alembic (migrations)

**Spec:** `docs/superpowers/specs/2026-03-27-image-backend-roadmap-design.md`

---

## File Map

### Root Files
| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | Create | Dependencies, ruff config, pytest config |
| `.env.example` | Create | Environment variables template |
| `.gitignore` | Create | Python + IDE ignores |
| `.python-version` | Create | Pin Python 3.14 |
| `Dockerfile` | Create | Production image |
| `docker-compose.yml` | Create | Dev infrastructure |
| `railway.toml` | Create | Deploy placeholder |
| `main.py` | Create | ASGI entry point |
| `alembic.ini` | Create | Alembic config |

### Phase 1: Shared Kernel (`src/shared/`)
| File | Action | Purpose |
|---|---|---|
| `src/__init__.py` | Create | Package marker |
| `src/shared/__init__.py` | Create | Package marker |
| `src/shared/exceptions.py` | Create | Exception hierarchy |
| `src/shared/schemas.py` | Create | CamelModel base |
| `src/shared/context.py` | Create | Request context vars |
| `src/shared/interfaces/__init__.py` | Create | Package marker |
| `src/shared/interfaces/blob_storage.py` | Create | IBlobStorage protocol |
| `src/shared/interfaces/config.py` | Create | IStorageConfig protocol |
| `src/shared/interfaces/uow.py` | Create | IUnitOfWork ABC |
| `src/shared/interfaces/logger.py` | Create | ILogger protocol |
| `src/shared/interfaces/storage.py` | Create | IStorageFacade protocol + PresignedUploadData |
| `src/shared/interfaces/entities.py` | Create | IBase, DomainEvent, AggregateRoot |

### Phase 2: Domain (`src/modules/storage/domain/`)
| File | Action | Purpose |
|---|---|---|
| `src/modules/__init__.py` | Create | Package marker |
| `src/modules/storage/__init__.py` | Create | Package marker |
| `src/modules/storage/domain/__init__.py` | Create | Package marker |
| `src/modules/storage/domain/value_objects.py` | Create | StorageStatus enum |
| `src/modules/storage/domain/entities.py` | Create | StorageFile attrs dataclass |
| `src/modules/storage/domain/interfaces.py` | Create | IStorageRepository ABC |
| `src/modules/storage/domain/exceptions.py` | Create | Domain exceptions |

### Phase 3: Infrastructure
| File | Action | Purpose |
|---|---|---|
| `src/infrastructure/__init__.py` | Create | Package marker |
| `src/infrastructure/database/__init__.py` | Create | Package marker |
| `src/infrastructure/database/base.py` | Create | SQLAlchemy Base |
| `src/infrastructure/database/session.py` | Create | Session helpers |
| `src/infrastructure/database/uow.py` | Create | UnitOfWork impl |
| `src/infrastructure/database/registry.py` | Create | Model registry |
| `src/infrastructure/database/provider.py` | Create | Dishka DB provider |
| `src/infrastructure/database/models/__init__.py` | Create | Package marker |
| `src/infrastructure/database/models/failed_task.py` | Create | DLQ ORM model |
| `src/infrastructure/storage/__init__.py` | Create | Package marker |
| `src/infrastructure/storage/factory.py` | Create | S3ClientFactory |
| `src/infrastructure/cache/__init__.py` | Create | Package marker |
| `src/infrastructure/cache/redis.py` | Create | Redis client helpers |
| `src/infrastructure/cache/provider.py` | Create | Dishka Redis provider |
| `src/infrastructure/logging/__init__.py` | Create | Package marker |
| `src/infrastructure/logging/adapter.py` | Create | StructlogAdapter |
| `src/infrastructure/logging/provider.py` | Create | Dishka logging provider |
| `src/infrastructure/logging/taskiq_middleware.py` | Create | TaskIQ log middleware |
| `src/infrastructure/logging/dlq_middleware.py` | Create | Dead letter queue middleware |
| `src/modules/storage/infrastructure/__init__.py` | Create | Package marker |
| `src/modules/storage/infrastructure/models.py` | Create | StorageObject ORM |
| `src/modules/storage/infrastructure/repository.py` | Create | StorageObjectRepository |
| `src/modules/storage/infrastructure/service.py` | Create | S3StorageService |
| `alembic/env.py` | Create | Alembic environment |
| `alembic/script.py.mako` | Create | Migration template |
| `alembic/versions/001_create_storage_objects.py` | Create | Initial migration |

### Phase 4: Application
| File | Action | Purpose |
|---|---|---|
| `src/modules/storage/application/__init__.py` | Create | Package marker |
| `src/modules/storage/application/commands/__init__.py` | Create | Package marker |
| `src/modules/storage/application/commands/process_image.py` | Create | Pillow processing pipeline |
| `src/modules/storage/application/consumers/__init__.py` | Create | Package marker |
| `src/modules/storage/application/queries/__init__.py` | Create | Package marker |

### Phase 5: Presentation
| File | Action | Purpose |
|---|---|---|
| `src/modules/storage/presentation/__init__.py` | Create | Package marker |
| `src/modules/storage/presentation/schemas.py` | Create | API Pydantic schemas |
| `src/modules/storage/presentation/router.py` | Create | 6 HTTP endpoints |
| `src/modules/storage/presentation/tasks.py` | Create | TaskIQ background tasks |
| `src/modules/storage/presentation/sse.py` | Create | SSEManager (Redis pub/sub) |
| `src/modules/storage/presentation/facade.py` | Create | StorageFacade |
| `src/modules/storage/presentation/dependencies.py` | Create | Dishka StorageProvider |
| `src/api/__init__.py` | Create | Package marker |
| `src/api/router.py` | Create | Root API router |
| `src/api/dependencies/__init__.py` | Create | Package marker |
| `src/api/dependencies/auth.py` | Create | API key auth |
| `src/api/exceptions/__init__.py` | Create | Package marker |
| `src/api/exceptions/handlers.py` | Create | Exception -> HTTP mapping |
| `src/api/middlewares/__init__.py` | Create | Package marker |
| `src/api/middlewares/logger.py` | Create | Access logger middleware |

### Phase 6: Bootstrap
| File | Action | Purpose |
|---|---|---|
| `src/bootstrap/__init__.py` | Create | Package marker |
| `src/bootstrap/config.py` | Create | Settings (pydantic-settings) |
| `src/bootstrap/logger.py` | Create | structlog setup |
| `src/bootstrap/broker.py` | Create | TaskIQ broker config |
| `src/bootstrap/container.py` | Create | Dishka container assembly |
| `src/bootstrap/worker.py` | Create | TaskIQ worker entry point |
| `src/bootstrap/scheduler.py` | Create | Task scheduler |
| `src/bootstrap/web.py` | Create | FastAPI factory |

### Phase 7: Unit Tests
| File | Action | Purpose |
|---|---|---|
| `tests/__init__.py` | Create | Package marker |
| `tests/unit/__init__.py` | Create | Package marker |
| `tests/unit/modules/__init__.py` | Create | Package marker |
| `tests/unit/modules/storage/__init__.py` | Create | Package marker |
| `tests/unit/modules/storage/domain/__init__.py` | Create | Package marker |
| `tests/unit/modules/storage/domain/test_value_objects.py` | Create | StorageStatus tests |
| `tests/unit/modules/storage/domain/test_entities.py` | Create | StorageFile tests |
| `tests/unit/modules/storage/application/__init__.py` | Create | Package marker |
| `tests/unit/modules/storage/application/test_process_image.py` | Create | Pillow pipeline tests |
| `tests/unit/modules/storage/presentation/__init__.py` | Create | Package marker |
| `tests/unit/modules/storage/presentation/test_sse.py` | Create | SSE channel tests |
| `tests/integration/__init__.py` | Create | Package marker |
| `tests/integration/test_upload_flow.py` | Create | Placeholder |

---

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`, `.env.example`, `.gitignore`, `.python-version`, `Dockerfile`, `docker-compose.yml`, `railway.toml`, `main.py`

- [ ] **Step 1: Create `pyproject.toml`**

```python
# pyproject.toml
[project]
name = "image-backend"
version = "0.1.0"
description = "Image processing microservice — upload, resize, thumbnail, webp conversion"
requires-python = ">=3.14"
dependencies = [
    "aiobotocore>=3.2.1",
    "alembic>=1.18.4",
    "anyio>=4.12.1",
    "asyncpg>=0.31.0",
    "attrs>=25.4.0",
    "dishka>=1.9.1",
    "fastapi[standard]>=0.115.0",
    "pillow>=11.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.2.2",
    "python-multipart>=0.0.22",
    "redis[hiredis]>=7.3.0",
    "sqlalchemy[asyncio]>=2.1.0b1",
    "structlog>=25.5.0",
    "taskiq>=0.12.1",
    "taskiq-aio-pika>=0.6.0",
    "uvicorn[standard]>=0.41.0",
    "httpx>=0.28.0",
]

[dependency-groups]
dev = [
    "httpx>=0.28.1",
    "mypy>=1.19.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py314"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501", "RUF001", "RUF002", "RUF003", "B008", "UP042", "UP046"]

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

- [ ] **Step 2: Create `.python-version`**

```
3.14
```

- [ ] **Step 3: Create `.env.example`**

```bash
# Application
PROJECT_NAME=Image Backend
VERSION=1.0.0
ENVIRONMENT=dev
DEBUG=True

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# PostgreSQL
PGHOST=127.0.0.1
PGPORT=5432
PGUSER=postgres
PGPASSWORD=postgres
PGDATABASE=image_backend

# Redis
REDISHOST=127.0.0.1
REDISPORT=6379
REDISUSER=default
REDISPASSWORD=password
REDISDATABASE=1

# S3 / MinIO
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_ACCESS_KEY=admin
S3_SECRET_KEY=password
S3_REGION=us-east-1
S3_BUCKET_NAME=media-bucket
S3_PUBLIC_BASE_URL=http://127.0.0.1:9000/media-bucket

# RabbitMQ
RABBITMQ_PRIVATE_URL=amqp://admin:password@127.0.0.1:5672/

# Service Auth
INTERNAL_API_KEY=change-me-in-production
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
.ruff_cache/
.mypy_cache/
*.db
dist/
build/
```

- [ ] **Step 5: Create `Dockerfile`**

```dockerfile
FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev --no-editable

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 6: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:18-alpine
    container_name: postgres
    networks: [dev_net]
    deploy:
      resources:
        limits:
          memory: 1024M
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
      TZ: UTC
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d postgres"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  redis:
    image: redis:8.4-alpine
    container_name: redis
    networks: [dev_net]
    deploy:
      resources:
        limits:
          memory: 512M
    command: >
      redis-server --requirepass password --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis:/data
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a password ping | grep PONG"]
      interval: 10s
      timeout: 5s
      retries: 3

  rabbitmq:
    image: rabbitmq:4.2.4-management-alpine
    container_name: rabbitmq
    networks: [dev_net]
    deploy:
      resources:
        limits:
          memory: 512M
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: password
    ports:
      - "127.0.0.1:5672:5672"
      - "127.0.0.1:15672:15672"
    volumes:
      - rabbitmq:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD-SHELL", "rabbitmq-diagnostics -q ping"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s

  minio:
    image: minio/minio:latest
    container_name: minio
    networks: [dev_net]
    deploy:
      resources:
        limits:
          memory: 512M
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password
    command: server /data --console-address ":9001"
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
    volumes:
      - minio:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9000/minio/health/live || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

networks:
  dev_net:
    driver: bridge

volumes:
  postgres:
  redis:
  rabbitmq:
  minio:
```

- [ ] **Step 7: Create `railway.toml`**

```toml
[build]
builder = "dockerfile"
```

- [ ] **Step 8: Create placeholder `main.py`**

```python
# Placeholder — will be completed in Task 22 (Bootstrap)
```

- [ ] **Step 9: Initialize uv and lock dependencies**

Run: `cd image_backend && uv sync`
Expected: `.venv/` created, `uv.lock` generated

- [ ] **Step 10: Initialize Alembic**

Run: `cd image_backend && uv run alembic init alembic`
Expected: `alembic/` directory and `alembic.ini` created

- [ ] **Step 11: Create package `__init__.py` files**

Create empty `__init__.py` in all directories:
```
src/__init__.py
src/shared/__init__.py
src/shared/interfaces/__init__.py
src/modules/__init__.py
src/modules/storage/__init__.py
src/modules/storage/domain/__init__.py
src/modules/storage/infrastructure/__init__.py
src/modules/storage/application/__init__.py
src/modules/storage/application/commands/__init__.py
src/modules/storage/application/consumers/__init__.py
src/modules/storage/application/queries/__init__.py
src/modules/storage/presentation/__init__.py
src/infrastructure/__init__.py
src/infrastructure/database/__init__.py
src/infrastructure/database/models/__init__.py
src/infrastructure/storage/__init__.py
src/infrastructure/cache/__init__.py
src/infrastructure/logging/__init__.py
src/api/__init__.py
src/api/dependencies/__init__.py
src/api/exceptions/__init__.py
src/api/middlewares/__init__.py
src/bootstrap/__init__.py
tests/__init__.py
tests/unit/__init__.py
tests/unit/modules/__init__.py
tests/unit/modules/storage/__init__.py
tests/unit/modules/storage/domain/__init__.py
tests/unit/modules/storage/application/__init__.py
tests/unit/modules/storage/presentation/__init__.py
tests/integration/__init__.py
```

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: scaffold project skeleton with dependencies and docker-compose"
```

---

## Task 2: Shared Kernel — Exceptions

**Files:**
- Create: `src/shared/exceptions.py`

- [ ] **Step 1: Write `src/shared/exceptions.py`**

```python
"""Application-level exception hierarchy.

Every expected error is a subclass of AppException. The presentation layer
catches these and maps them to HTTP status codes via the global exception handler.
"""

from typing import Any


class AppException(Exception):
    """Base class for all expected application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message: str = message
        self.status_code: int = status_code
        self.error_code: str = error_code
        self.details: dict[str, Any] = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=404, error_code=error_code, details=details)


class BadRequestError(AppException):
    def __init__(
        self,
        message: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=400, error_code=error_code, details=details)


class UnauthorizedError(AppException):
    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=401, error_code=error_code, details=details)


class ForbiddenError(AppException):
    def __init__(
        self,
        message: str = "Access denied. Insufficient permissions.",
        error_code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=403, error_code=error_code, details=details)


class ConflictError(AppException):
    def __init__(
        self,
        message: str = "Resource state conflict",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=409, error_code=error_code, details=details)


class ValidationError(AppException):
    def __init__(
        self,
        message: str = "Data validation error",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=400, error_code=error_code, details=details)


class UnprocessableEntityError(AppException):
    def __init__(
        self,
        message: str = "Cannot process entity (business logic violation)",
        error_code: str = "UNPROCESSABLE_ENTITY",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 422, error_code, details)


class ServiceUnavailableError(AppException):
    def __init__(
        self,
        message: str = "External service temporarily unavailable",
        error_code: str = "SERVICE_UNAVAILABLE",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=503, error_code=error_code, details=details)
```

- [ ] **Step 2: Commit**

```bash
git add src/shared/exceptions.py
git commit -m "feat: add shared exception hierarchy"
```

---

## Task 3: Shared Kernel — Interfaces

**Files:**
- Create: `src/shared/interfaces/blob_storage.py`, `src/shared/interfaces/config.py`, `src/shared/interfaces/uow.py`, `src/shared/interfaces/logger.py`, `src/shared/interfaces/storage.py`, `src/shared/interfaces/entities.py`

- [ ] **Step 1: Write `src/shared/interfaces/entities.py`**

```python
"""Domain entity base types and event infrastructure."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


class IBase(Protocol):
    """Contract for any identifiable domain entity."""
    id: uuid.UUID


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_type: str = ""
    aggregate_id: str = ""
    event_type: str = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.aggregate_type == "" or cls.event_type == "":
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' and 'event_type'"
            )


class AggregateRoot:
    """Mixin for domain aggregates that collect events in-memory."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    def __attrs_post_init__(self) -> None:
        self._domain_events: list[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        self._domain_events.clear()

    @property
    def domain_events(self) -> list[DomainEvent]:
        return self._domain_events.copy()
```

- [ ] **Step 2: Write `src/shared/interfaces/logger.py`**

```python
"""Logging port (Hexagonal Architecture)."""

from __future__ import annotations

from typing import Any, Protocol


class ILogger(Protocol):
    """Abstract logger for application and presentation layers."""

    def bind(self, **kwargs: Any) -> ILogger: ...
    def debug(self, event: str, **kwargs: Any) -> None: ...
    def info(self, event: str, **kwargs: Any) -> None: ...
    def warning(self, event: str, **kwargs: Any) -> None: ...
    def error(self, event: str, **kwargs: Any) -> None: ...
    def critical(self, event: str, **kwargs: Any) -> None: ...
    def exception(self, event: str, **kwargs: Any) -> None: ...
```

- [ ] **Step 3: Write `src/shared/interfaces/uow.py`**

```python
"""Unit of Work port (Hexagonal Architecture)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.interfaces.entities import AggregateRoot


class IUnitOfWork(ABC):
    """Abstract transactional boundary for write operations."""

    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork: ...

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    def register_aggregate(self, aggregate: AggregateRoot) -> None: ...
```

- [ ] **Step 4: Write `src/shared/interfaces/config.py`**

```python
"""Storage configuration port."""

from typing import Protocol


class IStorageConfig(Protocol):
    """Contract for object storage configuration values."""
    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str
```

- [ ] **Step 5: Write `src/shared/interfaces/blob_storage.py`**

```python
"""Binary object storage port (Hexagonal Architecture)."""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class IBlobStorage(Protocol):
    """Contract for binary (object) storage operations."""

    def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]: ...

    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str: ...

    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict: ...

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str: ...

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str: ...

    async def object_exists(self, object_name: str) -> bool: ...

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]: ...

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict: ...

    async def delete_object(self, object_name: str) -> None: ...

    async def delete_objects(self, object_names: list[str]) -> list[str]: ...

    async def copy_object(self, source_name: str, dest_name: str) -> None: ...
```

- [ ] **Step 6: Write `src/shared/interfaces/storage.py`**

```python
"""Storage facade port (Hexagonal Architecture)."""

import uuid
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PresignedUploadData:
    url_data: dict | str
    object_key: str
    file_id: uuid.UUID | None = None


class IStorageFacade(Protocol):
    """Public API of the Storage module (Facade pattern)."""

    async def request_upload(
        self, module: str, entity_id: str | uuid.UUID, filename: str
    ) -> PresignedUploadData: ...

    async def request_direct_upload(
        self, module: str, entity_id: str | uuid.UUID, filename: str,
        content_type: str, expire_in: int = 300,
    ) -> PresignedUploadData: ...

    async def reserve_upload_slot(
        self, module: str, entity_id: str | uuid.UUID, filename: str,
        content_type: str, expire_in: int = 300,
    ) -> PresignedUploadData: ...

    async def verify_upload(self, file_id: uuid.UUID) -> dict[str, Any]: ...

    async def verify_module_upload(
        self, module: str, entity_id: str | uuid.UUID, object_key: str
    ) -> dict[str, Any]: ...

    async def register_processed_media(
        self, module: str, entity_id: str | uuid.UUID, object_key: str,
        content_type: str, size: int,
    ) -> uuid.UUID: ...

    async def update_object_metadata(
        self, file_id: uuid.UUID, object_key: str, size_bytes: int, content_type: str,
    ) -> None: ...
```

- [ ] **Step 7: Commit**

```bash
git add src/shared/interfaces/
git commit -m "feat: add shared kernel interfaces (ports)"
```

---

## Task 4: Shared Kernel — Schemas & Context

**Files:**
- Create: `src/shared/schemas.py`, `src/shared/context.py`

- [ ] **Step 1: Write `src/shared/schemas.py`**

```python
"""Base Pydantic model with automatic camelCase aliasing."""

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
```

- [ ] **Step 2: Write `src/shared/context.py`**

```python
"""Request-scoped context variables."""

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
```

- [ ] **Step 3: Commit**

```bash
git add src/shared/schemas.py src/shared/context.py
git commit -m "feat: add CamelModel base schema and request context"
```

---

## Task 5: Domain — Value Objects (TDD)

**Files:**
- Create: `src/modules/storage/domain/value_objects.py`
- Test: `tests/unit/modules/storage/domain/test_value_objects.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/modules/storage/domain/test_value_objects.py
from src.modules.storage.domain.value_objects import StorageStatus


class TestStorageStatus:
    def test_values_match_strings(self):
        assert StorageStatus.PENDING_UPLOAD == "PENDING_UPLOAD"
        assert StorageStatus.PROCESSING == "PROCESSING"
        assert StorageStatus.COMPLETED == "COMPLETED"
        assert StorageStatus.FAILED == "FAILED"

    def test_is_terminal_for_completed(self):
        assert StorageStatus.COMPLETED.is_terminal is True

    def test_is_terminal_for_failed(self):
        assert StorageStatus.FAILED.is_terminal is True

    def test_is_not_terminal_for_pending(self):
        assert StorageStatus.PENDING_UPLOAD.is_terminal is False

    def test_is_not_terminal_for_processing(self):
        assert StorageStatus.PROCESSING.is_terminal is False

    def test_has_exactly_four_members(self):
        assert len(StorageStatus) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd image_backend && uv run pytest tests/unit/modules/storage/domain/test_value_objects.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.modules.storage.domain.value_objects'`

- [ ] **Step 3: Write implementation**

```python
# src/modules/storage/domain/value_objects.py
"""Storage domain value objects."""

from enum import StrEnum


class StorageStatus(StrEnum):
    """Processing lifecycle of a storage object."""

    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (StorageStatus.COMPLETED, StorageStatus.FAILED)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd image_backend && uv run pytest tests/unit/modules/storage/domain/test_value_objects.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/modules/storage/domain/value_objects.py tests/unit/modules/storage/domain/test_value_objects.py
git commit -m "feat: add StorageStatus value object with TDD"
```

---

## Task 6: Domain — Entity (TDD)

**Files:**
- Create: `src/modules/storage/domain/entities.py`
- Test: `tests/unit/modules/storage/domain/test_entities.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/modules/storage/domain/test_entities.py
import uuid

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.value_objects import StorageStatus


class TestStorageFileCreate:
    def test_create_generates_uuid(self):
        sf = StorageFile.create(
            bucket_name="test-bucket",
            object_key="raw/123/photo.jpg",
            content_type="image/jpeg",
        )
        assert isinstance(sf.id, uuid.UUID)

    def test_create_sets_pending_status(self):
        sf = StorageFile.create(
            bucket_name="test-bucket",
            object_key="raw/123/photo.jpg",
            content_type="image/jpeg",
        )
        assert sf.status == StorageStatus.PENDING_UPLOAD

    def test_create_sets_required_fields(self):
        sf = StorageFile.create(
            bucket_name="my-bucket",
            object_key="raw/abc/file.png",
            content_type="image/png",
            size_bytes=1024,
            owner_module="catalog",
            filename="file.png",
        )
        assert sf.bucket_name == "my-bucket"
        assert sf.object_key == "raw/abc/file.png"
        assert sf.content_type == "image/png"
        assert sf.size_bytes == 1024
        assert sf.owner_module == "catalog"
        assert sf.filename == "file.png"

    def test_create_defaults(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/jpeg",
        )
        assert sf.size_bytes == 0
        assert sf.is_latest is True
        assert sf.url is None
        assert sf.image_variants is None
        assert sf.owner_module is None
        assert sf.version_id is None
        assert sf.etag is None

    def test_two_creates_produce_different_ids(self):
        sf1 = StorageFile.create(bucket_name="b", object_key="k", content_type="image/jpeg")
        sf2 = StorageFile.create(bucket_name="b", object_key="k", content_type="image/jpeg")
        assert sf1.id != sf2.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd image_backend && uv run pytest tests/unit/modules/storage/domain/test_entities.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# src/modules/storage/domain/entities.py
"""Storage domain entities."""

import uuid
from datetime import datetime

from attr import dataclass

from src.modules.storage.domain.value_objects import StorageStatus


@dataclass
class StorageFile:
    """Domain entity representing a file in the object storage."""

    id: uuid.UUID
    bucket_name: str
    object_key: str
    content_type: str
    size_bytes: int = 0
    is_latest: bool = True
    owner_module: str | None = None
    version_id: str | None = None
    etag: str | None = None
    content_encoding: str | None = None
    cache_control: str | None = None
    status: StorageStatus = StorageStatus.PENDING_UPLOAD
    url: str | None = None
    image_variants: list[dict] | None = None
    filename: str | None = None
    created_at: datetime | None = None
    last_modified_in_s3: datetime | None = None

    @classmethod
    def create(
        cls,
        bucket_name: str,
        object_key: str,
        content_type: str,
        size_bytes: int = 0,
        owner_module: str | None = None,
        filename: str | None = None,
    ) -> StorageFile:
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            bucket_name=bucket_name,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            owner_module=owner_module,
            filename=filename,
        )
```

- [ ] **Step 4: Run tests**

Run: `cd image_backend && uv run pytest tests/unit/modules/storage/domain/ -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add src/modules/storage/domain/entities.py tests/unit/modules/storage/domain/test_entities.py
git commit -m "feat: add StorageFile domain entity with TDD"
```

---

## Task 7: Domain — Repository Interface & Exceptions

**Files:**
- Create: `src/modules/storage/domain/interfaces.py`, `src/modules/storage/domain/exceptions.py`

- [ ] **Step 1: Write `src/modules/storage/domain/interfaces.py`**

```python
"""Storage domain interfaces."""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from src.modules.storage.domain.entities import StorageFile


class IStorageRepository(ABC):
    @abstractmethod
    async def add(self, storage_file: StorageFile) -> None: ...

    @abstractmethod
    async def update(self, storage_file: StorageFile) -> None: ...

    @abstractmethod
    async def get_by_key(self, key: uuid.UUID) -> StorageFile | None: ...

    @abstractmethod
    async def get_active_by_key(self, bucket_name: str, object_key: str) -> StorageFile | None: ...

    @abstractmethod
    async def get_all_versions(self, bucket_name: str, object_key: str) -> Sequence[StorageFile]: ...

    @abstractmethod
    async def deactivate_previous_versions(self, bucket_name: str, object_key: str) -> None: ...

    @abstractmethod
    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None: ...

    @abstractmethod
    async def get_by_id(self, storage_object_id: uuid.UUID) -> StorageFile | None: ...

    @abstractmethod
    async def list_pending_expired(self, older_than: datetime) -> list[StorageFile]: ...
```

- [ ] **Step 2: Write `src/modules/storage/domain/exceptions.py`**

```python
"""Storage domain exceptions."""

from src.shared.exceptions import AppException


class StorageFileNotFoundError(AppException):
    def __init__(self, storage_object_id: str):
        super().__init__(
            message=f"Storage file '{storage_object_id}' not found.",
            status_code=404,
            error_code="STORAGE_FILE_NOT_FOUND",
            details={"storage_object_id": storage_object_id},
        )


class StorageFileAlreadyProcessedError(AppException):
    def __init__(self, storage_object_id: str):
        super().__init__(
            message=f"Storage file '{storage_object_id}' has already been processed.",
            status_code=409,
            error_code="STORAGE_FILE_ALREADY_PROCESSED",
            details={"storage_object_id": storage_object_id},
        )
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/storage/domain/interfaces.py src/modules/storage/domain/exceptions.py
git commit -m "feat: add repository interface and domain exceptions"
```

---

## Task 8: Infrastructure — Database Stack

**Files:**
- Create: `src/infrastructure/database/base.py`, `src/infrastructure/database/session.py`, `src/infrastructure/database/uow.py`, `src/infrastructure/database/registry.py`, `src/infrastructure/database/provider.py`, `src/infrastructure/database/models/failed_task.py`

This task creates all shared database infrastructure. See spec Phase 3.1 for details.

- [ ] **Step 1: Write all database infrastructure files**

See existing code for exact implementations. Key files:
- `base.py`: `Base = DeclarativeBase` with `type_annotation_map` for UUID
- `uow.py`: `UnitOfWork(IUnitOfWork)` wrapping `AsyncSession`, translates `IntegrityError` to `ConflictError`/`UnprocessableEntityError`
- `provider.py`: Dishka provider — `AsyncEngine` (APP), `async_sessionmaker` (APP), `AsyncSession` (REQUEST), `IUnitOfWork` (REQUEST). Pool: `pool_size=15`, `max_overflow=10`, `pool_pre_ping=True`
- `registry.py`: Imports all ORM models to ensure they're registered with `Base.metadata`
- `models/failed_task.py`: `FailedTask` ORM model for DLQ (table `failed_tasks`)

- [ ] **Step 2: Commit**

```bash
git add src/infrastructure/database/
git commit -m "feat: add database infrastructure (engine, UoW, provider, DLQ model)"
```

---

## Task 9: Infrastructure — ORM Model & Migration

**Files:**
- Create: `src/modules/storage/infrastructure/models.py`, `alembic/versions/001_create_storage_objects.py`

- [ ] **Step 1: Write `src/modules/storage/infrastructure/models.py`**

`StorageObject(Base)` — table `storage_objects`:
- PK: `id` UUID v7
- `bucket_name`: `String(255)`, indexed
- `object_key`: `String(1024)`
- `version_id`: `String(255)`, nullable
- `is_latest`: `Boolean`, server_default `true`
- `size_bytes`: `BigInteger`, server_default `0`
- `etag`: `String(64)`, nullable
- `content_type`: `String(255)`, indexed
- `content_encoding`, `cache_control`: `String(255)`, nullable
- `owner_module`: `String(100)`, indexed, nullable
- `status`: `SAEnum(StorageStatus)` as `storage_status_enum`, indexed
- `url`: `String(1024)`, nullable
- `image_variants`: `JSONB`, nullable
- `filename`: `String(255)`, nullable
- `created_at`: `TIMESTAMP(timezone=True)`, `server_default=func.now()`
- `last_modified_in_s3`: `TIMESTAMP(timezone=True)`, nullable
- Partial unique index: `uix_storage_active_object` on `(bucket_name, object_key) WHERE is_latest = true`

See spec Phase 3.2 for full column definitions.

- [ ] **Step 2: Configure `alembic/env.py`**

Update `alembic/env.py` to import `Base.metadata` from `src.infrastructure.database.base` and use async engine from settings.

- [ ] **Step 3: Generate migration**

Run: `cd image_backend && uv run alembic revision --autogenerate -m "create storage_objects and failed_tasks tables"`
Expected: New migration file in `alembic/versions/`

- [ ] **Step 4: Commit**

```bash
git add src/modules/storage/infrastructure/models.py alembic/
git commit -m "feat: add StorageObject ORM model and initial Alembic migration"
```

---

## Task 10: Infrastructure — Repository

**Files:**
- Create: `src/modules/storage/infrastructure/repository.py`

- [ ] **Step 1: Write `src/modules/storage/infrastructure/repository.py`**

`StorageObjectRepository(IStorageRepository)` — Data Mapper pattern:
- `_to_domain(orm: StorageObject) -> StorageFile`: maps all fields from ORM to domain entity
- `_to_orm(entity: StorageFile) -> StorageObject`: maps all fields from domain to ORM
- `add()`: `session.add(_to_orm(entity))`
- `update()`: `session.get()` then field-by-field update
- `get_by_id()`, `get_by_key()`: `session.get(StorageObject, uuid)`
- `get_active_by_key()`: `select(...).where(bucket, key, is_latest=True)`
- `get_all_versions()`: `select(...).order_by(created_at.desc())`
- `deactivate_previous_versions()`: `update(...).where(...).values(is_latest=False)`
- `mark_as_deleted()`: delegates to `deactivate_previous_versions`
- `list_pending_expired()`: `select(...).where(status == PENDING_UPLOAD, created_at < older_than)`

See spec Phase 3.4 for exact method signatures.

- [ ] **Step 2: Commit**

```bash
git add src/modules/storage/infrastructure/repository.py
git commit -m "feat: add StorageObjectRepository (Data Mapper)"
```

---

## Task 11: Infrastructure — S3 (Factory + Service)

**Files:**
- Create: `src/infrastructure/storage/factory.py`, `src/modules/storage/infrastructure/service.py`

- [ ] **Step 1: Write `src/infrastructure/storage/factory.py`**

`S3ClientFactory`:
- `__init__(access_key, secret_key, region, endpoint_url)` — stores credentials
- `create_client() -> AsyncGenerator[AioBaseClient]` — yields ephemeral client via `AioSession.create_client("s3", ...)` with `AioConfig(max_pool_connections=1, connect_timeout=5.0, read_timeout=60.0, retries={"max_attempts": 3, "mode": "standard"})`

- [ ] **Step 2: Write `src/modules/storage/infrastructure/service.py`**

`S3StorageService(IBlobStorage)`:
- `__init__(s3_client, bucket_name)`
- `_handle_client_error(e, object_name)`: maps `ClientError` codes `404`/`NoSuchKey`/`NotFound` -> `NotFoundError`, else `ServiceUnavailableError`
- `download_stream()`: `get_object` + chunked read
- `get_presigned_url()`: `generate_presigned_url("get_object", ...)`
- `generate_presigned_put_url()`: `generate_presigned_url("put_object", ..., ContentType)`
- `get_presigned_upload_url()`: `generate_presigned_post(...)`
- `upload_stream()`: multipart upload with 5 MB min part size, abort on error
- `object_exists()`: `head_object`, returns `True`/`False`
- `get_object_metadata()`: `head_object`, returns `{content_length, content_type, etag, last_modified, metadata}`
- `list_objects()`: `list_objects_v2` with pagination
- `delete_object()`: `delete_object`
- `delete_objects()`: batch delete in chunks of 1000
- `copy_object()`: `copy_object` within same bucket

See spec Phase 3.5 for full method list.

- [ ] **Step 3: Commit**

```bash
git add src/infrastructure/storage/factory.py src/modules/storage/infrastructure/service.py
git commit -m "feat: add S3ClientFactory and S3StorageService"
```

---

## Task 12: Infrastructure — Cache, SSE, Logging

**Files:**
- Create: `src/infrastructure/cache/redis.py`, `src/infrastructure/cache/provider.py`, `src/modules/storage/presentation/sse.py`, `src/infrastructure/logging/adapter.py`, `src/infrastructure/logging/provider.py`, `src/infrastructure/logging/taskiq_middleware.py`, `src/infrastructure/logging/dlq_middleware.py`

- [ ] **Step 1: Write cache files**

`cache/provider.py` — Dishka `CacheProvider`:
- `redis_client(settings: Settings) -> AsyncIterable[Redis]`: creates `Redis.from_url(settings.redis_url)`, yields, then `aclose()`

- [ ] **Step 2: Write `src/modules/storage/presentation/sse.py`**

`SSEManager`:
- `__init__(redis: Redis)`
- `channel_name(storage_object_id) -> str`: returns `f"media:status:{storage_object_id}"`
- `publish(storage_object_id, data)`: `redis.publish(channel, json.dumps(data))`
- `subscribe(storage_object_id, timeout=120.0, poll_interval=1.0) -> AsyncGenerator[dict | None]`: subscribe to channel, yield messages or `None` on timeout, stop on terminal status

- [ ] **Step 3: Write logging files**

- `adapter.py`: `StructlogAdapter(ILogger)` wrapping `structlog.BoundLogger`
- `provider.py`: Dishka `LoggingProvider` — provides `ILogger` at REQUEST scope
- `taskiq_middleware.py`: `LoggingTaskiqMiddleware` — logs task start/end/error
- `dlq_middleware.py`: `DLQMiddleware` — on max retries exceeded, saves task to `failed_tasks` table

- [ ] **Step 4: Commit**

```bash
git add src/infrastructure/cache/ src/modules/storage/presentation/sse.py src/infrastructure/logging/
git commit -m "feat: add Redis cache, SSE manager, logging infrastructure"
```

---

## Task 13: Application — Image Processing (TDD)

**Files:**
- Create: `src/modules/storage/application/commands/process_image.py`
- Test: `tests/unit/modules/storage/application/test_process_image.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/modules/storage/application/test_process_image.py
import io
import uuid

from PIL import Image

from src.modules.storage.application.commands.process_image import (
    VARIANT_SIZES,
    build_variants,
    convert_to_webp,
    resize_to_fit,
)


def _make_test_image(width: int = 100, height: int = 80, fmt: str = "JPEG") -> bytes:
    """Create a minimal test image as raw bytes."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestConvertToWebp:
    def test_returns_webp_bytes(self):
        raw = _make_test_image()
        result = convert_to_webp(raw)
        img = Image.open(io.BytesIO(result))
        assert img.format == "WEBP"

    def test_with_max_size_resizes(self):
        raw = _make_test_image(width=200, height=200)
        result = convert_to_webp(raw, max_size=(50, 50))
        img = Image.open(io.BytesIO(result))
        assert img.width <= 50
        assert img.height <= 50

    def test_handles_rgba_input(self):
        img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = convert_to_webp(buf.getvalue())
        out = Image.open(io.BytesIO(result))
        assert out.format == "WEBP"


class TestResizeToFit:
    def test_preserves_aspect_ratio(self):
        img = Image.new("RGB", (200, 100))
        result = resize_to_fit(img, 100, 100)
        assert result.width == 100
        assert result.height == 50

    def test_does_not_upscale(self):
        img = Image.new("RGB", (50, 30))
        result = resize_to_fit(img, 100, 100)
        assert result.width == 50
        assert result.height == 30


class TestBuildVariants:
    def test_returns_three_variants(self):
        raw = _make_test_image(width=1500, height=1000)
        sid = uuid.uuid4()
        main_bytes, variants_meta, variants_data = build_variants(
            raw, sid, "https://cdn.example.com/bucket"
        )
        assert len(variants_meta) == 3
        assert len(variants_data) == 3

    def test_main_is_webp(self):
        raw = _make_test_image()
        sid = uuid.uuid4()
        main_bytes, _, _ = build_variants(raw, sid, "https://cdn.example.com/bucket")
        img = Image.open(io.BytesIO(main_bytes))
        assert img.format == "WEBP"

    def test_variant_keys_follow_convention(self):
        raw = _make_test_image()
        sid = uuid.uuid4()
        _, _, variants_data = build_variants(raw, sid, "https://cdn.example.com/bucket")
        keys = set(variants_data.keys())
        assert f"public/{sid}_thumb.webp" in keys
        assert f"public/{sid}_md.webp" in keys
        assert f"public/{sid}_lg.webp" in keys

    def test_variant_meta_has_correct_fields(self):
        raw = _make_test_image()
        sid = uuid.uuid4()
        _, variants_meta, _ = build_variants(raw, sid, "https://cdn.example.com/bucket")
        for meta in variants_meta:
            assert "size" in meta
            assert "width" in meta
            assert "height" in meta
            assert "url" in meta

    def test_variant_sizes_config(self):
        assert "thumbnail" in VARIANT_SIZES
        assert "medium" in VARIANT_SIZES
        assert "large" in VARIANT_SIZES
        assert VARIANT_SIZES["thumbnail"] == (150, 150)
        assert VARIANT_SIZES["medium"] == (600, 600)
        assert VARIANT_SIZES["large"] == (1200, 1200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd image_backend && uv run pytest tests/unit/modules/storage/application/test_process_image.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# src/modules/storage/application/commands/process_image.py
"""Image processing pipeline — Pillow-based resize/convert to WebP."""

from __future__ import annotations

import io
import uuid

from PIL import Image, Resampling

VARIANT_SIZES: dict[str, tuple[int, int]] = {
    "thumbnail": (150, 150),
    "medium": (600, 600),
    "large": (1200, 1200),
}


def resize_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize preserving aspect ratio to fit within (max_w, max_h)."""
    img.thumbnail((max_w, max_h), Resampling.LANCZOS)
    return img


def convert_to_webp(
    raw_data: bytes,
    *,
    quality: int = 85,
    lossless: bool = False,
    max_size: tuple[int, int] | None = None,
) -> bytes:
    """Convert raw image bytes to WebP format."""
    img = Image.open(io.BytesIO(raw_data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    if max_size:
        img = resize_to_fit(img, *max_size)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, lossless=lossless)
    return buf.getvalue()


def build_variants(
    raw_data: bytes,
    storage_object_id: uuid.UUID,
    public_base_url: str,
) -> tuple[bytes, list[dict], dict[str, bytes]]:
    """Process raw image into main + size variants."""
    main_bytes = convert_to_webp(raw_data, lossless=True)
    variants_meta: list[dict] = []
    variants_data: dict[str, bytes] = {}

    for size_name, (w, h) in VARIANT_SIZES.items():
        variant_bytes = convert_to_webp(raw_data, quality=85, max_size=(w, h))
        img = Image.open(io.BytesIO(variant_bytes))
        suffix = {"thumbnail": "thumb", "medium": "md", "large": "lg"}[size_name]
        s3_key = f"public/{storage_object_id}_{suffix}.webp"
        url = f"{public_base_url.rstrip('/')}/{s3_key}"

        variants_meta.append(
            {
                "size": size_name,
                "width": img.width,
                "height": img.height,
                "url": url,
            }
        )
        variants_data[s3_key] = variant_bytes

    return main_bytes, variants_meta, variants_data
```

- [ ] **Step 4: Run tests**

Run: `cd image_backend && uv run pytest tests/unit/modules/storage/application/test_process_image.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add src/modules/storage/application/commands/process_image.py tests/unit/modules/storage/application/test_process_image.py
git commit -m "feat: add image processing pipeline (resize + WebP) with TDD"
```

---

## Task 14: Presentation — Schemas

**Files:**
- Create: `src/modules/storage/presentation/schemas.py`

- [ ] **Step 1: Write schemas**

```python
# src/modules/storage/presentation/schemas.py
"""ImageBackend API schemas — matches spec contract."""

from __future__ import annotations

import uuid
from datetime import datetime

from src.shared.schemas import CamelModel


class UploadRequest(CamelModel):
    content_type: str
    filename: str | None = None


class UploadResponse(CamelModel):
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int = 300


class ConfirmResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str = "processing"


class MediaVariant(CamelModel):
    size: str
    width: int
    height: int
    url: str


class StatusEventData(CamelModel):
    status: str
    storage_object_id: uuid.UUID
    url: str | None = None
    variants: list[MediaVariant] = []
    error: str | None = None


class ExternalImportRequest(CamelModel):
    url: str


class ExternalImportResponse(CamelModel):
    storage_object_id: uuid.UUID
    url: str
    variants: list[MediaVariant] = []


class MetadataResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str
    url: str | None = None
    content_type: str | None = None
    size_bytes: int = 0
    variants: list[MediaVariant] = []
    created_at: datetime | None = None


class DeleteResponse(CamelModel):
    deleted: bool = True
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/storage/presentation/schemas.py
git commit -m "feat: add API Pydantic schemas"
```

---

## Task 15: Presentation — Router (all 6 endpoints)

**Files:**
- Create: `src/modules/storage/presentation/router.py`

- [ ] **Step 1: Write router with all 6 endpoints**

Implements all endpoints from spec Phase 5.2:

1. `POST /upload` (201) — create `StorageFile`, presigned PUT URL, key `raw/{id}/{filename}`
2. `POST /{id}/confirm` (202) — HEAD check S3, status -> PROCESSING, dispatch `process_image_task.kiq()`
3. `GET /{id}/status` (SSE) — `EventSourceResponse`, initial state from DB, subscribe Redis pub/sub via `SSEManager`
4. `GET /{id}` (200) — metadata + variants from DB
5. `DELETE /{id}` (200) — idempotent, S3 cleanup (raw + main + thumb/md/lg), soft-delete
6. `POST /external` (201) — download (httpx, 30s, max 10 MB), process in thread, upload S3, status=COMPLETED

Key: `media_router = APIRouter(route_class=DishkaRoute)`, dependencies injected via `FromDishka[]`.

See spec Phase 5.2 for detailed logic of each endpoint.

- [ ] **Step 2: Commit**

```bash
git add src/modules/storage/presentation/router.py
git commit -m "feat: add media router with all 6 endpoints"
```

---

## Task 16: Presentation — Background Tasks

**Files:**
- Create: `src/modules/storage/presentation/tasks.py`

- [ ] **Step 1: Write TaskIQ tasks**

Two tasks:

**`process_image_task`**: `@broker.task(task_name="process_image", queue_name="image_processing", retry_on_error=True, max_retries=2, timeout=300)`
Pipeline: download raw -> `build_variants` in `asyncio.to_thread` -> upload main + variants -> delete raw -> update DB (COMPLETED, url, variants) -> publish SSE
Error path: status=FAILED, publish SSE error, re-raise

**`cleanup_orphans_task`**: `@broker.task(task_name="cleanup_orphans", queue_name="maintenance", timeout=600, schedule=[{"cron": "0 */6 * * *"}])`
Logic: find PENDING_UPLOAD older than 24h -> delete S3 objects -> soft-delete in DB

Both use `FromDishka[]` for DI.

See spec Phase 5.3 for full details.

- [ ] **Step 2: Commit**

```bash
git add src/modules/storage/presentation/tasks.py
git commit -m "feat: add background tasks (image processing + orphan cleanup)"
```

---

## Task 17: Presentation — Facade & Dependencies

**Files:**
- Create: `src/modules/storage/presentation/facade.py`, `src/modules/storage/presentation/dependencies.py`

- [ ] **Step 1: Write `facade.py`**

`StorageFacade(IStorageFacade)` — see spec Phase 5.4 for all methods:
- `request_upload`, `request_direct_upload`, `reserve_upload_slot`
- `verify_upload`, `verify_module_upload`
- `register_processed_media`, `update_object_metadata`

- [ ] **Step 2: Write `dependencies.py`**

`StorageProvider(Provider)` — Dishka wiring:
- `S3ClientFactory` (APP scope)
- `AioBaseClient` (REQUEST, from factory)
- `IStorageRepository -> StorageObjectRepository` (REQUEST)
- `IBlobStorage -> S3StorageService` (REQUEST)
- `SSEManager` (APP, from Redis)
- `IStorageFacade -> StorageFacade` (REQUEST)

See spec Phase 5.5 for scope table.

- [ ] **Step 3: Commit**

```bash
git add src/modules/storage/presentation/facade.py src/modules/storage/presentation/dependencies.py
git commit -m "feat: add StorageFacade and Dishka StorageProvider"
```

---

## Task 18: Presentation — API Layer

**Files:**
- Create: `src/api/router.py`, `src/api/dependencies/auth.py`, `src/api/exceptions/handlers.py`, `src/api/middlewares/logger.py`

- [ ] **Step 1: Write `src/api/dependencies/auth.py`**

```python
"""API-key authentication dependency."""

import hmac

import structlog
from fastapi import Header, Query

from src.bootstrap.config import settings
from src.shared.exceptions import UnauthorizedError

logger = structlog.get_logger(__name__)


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key: str | None = Query(None),
) -> None:
    """Validate API key from header or query param (needed for SSE)."""
    key = x_api_key or api_key
    internal_key = settings.INTERNAL_API_KEY.get_secret_value()
    if not internal_key:
        return  # auth disabled in dev

    if not key or not hmac.compare_digest(key, internal_key):
        raise UnauthorizedError(
            message="Invalid API key.",
            error_code="INVALID_API_KEY",
        )
```

- [ ] **Step 2: Write `src/api/exceptions/handlers.py`**

Four handlers + `setup_exception_handlers(app)`:
- `app_exception_handler` — `AppException` -> JSON `{error: {code, message, details}}`
- `validation_exception_handler` — `RequestValidationError` -> 422
- `http_exception_handler` — `StarletteHTTPException` -> JSON envelope
- `unhandled_exception_handler` — `Exception` -> 500

See existing code for exact implementations.

- [ ] **Step 3: Write `src/api/middlewares/logger.py`**

`AccessLoggerMiddleware` — structlog for each request/response with method, path, status, duration.

- [ ] **Step 4: Write `src/api/router.py`**

```python
"""Root API router."""

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import verify_api_key
from src.modules.storage.presentation.router import media_router

router = APIRouter(dependencies=[Depends(verify_api_key)])
router.include_router(media_router, prefix="/media", tags=["Media"])
```

- [ ] **Step 5: Commit**

```bash
git add src/api/
git commit -m "feat: add API layer (auth, exception handlers, access logger, root router)"
```

---

## Task 19: Bootstrap — Config & Logger

**Files:**
- Create: `src/bootstrap/config.py`, `src/bootstrap/logger.py`

- [ ] **Step 1: Write `src/bootstrap/config.py`**

`Settings(BaseSettings)` with all env vars from `.env.example`. Computed fields: `database_url` (postgresql+asyncpg), `redis_url`. Model config: `env_file=".env"`, `extra="ignore"`, `case_sensitive=False`.

Processing constants: `SSE_TIMEOUT=120`, `SSE_HEARTBEAT=15`, `PROCESSING_TIMEOUT=300`, `MAX_FILE_SIZE=50MB`, `PRESIGNED_URL_TTL=300`.

Singleton: `settings = get_settings()` with `@lru_cache`.

See spec Phase 6.1 for full variable table.

- [ ] **Step 2: Write `src/bootstrap/logger.py`**

`setup_logging()` — configures structlog: JSON renderer in prod, colored dev console otherwise. Processors: timestamp (ISO), log level, caller info.

- [ ] **Step 3: Commit**

```bash
git add src/bootstrap/config.py src/bootstrap/logger.py
git commit -m "feat: add Settings config and structlog setup"
```

---

## Task 20: Bootstrap — Broker & Worker

**Files:**
- Create: `src/bootstrap/broker.py`, `src/bootstrap/worker.py`, `src/bootstrap/scheduler.py`

- [ ] **Step 1: Write `src/bootstrap/broker.py`**

```python
"""TaskIQ message broker configuration."""

import structlog
from taskiq_aio_pika import AioPikaBroker

from src.bootstrap.config import settings
from src.infrastructure.logging.taskiq_middleware import LoggingTaskiqMiddleware

logger = structlog.get_logger(__name__)

broker: AioPikaBroker = AioPikaBroker(
    url=str(settings.RABBITMQ_PRIVATE_URL),
    exchange_name="taskiq_rpc_exchange",
    queue_name="taskiq_background_jobs",
    qos=10,
    declare_exchange=True,
    declare_queue=True,
).with_middlewares(LoggingTaskiqMiddleware())
```

- [ ] **Step 2: Write `src/bootstrap/worker.py`**

Critical init order:
1. `container = create_container()` + `setup_dishka(container, broker)`
2. DLQ middleware with separate engine (`pool_size=2`)
3. `import src.modules.storage.presentation.tasks` (registers tasks)
4. `WORKER_STARTUP` / `WORKER_SHUTDOWN` events

See spec Phase 6.5 for exact order.

- [ ] **Step 3: Create empty `src/bootstrap/scheduler.py`**

```python
"""Task scheduler — placeholder for future scheduled tasks."""
```

- [ ] **Step 4: Commit**

```bash
git add src/bootstrap/broker.py src/bootstrap/worker.py src/bootstrap/scheduler.py
git commit -m "feat: add TaskIQ broker config and worker entry point"
```

---

## Task 21: Bootstrap — Container & Web Factory

**Files:**
- Create: `src/bootstrap/container.py`, `src/bootstrap/web.py`
- Modify: `main.py`

- [ ] **Step 1: Write `src/bootstrap/container.py`**

```python
"""Dependency injection container assembly."""

import structlog
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from structlog import BoundLogger

from src.bootstrap.config import Settings, settings
from src.infrastructure.cache.provider import CacheProvider
from src.infrastructure.database.provider import DatabaseProvider
from src.infrastructure.logging.provider import LoggingProvider
from src.modules.storage.presentation.dependencies import StorageProvider
from src.shared.interfaces.config import IStorageConfig

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return settings

    @provide(scope=Scope.APP)
    def get_storage_config(self, s: Settings) -> IStorageConfig:
        return s


def create_container() -> AsyncContainer:
    logger.info("Initialising Dishka IoC container...")
    return make_async_container(
        ConfigProvider(),
        LoggingProvider(),
        DatabaseProvider(),
        CacheProvider(),
        StorageProvider(),
    )
```

- [ ] **Step 2: Write `src/bootstrap/web.py`**

`create_app() -> FastAPI`:
1. `FastAPI(lifespan=lifespan, title, version, docs_url, ...)`
2. CORS middleware if `CORS_ORIGINS` set
3. `AccessLoggerMiddleware`
4. `setup_exception_handlers(app)`
5. `app.include_router(router, prefix=API_V1_STR)`
6. `GET /health -> {"status": "ok", "environment": ...}`
7. `setup_dishka(container, app)`

Lifespan: startup broker (if not worker) -> yield -> shutdown broker -> close container.

See spec Phase 6.6 for exact middleware order.

- [ ] **Step 3: Finalize `main.py`**

```python
from fastapi.applications import FastAPI

from src.bootstrap.web import create_app

app: FastAPI = create_app()
```

- [ ] **Step 4: Commit**

```bash
git add src/bootstrap/container.py src/bootstrap/web.py main.py
git commit -m "feat: add DI container, FastAPI factory, and ASGI entry point"
```

---

## Task 22: Unit Tests — SSE Channel

**Files:**
- Test: `tests/unit/modules/storage/presentation/test_sse.py`

- [ ] **Step 1: Write test**

```python
# tests/unit/modules/storage/presentation/test_sse.py
import uuid

from src.modules.storage.presentation.sse import SSEManager


class TestSSEManagerChannelName:
    def test_channel_name_format(self):
        # SSEManager requires a Redis instance, but channel_name is pure
        # We test with a mock-like approach
        sid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        manager = SSEManager.__new__(SSEManager)
        result = manager.channel_name(sid)
        assert result == "media:status:12345678-1234-5678-1234-567812345678"

    def test_channel_name_unique_per_id(self):
        manager = SSEManager.__new__(SSEManager)
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        assert manager.channel_name(id1) != manager.channel_name(id2)
```

- [ ] **Step 2: Run all tests**

Run: `cd image_backend && uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "feat: add unit tests for SSE channel naming"
```

---

## Task 23: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd image_backend && uv run pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run linter**

Run: `cd image_backend && uv run ruff check src/ tests/`
Expected: No errors (or only ignored rules)

- [ ] **Step 3: Verify all `__init__.py` files exist**

Run: `find image_backend/src -type d -exec sh -c 'test -f "$1/__init__.py" || echo "Missing: $1/__init__.py"' _ {} \;`
Expected: No missing files

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```
