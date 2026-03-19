# Architecture Plan -- MT-17: Add ProductRepository implementation

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-17
> **Layer:** Infrastructure
> **Module:** catalog
> **FR Reference:** FR-001, FR-005
> **Depends on:** MT-5, MT-16

---

## Research findings

- **SQLAlchemy 2.1** `selectinload`: Use `select(OrmProduct).options(selectinload(OrmProduct.skus))` to eager-load the SKU collection in a single second query. Import from `sqlalchemy.orm import selectinload`.
- **SQLAlchemy 2.1** `StaleDataError`: Raised by ORM flush when `version_id_col` detects a mismatch. Import from `sqlalchemy.orm.exc import StaleDataError`.
- **SQLAlchemy 2.1** `func.count`: Use `select(func.count()).select_from(...)` for total count in pagination queries.
- **Existing pattern**: Repositories in this codebase do NOT extend `BaseRepository`. Despite `base.py` existing, `BrandRepository` and `AttributeRepository` implement `__init__(self, session: AsyncSession)` directly and implement all methods manually. The existing placeholder `ProductRepository` does extend `BaseRepository`, but it is a stub to be fully replaced. The new implementation MUST follow the `BrandRepository`/`AttributeRepository` pattern (direct implementation, no `BaseRepository` inheritance) for consistency.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Inherit from BaseRepository? | No -- direct implementation | BrandRepository and AttributeRepository (the mature, non-placeholder repos) do NOT use BaseRepository. They implement `__init__`, `_to_domain`, `_to_orm`, and all CRUD methods directly. Follow the established pattern. |
| SKU mapping approach | Private `_sku_to_domain` / `_sku_to_orm` helper methods | SKU is a child entity of Product. The Product `_to_domain` calls `_sku_to_domain` for each ORM SKU. The `_to_orm` calls `_sku_to_orm` for each domain SKU. |
| Money mapping | Decompose Money VO to/from ORM flat columns | ORM SKU has `price: int`, `compare_at_price: int | None`, `currency: str`. Domain SKU has `price: Money`, `compare_at_price: Money | None`. Map `Money(amount=orm.price, currency=orm.currency)` and reverse. |
| StaleDataError catch location | Wrap `flush()` calls in `add` and `update` | Both methods call `flush()`. Catch `StaleDataError` there and re-raise as `ConcurrencyError`. |
| Soft-delete exclusion in `list_products` | `WHERE deleted_at IS NULL` filter | Matches domain requirement and existing ORM index `ix_products_catalog_listing`. |
| `get_with_skus` loading strategy | `selectinload(OrmProduct.skus)` | Context7 confirms this is the recommended pattern for one-to-many in async sessions. |
| Status enum mapping | Map domain `ProductStatus` value string to ORM `ProductStatus` by value | Both enums share the same string values (`"draft"`, `"enriching"`, etc.). Use `OrmProductStatus(domain_status.value)` for domain-to-ORM and `DomainProductStatus(orm_status.value)` for ORM-to-domain. |
| SKU `variant_attributes` mapping | Load from `SKUAttributeValueLink` rows on ORM SKU | ORM `SKU.attribute_values` relationship holds `SKUAttributeValueLink` rows. Map each to `(link.attribute_id, link.attribute_value_id)` tuple. On `_to_orm`, sync the link collection. |

---

## File plan

### `src/modules/catalog/infrastructure/repositories/product.py` -- MODIFY (full rewrite)

**Purpose:** Data Mapper repository for the Product aggregate with SKU child entities. Replaces the placeholder stub entirely.
**Layer:** Infrastructure

#### Imports:

```python
import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import SKU as DomainSKU
from src.modules.catalog.domain.exceptions import ConcurrencyError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from src.modules.catalog.domain.value_objects import ProductStatus as DomainProductStatus
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import ProductStatus as OrmProductStatus
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import SKUAttributeValueLink as OrmSKUAttrLink
```

#### Classes / functions:

**`ProductRepository`** (full rewrite of existing stub)

- Implements: `IProductRepository`
- Constructor args:
  - `session: AsyncSession` -- SQLAlchemy async session scoped to the current request
- DI scope: REQUEST
- Events raised: none (deferred to P2)

**Private helper methods:**

1. `_sku_to_domain(self, orm_sku: OrmSKU) -> DomainSKU`
   - Maps ORM SKU to domain SKU.
   - `price` = `Money(amount=orm_sku.price, currency=orm_sku.currency)`
   - `compare_at_price` = `Money(amount=orm_sku.compare_at_price, currency=orm_sku.currency)` if `orm_sku.compare_at_price is not None` else `None`
   - `variant_attributes` = `[(link.attribute_id, link.attribute_value_id) for link in orm_sku.attribute_values]`
   - All other fields mapped 1:1 by name: `id`, `product_id`, `sku_code`, `variant_hash`, `is_active`, `version`, `deleted_at`, `created_at`, `updated_at`

2. `_sku_to_orm(self, domain_sku: DomainSKU, orm_sku: OrmSKU | None = None) -> OrmSKU`
   - If `orm_sku is None`, create `OrmSKU()`.
   - Map flat fields: `id`, `product_id`, `sku_code`, `variant_hash`, `is_active`, `version`, `deleted_at`, `created_at`, `updated_at`
   - `orm_sku.price = domain_sku.price.amount`
   - `orm_sku.compare_at_price = domain_sku.compare_at_price.amount if domain_sku.compare_at_price is not None else None`
   - `orm_sku.currency = domain_sku.price.currency`
   - `orm_sku.main_image_url = None` (not on domain entity, preserve existing ORM value if updating: only set to None on create)
   - `orm_sku.attributes_cache = {}` (not on domain entity, preserve existing ORM value if updating: only set to `{}` on create)
   - For `variant_attributes` -- sync the `orm_sku.attribute_values` relationship:
     - Clear existing links: `orm_sku.attribute_values.clear()`
     - For each `(attr_id, attr_val_id)` in `domain_sku.variant_attributes`, append `OrmSKUAttrLink(sku_id=domain_sku.id, attribute_id=attr_id, attribute_value_id=attr_val_id)`
   - Return `orm_sku`

3. `_to_domain(self, orm: OrmProduct) -> DomainProduct`
   - Maps ORM Product to domain Product.
   - `status` = `DomainProductStatus(orm.status.value)`
   - `skus` = `[self._sku_to_domain(sku) for sku in orm.skus]` -- NOTE: `orm.skus` must be loaded (either eager or already in session). If not loaded, this will raise. Callers that need SKUs must use `get_with_skus`.
   - All other fields mapped 1:1: `id`, `slug`, `brand_id`, `primary_category_id`, `supplier_id`, `version`, `deleted_at`, `created_at`, `updated_at`, `published_at`, `country_of_origin`
   - `title_i18n` = `dict(orm.title_i18n) if orm.title_i18n else {}`
   - `description_i18n` = `dict(orm.description_i18n) if orm.description_i18n else {}`
   - `tags` = `list(orm.tags) if orm.tags else []`

4. `_to_domain_without_skus(self, orm: OrmProduct) -> DomainProduct`
   - Same as `_to_domain` but passes `skus=[]` instead of mapping SKUs.
   - Used by methods that do not eager-load SKUs (e.g., `get`, `list_products`, `get_by_slug`).

5. `_to_orm(self, entity: DomainProduct, orm: OrmProduct | None = None) -> OrmProduct`
   - If `orm is None`, create `OrmProduct()`.
   - Map flat fields: `id`, `slug`, `brand_id`, `primary_category_id`, `supplier_id`, `version`, `deleted_at`, `created_at`, `updated_at`, `published_at`, `country_of_origin`, `popularity_score=0` (on create only), `is_visible=True` (on create only), `source_url=None` (on create only)
   - `orm.status = OrmProductStatus(entity.status.value)`
   - `orm.title_i18n = entity.title_i18n`  (type: ignore[assignment])
   - `orm.description_i18n = entity.description_i18n`  (type: ignore[assignment])
   - `orm.tags = entity.tags`  (type: ignore[assignment])
   - `orm.attributes = {}`  (type: ignore[assignment], on create only; preserve on update)
   - SKU sync: For `add`, sync SKUs on the ORM via `orm.skus` collection. For `update`, SKU sync is handled separately by `_sync_skus` to properly handle additions, updates, and removals.

6. `_sync_skus(self, product: DomainProduct, orm: OrmProduct) -> None`
   - Build a dict of existing ORM SKUs by ID: `{sku.id: sku for sku in orm.skus}`
   - For each domain SKU:
     - If ID exists in dict: call `_sku_to_orm(domain_sku, existing_orm_sku)`
     - If ID not in dict: call `_sku_to_orm(domain_sku)` and append to `orm.skus`
   - For ORM SKUs whose ID is not in the domain SKU list: remove from `orm.skus`

**Public methods (IProductRepository + ICatalogRepository):**

7. `async def add(self, entity: DomainProduct) -> DomainProduct`
   - Create ORM via `_to_orm(entity)`.
   - For each SKU in `entity.skus`, call `_sku_to_orm(sku)` and append to `orm.skus`.
   - `self._session.add(orm)`
   - Wrap `await self._session.flush()` in try/except `StaleDataError` -> raise `ConcurrencyError(entity_type="Product", entity_id=entity.id, expected_version=entity.version, actual_version=-1)`
   - Return `self._to_domain(orm)` (SKUs are now loaded on the ORM object)

8. `async def get(self, entity_id: uuid.UUID) -> DomainProduct | None`
   - `orm = await self._session.get(OrmProduct, entity_id)`
   - If `orm is None` or `orm.deleted_at is not None`: return `None`
   - Return `self._to_domain_without_skus(orm)`

9. `async def update(self, entity: DomainProduct) -> DomainProduct`
   - Load existing ORM with SKUs eager-loaded:
     ```
     stmt = select(OrmProduct).where(OrmProduct.id == entity.id).options(selectinload(OrmProduct.skus).selectinload(OrmSKU.attribute_values))
     result = await self._session.execute(stmt)
     orm = result.scalar_one_or_none()
     ```
   - If `orm is None`: raise `ValueError(f"Product with id {entity.id} not found in DB")`
   - Call `_to_orm(entity, orm)` for Product-level fields.
   - Call `_sync_skus(entity, orm)` for SKU child entities.
   - Wrap `await self._session.flush()` in try/except `StaleDataError` -> raise `ConcurrencyError(entity_type="Product", entity_id=entity.id, expected_version=entity.version, actual_version=-1)`
   - Return `self._to_domain(orm)`

10. `async def delete(self, entity_id: uuid.UUID) -> None`
    - `stmt = delete(OrmProduct).where(OrmProduct.id == entity_id)`
    - `await self._session.execute(stmt)`

11. `async def get_by_slug(self, slug: str) -> DomainProduct | None`
    - `stmt = select(OrmProduct).where(OrmProduct.slug == slug, OrmProduct.deleted_at.is_(None)).limit(1)`
    - Execute, get `scalar_one_or_none()`.
    - If found: return `self._to_domain_without_skus(orm)`. Else `None`.

12. `async def check_slug_exists(self, slug: str) -> bool`
    - `stmt = select(OrmProduct.id).where(OrmProduct.slug == slug, OrmProduct.deleted_at.is_(None)).limit(1)`
    - Return `result.first() is not None`

13. `async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool`
    - Same as above but add `.where(OrmProduct.id != exclude_id)`

14. `async def get_for_update(self, product_id: uuid.UUID) -> DomainProduct | None`
    - `stmt = select(OrmProduct).where(OrmProduct.id == product_id).with_for_update()`
    - Execute, get `scalar_one_or_none()`.
    - If found: return `self._to_domain_without_skus(orm)`. Else `None`.

15. `async def get_with_skus(self, product_id: uuid.UUID) -> DomainProduct | None`
    - `stmt = select(OrmProduct).where(OrmProduct.id == product_id).options(selectinload(OrmProduct.skus).selectinload(OrmSKU.attribute_values))`
    - Execute, get `scalar_one_or_none()`.
    - If `orm is None` or `orm.deleted_at is not None`: return `None`.
    - Return `self._to_domain(orm)` (with SKUs mapped).

16. `async def list_products(self, limit: int, offset: int, status: DomainProductStatus | None = None, brand_id: uuid.UUID | None = None) -> tuple[list[DomainProduct], int]`
    - Build base filter: `OrmProduct.deleted_at.is_(None)`
    - If `status is not None`: add `.where(OrmProduct.status == OrmProductStatus(status.value))`
    - If `brand_id is not None`: add `.where(OrmProduct.brand_id == brand_id)`
    - **Count query**: `count_stmt = select(func.count()).select_from(OrmProduct).where(*filters)`
    - **Data query**: `data_stmt = select(OrmProduct).where(*filters).order_by(OrmProduct.created_at.desc()).limit(limit).offset(offset)`
    - Execute both.
    - Map data results with `_to_domain_without_skus`.
    - Return `(products_list, total_count)`.

#### Structural sketch (pseudo-code):

```python
class ProductRepository(IProductRepository):
    """Data Mapper repository for the Product aggregate."""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _sku_to_domain(self, orm_sku: OrmSKU) -> DomainSKU:
        # map ORM SKU -> domain SKU with Money VOs
        ...

    def _sku_to_orm(self, domain_sku: DomainSKU, orm_sku: OrmSKU | None = None) -> OrmSKU:
        # map domain SKU -> ORM SKU, sync variant_attributes links
        ...

    def _to_domain(self, orm: OrmProduct) -> DomainProduct:
        # map ORM Product -> domain Product WITH skus
        ...

    def _to_domain_without_skus(self, orm: OrmProduct) -> DomainProduct:
        # map ORM Product -> domain Product with skus=[]
        ...

    def _to_orm(self, entity: DomainProduct, orm: OrmProduct | None = None) -> OrmProduct:
        # map domain Product -> ORM Product (product-level fields only)
        ...

    def _sync_skus(self, product: DomainProduct, orm: OrmProduct) -> None:
        # reconcile domain SKU list with ORM SKU collection
        ...

    async def add(self, entity: DomainProduct) -> DomainProduct:
        # persist + catch StaleDataError
        ...

    async def get(self, entity_id: uuid.UUID) -> DomainProduct | None:
        # by PK, exclude soft-deleted, no SKUs
        ...

    async def update(self, entity: DomainProduct) -> DomainProduct:
        # load with SKUs, sync, flush, catch StaleDataError
        ...

    async def delete(self, entity_id: uuid.UUID) -> None:
        # hard delete
        ...

    # ... remaining IProductRepository methods
```

---

### `src/modules/catalog/infrastructure/repositories/__init__.py` -- NO CHANGE

**Reason:** The `__init__.py` already imports and exports `ProductRepository`. No modification needed.

---

## Dependency registration

No DI changes required for this micro-task. ProductRepository is already registered in the DI container (it was registered when the placeholder was created). The class name and import path remain the same.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| SKUs not eager-loaded when `_to_domain` is called | `MissingGreenlet` / lazy load error in async context | Use `_to_domain_without_skus` for methods that don't load SKUs; only use `_to_domain` (with SKU mapping) when `selectinload` was applied |
| `StaleDataError` may not carry version details | `ConcurrencyError` constructor requires `expected_version` and `actual_version` | Pass `expected_version=entity.version` and `actual_version=-1` (unknown) since `StaleDataError` does not expose the DB version. The `-1` sentinel signals "unknown DB version". |
| ORM SKU `main_image_url` and `attributes_cache` not on domain entity | Fields lost on round-trip through domain | On create (`orm is None`), set defaults (`None` / `{}`). On update (`orm is not None`), these fields are preserved because `_sku_to_orm` only overwrites fields that exist on the domain entity. Explicitly: do NOT overwrite `main_image_url` or `attributes_cache` when `orm_sku is not None`. |
| ORM Product `popularity_score`, `is_visible`, `source_url`, `attributes` (JSONB) not on domain | Fields lost on round-trip | Same pattern: set defaults on create, preserve on update (do NOT overwrite when `orm is not None`). |
| Domain `ProductStatus` vs ORM `ProductStatus` enum mismatch | String values are identical but types differ | Explicit conversion via `.value`: `DomainProductStatus(orm.status.value)` and `OrmProductStatus(entity.status.value)` |

## Acceptance verification

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**

- [ ] `ProductRepository` implements `IProductRepository` (all abstract methods present)
- [ ] `_to_domain()` maps ORM Product + SKUs to domain Product with SKU child entities
- [ ] `_to_orm()` maps domain Product back to ORM (create and update modes)
- [ ] SKU `_sku_to_domain`/`_sku_to_orm` handles Money value object mapping (`price`/`compare_at_price`/`currency` <-> `Money`)
- [ ] `get_with_skus` loads Product with eager-loaded SKUs via `selectinload`
- [ ] `list_products` supports limit/offset pagination with optional status and brand_id filters, excludes soft-deleted
- [ ] Catches `StaleDataError` on flush and re-raises as domain `ConcurrencyError`
- [ ] ORM models never leak outside repository (all public methods return domain types)
- [ ] Domain layer has zero framework imports
- [ ] `__init__.py` already exports `ProductRepository` (no change needed)
- [ ] All existing tests pass after this change
- [ ] Linter/type-checker passes
