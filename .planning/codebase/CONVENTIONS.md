# Coding Conventions

**Analysis Date:** 2026-03-28

## Project Structure

The codebase is a multi-service monorepo with three main subsystems:
- **backend/** -- Main API (Python, FastAPI, Clean Architecture + CQRS)
- **image_backend/** -- Image processing microservice (same stack, same conventions)
- **frontend/admin/** -- Admin panel (Next.js 16, React 19, JSX, no TypeScript)
- **frontend/main/** -- Customer-facing Telegram Mini App (Next.js 16, React 19, TypeScript)

## Naming Patterns

### Python (backend, image_backend)

**Files:**
- Use `snake_case.py` for all Python files
- Domain layer: `entities.py`, `value_objects.py`, `exceptions.py`, `interfaces.py`, `events.py`, `constants.py`
- Commands: one command per file, named after the action: `create_brand.py`, `update_category.py`, `delete_product.py`
- Queries: one query per file, named after the read: `list_brands.py`, `get_category.py`, `get_category_tree.py`
- Repositories: named after the aggregate: `brand.py`, `category.py`, `product.py`
- Routers: prefixed with `router_`: `router_brands.py`, `router_categories.py`, `router_storefront.py`
- ORM models: `models.py` (single file per module's infrastructure layer)
- Schemas: `schemas.py` (single file per module's presentation layer)

**Functions:**
- Use `snake_case` for all functions and methods
- Async functions: `async def handle(...)`, `async def get(...)`, `async def add(...)`
- Validators: prefixed with `_validate_`: `_validate_slug()`, `_validate_sort_order()`
- Factory methods on entities: `Entity.create(...)`, `Entity.create_root(...)`, `Entity.create_child(...)`

**Variables:**
- Use `snake_case` for all variables
- Private attributes: prefixed with `_`: `self._brand_repo`, `self._uow`, `self._logger`
- Constants: `UPPER_SNAKE_CASE`: `MAX_CATEGORY_DEPTH`, `GENERAL_GROUP_CODE`, `DEFAULT_CURRENCY`
- ClassVar guarded fields: `_PRODUCT_GUARDED_FIELDS`, `_UPDATABLE_FIELDS`

**Types / Classes:**
- Use `PascalCase` for all classes
- Domain entities: bare names: `Brand`, `Category`, `Product`, `SKU`
- Value objects: descriptive names: `Money`, `BehaviorFlags`, `ProductStatus`
- Exceptions: suffixed with `Error`: `BrandNotFoundError`, `CategoryMaxDepthError`, `InvalidStatusTransitionError`
- Repository interfaces: prefixed with `I`: `IBrandRepository`, `ICategoryRepository`, `IProductRepository`
- Generic base: `ICatalogRepository[T]`
- Commands: suffixed with `Command`: `CreateBrandCommand`, `UpdateCategoryCommand`
- Handlers: suffixed with `Handler`: `CreateBrandHandler`, `ListBrandsHandler`
- Results: suffixed with `Result`: `CreateBrandResult`, `UpdateBrandResult`
- Events: suffixed with `Event`: `BrandCreatedEvent`, `ProductStatusChangedEvent`
- Read models: suffixed with `ReadModel`: `BrandReadModel`, `BrandListReadModel`
- Pydantic schemas: suffixed with `Request`/`Response`: `BrandCreateRequest`, `BrandResponse`
- ORM factories (tests): suffixed with `ModelFactory`: `BrandModelFactory`
- Object Mothers (tests): suffixed with `Mothers`: `IdentityMothers`, `CategoryMothers`
- Test builders (tests): suffixed with `Builder`: `RoleBuilder`, `SessionBuilder`, `CategoryBuilder`

**Enums:**
- Use `StrEnum` for all domain enums (enables string-based DB mapping without translation)
- Values are lowercase strings: `ProductStatus.DRAFT = "draft"`, `AttributeDataType.STRING = "string"`

### JavaScript/TypeScript (frontend)

**Files:**
- React components: `PascalCase.jsx` -- `Modal.jsx`, `Badge.jsx`, `ProductRow.jsx`
- Non-component files: `camelCase.js` / `kebab-case.js` -- `api-client.js`, `dayjs.js`
- Next.js route files: `route.js`, `page.jsx`, `layout.jsx`, `loading.jsx`, `error.jsx`
- Hooks: `use` prefix: `useAuth.jsx`, `useBodyScrollLock.js`
- Frontend/main (TypeScript): `kebab-case.ts` -- `cookie-helpers.ts`, `brand-image.ts`

**Functions:**
- React components: `PascalCase` -- `export function Modal({ open, onClose, ... })`
- Hooks: `camelCase` with `use` prefix -- `useAuth()`, `useBodyScrollLock()`
- Utility functions: `camelCase` -- `backendFetch()`, `formatPrice()`

**Variables:**
- `camelCase` for local variables and props
- `UPPER_SNAKE_CASE` for constants: `BACKEND_URL`

## Code Style

**Formatting (Python):**
- Ruff as formatter and linter (replaces Black + isort + flake8)
- Line length: 88 characters
- Target Python version: 3.14
- Config in `backend/pyproject.toml` and `image_backend/pyproject.toml`

**Linting (Python):**
- Ruff rules: `["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]`
- Suppressed rules: `["E501", "RUF001", "RUF002", "RUF003", "B008", "UP042", "UP046"]` (long lines, unicode chars, `Depends()` in signatures, PEP 695 types)
- isort first-party: `["src"]`

**Type Checking (Python):**
- mypy with `disallow_untyped_defs = true` for production code
- `disallow_untyped_defs = false` for tests (relaxed)
- `pydantic.mypy` plugin enabled
- Config in `backend/pyproject.toml` `[tool.mypy]`

**Formatting (Frontend):**
- Admin panel: Prettier with `prettier-plugin-tailwindcss`
- ESLint with `eslint-config-next`

## Import Organization

### Python

**Order:**
1. Standard library imports
2. Third-party imports (FastAPI, SQLAlchemy, attrs, etc.)
3. First-party imports from `src.*`
4. Test-only imports from `tests.*`

**Path Aliases:**
- No aliases. All imports use full paths from `src.` root: `from src.modules.catalog.domain.entities import Brand`
- Tests import from `tests.factories.*`: `from tests.factories.identity_mothers import IdentityMothers`

**Ruff isort config enforces first-party detection:**
```toml
[tool.ruff.lint.isort]
known-first-party = ["src"]
```

### JavaScript/TypeScript

**Pattern:**
- `'use client'` directive at top when needed
- React imports first
- Third-party libraries second
- Local imports (`@/`, `../`) last

## Error Handling

### Domain Exception Hierarchy

All expected errors extend a shared base class hierarchy defined in `backend/src/shared/exceptions.py`:

```python
AppException (base)
├── NotFoundError        (404)
├── UnauthorizedError    (401)
├── ForbiddenError       (403)
├── ConflictError        (409)
├── ValidationError      (400)
└── UnprocessableEntityError (422)
```

**Convention:** Each domain module defines concrete exceptions that extend these bases.
- Name: `{Entity}{Issue}Error` -- e.g., `BrandNotFoundError`, `CategoryMaxDepthError`
- Constructor: Always pass `message`, `error_code`, and `details` to super()
- `error_code`: `UPPER_SNAKE_CASE` string constant -- e.g., `"CATEGORY_NOT_FOUND"`, `"BRAND_SLUG_CONFLICT"`
- `details`: dict with relevant entity IDs as strings

Example pattern from `backend/src/modules/catalog/domain/exceptions.py`:

```python
class BrandNotFoundError(NotFoundError):
    def __init__(self, brand_id: uuid.UUID | str):
        super().__init__(
            message=f"Brand with ID {brand_id} not found.",
            error_code="BRAND_NOT_FOUND",
            details={"brand_id": str(brand_id)},
        )
```

### Global Exception Handler

Registered in `backend/src/api/exceptions/handlers.py`. Converts all `AppException` subclasses into a uniform JSON envelope:

```json
{
  "error": {
    "code": "BRAND_NOT_FOUND",
    "message": "Brand with ID ... not found.",
    "details": {"brand_id": "..."},
    "request_id": "..."
  }
}
```

### Domain Validation

- Domain entities validate in `create()` factory methods and `update()` methods
- Raise `ValueError` for invariant violations (caught by global handler as 422/500)
- Raise specific domain exceptions (e.g., `CategoryMaxDepthError`) for business rule violations
- Use `__setattr__` guard pattern (DDD-01) to prevent direct mutation of guarded fields:

```python
_PRODUCT_GUARDED_FIELDS: frozenset[str] = frozenset({"status"})

def __setattr__(self, name: str, value: object) -> None:
    if name in _PRODUCT_GUARDED_FIELDS and getattr(self, "_Product__initialized", False):
        raise AttributeError("Cannot set 'status' directly. Use transition_status().")
    super().__setattr__(name, value)
```

### Command Handler Error Flow

1. Handler validates preconditions (slug uniqueness, entity existence) via repository calls
2. Delegates business logic to domain entity factory/methods (which raise `ValueError` or domain exceptions)
3. Persists via repository, registers aggregate for outbox events, commits via UoW

```python
async with self._uow:
    if await self._brand_repo.check_slug_exists(command.slug):
        raise BrandSlugConflictError(slug=command.slug)
    brand = Brand.create(name=command.name, slug=command.slug)
    brand = await self._brand_repo.add(brand)
    brand.add_domain_event(BrandCreatedEvent(...))
    self._uow.register_aggregate(brand)
    await self._uow.commit()
```

## Logging

**Framework:** structlog (structured JSON logging)

**Port pattern:** Application code depends on `ILogger` protocol (`backend/src/shared/interfaces/logger.py`), not structlog directly. Concrete structlog adapter injected via Dishka DI.

**Patterns:**
- Bind handler name at construction: `self._logger = logger.bind(handler="CreateBrandHandler")`
- Log after successful operations: `self._logger.info("Brand created", brand_id=str(brand.id))`
- Use structured key-value pairs, not string interpolation
- Log levels: `info` for success, `warning` for client errors (4xx), `error` for server errors (5xx)

## Comments

**When to Comment:**
- Module-level docstrings on every Python file explaining purpose and layer placement
- Class-level docstrings with Attributes section listing all fields
- Method-level docstrings with Args/Returns/Raises sections (Google style)
- Inline comments for DDD pattern markers: `# DDD-01: guard slug against direct mutation`
- Architecture decision markers: `# ARCH-03: Domain enums moved from infrastructure`

**Docstring Style:**
```python
def transition_status(self, new_status: ProductStatus) -> None:
    """Transition the product to a new lifecycle status.

    Validates the transition against the FSM table defined in
    ``_ALLOWED_TRANSITIONS``.

    Args:
        new_status: The target ProductStatus value.

    Raises:
        InvalidStatusTransitionError: If transition is not allowed.
    """
```

## Function Design

**Command handlers:**
- One public method: `async def handle(self, command: XCommand) -> XResult`
- Dependencies injected via `__init__` and stored as `_private_attrs`
- Return a frozen dataclass result (not the entity itself)

**Query handlers:**
- One public method: `async def handle(self, query: XQuery) -> ReadModel`
- Inject `AsyncSession` directly (CQRS read side skips UoW/repositories)
- Return Pydantic read models, not domain entities

**Domain entity factory methods:**
- `@classmethod def create(cls, *, keyword_only_args) -> Self`
- Validate all invariants before constructing
- Generate UUIDs internally (uuid7 preferred, uuid4 fallback)

**Partial update pattern:**
- `_UPDATABLE_FIELDS: ClassVar[frozenset[str]]` whitelist on entities
- `update(**kwargs)` rejects unknown fields via `TypeError`
- Uses `...` (Ellipsis) sentinel for "keep current" on nullable fields

## Module Design

**Exports:**
- No barrel `__init__.py` re-exports in production code (most `__init__.py` files are empty)
- Each file exports its own classes/functions directly
- Tests use `__init__.py` as empty markers for pytest discovery

**API Schema Convention:**
- All Pydantic schemas inherit from `CamelModel` (`backend/src/shared/schemas.py`)
- `CamelModel` auto-converts `snake_case` Python fields to `camelCase` JSON
- Request schemas: `BrandCreateRequest`, `BrandUpdateRequest`
- Response schemas: `BrandResponse`, `BrandListResponse`
- Generic pagination: `PaginatedResponse[S]`
- i18n fields validated with custom `I18nDict` annotated type

**Router Convention:**
- Each router file defines one `APIRouter` with prefix and tags
- Uses `DishkaRoute` for automatic DI injection
- `FromDishka[HandlerType]` for handler injection in endpoint params
- Permission checks via `Depends(RequirePermission(codename="catalog:manage"))`
- Mutating endpoints: POST (201), PATCH (200), DELETE (204)
- Read endpoints: GET (200) with `Cache-Control: no-store` header

**DI Container:**
- Dishka as the DI framework
- Each module has a `dependencies.py` (presentation layer) or `provider.py` (infrastructure layer) with Dishka Provider classes
- Scopes: `APP` for singletons (engine, redis), `REQUEST` for per-request (session, handlers)

---

*Convention analysis: 2026-03-28*
