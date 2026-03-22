# ProductVariant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `ProductVariant` as an intermediate entity between Product and SKU, enabling the UI's variation-tab model where each tab has its own name, media, attributes, and prices.

**Architecture:** ProductVariant is a child entity of Product (same pattern as existing SKU). Product.skus is replaced by Product.variants, where each variant owns its SKUs. MediaAsset.attribute_value_id is replaced by variant_id. SKU.price becomes nullable with fallback to variant.default_price. This is a breaking API change (pre-production).

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, attrs, Dishka DI, Alembic

**Spec:** `docs/superpowers/specs/2026-03-23-product-variant-design.md`

---

## Task 1: Domain Layer — ProductVariant entity + Product/SKU/MediaAsset changes

**Files:**

- Modify: `src/modules/catalog/domain/entities.py`
- Modify: `src/modules/catalog/domain/exceptions.py`
- Modify: `src/modules/catalog/domain/interfaces.py`

This is the foundation. All other tasks depend on it.

- [ ] **Step 1: Add new domain exceptions**

In `src/modules/catalog/domain/exceptions.py`, add:

```python
class VariantNotFoundError(NotFoundError):
    """Raised when a product variant lookup yields no result."""
    def __init__(self, variant_id: uuid.UUID | str, product_id: uuid.UUID | str | None = None):
        details: dict[str, str] = {"variant_id": str(variant_id)}
        if product_id is not None:
            details["product_id"] = str(product_id)
        super().__init__(
            message=f"Product variant with ID {variant_id} not found.",
            error_code="VARIANT_NOT_FOUND",
            details=details,
        )

class LastVariantRemovalError(UnprocessableEntityError):
    """Raised when attempting to remove the last active variant from a product."""
    def __init__(self, product_id: uuid.UUID) -> None:
        super().__init__(
            message="Cannot remove the last variant from a product.",
            error_code="LAST_VARIANT_REMOVAL",
            details={"product_id": str(product_id)},
        )
```

- [ ] **Step 2: Add ProductVariant entity to entities.py**

Add `ProductVariant` class between the SKU section and the MediaAsset section in `entities.py`. It is a child entity (NOT AggregateRoot), following the same attrs `@dataclass` pattern as SKU:

```python
@dataclass
class ProductVariant:
    """Product variant — a named variation grouping that owns SKUs.

    Child entity of the Product aggregate. Each variant represents a
    tab in the admin UI with its own name, media, and set of SKUs.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: Money | None
    default_currency: str
    skus: list[SKU]
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))

    @classmethod
    def create(cls, *, product_id, name_i18n, description_i18n=None,
               sort_order=0, default_price=None, default_currency="RUB",
               variant_id=None) -> ProductVariant:
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")
        return cls(
            id=variant_id or _generate_id(),
            product_id=product_id,
            name_i18n=name_i18n,
            description_i18n=description_i18n,
            sort_order=sort_order,
            default_price=default_price,
            default_currency=default_currency,
            skus=[],
        )

    def soft_delete(self) -> None:
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now
        for sku in self.skus:
            if sku.deleted_at is None:
                sku.soft_delete()
```

- [ ] **Step 3: Add variant_id to SKU, make price nullable**

In `entities.py`, modify the SKU class:

- Add `variant_id: uuid.UUID` field after `product_id`
- Change `price: Money` to `price: Money | None = None`
- Update `__attrs_post_init__`: only validate compare_at_price when price is not None. If price is None and compare_at_price is not None, raise ValueError.
- Update `update(**kwargs)`: same validation — if resulting price is None, compare_at_price must also be None.

- [ ] **Step 4: Change MediaAsset: attribute_value_id → variant_id**

In `entities.py`, in the MediaAsset class:

- Rename field `attribute_value_id` to `variant_id`
- Update `create_upload()` and `create_external()` factory methods: rename parameter `attribute_value_id` to `variant_id`

- [ ] **Step 5: Refactor Product aggregate: skus → variants**

In `entities.py`, modify Product class:

- Replace `skus: list[SKU] = field(factory=list)` with `variants: list[ProductVariant] = field(factory=list)`
- Update `Product.create()`: auto-create 1 default variant with `name_i18n=title_i18n`
- Add `add_variant()`, `find_variant()`, `remove_variant()` methods
- Refactor `add_sku(variant_id, ...)`: find variant, create SKU with variant_id, append to variant.skus
- Refactor `find_sku()`: search through all variants
- Refactor `remove_sku()`: search through all variants
- `remove_variant()`: raises `LastVariantRemovalError` if only 1 non-deleted variant remains; soft-deletes variant and all its SKUs
- Update `compute_variant_hash()` — keep as Product static method (global uniqueness)
- Remove old `skus` property/field entirely

- [ ] **Step 6: Update IProductRepository interface**

In `interfaces.py`:

- Rename `get_with_skus` → `get_with_variants`
- Update return type docstrings

- [ ] **Step 7: Update IMediaAssetRepository interface**

In `interfaces.py`:

- `has_main_for_variant(product_id, variant_id)` — rename parameter from `attribute_value_id`
- `list_by_product()` — update docstring (orders by variant_id, sort_order)
- Add `list_by_variant(variant_id) -> list[DomainMediaAsset]`

- [ ] **Step 8: Verify syntax**

```bash
python -c "
import ast
for f in ['src/modules/catalog/domain/entities.py', 'src/modules/catalog/domain/exceptions.py', 'src/modules/catalog/domain/interfaces.py']:
    with open(f) as fh: ast.parse(fh.read())
    print(f'{f.split(\"/\")[-1]} OK')
"
```

- [ ] **Step 9: Commit**

```bash
git add src/modules/catalog/domain/
git commit -m "feat: add ProductVariant domain entity, refactor Product → Variants → SKUs"
```

---

## Task 2: Infrastructure Layer — ORM model + Migration

**Files:**

- Modify: `src/modules/catalog/infrastructure/models.py`
- Modify: `src/modules/catalog/infrastructure/repositories/product.py`
- Modify: `src/modules/catalog/infrastructure/repositories/media_asset.py`
- Modify: `src/infrastructure/database/registry.py`
- Create: Alembic migration file

- [ ] **Step 1: Add ProductVariant ORM model to models.py**

Add the `ProductVariant` ORM class between Product and MediaAsset in models.py. Follow the exact column spec from section 4 of the design spec.

- [ ] **Step 2: Update Product ORM model**

- **Remove** `skus` relationship (`cascade="all, delete-orphan"`)
- **Add** `variants: Mapped[list[ProductVariant]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")`

- [ ] **Step 3: Update SKU ORM model**

- Add `variant_id` FK column: `variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), index=True)`
- Add `variant` relationship: `variant: Mapped[ProductVariant] = relationship("ProductVariant", back_populates="skus")`
- Change `product` relationship: keep but remove `back_populates="skus"` (now it's a read-only convenience)
- Make `price` column nullable: remove `server_default=text("0")`, add `nullable=True`

- [ ] **Step 4: Update MediaAsset ORM model**

- Remove `attribute_value_id` column, FK, and `color_attribute` relationship
- Add `variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True)`
- Add `variant: Mapped[ProductVariant | None] = relationship("ProductVariant", back_populates="media_assets")`
- Rename index `uix_media_single_main_per_color` → `uix_media_single_main_per_variant` on `(product_id, variant_id)`
- Remove `ix_media_assets_product_attr` index

- [ ] **Step 5: Update database registry**

In `src/infrastructure/database/registry.py`, add `ProductVariant` import and `__all__` entry.

- [ ] **Step 6: Refactor ProductRepository — \_sync_variants**

In `repositories/product.py`:

- Rename `_sync_skus` → add `_sync_variants` (two-level sync: variants then SKUs within each variant)
- Rename `get_with_skus` → `get_with_variants` with 3-level selectinload: `Product.variants → Variant.skus → SKU.attribute_values`
- Update `_to_domain` and `_to_orm` to handle Product.variants instead of Product.skus
- Add variant-level mapping helpers: `_variant_to_domain`, `_variant_to_orm`

- [ ] **Step 7: Refactor MediaAssetRepository**

In `repositories/media_asset.py`:

- Rename `attribute_value_id` parameter → `variant_id` in `has_main_for_variant`
- Update `list_by_product` ordering: `(variant_id, sort_order)`
- Add `list_by_variant(variant_id)` method

- [ ] **Step 8: Create Alembic migration**

Run: `alembic revision --autogenerate -m "add_product_variants"`

The autogenerated migration will handle schema changes (new table, new columns, dropped columns). **Manually add** these data backfill steps in `upgrade()` between the schema changes:

```python
# After creating product_variants table:
op.execute("""
    INSERT INTO product_variants (id, product_id, name_i18n, sort_order, default_currency, created_at, updated_at)
    SELECT gen_random_uuid(), id, title_i18n, 0, 'RUB', now(), now()
    FROM products
""")

# After adding variant_id column to skus (nullable):
op.execute("""
    UPDATE skus SET variant_id = (
        SELECT pv.id FROM product_variants pv WHERE pv.product_id = skus.product_id LIMIT 1
    )
""")
# Then ALTER variant_id to NOT NULL

# After adding variant_id column to media_assets (nullable):
op.execute("""
    UPDATE media_assets SET variant_id = (
        SELECT pv.id FROM product_variants pv WHERE pv.product_id = media_assets.product_id LIMIT 1
    ) WHERE attribute_value_id IS NOT NULL
""")
# Then DROP attribute_value_id column

# Rename constraint:
op.execute("ALTER INDEX uix_media_single_main_per_color RENAME TO uix_media_single_main_per_variant")
```

- [ ] **Step 9: Verify syntax**

```bash
python -c "
import ast
for f in ['src/modules/catalog/infrastructure/models.py', 'src/modules/catalog/infrastructure/repositories/product.py', 'src/modules/catalog/infrastructure/repositories/media_asset.py']:
    with open(f) as fh: ast.parse(fh.read())
    print(f'{f.split(\"/\")[-1]} OK')
"
```

- [ ] **Step 10: Commit**

```bash
git add src/modules/catalog/infrastructure/ src/infrastructure/database/registry.py alembic/
git commit -m "feat: add ProductVariant ORM model, refactor repos, create migration"
```

---

## Task 3: Application Layer — Variant CRUD commands + queries

**Files:**

- Create: `src/modules/catalog/application/commands/add_variant.py`
- Create: `src/modules/catalog/application/commands/update_variant.py`
- Create: `src/modules/catalog/application/commands/delete_variant.py`
- Create: `src/modules/catalog/application/queries/list_variants.py`
- Modify: `src/modules/catalog/application/queries/read_models.py`

- [ ] **Step 1: Add ProductVariantReadModel to read_models.py**

```python
class ProductVariantReadModel(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: MoneyReadModel | None
    skus: list[SKUReadModel]
```

Also add the `resolve_sku_price` utility function to `read_models.py` (alongside the read model definitions — this is the application layer's single source of truth for price resolution):

```python
def resolve_sku_price(sku_price: MoneyReadModel | None, variant_default: MoneyReadModel | None) -> MoneyReadModel:
    """Resolve effective SKU price: SKU override → variant default → error."""
    if sku_price is not None:
        return sku_price
    if variant_default is not None:
        return variant_default
    raise ValueError("No price: neither SKU nor variant has a price set")
```

Also update `ProductReadModel`: replace `skus: list[SKUReadModel]` with `variants: list[ProductVariantReadModel]`.

Update `SKUReadModel`: add `variant_id: uuid.UUID`, make `price: MoneyReadModel | None`, add `resolved_price: MoneyReadModel`.

Update `MediaAssetReadModel` (in list_product_media.py): rename `attribute_value_id` → `variant_id`.

- [ ] **Step 2: Create add_variant.py**

Follow the existing `add_sku.py` pattern: AddVariantCommand, AddVariantResult, AddVariantHandler. Handler loads product via `get_with_variants`, calls `product.add_variant()`, updates, commits.

- [ ] **Step 3: Create update_variant.py**

Follow `update_brand.py` pattern with `_provided_fields` for PATCH. UpdateVariantCommand, UpdateVariantResult, UpdateVariantHandler.

- [ ] **Step 4: Create delete_variant.py**

Follow `delete_sku.py` pattern. Handler loads product, calls `product.remove_variant(variant_id)`, updates, commits. LastVariantRemovalError propagates to the API as 422.

- [ ] **Step 5: Create list_variants.py**

CQRS read-side query handler. Uses AsyncSession + ORM directly. Returns `list[ProductVariantReadModel]` with nested SKUs and media.

- [ ] **Step 6: Verify syntax + Commit**

```bash
git add src/modules/catalog/application/
git commit -m "feat: add Variant CRUD command/query handlers"
```

---

## Task 4: Application Layer — Refactor existing SKU + Media handlers

**Files:**

- Modify: `src/modules/catalog/application/commands/add_sku.py`
- Modify: `src/modules/catalog/application/commands/update_sku.py`
- Modify: `src/modules/catalog/application/commands/delete_sku.py`
- Modify: `src/modules/catalog/application/commands/add_product_media.py`
- Modify: `src/modules/catalog/application/commands/add_external_product_media.py`
- Modify: `src/modules/catalog/application/queries/list_skus.py`
- Modify: `src/modules/catalog/application/queries/get_product.py`
- Modify: `src/modules/catalog/application/queries/list_product_media.py`
- Modify: `src/modules/catalog/presentation/mappers.py`

- [ ] **Step 1: Refactor add_sku.py**

- Add `variant_id: uuid.UUID` to `AddSKUCommand`
- Make `price_amount: int | None = None` (nullable — can inherit from variant)
- Handler uses `get_with_variants` instead of `get_with_skus`
- Handler calls `product.add_sku(variant_id, ...)` instead of `product.add_sku(...)`

- [ ] **Step 2: Refactor update_sku.py**

- Needs variant context for price fallback when `sku.price` is None
- When `sku.price` is None and only currency is updated, must use variant.default_price as base
- Update variant_hash iteration to search through product.variants[].skus

- [ ] **Step 3: Refactor delete_sku.py**

- Uses `get_with_variants` instead of `get_with_skus`
- Calls `product.remove_sku(sku_id)` (unchanged — Product method searches all variants)

- [ ] **Step 4: Refactor media command handlers**

In `add_product_media.py` and `add_external_product_media.py`:

- Rename `attribute_value_id` → `variant_id` in command, result, handler
- Update constraint name string: `"uix_media_single_main_per_color"` → `"uix_media_single_main_per_variant"`
- Update `MediaAsset.create_upload(variant_id=...)` call

- [ ] **Step 5: Refactor query handlers**

In `list_skus.py`:

- `sku_orm_to_read_model()`: handle nullable price — add `resolved_price` field
- Filter by variant_id instead of product_id (or add variant_id parameter)

In `get_product.py`:

- Use `get_with_variants` selectinload pattern (3 levels)
- Build `ProductVariantReadModel` list instead of flat SKU list
- Price aggregation uses `resolve_sku_price()`

In `list_product_media.py`:

- Rename `attribute_value_id` → `variant_id` in ORM query and read model

- [ ] **Step 6: Update mappers.py**

`to_sku_response()`: handle nullable `model.price`. Add `resolved_price` to response.

- [ ] **Step 7: Verify syntax + Commit**

```bash
git add src/modules/catalog/application/ src/modules/catalog/presentation/mappers.py
git commit -m "refactor: adapt SKU and media handlers for ProductVariant"
```

---

## Task 5: Presentation Layer — Schemas + Variant Router

**Files:**

- Modify: `src/modules/catalog/presentation/schemas.py`
- Create: `src/modules/catalog/presentation/router_variants.py`
- Modify: `src/modules/catalog/presentation/router_skus.py`
- Modify: `src/modules/catalog/presentation/router_product_media.py`
- Modify: `src/modules/catalog/presentation/router_products.py`

- [ ] **Step 1: Add variant schemas to schemas.py**

Add `ProductVariantCreateRequest`, `ProductVariantUpdateRequest`, `ProductVariantResponse`. Update `ProductResponse` to use `variants: list[ProductVariantResponse]` instead of `skus: list[SKUResponse]`. Update `SKUResponse`: make `price` nullable, add `resolved_price: MoneySchema`. Make `SKUCreateRequest.price_amount` optional. Rename `attribute_value_id` → `variant_id` in `ProductMediaUploadRequest`, `ProductMediaExternalRequest`, `ProductMediaResponse`.

- [ ] **Step 2: Create router_variants.py**

New router with CRUD endpoints:

```
POST   /products/{product_id}/variants
GET    /products/{product_id}/variants
PATCH  /products/{product_id}/variants/{variant_id}
DELETE /products/{product_id}/variants/{variant_id}
```

Follow the existing router patterns (Dishka DI, RequirePermission, path= keyword, description=).

- [ ] **Step 3: Rewrite router_skus.py**

Change prefix to `/products/{product_id}/variants/{variant_id}/skus`. Add `variant_id: uuid.UUID` to all endpoint signatures. Update command construction to pass `variant_id`.

- [ ] **Step 4: Update router_product_media.py**

Rename `attribute_value_id` → `variant_id` in request parameter mapping.

- [ ] **Step 5: Update router_products.py**

Update `_to_product_response()` to map variants instead of flat SKUs.

- [ ] **Step 6: Verify syntax + Commit**

```bash
git add src/modules/catalog/presentation/
git commit -m "feat: add variant router, rewrite SKU router under variants, update schemas"
```

---

## Task 6: DI Wiring + Router Mounting

**Files:**

- Modify: `src/modules/catalog/presentation/dependencies.py`
- Modify: `src/api/router.py`

- [ ] **Step 1: Register new handlers in dependencies.py**

Add to `ProductProvider`:

- `AddVariantHandler`
- `UpdateVariantHandler`
- `DeleteVariantHandler`
- `ListVariantsHandler`

- [ ] **Step 2: Mount variant router in api/router.py**

Import `router_variants` and include it under `/catalog` prefix.

- [ ] **Step 3: Verify syntax + Commit**

```bash
git add src/modules/catalog/presentation/dependencies.py src/api/router.py
git commit -m "feat: wire ProductVariant DI providers and mount router"
```

---

## Task 7: Integration Verification

- [ ] **Step 1: Full syntax check on all modified files**

```bash
python -c "
import ast, glob
for f in glob.glob('src/modules/catalog/**/*.py', recursive=True):
    with open(f) as fh: ast.parse(fh.read())
print('All catalog files OK')
"
```

- [ ] **Step 2: Verify no broken references**

```bash
# No leftover attribute_value_id in catalog module (except attribute EAV which is correct)
grep -rn 'attribute_value_id' src/modules/catalog/ --include='*.py' | grep -v 'sku_attribute\|SKUAttribute\|variant_attribute\|VariantAttribute\|ProductAttribute\|assign_product\|remove_product\|list_product_attr'
```

- [ ] **Step 3: Verify no leftover Product.skus references**

```bash
grep -rn '\.skus\b' src/modules/catalog/ --include='*.py' | grep -v 'variant.*skus\|_sync\|test'
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: ProductVariant implementation complete (Phase 1)"
```
