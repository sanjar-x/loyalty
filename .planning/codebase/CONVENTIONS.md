# Coding Conventions

**Analysis Date:** 2026-03-29

## Naming Patterns

**Files:**
- Python source: `snake_case.py` everywhere -- `create_brand.py`, `router_brands.py`, `value_objects.py`
- One command per file, named after the action: `create_brand.py`, `update_category.py`, `delete_product.py`
- One query per file, named after the read: `list_brands.py`, `get_category.py`, `get_category_tree.py`
- Routers: prefixed with `router_`: `router_brands.py`, `router_categories.py`
- Domain layer files: `entities.py` (or `entities/` package), `value_objects.py`, `exceptions.py`, `interfaces.py`, `events.py`, `constants.py`
- ORM models: single `models.py` per module infrastructure layer
- Schemas: single `schemas.py` per module presentation layer
- Test files: `test_` prefix: `test_brand.py`, `test_brand_handlers.py`
- Test builders: `{entity}_builder.py` -- `brand_builder.py`, `product_builder.py`
- Test mothers: `{module}_mothers.py` -- `catalog_mothers.py`, `identity_mothers.py`

**Functions:**
- Use `snake_case` for all functions and methods
- Async handlers: `async def handle(self, command: XCommand) -> XResult`
- Factory methods: `Entity.create(...)`, `Entity.create_root(...)`, `Entity.create_child(...)`
- Validators: prefixed with `_validate_`: `_validate_slug()`, `_validate_sort_order()`
- Private helper functions: leading underscore: `_validate_string_rules()`, `_check_nesting_depth()`

**Variables:**
- Use `snake_case` for all variables
- Private attributes: prefixed with `_`: `self._brand_repo`, `self._uow`, `self._logger`
- Constants: `UPPER_SNAKE_CASE`: `MAX_CATEGORY_DEPTH`, `DEFAULT_CURRENCY`, `REQUIRED_LOCALES`
- ClassVar guarded fields: `_BRAND_GUARDED_FIELDS`, `_UPDATABLE_FIELDS`

**Types:**
- Domain entities: bare `PascalCase`: `Brand`, `Category`, `Product`, `SKU`
- Value objects: descriptive `PascalCase`: `Money`, `BehaviorFlags`, `ProductStatus`
- Exceptions: suffixed with `Error`: `BrandNotFoundError`, `CategoryMaxDepthError`
- Repository interfaces: prefixed with `I`: `IBrandRepository`, `ICategoryRepository`
- Generic base: `ICatalogRepository[T]`
- Commands: suffixed with `Command`: `CreateBrandCommand`, `UpdateCategoryCommand`
- Handlers: suffixed with `Handler`: `CreateBrandHandler`, `ListBrandsHandler`
- Results: suffixed with `Result`: `CreateBrandResult`, `UpdateBrandResult`
- Events: suffixed with `Event`: `BrandCreatedEvent`, `ProductStatusChangedEvent`
- Read models: suffixed with `ReadModel`: `BrandReadModel`, `BrandListReadModel`
- Pydantic schemas: suffixed with `Request`/`Response`: `BrandCreateRequest`, `BrandResponse`
- ORM factories (tests): suffixed with `ModelFactory`: `BrandModelFactory`
- Object Mothers (tests): suffixed with `Mothers`: `IdentityMothers`, `CategoryMothers`
- Test builders (tests): suffixed with `Builder`: `BrandBuilder`, `ProductBuilder`
- Domain enums: `StrEnum` with lowercase string values: `ProductStatus.DRAFT = "draft"`

## Code Style

**Formatting:**
- Ruff as formatter and linter (replaces Black + isort + flake8)
- Line length: 88 characters
- Target Python version: 3.14
- Config in `backend/pyproject.toml`

**Linting:**
- Ruff rule selection: `["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`
- Suppressed rules: `["E501", "RUF001", "RUF002", "RUF003", "B008", "UP042", "UP046"]`
  - `E501`: Long lines allowed (Ruff formatter handles wrapping)
  - `RUF001/2/3`: Unicode chars permitted (Russian text in i18n)
  - `B008`: `Depends()` in function signatures is fine (FastAPI pattern)
  - `UP042/UP046`: PEP 695 type syntax not enforced yet

**Type Checking:**
- mypy with `disallow_untyped_defs = true` for production code
- `disallow_untyped_defs = false` for tests (relaxed)
- `pydantic.mypy` plugin enabled
- `warn_return_any = true`, `warn_unused_configs = true`
- Config in `backend/pyproject.toml` `[tool.mypy]`

## Import Organization

**Order:**
1. Standard library imports (`uuid`, `datetime`, `typing`, `dataclasses`)
2. Third-party imports (`attrs`, `sqlalchemy`, `fastapi`, `pydantic`, `pytest`)
3. First-party imports (`from src.modules...`, `from src.shared...`)

**Path Aliases:**
- No aliases. All imports use full paths from `src.` root:
  ```python
  from src.modules.catalog.domain.entities import Brand
  from src.modules.catalog.domain.exceptions import BrandNotFoundError
  from src.shared.interfaces.uow import IUnitOfWork
  ```
- Tests import from `tests.` root:
  ```python
  from tests.factories.brand_builder import BrandBuilder
  from tests.fakes.fake_uow import FakeUnitOfWork
  ```
- isort `known-first-party = ["src"]`

## Error Handling

**Exception Hierarchy:**
- All expected errors inherit from `AppException` (`backend/src/shared/exceptions.py`)
- Base `AppException` carries: `message: str`, `status_code: int`, `error_code: str`, `details: dict`
- HTTP-mapped subclasses:
  - `NotFoundError` (404)
  - `UnauthorizedError` (401)
  - `ForbiddenError` (403)
  - `ConflictError` (409)
  - `ValidationError` (400)
  - `UnprocessableEntityError` (422)

**Domain Exceptions:**
- Module-specific exceptions inherit from the appropriate HTTP base
- Naming: `{Entity}{Issue}Error` -- e.g., `BrandNotFoundError`, `CategoryMaxDepthError`
- Constructor always passes `message`, `error_code`, and `details` to super()
- `error_code` is `UPPER_SNAKE_CASE`: `"CATEGORY_NOT_FOUND"`, `"BRAND_SLUG_CONFLICT"`
- `details` contains relevant entity IDs as strings
- Location: `backend/src/modules/{module}/domain/exceptions.py`

**Exception example pattern:**
```python
class BrandNotFoundError(NotFoundError):
    def __init__(self, brand_id: uuid.UUID | str):
        super().__init__(
            message=f"Brand with ID {brand_id} not found.",
            error_code="BRAND_NOT_FOUND",
            details={"brand_id": str(brand_id)},
        )
```

**Global Exception Handlers:**
- Centralized in `backend/src/api/exceptions/handlers.py`
- Uniform JSON envelope: `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}`
- `AppException` -> mapped to its `status_code`
- `RequestValidationError` -> 422 with per-field error details
- `StarletteHTTPException` -> wrapped in uniform envelope
- Unhandled `Exception` -> 500 with generic message, full traceback logged

**Domain Validation:**
- Domain entities validate in `create()` factory methods and `update()` methods
- Raise `ValueError` for invariant violations (caught by global handler as 422/500)
- Raise specific domain exceptions for business rule violations
- Use `__setattr__` guard pattern (DDD-01) to prevent direct mutation of guarded fields:
  ```python
  _BRAND_GUARDED_FIELDS: frozenset[str] = frozenset({"slug"})

  def __setattr__(self, name: str, value: object) -> None:
      if name in _BRAND_GUARDED_FIELDS and getattr(self, "_Brand__initialized", False):
          raise AttributeError(f"Cannot set '{name}' directly on Brand.")
      super().__setattr__(name, value)
  ```

## Logging

**Framework:** structlog with contextvars for request-scoped fields

**Patterns:**
- Bind handler name at construction: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Log after successful operations: `self._logger.info("Brand created", brand_id=str(brand.id))`
- Use structured key-value pairs, not string interpolation
- Log levels: `info` for success, `warning` for client errors (4xx), `error` for server errors (5xx)
- ILogger protocol at `backend/src/shared/interfaces/logger.py`

## Comments

**When to Comment:**
- Module-level docstrings on every Python file explaining purpose and layer placement
- Class-level docstrings with Attributes section listing all fields
- Method-level docstrings with Args/Returns/Raises sections (Google style)
- Inline comments for DDD pattern markers: `# DDD-01: guard slug against direct mutation`
- Architecture decision markers: `# ARCH-03: Domain enums moved from infrastructure`
- Quality markers: `# QUAL-01: BehaviorFlags value object`

**Docstring Example:**
```python
"""
Command handler: create a new brand.

Validates slug uniqueness, persists the Brand aggregate, and optionally
stores a logo URL and storage object reference. Part of the application
layer (CQRS write side).
"""
```

## Function Design

**Command Handlers:**
- One public method: `async def handle(self, command: XCommand) -> XResult`
- Dependencies injected via `__init__` and stored as `_private_attrs`
- Return a frozen dataclass result (not the entity itself)
- Wrap mutations in `async with self._uow:` context manager
- Call `self._uow.register_aggregate(entity)` before commit
- Log after successful operations (outside the UoW context)

**Query Handlers:**
- One public method: `async def handle(self, query: XQuery) -> ReadModel`
- Inject `AsyncSession` directly (CQRS read side skips UoW/repositories)
- Return Pydantic read models, not domain entities

**Entity Factory Methods:**
- `@classmethod def create(cls, *, keyword_only_args) -> Self`
- Validate all invariants before constructing
- Generate UUIDs internally (uuid7 preferred, uuid4 fallback)

**Entity Update Methods:**
- `_UPDATABLE_FIELDS: ClassVar[frozenset[str]]` whitelist on entities
- `update(**kwargs)` rejects unknown fields via `TypeError`
- Uses `...` (Ellipsis) sentinel for "keep current" on nullable fields
- Pattern for nullable with keep-current:
  ```python
  def update(self, logo_url: str | None = ...) -> None:
      if logo_url is not ...:
          self.logo_url = logo_url
  ```

## Module Design

**Exports:**
- No barrel `__init__.py` re-exports in production code (most `__init__.py` files are empty)
- Each file exports its own classes/functions directly
- Exception: `backend/src/modules/catalog/domain/entities/__init__.py` re-exports all entity classes from submodules
- Tests use `__init__.py` as empty markers for pytest discovery

**Pydantic Schemas:**
- All schemas inherit from `CamelModel` (`backend/src/shared/schemas.py`)
- `CamelModel` auto-converts `snake_case` Python fields to `camelCase` JSON
- Request schemas: `BrandCreateRequest`, `BrandUpdateRequest`
- Response schemas: `BrandResponse`, `BrandListResponse`
- Generic pagination: `PaginatedResponse[S]`
- i18n fields validated with custom `I18nDict` annotated type
- JSON bomb protection with `BoundedJsonDict` (10 KB size, depth 4 limit)

**Routers:**
- Each router file defines one `APIRouter` with prefix and tags
- Uses `DishkaRoute` for automatic DI injection
- `FromDishka[HandlerType]` for handler injection in endpoint params
- Permission checks via `Depends(RequirePermission(codename="catalog:manage"))`
- Mutating endpoints: POST (201), PATCH (200), DELETE (204)
- Read endpoints: GET (200) with `Cache-Control: no-store` header

**Dependency Injection:**
- Dishka as the DI framework
- Each module has a `dependencies.py` (presentation layer) or `provider.py` (infrastructure layer) with Dishka Provider classes
- Scopes: `APP` for singletons (engine, redis), `REQUEST` for per-request (session, handlers)

## Domain Enums

- Use `StrEnum` for all domain enums (enables string-based DB mapping without translation)
- Values are lowercase strings: `ProductStatus.DRAFT = "draft"`, `AttributeDataType.STRING = "string"`
- Location: `backend/src/modules/catalog/domain/value_objects.py`

## Value Objects

- Use `@frozen` from `attrs` for immutable value objects: `Money`, `BehaviorFlags`
- Validation in `__attrs_post_init__()` (read-only; no assignment)
- Comparison operators defined manually when ordering matters (e.g., `Money.__lt__`)
- Currency mismatch raises `ValueError` on comparison

## i18n Conventions

- Required locales: `{"ru", "en"}` -- enforced at both domain and schema level
- i18n fields are `dict[str, str]` with ISO 639-1 two-letter lowercase keys
- Domain validation: `validate_i18n_completeness()` in `backend/src/modules/catalog/domain/value_objects.py`
- Schema validation: `I18nDict` annotated type in `backend/src/modules/catalog/presentation/schemas.py`
- Max 20 language entries, max 10,000 chars per value

---

*Convention analysis: 2026-03-29*
