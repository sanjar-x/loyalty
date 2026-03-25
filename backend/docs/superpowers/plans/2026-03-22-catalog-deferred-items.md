# Catalog Deferred Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve 6 deferred design items in the catalog module: event_type naming, meta_data comment, list_product_attributes stub, BaseRepository adoption, and unified PATCH semantics.

**Architecture:** Each task is independent and can be committed separately. Tasks 1-4 are parallelizable. Task 5 (PATCH semantics) is the largest and should be done last as it touches the most files.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, attrs, Dishka DI

**Spec:** `docs/superpowers/specs/2026-03-22-catalog-deferred-items-design.md`

---

## Task 1: BrandLogoUploadInitiatedEvent.event_type fix

**Files:**

- Modify: `src/modules/catalog/domain/events.py:43`
- Modify: `src/infrastructure/outbox/tasks.py:90`
- Modify: `src/modules/storage/application/consumers/brand_events.py:39`
- Modify: `tests/unit/modules/catalog/domain/test_events.py`
- Modify: `tests/unit/infrastructure/outbox/test_tasks.py`
- Modify: `tests/unit/modules/storage/application/consumers/test_brand_events.py`
- Modify: `tests/integration/modules/catalog/application/commands/test_create_brand.py`

- [ ] **Step 1: Fix event_type in events.py**

In `src/modules/catalog/domain/events.py`, change line 43:

```python
# FROM:
event_type: str = "BrandCreatedEvent"  # backward-compat with Outbox routing
# TO:
event_type: str = "BrandLogoUploadInitiatedEvent"
```

- [ ] **Step 2: Update Outbox routing in tasks.py**

In `src/infrastructure/outbox/tasks.py`, find the `_handle_brand_created` function and `register_event_handler` call:

```python
# Rename function _handle_brand_created -> _handle_brand_logo_upload_initiated
# Update registration:
register_event_handler("BrandLogoUploadInitiatedEvent", _handle_brand_logo_upload_initiated)
```

- [ ] **Step 3: Update storage consumer**

In `src/modules/storage/application/consumers/brand_events.py`:

- Rename the handler function from `handle_brand_created_event` to `handle_brand_logo_upload_initiated_event`
- Update docstring from "BrandCreatedEvent" to "BrandLogoUploadInitiatedEvent"

- [ ] **Step 4: Update all test files**

Search all test files for `"BrandCreatedEvent"` string and class references. Update:

- `test_events.py`: assertion `event.event_type == "BrandCreatedEvent"` → `"BrandLogoUploadInitiatedEvent"`
- `test_tasks.py`: any event_type string references
- `test_brand_events.py`: handler function name references
- `test_create_brand.py`: outbox `event_type == "BrandCreatedEvent"` assertion

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/unit/modules/catalog/domain/test_events.py tests/unit/infrastructure/outbox/ -v --timeout=30`

```bash
git add -A && git commit -m "fix: align BrandLogoUploadInitiatedEvent.event_type with class name"
```

---

## Task 2: meta_data comment (trivial)

**Files:**

- Modify: `src/modules/catalog/infrastructure/models.py` (AttributeValue.meta_data field)
- Modify: `src/modules/catalog/domain/entities.py` (AttributeValue.meta_data field)

- [ ] **Step 1: Add comment in models.py**

Find `AttributeValue` ORM model's `meta_data` column and add above it:

```python
# Named `meta_data` (not `metadata`) to avoid collision with SQLAlchemy Base.metadata
meta_data: Mapped[dict[str, Any]] = ...
```

- [ ] **Step 2: Add comment in entities.py**

Find `AttributeValue` dataclass's `meta_data` field and add above it:

```python
# Named `meta_data` (not `metadata`) to avoid collision with SQLAlchemy Base.metadata
meta_data: dict[str, Any] = field(factory=dict)
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/infrastructure/models.py src/modules/catalog/domain/entities.py
git commit -m "docs: explain meta_data naming (SQLAlchemy Base.metadata collision)"
```

---

## Task 3: list_product_attributes implementation

**Files:**

- Modify: `src/modules/catalog/application/queries/read_models.py`
- Modify: `src/modules/catalog/application/queries/list_product_attributes.py`
- Modify: `src/modules/catalog/presentation/schemas.py` (ProductAttributeResponse — add new fields)
- Modify: `src/modules/catalog/presentation/router_product_attributes.py` (update import + mapping)

- [ ] **Step 1: Add ProductAttributeReadModel to read_models.py**

At the end of `read_models.py`, add:

```python
class ProductAttributeReadModel(BaseModel):
    """Read model for a product's attribute assignment with joined attribute data."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID
    attribute_code: str
    attribute_name_i18n: dict[str, str]
```

- [ ] **Step 2: Implement the query handler**

Replace the entire `list_product_attributes.py` with:

```python
"""
Query handler: list product attribute assignments with attribute metadata.

Joins ProductAttributeValue with Attribute to provide attribute code and name
alongside each assignment. CQRS read side — queries ORM directly.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    ProductAttributeReadModel,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
    ProductAttributeValue as OrmProductAttributeValue,
)


class ListProductAttributesQuery:
    """Parameters for listing attribute assignments of a product."""

    def __init__(self, product_id: uuid.UUID) -> None:
        self.product_id = product_id


class ListProductAttributesHandler:
    """Fetch all attribute assignments for a product with attribute metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, query: ListProductAttributesQuery
    ) -> list[ProductAttributeReadModel]:
        """Retrieve product attribute assignments joined with attribute data."""
        stmt = (
            select(OrmProductAttributeValue, OrmAttribute)
            .join(OrmAttribute, OrmProductAttributeValue.attribute_id == OrmAttribute.id)
            .where(OrmProductAttributeValue.product_id == query.product_id)
            .order_by(OrmAttribute.sort_order)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            ProductAttributeReadModel(
                id=pav.id,
                product_id=pav.product_id,
                attribute_id=pav.attribute_id,
                attribute_value_id=pav.attribute_value_id,
                attribute_code=attr.code,
                attribute_name_i18n=dict(attr.name_i18n),
            )
            for pav, attr in rows
        ]
```

- [ ] **Step 3: Update ProductAttributeResponse schema**

In `src/modules/catalog/presentation/schemas.py`, find `ProductAttributeResponse` and add the new fields:

```python
class ProductAttributeResponse(CamelModel):
    """Single product-attribute assignment detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID
    attribute_code: str = ""
    attribute_name_i18n: dict[str, str] = Field(default_factory=dict)
```

The new fields have defaults so existing code that constructs `ProductAttributeResponse` without them (e.g., `get_product.py` response mapping) still works.

- [ ] **Step 4: Update router_product_attributes.py**

Update the import and response mapping:

```python
# Change import from:
from src.modules.catalog.application.queries.read_models import (
    ProductAttributeValueReadModel,
)
# To:
from src.modules.catalog.application.queries.read_models import (
    ProductAttributeReadModel,
)

# Update the list handler response mapping:
items: list[ProductAttributeReadModel] = await handler.handle(query)
return [
    ProductAttributeResponse(
        id=item.id,
        product_id=item.product_id,
        attribute_id=item.attribute_id,
        attribute_value_id=item.attribute_value_id,
        attribute_code=item.attribute_code,
        attribute_name_i18n=item.attribute_name_i18n,
    )
    for item in items
]
```

- [ ] **Step 5: Verify syntax**

Run: `python -c "import ast; ast.parse(open('src/modules/catalog/application/queries/list_product_attributes.py').read()); print('OK')"`

- [ ] **Step 6: Commit**

```bash
git add src/modules/catalog/application/queries/read_models.py src/modules/catalog/application/queries/list_product_attributes.py src/modules/catalog/presentation/schemas.py src/modules/catalog/presentation/router_product_attributes.py
git commit -m "feat: implement list_product_attributes query handler (was stub)"
```

---

## Task 4: BaseRepository adoption (6 repos)

**Files:**

- Modify: `src/modules/catalog/infrastructure/repositories/brand.py`
- Modify: `src/modules/catalog/infrastructure/repositories/attribute_group.py`
- Modify: `src/modules/catalog/infrastructure/repositories/attribute.py`
- Modify: `src/modules/catalog/infrastructure/repositories/attribute_value.py`
- Modify: `src/modules/catalog/infrastructure/repositories/category_attribute_binding.py`
- Modify: `src/modules/catalog/infrastructure/repositories/product_attribute_value.py`
- Modify: `src/modules/catalog/infrastructure/repositories/base.py` (update docstring)

Each repo migration follows the same pattern:

1. Change class inheritance: `class XRepository(IXRepository)` → `class XRepository(BaseRepository[DomainX, OrmX], IXRepository, model_class=OrmX)`
2. Remove manual `__init__`, `add`, `get`, `update`, `delete` methods (inherited from BaseRepository)
3. Keep `_to_domain`, `_to_orm`, and all custom query methods
4. Remove now-unused imports (`delete` from sqlalchemy, `AsyncSession`)

- [ ] **Step 1: Migrate BrandRepository**

Rewrite `brand.py`:

```python
"""
Brand repository — Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Brand`
(domain) and the ``brands`` ORM table.  Provides slug-based lookups and
a ``FOR UPDATE`` lock method used by the logo processing pipeline.
"""

import uuid

from sqlalchemy import select

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class BrandRepository(
    BaseRepository[DomainBrand, OrmBrand],
    IBrandRepository,
    model_class=OrmBrand,
):
    """Data Mapper repository for the Brand aggregate.

    Inherits generic CRUD from BaseRepository. Adds slug-based lookups
    and pessimistic locking for the logo processing pipeline.
    """

    def _to_domain(self, orm: OrmBrand) -> DomainBrand:
        return DomainBrand(
            id=orm.id,
            name=orm.name,
            slug=orm.slug,
            logo_status=orm.logo_status,
            logo_file_id=orm.logo_file_id,
            logo_url=orm.logo_url,
        )

    def _to_orm(self, entity: DomainBrand, orm: OrmBrand | None = None) -> OrmBrand:
        if orm is None:
            orm = OrmBrand()
        orm.id = entity.id
        orm.name = entity.name
        orm.slug = entity.slug
        orm.logo_status = entity.logo_status
        orm.logo_file_id = entity.logo_file_id
        orm.logo_url = entity.logo_url
        return orm

    async def get_by_slug(self, slug: str) -> DomainBrand | None:
        stmt = select(OrmBrand).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def check_slug_exists(self, slug: str) -> bool:
        stmt = select(OrmBrand.id).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        stmt = select(OrmBrand.id).where(OrmBrand.slug == slug, OrmBrand.id != exclude_id).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        stmt = select(OrmBrand).where(OrmBrand.id == brand_id).with_for_update()
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
```

- [ ] **Step 2: Migrate AttributeGroupRepository**

Same pattern — inherit BaseRepository, remove manual CRUD, keep custom queries (`check_code_exists`, `get_by_code`, `has_attributes`, `move_attributes_to_group`).

- [ ] **Step 3: Migrate AttributeRepository**

Same pattern — keep `check_code_exists`, `check_slug_exists`, `check_*_excluding`, `get_by_slug`, `has_category_bindings`.

- [ ] **Step 4: Migrate AttributeValueRepository**

Same pattern — keep `check_code_exists`, `check_slug_exists`, `check_*_excluding`, `bulk_update_sort_order`.

- [ ] **Step 5: Migrate CategoryAttributeBindingRepository**

Same pattern — keep `exists`, `get_by_category_and_attribute`, `bulk_update_sort_order`, `bulk_update_requirement_level`.

- [ ] **Step 6: Migrate ProductAttributeValueRepository**

Same pattern — keep `exists`, `list_by_product`, `get_by_product_and_attribute`.

- [ ] **Step 7: Update BaseRepository docstring**

Remove the "only CategoryRepository" note from `base.py` module docstring. Replace with:

```python
"""
Base repository implementing the Data Mapper pattern for catalog aggregates.

Provides generic CRUD operations that convert between SQLAlchemy ORM models
and domain entities. Concrete repositories inherit from :class:`BaseRepository`
and supply the ``_to_domain`` / ``_to_orm`` mapping methods.

ProductRepository and MediaAssetRepository remain standalone due to their
complex custom logic (optimistic locking, SKU sync, processing status mapping).
"""
```

- [ ] **Step 8: Verify syntax on all 7 files**

```bash
python -c "
import ast
for f in ['src/modules/catalog/infrastructure/repositories/brand.py','src/modules/catalog/infrastructure/repositories/attribute_group.py','src/modules/catalog/infrastructure/repositories/attribute.py','src/modules/catalog/infrastructure/repositories/attribute_value.py','src/modules/catalog/infrastructure/repositories/category_attribute_binding.py','src/modules/catalog/infrastructure/repositories/product_attribute_value.py','src/modules/catalog/infrastructure/repositories/base.py']:
    with open(f) as fh: ast.parse(fh.read())
    print(f'{f.split(\"/\")[-1]} OK')
"
```

- [ ] **Step 9: Commit**

```bash
git add src/modules/catalog/infrastructure/repositories/
git commit -m "refactor: migrate 6 repos to BaseRepository, remove CRUD duplication"
```

---

## Task 5: Unified PATCH semantics via model_fields_set

This is done per-entity in 8 sub-steps. Each sub-step touches 4 layers: schema → router → command → entity.

**Key pattern for each entity:**

**Schema** — remove sentinels, all fields `Type | None = None`:

```python
class XUpdateRequest(CamelModel):
    field_a: str | None = None
    field_b: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> XUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
```

**Router** — build kwargs from model_fields_set:

```python
update_kwargs = {
    field: getattr(request, field)
    for field in request.model_fields_set
}
command = UpdateXCommand(x_id=x_id, **update_kwargs)
```

**Command** — all fields `None` default:

```python
@dataclass(frozen=True)
class UpdateXCommand:
    x_id: uuid.UUID
    field_a: str | None = None
    field_b: int | None = None
```

**Handler** — pass only provided kwargs to entity:

```python
update_kwargs = {}
if command.field_a is not None:
    update_kwargs["field_a"] = command.field_a
# for truly nullable fields, check if it was explicitly passed:
if "field_b" in provided_fields:  # or just pass through
    update_kwargs["field_b"] = command.field_b
entity.update(**update_kwargs)
```

**Simplification**: Since routers already filter to only provided fields via `model_fields_set`, the command will only have non-None values for fields that were actually sent. Handlers can simply pass all non-None command fields to the entity `.update()`. For truly nullable fields (where None IS a valid value to set), the router includes them in kwargs, the command receives them, and the handler passes them through.

### Sub-step 5.1: Brand (simplest — no sentinels currently)

**Files:**

- Modify: `src/modules/catalog/presentation/schemas.py` (BrandUpdateRequest)
- Modify: `src/modules/catalog/presentation/router_brands.py`
- Modify: `src/modules/catalog/application/commands/update_brand.py`

- [ ] **5.1.1: Update BrandUpdateRequest validator**

```python
class BrandUpdateRequest(CamelModel):
    """Partial update request -- all fields optional (PATCH semantics)."""
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")

    @model_validator(mode="after")
    def at_least_one_field(self) -> BrandUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
```

- [ ] **5.1.2: Update router_brands.py update endpoint**

```python
async def update_brand(...) -> BrandResponse:
    update_kwargs = {
        field: getattr(request, field)
        for field in request.model_fields_set
    }
    command = UpdateBrandCommand(brand_id=brand_id, **update_kwargs)
    ...
```

- [ ] **5.1.3: Verify and commit**

```bash
git commit -m "refactor(brand): use model_fields_set for PATCH semantics"
```

### Sub-step 5.2: Category

Same pattern. `CategoryUpdateRequest` already has all-None defaults. Just update validator.

- [ ] **5.2.1-5.2.3: Schema → Router → Commit**

### Sub-step 5.3: AttributeGroup

Same pattern. Simple schema, no sentinels.

- [ ] **5.3.1-5.3.3: Schema → Router → Commit**

### Sub-step 5.4: Attribute (has Ellipsis for validation_rules and group_id)

- [ ] **5.4.1: Update AttributeUpdateRequest** — remove `... # type: ignore`, all fields `None`
- [ ] **5.4.2: Update router_attributes.py** — use `model_fields_set`
- [ ] **5.4.3: Update update_attribute.py command** — remove `_SENTINEL`, fields default `None`
- [ ] **5.4.4: Update Attribute.update() in entities.py** — remove Ellipsis defaults, use `None`
- [ ] **5.4.5: Commit**

```bash
git commit -m "refactor(attribute): use model_fields_set for PATCH semantics"
```

### Sub-step 5.5: AttributeValue (has Ellipsis for value_group)

- [ ] **5.5.1-5.5.5: Same 5-step pattern as 5.4**

### Sub-step 5.6: CategoryAttributeBinding (has Ellipsis for flag_overrides/filter_settings)

- [ ] **5.6.1-5.6.5: Same 5-step pattern**

### Sub-step 5.7: SKU (has \_SENTINEL for compare_at_price)

- [ ] **5.7.1: Update SKUUpdateRequest** — remove `... # type: ignore`
- [ ] **5.7.2: Update router_skus.py** — use `model_fields_set`
- [ ] **5.7.3: Update update_sku.py** — remove `_SENTINEL` definition and usage
- [ ] **5.7.4: Update SKU.update() in entities.py** — remove `_SENTINEL` default
- [ ] **5.7.5: Commit**

### Sub-step 5.8: Product (has \_SENTINEL + \_UNSET, most complex)

- [ ] **5.8.1: Update ProductUpdateRequest** — remove `... # type: ignore` from `supplier_id`, `country_of_origin`
- [ ] **5.8.2: Update router_products.py** — remove `_UNSET`, use `model_fields_set`, filter out `version`
- [ ] **5.8.3: Update update_product.py** — remove `_SENTINEL` definition and usage
- [ ] **5.8.4: Update Product.update() in entities.py** — remove `_SENTINEL` default
- [ ] **5.8.5: Remove `_SENTINEL` module-level object from entities.py** (if no longer used by any entity)
- [ ] **5.8.6: Commit**

```bash
git commit -m "refactor(product): use model_fields_set for PATCH semantics"
```

- [ ] **Step 5.9: Final cleanup — remove \_SENTINEL from entities.py**

After all 8 entities are migrated, verify `_SENTINEL` is no longer referenced anywhere in entities.py. Remove the definition at module level.

Run: `grep -n "_SENTINEL" src/modules/catalog/domain/entities.py`

If no hits, it's already clean. Commit only if changes needed.

- [ ] **Step 5.10: Final syntax check**

```bash
python -c "
import ast
for f in [
    'src/modules/catalog/presentation/schemas.py',
    'src/modules/catalog/presentation/router_brands.py',
    'src/modules/catalog/presentation/router_categories.py',
    'src/modules/catalog/presentation/router_attribute_groups.py',
    'src/modules/catalog/presentation/router_attributes.py',
    'src/modules/catalog/presentation/router_attribute_values.py',
    'src/modules/catalog/presentation/router_category_bindings.py',
    'src/modules/catalog/presentation/router_skus.py',
    'src/modules/catalog/presentation/router_products.py',
    'src/modules/catalog/domain/entities.py',
]:
    with open(f) as fh: ast.parse(fh.read())
    print(f'{f.split(\"/\")[-1]} OK')
"
```
