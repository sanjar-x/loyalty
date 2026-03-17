# Brand CRUD Design Specification

**Date:** 2026-03-17
**Module:** Catalog
**Scope:** Add Read (single + list), Update, Delete operations for the Brand aggregate

## Context

The Brand entity already exists with:
- **Domain:** `Brand` aggregate root with `create()` factory + logo FSM methods
- **Application:** `CreateBrandHandler`, `ConfirmBrandLogoUploadHandler`
- **Infrastructure:** `BrandRepository` with `add`, `get`, `update`, `delete`, `get_for_update`, `check_slug_exists`
- **Presentation:** `POST /brands`, `POST /brands/{id}/logo/confirm`

Missing: Read (single + paginated list), Update (name + slug), Delete (hard delete) operations at the application and presentation layers.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Update scope | Name + slug only | Logo has its own FSM workflow; SRP |
| Pagination | Offset/limit | Simple, no existing pagination pattern to follow |
| Delete type | Hard delete | No soft-delete infrastructure needed yet |
| Query handlers | Raw SQL via AsyncSession | CQRS read-side: no domain entities, repositories, or UoW |
| Command handlers | Repository + UoW | CQRS write-side: domain entities, transactional |
| Update locking | `get_for_update` (SELECT FOR UPDATE) | Prevents race conditions on slug uniqueness |
| PATCH semantics | All fields optional (true partial update) | Correct REST semantics for PATCH |

## Changes by Layer

### 1. Domain Layer

**`src/modules/catalog/domain/entities.py`** — Add `update()` method:
```python
def update(self, name: str | None = None, slug: str | None = None) -> None:
    """Update brand details. Logo fields are managed separately via FSM methods."""
    if name is not None:
        self.name = name
    if slug is not None:
        self.slug = slug
```

**`src/modules/catalog/domain/interfaces.py`** — Extend `IBrandRepository`:
```python
@abstractmethod
async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
    pass
```

Note: No `get_list` on repository — list query uses raw SQL via AsyncSession (CQRS read-side).

### 2. Application Layer

**`src/modules/catalog/application/queries/read_models.py`** — Add read models:
```python
class BrandReadModel(BaseModel):
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

**`src/modules/catalog/application/queries/get_brand.py`** — GetBrandHandler:
- Input: `brand_id: UUID`
- Inject: `AsyncSession`
- Query: `SELECT id, name, slug, logo_url, logo_status FROM brands WHERE id = :id`
- Output: `BrandReadModel`
- Raises: `BrandNotFoundError` if not found

**`src/modules/catalog/application/queries/list_brands.py`** — ListBrandsHandler:
- Input: `ListBrandsQuery(offset: int = 0, limit: int = 20)`
- Inject: `AsyncSession`
- Queries: raw SQL — `SELECT ... FROM brands ORDER BY name LIMIT :limit OFFSET :offset` + `SELECT count(*) FROM brands`
- Output: `BrandListReadModel` with items, total, offset, limit

**`src/modules/catalog/application/commands/update_brand.py`** — UpdateBrandHandler:
- Input: `UpdateBrandCommand(brand_id: UUID, name: str | None, slug: str | None)` (`@dataclass(frozen=True)`)
- Inject: `IBrandRepository`, `IUnitOfWork`, `ILogger`
- Logic:
  1. `repo.get_for_update(brand_id)` → raise `BrandNotFoundError` if None (pessimistic lock)
  2. If slug changed: `repo.check_slug_exists_excluding(slug, brand_id)` → raise `BrandSlugConflictError`
  3. `brand.update(name=command.name, slug=command.slug)`
  4. `repo.update(brand)`, `uow.commit()`
- Output: `UpdateBrandResult(id, name, slug)` (`@dataclass(frozen=True)`)

**`src/modules/catalog/application/commands/delete_brand.py`** — DeleteBrandHandler:
- Input: `DeleteBrandCommand(brand_id: UUID)` (`@dataclass(frozen=True)`)
- Inject: `IBrandRepository`, `IUnitOfWork`, `ILogger`
- Logic:
  1. `repo.get(brand_id)` → raise `BrandNotFoundError` if None
  2. `repo.delete(brand_id)`, `uow.commit()`
- Output: None
- Note: No `register_aggregate` call — no domain events emitted. When `BrandDeletedEvent` is needed, add it to the entity and register here.

### 3. Infrastructure Layer

**`src/modules/catalog/infrastructure/repositories/brand.py`** — Add method:
```python
async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
    statement = select(OrmBrand.id).where(
        OrmBrand.slug == slug, OrmBrand.id != exclude_id
    ).limit(1)
    result = await self._session.execute(statement)
    return result.first() is not None
```

### 4. Presentation Layer

**`src/modules/catalog/presentation/schemas.py`** — Add schemas:
```python
class BrandResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None

class BrandUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")

class BrandListResponse(BaseModel):
    items: list[BrandResponse]
    total: int
    offset: int
    limit: int
```

**`src/modules/catalog/presentation/router.py`** — Add 4 endpoints:
- `GET /brands/{brand_id}` → 200, `BrandResponse`
- `GET /brands` → 200, `BrandListResponse` (query params: offset=0, limit=20)
- `PATCH /brands/{brand_id}` → 200, `BrandResponse`
- `DELETE /brands/{brand_id}` → 204 No Content

### 5. DI Registration

**`src/modules/catalog/presentation/dependencies.py`** — Register in `BrandProvider`:
- `GetBrandHandler` (scope=REQUEST)
- `ListBrandsHandler` (scope=REQUEST)
- `UpdateBrandHandler` (scope=REQUEST)
- `DeleteBrandHandler` (scope=REQUEST)

## Files Modified

| File | Action |
|---|---|
| `src/modules/catalog/domain/entities.py` | Add `Brand.update()` method |
| `src/modules/catalog/domain/interfaces.py` | Add `check_slug_exists_excluding` to `IBrandRepository` |
| `src/modules/catalog/application/queries/read_models.py` | Add `BrandReadModel`, `BrandListReadModel` |
| `src/modules/catalog/application/queries/get_brand.py` | **New file** |
| `src/modules/catalog/application/queries/list_brands.py` | **New file** |
| `src/modules/catalog/application/commands/update_brand.py` | **New file** |
| `src/modules/catalog/application/commands/delete_brand.py` | **New file** |
| `src/modules/catalog/infrastructure/repositories/brand.py` | Add `check_slug_exists_excluding` method |
| `src/modules/catalog/presentation/schemas.py` | Add 3 schemas |
| `src/modules/catalog/presentation/router.py` | Add 4 endpoints + imports |
| `src/modules/catalog/presentation/dependencies.py` | Register 4 handlers |

## Non-Goals

- No logo management changes (existing FSM workflow unchanged)
- No caching for brand queries (can be added later)
- No filtering/search on list endpoint (can be added later)
- No soft delete (hard delete only)
- No domain events for update/delete (can be added when consumers exist; add `register_aggregate` at that time)
- `logo_file_id` intentionally excluded from read models (internal reference, not useful for API consumers)
