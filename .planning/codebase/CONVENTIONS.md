# Coding Conventions

**Analysis Date:** 2026-03-28

## Project Structure

The codebase is a **Python 3.14 monorepo** with three service boundaries:
- **backend/** -- Main API (FastAPI + CQRS + Clean Architecture)
- **image_backend/** -- Image processing microservice (same stack, smaller scope)
- **frontend/** -- Two Next.js apps (`frontend/main`, `frontend/admin`)

This document covers the **backend/** and **image_backend/** Python services. Frontend conventions are not yet codified.

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python files
- One command handler per file, named after the action: `create_brand.py`, `delete_category.py`, `update_product.py`
- One query handler per file: `list_brands.py`, `get_brand.py`, `list_categories.py`
- Router files prefixed with `router_`: `router_auth.py`, `router_brands.py`, `router_products.py`
- ORM models collected in a single `models.py` per module: `backend/src/modules/catalog/infrastructure/models.py`
- Domain entities collected in `entities.py`, value objects in `value_objects.py`, exceptions in `exceptions.py`

**Classes:**
- Domain entities: PascalCase attrs `@dataclass` -- `Identity`, `Session`, `Brand`, `Category`
- Aggregate roots extend `AggregateRoot` mixin: `class Identity(AggregateRoot):`
- Command DTOs: `@dataclass(frozen=True)` with `Command` suffix -- `CreateBrandCommand`, `LoginCommand`
- Result DTOs: `@dataclass(frozen=True)` with `Result` suffix -- `CreateBrandResult`, `LoginResult`
- Query DTOs: `@dataclass(frozen=True)` with `Query` suffix -- `ListBrandsQuery`
- Handlers: PascalCase with `Handler` suffix -- `CreateBrandHandler`, `ListBrandsHandler`
- Repositories: `I` prefix for interface (ABC), no prefix for implementation -- `IBrandRepository` / `BrandRepository`
- ORM models: PascalCase matching domain entity name, in separate `models.py` -- `Brand`, `Category`, `IdentityModel`
- Pydantic schemas: PascalCase with `Request`/`Response` suffix -- `LoginRequest`, `TokenResponse`, `RegisterResponse`
- DI Providers: PascalCase with `Provider` suffix -- `BrandProvider`, `IdentityProvider`, `CacheProvider`
- Exceptions: PascalCase with `Error` suffix -- `NotFoundError`, `BrandSlugConflictError`

**Functions/Methods:**
- Use `snake_case` for all functions and methods
- Command/query handler entry point is always `async def handle(self, command/query) -> ResultType:`
- Repository methods: `add`, `get`, `update`, `delete`, `check_slug_exists`, `get_by_email`, `get_for_update`
- Factory classmethods on entities: `Brand.create(...)`, `Session.create(...)`, `Identity.register(...)`
- Domain mutation methods: `identity.deactivate(reason=...)`, `session.revoke()`, `session.rotate_refresh_token(...)`
- Validation guard methods: `identity.ensure_active()`, `session.ensure_valid()`

**Variables:**
- Use `snake_case` for all variables
- Private instance attributes prefixed with `_`: `self._session`, `self._brand_repo`, `self._uow`
- Constants: `UPPER_SNAKE_CASE` -- `GENERAL_GROUP_CODE`, `DEFAULT_CURRENCY`, `MAX_SEARCH_WEIGHT`

**Enumerations:**
- Use `enum.StrEnum` for all enums (Python 3.11+): `ProductStatus`, `IdentityType`, `AccountType`
- Enum values are `UPPER_CASE` strings matching their name: `LOCAL = "LOCAL"`, `CUSTOMER = "CUSTOMER"`

## Code Style

**Formatting:**
- Tool: **Ruff** (formatter + linter combined)
- Line length: 88 characters (Black-compatible default)
- Target: Python 3.14
- Config: `backend/pyproject.toml` `[tool.ruff]` section

**Linting:**
- Tool: **Ruff** with rules: `E, F, W, I, UP, B, SIM, RUF`
- Ignored rules: `E501` (line length handled by formatter), `RUF001/2/3` (Cyrillic text allowed), `B008` (function calls in defaults for FastAPI Depends), `UP042/UP046`
- Import sorting: isort-compatible, `known-first-party = ["src"]`
- Config: `backend/pyproject.toml` `[tool.ruff.lint]`

**Type Checking:**
- Tool: **mypy** with `disallow_untyped_defs = true` and `warn_return_any = true`
- Plugin: `pydantic.mypy`
- Tests exempt from `disallow_untyped_defs` via `[[tool.mypy.overrides]]`
- Config: `backend/pyproject.toml` `[tool.mypy]`

## Import Organization

**Order (enforced by Ruff isort):**
1. Standard library (`uuid`, `datetime`, `dataclasses`, `hashlib`, `enum`)
2. Third-party packages (`fastapi`, `sqlalchemy`, `attrs`, `dishka`, `structlog`, `pydantic`)
3. First-party (`src.*`)
4. Local (`tests.*`)

**Path style:**
- Always use absolute imports from `src`: `from src.modules.catalog.domain.entities import Brand`
- Never use relative imports
- No path aliases configured

**Example (from `backend/src/modules/identity/application/commands/login.py`):**
```python
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import Session
from src.modules.identity.domain.exceptions import (
    InvalidCredentialsError,
    MaxSessionsExceededError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork
```

## Error Handling

**Exception Hierarchy:**
All expected errors inherit from `AppException` in `backend/src/shared/exceptions.py`:
```
AppException (base, 500)
  +-- NotFoundError (404)
  +-- UnauthorizedError (401)
  +-- ForbiddenError (403)
  +-- ConflictError (409)
  +-- ValidationError (400)
  +-- UnprocessableEntityError (422)
```

**Module-Specific Exceptions:**
Each module defines its own exceptions extending the shared hierarchy in `domain/exceptions.py`:
```python
# backend/src/modules/identity/domain/exceptions.py
class InvalidCredentialsError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )
```

**Convention: Every exception has a machine-readable `error_code`.**
- Error codes are `UPPER_SNAKE_CASE` strings: `"INVALID_CREDENTIALS"`, `"BRAND_SLUG_CONFLICT"`, `"SESSION_EXPIRED"`
- Error codes MUST be unique across the codebase
- Always provide `message`, `error_code`; optionally `details` dict

**Global Exception Handler:**
All exceptions are caught and serialized to a uniform JSON envelope in `backend/src/api/exceptions/handlers.py`:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid-hex"
  }
}
```

**UnitOfWork catches `IntegrityError`:**
- `sqlstate 23503` (FK violation) -> `UnprocessableEntityError`
- Other integrity errors -> `ConflictError`
- Defined in `backend/src/infrastructure/database/uow.py`

**Pattern: Guard methods on domain entities raise exceptions.**
```python
# backend/src/modules/identity/domain/entities.py
def ensure_active(self) -> None:
    if not self.is_active:
        raise IdentityDeactivatedError()
```

## Logging

**Framework:** structlog (wrapped behind `ILogger` protocol)

**Protocol:** `backend/src/shared/interfaces/logger.py` -- `ILogger` with `bind()`, `debug()`, `info()`, `warning()`, `error()`, `critical()`, `exception()`

**Pattern: Bind handler context on construction:**
```python
def __init__(self, ..., logger: ILogger) -> None:
    self._logger = logger.bind(handler="CreateBrandHandler")
```

**Structured event strings use dot-notation:**
```python
self._logger.info("identity.login.success", identity_id=str(identity.id), ip=command.ip_address)
self._logger.warning("identity.login.failed", login=command.login, reason="invalid_credentials")
self._logger.info("Brand created", brand_id=str(brand.id))
```

**Always stringify UUIDs** when passing to log fields: `identity_id=str(identity.id)`

## Comments

**Module-level docstrings are mandatory.** Every `.py` file starts with a triple-quoted docstring explaining purpose.

**Class and method docstrings follow Google-style format** with `Args:`, `Returns:`, `Raises:` sections:
```python
def handle(self, command: LoginCommand) -> LoginResult:
    """Execute the login command.

    Args:
        command: The login command with credentials and client info.

    Returns:
        A result containing access and refresh tokens.

    Raises:
        InvalidCredentialsError: If email is not found or password is wrong.
    """
```

**Section separators** use commented lines:
```python
# ---------------------------------------------------------------------------
# Authentication schemas
# ---------------------------------------------------------------------------
```

## Domain Entity Design

**Use attrs `@dataclass` (NOT stdlib dataclasses) for domain entities:**
```python
from attr import dataclass
from src.shared.interfaces.entities import AggregateRoot

@dataclass
class Brand(AggregateRoot):
    id: uuid.UUID
    name: str
    slug: str
```

**Use stdlib `@dataclass(frozen=True)` for Commands, Queries, Results, and Events.**

**Use Pydantic `BaseModel` (via `CamelModel`) only in the presentation layer for API schemas.**

**Use `enum.StrEnum` for value objects that are simple enumerations.**

**Use stdlib `@dataclass(frozen=True, slots=True)` for immutable value objects:**
```python
# backend/src/modules/identity/domain/value_objects.py
@dataclass(frozen=True, slots=True)
class TelegramUserData:
    telegram_id: int
    first_name: str
    ...
```

## Presentation Layer (API Schemas)

**All schemas inherit from `CamelModel`** (`backend/src/shared/schemas.py`) -- automatic `snake_case` -> `camelCase` alias generation:
```python
from src.shared.schemas import CamelModel

class TokenResponse(CamelModel):
    access_token: str   # serialized as "accessToken"
    refresh_token: str  # serialized as "refreshToken"
```

**Use `Field(...)` for validation constraints:**
```python
password: str = Field(..., min_length=8, max_length=128)
name: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z_]+$")
```

**Use `model_validator(mode="after")` for cross-field validation:**
```python
@model_validator(mode="after")
def at_least_one_field(self) -> Self:
    if self.name is None and self.description is None:
        raise ValueError("At least one field must be provided")
    return self
```

## Router (Presentation) Pattern

**Use Dishka for DI, NOT FastAPI Depends:**
```python
from dishka.integrations.fastapi import DishkaRoute, FromDishka

router = APIRouter(prefix="/brands", tags=["Brands"], route_class=DishkaRoute)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_brand(
    body: CreateBrandRequest,
    handler: FromDishka[CreateBrandHandler],
) -> CreateBrandResponse:
```

**Router files are thin** -- map HTTP request to Command/Query, call `handler.handle(...)`, map result to Response schema. No business logic.

## CQRS Conventions

**Commands (write side):**
- Handler depends on repository interfaces (`IBrandRepository`), `IUnitOfWork`, `ILogger`
- Always wrap mutations in `async with self._uow:` block
- Call `self._uow.register_aggregate(entity)` before `await self._uow.commit()` to persist domain events
- File location: `backend/src/modules/{module}/application/commands/{action}.py`

**Queries (read side):**
- Handler depends on `AsyncSession` (raw SQLAlchemy) and `ILogger` directly -- NO repository, NO UoW
- Queries ORM models directly for read-side performance
- Returns Pydantic read models (not domain entities)
- File location: `backend/src/modules/{module}/application/queries/{action}.py`

## Dependency Injection

**Framework:** Dishka (async-first Python DI container)

**Provider pattern:** One `Provider` class per feature area, registered in `backend/src/bootstrap/container.py`:
```python
class BrandProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def brand_repo(self, session: AsyncSession) -> IBrandRepository:
        return BrandRepository(session=session)

    create_brand_handler = provide(CreateBrandHandler, scope=Scope.REQUEST)
```

**Scopes:** `Scope.APP` for singletons (engine, redis, settings), `Scope.REQUEST` for per-request (session, handlers, repos)

## Data Mapper Pattern

Repositories translate between domain entities and ORM models using explicit `_to_domain()` and `_to_orm()` methods. Domain entities NEVER touch SQLAlchemy.

**Base repository** at `backend/src/modules/catalog/infrastructure/repositories/base.py` provides generic CRUD:
```python
class BaseRepository[EntityType, ModelType: IBase](ICatalogRepository[EntityType]):
    model: type[ModelType]

    @abstractmethod
    def _to_domain(self, orm: ModelType) -> EntityType: ...

    @abstractmethod
    def _to_orm(self, entity: EntityType, orm: ModelType | None = None) -> ModelType: ...
```

## Domain Event Pattern

**Events are stdlib `@dataclass` extending `DomainEvent`** (`backend/src/shared/interfaces/entities.py`):
- Must override `aggregate_type` and `event_type` with non-empty defaults (enforced at class definition time)
- Events accumulate on `AggregateRoot._domain_events` via `add_domain_event()`
- `UnitOfWork.commit()` flushes events to the `outbox_messages` table atomically (Transactional Outbox)

---

*Convention analysis: 2026-03-28*
