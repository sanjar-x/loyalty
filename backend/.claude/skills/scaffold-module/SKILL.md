---
name: scaffold-module
description: Создание нового DDD-модуля с полной структурой слоёв (domain, application, infrastructure, presentation) по конвенциям проекта
disable-model-invocation: true
---

# Scaffold Module

Создаёт новый bounded-context модуль в `src/modules/` с полной 4-слойной архитектурой, следуя конвенциям проекта.

## Аргументы

Пользователь указывает:

- **Имя модуля** (snake_case, например: `loyalty`, `notification`, `order`)
- **Описание модуля** (что делает bounded context)
- **Основные сущности** (агрегаты, например: `Program`, `Reward`)

Если аргументы не указаны — спроси у пользователя.

## Структура для генерации

Создай следующее дерево файлов в `src/modules/{module_name}/`:

```
{module_name}/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py
│   ├── events.py
│   ├── exceptions.py
│   ├── interfaces.py
│   └── value_objects.py
├── application/
│   ├── __init__.py
│   ├── commands/
│   │   └── __init__.py
│   └── queries/
│       ├── __init__.py
│       └── read_models.py
├── infrastructure/
│   ├── __init__.py
│   ├── models.py
│   └── repositories/
│       ├── __init__.py
│       └── (один файл на сущность)
└── presentation/
    ├── __init__.py
    ├── dependencies.py
    ├── schemas.py
    └── router.py
```

## Шаблоны файлов

### `__init__.py` (корень модуля)

```python
"""{Module description} bounded-context module.

{Expanded description of what this module manages and its role
in the system architecture.}
"""
```

### `domain/entities.py`

```python
"""{Module} domain entities (aggregate roots).

Contains the core business objects for the {module} bounded context.
Uses attrs frozen/define dataclasses — zero infrastructure imports.
"""

import uuid
from datetime import UTC, datetime

import attrs

from src.shared.interfaces.entities import AggregateRoot


@attrs.define
class {Entity}(AggregateRoot):
    """{Entity description}.

    Attributes:
        id: Unique identifier.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last modification.
    """

    id: uuid.UUID
    created_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
```

### `domain/events.py`

```python
"""{Module} domain events.

Domain events for the Transactional Outbox pattern. Each event is a
frozen dataclass inheriting from ``DomainEvent``.
"""

from dataclasses import dataclass

from src.shared.interfaces.entities import DomainEvent


@dataclass(frozen=True)
class {Entity}CreatedEvent(DomainEvent):
    """{Entity} was created."""

    aggregate_type: str = "{module_name}"
    event_type: str = "{entity_lower}_created"
    {entity_lower}_id: str = ""
```

### `domain/exceptions.py`

```python
"""{Module} domain exceptions.

Each exception maps to a specific business-rule violation within the
{Module} bounded context. The presentation layer translates these into
HTTP error responses via the global exception handler.
"""

from src.shared.exceptions import NotFoundError


class {Entity}NotFoundError(NotFoundError):
    """Raised when a {entity_lower} lookup yields no result."""

    def __init__(self, {entity_lower}_id: object):
        super().__init__(
            message=f"{Entity} with id '{{{entity_lower}_id}}' not found.",
            error_code="{ENTITY_UPPER}_NOT_FOUND",
            details={{"{entity_lower}_id": str({entity_lower}_id)}},
        )
```

### `domain/interfaces.py`

```python
"""{Module} repository port interfaces.

Defines abstract repository contracts. The application layer depends
only on these interfaces; concrete implementations live in the
infrastructure layer.
"""

from abc import ABC, abstractmethod
import uuid

from src.modules.{module_name}.domain.entities import {Entity}


class I{Entity}Repository(ABC):
    """Repository contract for {Entity} aggregate."""

    @abstractmethod
    async def get(self, id: uuid.UUID) -> {Entity} | None:
        """Retrieve a {entity_lower} by ID."""

    @abstractmethod
    async def add(self, entity: {Entity}) -> None:
        """Persist a new {entity_lower}."""

    @abstractmethod
    async def update(self, entity: {Entity}) -> None:
        """Update an existing {entity_lower}."""
```

### `domain/value_objects.py`

```python
"""{Module} domain value objects.

Contains immutable types used across the {module} bounded context.
Part of the domain layer — zero infrastructure imports.
"""
```

### `application/queries/read_models.py`

```python
"""{Module} read models (DTOs).

Pydantic models for the CQRS read side. Query handlers return these
directly, bypassing the domain layer for optimal read performance.
"""
```

### `infrastructure/models.py`

```python
"""{Module} SQLAlchemy ORM models.

Maps domain aggregates to database tables. These models are used
exclusively by the infrastructure layer (repositories).
"""

import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class {Entity}Model(Base):
    """ORM model for the {entity_lower} aggregate."""

    __tablename__ = "{table_name}"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

Не забудь `from datetime import datetime` в models.py.

### `infrastructure/repositories/{entity_lower}_repository.py`

```python
"""{Entity} repository implementation.

Concrete SQLAlchemy-based implementation of ``I{Entity}Repository``.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.{module_name}.domain.entities import {Entity}
from src.modules.{module_name}.domain.interfaces import I{Entity}Repository
from src.modules.{module_name}.infrastructure.models import {Entity}Model


class {Entity}Repository(I{Entity}Repository):
    """SQLAlchemy implementation of the {Entity} repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: uuid.UUID) -> {Entity} | None:
        result = await self._session.get({Entity}Model, id)
        if result is None:
            return None
        return self._to_domain(result)

    async def add(self, entity: {Entity}) -> None:
        model = self._to_model(entity)
        self._session.add(model)

    async def update(self, entity: {Entity}) -> None:
        # merge or update as needed
        pass

    @staticmethod
    def _to_domain(model: {Entity}Model) -> {Entity}:
        return {Entity}(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entity: {Entity}) -> {Entity}Model:
        return {Entity}Model(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
```

### `infrastructure/repositories/__init__.py`

```python
"""{Module} repository exports."""

from src.modules.{module_name}.infrastructure.repositories.{entity_lower}_repository import (
    {Entity}Repository,
)

__all__ = ["{Entity}Repository"]
```

### `presentation/dependencies.py`

```python
"""Dishka IoC providers for the {Module} bounded context.

Registers repository implementations and handlers into the
request-scoped DI container.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.{module_name}.domain.interfaces import I{Entity}Repository
from src.modules.{module_name}.infrastructure.repositories import {Entity}Repository


class {Module}Provider(Provider):
    """DI provider for {module} repositories and handlers."""

    {entity_lower}_repo: CompositeDependencySource = provide(
        {Entity}Repository,
        scope=Scope.REQUEST,
        provides=I{Entity}Repository,
    )
```

### `presentation/schemas.py`

```python
"""{Module} Pydantic request/response schemas.

Used by the presentation layer (routers) for API validation
and serialization.
"""
```

### `presentation/router.py`

```python
"""FastAPI router for {Module} endpoints.

Exposes REST API endpoints for the {module} bounded context.
"""

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

{module_lower}_router = APIRouter(
    prefix="/{module_lower}",
    tags=["{Module}"],
    route_class=DishkaRoute,
)
```

## Пост-генерация: интеграция

После создания файлов сообщи пользователю, что для интеграции нужно:

1. **DI-контейнер** — добавить `{Module}Provider` в `src/bootstrap/container.py`:

   ```python
   from src.modules.{module_name}.presentation.dependencies import {Module}Provider
   # и добавить {Module}Provider() в create_container()
   ```

2. **API роутер** — добавить роутер в `src/api/router.py`:

   ```python
   from src.modules.{module_name}.presentation.router import {module_lower}_router
   router.include_router({module_lower}_router)
   ```

3. **Alembic миграция** — после добавления ORM-моделей создать миграцию:
   ```bash
   uv run alembic revision --autogenerate -m "add {module_name} tables"
   ```

Спроси пользователя, хочет ли он, чтобы ты выполнил эти шаги интеграции автоматически.
