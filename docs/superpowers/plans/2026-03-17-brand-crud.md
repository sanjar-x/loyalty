# Brand CRUD Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Read (single + paginated list), Update, and Delete operations for the Brand aggregate in the catalog module.

**Architecture:** CQRS with Clean Architecture layers. Commands (Update, Delete) use domain entities + `IBrandRepository` + `IUnitOfWork`. Queries (Get, List) use raw SQL via `AsyncSession` returning Pydantic read models — no domain entities or repositories on the read path.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, Dishka DI, attrs dataclasses (domain), Pydantic v2 (schemas + read models), pytest

**Spec:** `docs/superpowers/specs/2026-03-17-brand-crud-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/modules/catalog/domain/entities.py` | Modify | Add `Brand.update()` method |
| `src/modules/catalog/domain/interfaces.py` | Modify | Add `check_slug_exists_excluding` to `IBrandRepository` |
| `src/modules/catalog/application/queries/read_models.py` | Modify | Add `BrandReadModel`, `BrandListReadModel` |
| `src/modules/catalog/application/queries/get_brand.py` | Create | `GetBrandHandler` — CQRS read single brand |
| `src/modules/catalog/application/queries/list_brands.py` | Create | `ListBrandsHandler` — CQRS read paginated list |
| `src/modules/catalog/application/commands/update_brand.py` | Create | `UpdateBrandHandler` — partial update name/slug |
| `src/modules/catalog/application/commands/delete_brand.py` | Create | `DeleteBrandHandler` — hard delete |
| `src/modules/catalog/infrastructure/repositories/brand.py` | Modify | Add `check_slug_exists_excluding` |
| `src/modules/catalog/presentation/schemas.py` | Modify | Add `BrandResponse`, `BrandUpdateRequest`, `BrandListResponse` |
| `src/modules/catalog/presentation/router.py` | Modify | Add 4 endpoints |
| `src/modules/catalog/presentation/dependencies.py` | Modify | Register 4 new handlers in `BrandProvider` |
| `tests/unit/modules/catalog/domain/test_entities.py` | Modify | Add `Brand.update()` unit tests |

---

## Chunk 1: Domain + Infrastructure

### Task 1: Brand.update() domain method

**Files:**
- Modify: `src/modules/catalog/domain/entities.py:11-17` (Brand class)
- Test: `tests/unit/modules/catalog/domain/test_entities.py`

- [ ] **Step 1: Write failing tests for Brand.update()**

Add to `tests/unit/modules/catalog/domain/test_entities.py`:

```python
def test_brand_update_name_only():
    brand = Brand.create(name="Old Name", slug="old-slug")
    brand.update(name="New Name")
    assert brand.name == "New Name"
    assert brand.slug == "old-slug"  # unchanged


def test_brand_update_slug_only():
    brand = Brand.create(name="Apple", slug="old-slug")
    brand.update(slug="new-slug")
    assert brand.slug == "new-slug"
    assert brand.name == "Apple"  # unchanged


def test_brand_update_both_fields():
    brand = Brand.create(name="Old", slug="old")
    brand.update(name="New", slug="new")
    assert brand.name == "New"
    assert brand.slug == "new"


def test_brand_update_no_args_changes_nothing():
    brand = Brand.create(name="Apple", slug="apple")
    brand.update()
    assert brand.name == "Apple"
    assert brand.slug == "apple"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/modules/catalog/domain/test_entities.py::test_brand_update_name_only -v`
Expected: FAIL — `AttributeError: 'Brand' object has no attribute 'update'`

- [ ] **Step 3: Implement Brand.update()**

Add to `src/modules/catalog/domain/entities.py` inside the `Brand` class, after `create()` and before `init_logo_upload()`:

```python
def update(self, name: str | None = None, slug: str | None = None) -> None:
    """Update brand details. Logo fields are managed separately via FSM methods."""
    if name is not None:
        self.name = name
    if slug is not None:
        self.slug = slug
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/modules/catalog/domain/test_entities.py -k "test_brand_update" -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/domain/entities.py tests/unit/modules/catalog/domain/test_entities.py
git commit -m "feat(catalog): add Brand.update() domain method for partial updates"
```

---

### Task 2: IBrandRepository.check_slug_exists_excluding interface + implementation

**Files:**
- Modify: `src/modules/catalog/domain/interfaces.py:34-44` (IBrandRepository)
- Modify: `src/modules/catalog/infrastructure/repositories/brand.py:75-78` (after check_slug_exists)

- [ ] **Step 1: Add abstract method to IBrandRepository**

Add to `src/modules/catalog/domain/interfaces.py` inside `IBrandRepository`, after `get_for_update`:

```python
@abstractmethod
async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
    """Check if slug is taken by another brand (excluding given ID)."""
    pass
```

- [ ] **Step 2: Implement in BrandRepository**

Add to `src/modules/catalog/infrastructure/repositories/brand.py` after the `check_slug_exists` method:

```python
async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
    statement = (
        select(OrmBrand.id)
        .where(OrmBrand.slug == slug, OrmBrand.id != exclude_id)
        .limit(1)
    )
    result = await self._session.execute(statement)
    return result.first() is not None
```

- [ ] **Step 3: Run lint to verify no errors**

Run: `uv run ruff check src/modules/catalog/domain/interfaces.py src/modules/catalog/infrastructure/repositories/brand.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/domain/interfaces.py src/modules/catalog/infrastructure/repositories/brand.py
git commit -m "feat(catalog): add check_slug_exists_excluding to IBrandRepository"
```

---

## Chunk 2: Application Layer — Query Handlers

### Task 3: Brand read models

**Files:**
- Modify: `src/modules/catalog/application/queries/read_models.py`

- [ ] **Step 1: Add BrandReadModel and BrandListReadModel**

Add to `src/modules/catalog/application/queries/read_models.py` after the `CategoryNode` class:

```python
class BrandReadModel(BaseModel):
    """Read model for a single brand."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class BrandListReadModel(BaseModel):
    """Paginated brand list read model."""

    items: list[BrandReadModel]
    total: int
    offset: int
    limit: int
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/application/queries/read_models.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/queries/read_models.py
git commit -m "feat(catalog): add Brand read models for CQRS query side"
```

---

### Task 4: GetBrandHandler query handler

**Files:**
- Create: `src/modules/catalog/application/queries/get_brand.py`

Reference pattern: `src/modules/catalog/application/queries/get_category_tree.py` — same CQRS read-side approach: `AsyncSession` + raw SQL, Pydantic read models, no domain entities.

- [ ] **Step 1: Create GetBrandHandler**

Create `src/modules/catalog/application/queries/get_brand.py`:

```python
"""
Query Handler: получить бренд по ID.

Строгий CQRS — не использует IUnitOfWork, доменные агрегаты
и репозитории. Работает напрямую с AsyncSession + raw SQL,
возвращает Pydantic Read Model.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import BrandReadModel
from src.modules.catalog.domain.exceptions import BrandNotFoundError

_GET_BRAND_SQL = text(
    "SELECT id, name, slug, logo_url, logo_status "
    "FROM brands "
    "WHERE id = :brand_id"
)


class GetBrandHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, brand_id: uuid.UUID) -> BrandReadModel:
        result = await self._session.execute(_GET_BRAND_SQL, {"brand_id": brand_id})
        row = result.mappings().first()

        if row is None:
            raise BrandNotFoundError(brand_id=brand_id)

        return BrandReadModel(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            logo_url=row["logo_url"],
            logo_status=row["logo_status"],
        )
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/application/queries/get_brand.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/queries/get_brand.py
git commit -m "feat(catalog): add GetBrandHandler CQRS query"
```

---

### Task 5: ListBrandsHandler query handler

**Files:**
- Create: `src/modules/catalog/application/queries/list_brands.py`

- [ ] **Step 1: Create ListBrandsHandler**

Create `src/modules/catalog/application/queries/list_brands.py`:

```python
"""
Query Handler: список брендов с пагинацией.

Строгий CQRS — не использует IUnitOfWork, доменные агрегаты
и репозитории. Работает напрямую с AsyncSession + raw SQL,
возвращает Pydantic Read Model.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
    BrandReadModel,
)

_LIST_BRANDS_SQL = text(
    "SELECT id, name, slug, logo_url, logo_status "
    "FROM brands "
    "ORDER BY name "
    "LIMIT :limit OFFSET :offset"
)

_COUNT_BRANDS_SQL = text("SELECT count(*) FROM brands")


@dataclass(frozen=True)
class ListBrandsQuery:
    offset: int = 0
    limit: int = 20


class ListBrandsHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, query: ListBrandsQuery) -> BrandListReadModel:
        count_result = await self._session.execute(_COUNT_BRANDS_SQL)
        total = count_result.scalar_one()

        result = await self._session.execute(
            _LIST_BRANDS_SQL, {"limit": query.limit, "offset": query.offset}
        )
        rows = result.mappings().all()

        items = [
            BrandReadModel(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                logo_url=row["logo_url"],
                logo_status=row["logo_status"],
            )
            for row in rows
        ]

        return BrandListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/application/queries/list_brands.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/queries/list_brands.py
git commit -m "feat(catalog): add ListBrandsHandler CQRS query with pagination"
```

---

## Chunk 3: Application Layer — Command Handlers

### Task 6: UpdateBrandHandler command handler

**Files:**
- Create: `src/modules/catalog/application/commands/update_brand.py`

Reference pattern: `src/modules/catalog/application/commands/create_brand.py` — same structure: frozen dataclass command/result, handler with repo + UoW + logger injection, `async with self._uow` block.

- [ ] **Step 1: Create UpdateBrandHandler**

Create `src/modules/catalog/application/commands/update_brand.py`:

```python
import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    BrandSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateBrandCommand:
    brand_id: uuid.UUID
    name: str | None = None
    slug: str | None = None


@dataclass(frozen=True)
class UpdateBrandResult:
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class UpdateBrandHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateBrandHandler")

    async def handle(self, command: UpdateBrandCommand) -> UpdateBrandResult:
        async with self._uow:
            brand = await self._brand_repo.get_for_update(command.brand_id)
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            if command.slug is not None and command.slug != brand.slug:
                if await self._brand_repo.check_slug_exists_excluding(
                    command.slug, command.brand_id
                ):
                    raise BrandSlugConflictError(slug=command.slug)

            brand.update(name=command.name, slug=command.slug)
            await self._brand_repo.update(brand)
            await self._uow.commit()

        self._logger.info("Бренд обновлён", brand_id=str(brand.id))

        return UpdateBrandResult(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            logo_url=brand.logo_url,
            logo_status=brand.logo_status.value if brand.logo_status else None,
        )
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/application/commands/update_brand.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/update_brand.py
git commit -m "feat(catalog): add UpdateBrandHandler with pessimistic locking"
```

---

### Task 7: DeleteBrandHandler command handler

**Files:**
- Create: `src/modules/catalog/application/commands/delete_brand.py`

- [ ] **Step 1: Create DeleteBrandHandler**

Create `src/modules/catalog/application/commands/delete_brand.py`:

```python
import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import BrandNotFoundError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteBrandCommand:
    brand_id: uuid.UUID


class DeleteBrandHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteBrandHandler")

    async def handle(self, command: DeleteBrandCommand) -> None:
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            await self._brand_repo.delete(command.brand_id)
            await self._uow.commit()

        self._logger.info("Бренд удалён", brand_id=str(command.brand_id))
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/application/commands/delete_brand.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/delete_brand.py
git commit -m "feat(catalog): add DeleteBrandHandler with existence check"
```

---

## Chunk 4: Presentation Layer + DI

### Task 8: Pydantic schemas

**Files:**
- Modify: `src/modules/catalog/presentation/schemas.py`

- [ ] **Step 1: Add Brand response/request schemas**

Add to `src/modules/catalog/presentation/schemas.py` after the `ConfirmLogoRequest` class:

```python
class BrandResponse(BaseModel):
    """Brand detail response."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class BrandUpdateRequest(BaseModel):
    """Partial update request — all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")


class BrandListResponse(BaseModel):
    """Paginated brand list response."""

    items: list[BrandResponse]
    total: int
    offset: int
    limit: int
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/presentation/schemas.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/presentation/schemas.py
git commit -m "feat(catalog): add Brand CRUD Pydantic schemas"
```

---

### Task 9: FastAPI router endpoints

**Files:**
- Modify: `src/modules/catalog/presentation/router.py`

- [ ] **Step 1: Add imports to router.py**

Merge `Query` into the existing fastapi import line and add new handler/schema imports at the top of `src/modules/catalog/presentation/router.py`:

Change `from fastapi import APIRouter, status` to:
```python
from fastapi import APIRouter, Query, status
```

Add these new imports alongside the existing ones:
```python
from src.modules.catalog.application.commands.delete_brand import (
    DeleteBrandCommand,
    DeleteBrandHandler,
)
from src.modules.catalog.application.commands.update_brand import (
    UpdateBrandCommand,
    UpdateBrandHandler,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.list_brands import (
    ListBrandsHandler,
    ListBrandsQuery,
)
```

Update the schemas import to include new schemas:
```python
from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    BrandCreateResponse,
    BrandListResponse,
    BrandResponse,
    BrandUpdateRequest,
    CategoryCreateRequest,
    CategoryCreateResponse,
    CategoryTreeResponse,
    ConfirmLogoRequest,
)
```

- [ ] **Step 2: Add 4 endpoint functions in correct order**

The final order of brand endpoints in `router.py` must be:
1. `POST ""` (create_brand) — **existing, keep in place**
2. `GET ""` (list_brands) — **NEW, insert right after create_brand**
3. `GET "/{brand_id}"` (get_brand) — **NEW**
4. `PATCH "/{brand_id}"` (update_brand) — **NEW**
5. `DELETE "/{brand_id}"` (delete_brand) — **NEW**
6. `POST "/{brand_id}/logo/confirm"` (confirm_logo_upload) — **existing, move to end**

**Why this order matters:** FastAPI matches routes in registration order. `GET ""` must come before `GET "/{brand_id}"` to prevent the empty path from being swallowed by the parameterized route.

Insert after `create_brand` and before `confirm_logo_upload`:

```python
@brand_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=BrandListResponse,
    summary="Получить список брендов",
)
async def list_brands(
    handler: FromDishka[ListBrandsHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> BrandListResponse:
    query = ListBrandsQuery(offset=offset, limit=limit)
    result = await handler.handle(query)
    return BrandListResponse(
        items=[
            BrandResponse(
                id=item.id,
                name=item.name,
                slug=item.slug,
                logo_url=item.logo_url,
                logo_status=item.logo_status,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@brand_router.get(
    "/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Получить бренд по ID",
)
async def get_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[GetBrandHandler],
) -> BrandResponse:
    result = await handler.handle(brand_id)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.patch(
    "/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Обновить бренд",
)
async def update_brand(
    brand_id: uuid.UUID,
    request: BrandUpdateRequest,
    handler: FromDishka[UpdateBrandHandler],
) -> BrandResponse:
    command = UpdateBrandCommand(
        brand_id=brand_id,
        name=request.name,
        slug=request.slug,
    )
    result = await handler.handle(command)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бренд",
)
async def delete_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[DeleteBrandHandler],
) -> None:
    command = DeleteBrandCommand(brand_id=brand_id)
    await handler.handle(command)
```

- [ ] **Step 3: Run lint**

Run: `uv run ruff check src/modules/catalog/presentation/router.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/presentation/router.py
git commit -m "feat(catalog): add Brand CRUD endpoints (GET, PATCH, DELETE)"
```

---

### Task 10: Dishka DI provider registration

**Files:**
- Modify: `src/modules/catalog/presentation/dependencies.py:35-47` (BrandProvider class)

- [ ] **Step 1: Add handler imports and provider registrations**

Add imports at the top of `src/modules/catalog/presentation/dependencies.py`:

```python
from src.modules.catalog.application.commands.delete_brand import DeleteBrandHandler
from src.modules.catalog.application.commands.update_brand import UpdateBrandHandler
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.list_brands import ListBrandsHandler
```

Add to `BrandProvider` class body (after `brand_logo_processor`):

```python
get_brand_handler: CompositeDependencySource = provide(
    GetBrandHandler, scope=Scope.REQUEST
)
list_brands_handler: CompositeDependencySource = provide(
    ListBrandsHandler, scope=Scope.REQUEST
)
update_brand_handler: CompositeDependencySource = provide(
    UpdateBrandHandler, scope=Scope.REQUEST
)
delete_brand_handler: CompositeDependencySource = provide(
    DeleteBrandHandler, scope=Scope.REQUEST
)
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/presentation/dependencies.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/presentation/dependencies.py
git commit -m "feat(catalog): register Brand CRUD handlers in Dishka provider"
```

---

## Chunk 5: Verification

### Task 11: Full quality gate

- [ ] **Step 1: Run ruff lint + format on all modified files**

```bash
uv run ruff check --fix . && uv run ruff format .
```

Expected: No errors

- [ ] **Step 2: Run mypy type check**

```bash
uv run mypy src/modules/catalog/
```

Expected: No type errors on modified modules

- [ ] **Step 3: Run unit tests**

```bash
uv run pytest tests/unit/modules/catalog/ -v
```

Expected: All tests pass, including new `test_brand_update_*` tests

- [ ] **Step 4: Run architecture tests**

```bash
uv run pytest tests/architecture/ -v
```

Expected: No boundary violations — all new code follows Clean Architecture layers

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "fix(catalog): address lint/type/test issues from quality gate"
```

Only run this if previous steps required fixes.

---

## Parallelism Notes

Tasks that can run in parallel (independent, no shared state):
- **Tasks 1, 2, 3** — all independent: domain entity update, repo interface, read models
- **Task 4** and **Task 5** — both depend on Task 3 but not each other
- **Task 6** depends on Tasks 1 + 2 (uses `Brand.update()` + `check_slug_exists_excluding`)
- **Task 7** is independent of Tasks 1-2 (only imports `IBrandRepository.get` + `delete` which already exist)
- **Tasks 4, 5, 7** can run in parallel once Task 3 is done (Task 7 has no dependency on Task 3 either, so it can start immediately)

Sequential dependencies:
- Tasks 4-5 depend on Task 3 (import read models)
- Task 6 depends on Tasks 1 + 2 (imports `Brand.update()` and `check_slug_exists_excluding`)
- Tasks 8-10 depend on Tasks 4-7 (import handlers)
- Task 11 depends on all previous tasks
