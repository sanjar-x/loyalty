# ProductVariant — Design Spec

**Date:** 2026-03-23
**Status:** Approved
**Scope:** New `ProductVariant` entity — intermediate level between Product and SKU

---

## Problem

The UI shows product variations as tabs: each tab has its own name, media, attributes, and sizes. The current model has only Product → SKU (flat), with no entity representing a "variation group." MediaAsset links to `attribute_value_id` which only works for color-based grouping, not arbitrary admin-created variations.

## Solution

Introduce `ProductVariant` as a child entity of Product. SKUs become children of Variant instead of direct children of Product.

```
Product (brand, category, tags, status)
  └── ProductVariant (name, description, media, default price)
        └── SKU (sku_code, price override, variant_attributes)
```

**Breaking API change:** Old SKU paths (`/products/{id}/skus`) are removed. All SKU operations move under `/products/{id}/variants/{vid}/skus`. This is acceptable pre-production.

---

## 1. Data Model

### New table: `product_variants`

| Column           | Type          | Constraints                                         |
| ---------------- | ------------- | --------------------------------------------------- |
| id               | UUID          | PK                                                  |
| product_id       | UUID          | FK → products (CASCADE), NOT NULL                   |
| name_i18n        | JSONB         | NOT NULL, server_default `'{}'::jsonb`              |
| description_i18n | JSONB         | nullable                                            |
| sort_order       | int           | NOT NULL, server_default 0                          |
| default_price    | int           | nullable (smallest currency units)                  |
| default_currency | str(3)        | FK → currencies.code, server_default 'RUB'          |
| deleted_at       | timestamp(tz) | nullable (soft-delete, consistent with SKU pattern) |
| created_at       | timestamp(tz) | server_default now()                                |
| updated_at       | timestamp(tz) | server_default now(), onupdate now()                |

**Indexes:**

- `ix_product_variants_product_id` on `product_id`

### Changes to `skus`

- **Add:** `variant_id: UUID` — FK → product_variants (CASCADE), NOT NULL
- **Keep:** `product_id: UUID` — denormalized for query performance, NOT NULL
- **Add index:** `ix_skus_variant_id` on `variant_id`
- **Keep:** `variant_hash` globally unique constraint (unchanged — `uix_skus_variant_hash WHERE deleted_at IS NULL`)

### Changes to `media_assets`

- **Remove:** `attribute_value_id` column and its FK/indexes
- **Add:** `variant_id: UUID` — FK → product_variants (CASCADE), nullable
- When `variant_id = NULL`: media belongs to product generically (e.g., size guide)
- When `variant_id = UUID`: media belongs to a specific variation
- **Update index:** `uix_media_single_main_per_color` → `uix_media_single_main_per_variant` on `(product_id, variant_id)` WHERE `role = 'main'`

---

## 2. Domain Design

### ProductVariant (child entity, NOT aggregate root)

```python
@dataclass
class ProductVariant:
    id: uuid.UUID
    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: Money | None       # None = each SKU must specify its own price
    skus: list[SKU]                   # owned children
    deleted_at: datetime | None       # soft-delete
    created_at: datetime
    updated_at: datetime
```

**Invariants:**

- `name_i18n` must have at least 1 language entry
- SKU `variant_hash` uniqueness enforced globally (existing DB constraint preserved)
- Currency consistency: if `default_price` is set, all SKU prices within this variant that are not None must use the same currency as `default_currency`

**Factory method:**

```python
@classmethod
def create(cls, *, product_id, name_i18n, description_i18n=None,
           sort_order=0, default_price=None) -> ProductVariant
```

### Changes to Product

```python
@dataclass
class Product(AggregateRoot):
    # REPLACE: skus: list[SKU]
    # WITH:
    variants: list[ProductVariant]

    @classmethod
    def create(cls, *, slug, title_i18n, brand_id, primary_category_id,
               ...) -> Product:
        """Auto-creates 1 default variant with name_i18n = title_i18n."""

    def add_variant(self, *, name_i18n, ...) -> ProductVariant
    def find_variant(self, variant_id) -> ProductVariant | None
    def remove_variant(self, variant_id) -> None
        # Raises ValueError if this is the last non-deleted variant
        # Soft-deletes the variant and all its SKUs

    # SKU operations now go through variant:
    def add_sku(self, variant_id, *, sku_code, price, ...) -> SKU
    def find_sku(self, sku_id) -> SKU | None         # searches all variants
    def remove_sku(self, sku_id) -> None
```

**Minimum variant invariant:** `remove_variant` raises `ValueError("Cannot remove the last variant")` if only 1 non-deleted variant remains. A Product always has >= 1 active variant.

### Changes to SKU

- **Add:** `variant_id: uuid.UUID` — reference to parent variant
- **Keep:** `product_id: uuid.UUID` (denormalized)
- **`price` becomes `Money | None`** — nullable. When None, resolved from variant.default_price

**Cascading impact of nullable SKU.price:**

- `SKU.__attrs_post_init__`: compare_at_price validation only runs when `price is not None`. If price is None and compare_at_price is set, raise ValueError.
- `SKU.update(**kwargs)`: same validation — if resulting price is None, compare_at_price must also be None.
- ORM column `skus.price`: remove `server_default=text("0")`, make nullable.
- All consumers of `sku.price` must use `resolve_sku_price()` instead of direct access.

### Changes to MediaAsset

- **Remove:** `attribute_value_id`
- **Add:** `variant_id: uuid.UUID | None`

### Price Resolution (application layer)

```python
def resolve_sku_price(sku: SKU, variant: ProductVariant) -> Money:
    if sku.price is not None:
        return sku.price
    if variant.default_price is not None:
        return variant.default_price
    raise ValueError("No price: neither SKU nor variant has a price set")
```

---

## 3. API Design

### New endpoints

```
POST   /products/{product_id}/variants                    → create variant
GET    /products/{product_id}/variants                    → list variants with SKUs and media
PATCH  /products/{product_id}/variants/{variant_id}       → update variant
DELETE /products/{product_id}/variants/{variant_id}       → soft-delete variant + SKUs
```

### Changed endpoints

**SKU CRUD** — nested under variant:

```
POST   /products/{product_id}/variants/{variant_id}/skus
GET    /products/{product_id}/variants/{variant_id}/skus
PATCH  /products/{product_id}/variants/{variant_id}/skus/{sku_id}
DELETE /products/{product_id}/variants/{variant_id}/skus/{sku_id}
```

**Media schemas** — `attribute_value_id` → `variant_id` in ALL three schemas:

```python
class ProductMediaUploadRequest:
    variant_id: uuid.UUID | None    # was: attribute_value_id
    ...

class ProductMediaExternalRequest:
    variant_id: uuid.UUID | None    # was: attribute_value_id
    ...

class ProductMediaResponse:
    variant_id: uuid.UUID | None    # was: attribute_value_id
    ...
```

### Enriched Product response

```json
{
  "id": "...",
  "slug": "...",
  "title_i18n": { "ru": "Футболка BALENCIAGA" },
  "brand_id": "...",
  "primary_category_id": "...",
  "status": "draft",
  "variants": [
    {
      "id": "...",
      "name_i18n": { "ru": "Чёрная футболка BALENCIAGA x Adidas Logo" },
      "description_i18n": null,
      "sort_order": 0,
      "default_price": { "amount": 7990, "currency": "RUB" },
      "skus": [
        {
          "id": "...",
          "sku_code": "BLC-BLK-S",
          "price": null,
          "resolved_price": { "amount": 7990, "currency": "RUB" },
          "variant_attributes": [
            { "attribute_id": "...", "attribute_value_id": "..." }
          ]
        }
      ],
      "media": [
        {
          "id": "...",
          "public_url": "https://...",
          "role": "main",
          "sort_order": 0
        }
      ]
    }
  ]
}
```

### New schemas

```python
class ProductVariantCreateRequest(CamelModel):
    name_i18n: dict[str, str] = Field(..., min_length=1)
    description_i18n: dict[str, str] | None = None
    sort_order: int = Field(0, ge=0)
    default_price_amount: int | None = Field(None, ge=0)
    default_price_currency: str = Field("RUB", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")

class ProductVariantResponse(CamelModel):
    id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: MoneySchema | None
    skus: list[SKUResponse]
    media: list[ProductMediaResponse]
```

---

## 4. Repository & Infrastructure

### Repository strategy: no separate IProductVariantRepository

ProductVariant is a child entity of Product aggregate — managed through `IProductRepository`. No separate repository. Same pattern as existing SKU management.

### IProductRepository changes

- `get_with_skus()` → `get_with_variants()` — eagerly loads Product → Variants → SKUs → SKUAttributeValueLinks
- `update()` — syncs variants and their SKUs (extends existing `_sync_skus` to `_sync_variants`)

### IMediaAssetRepository changes

- `has_main_for_variant(product_id, variant_id)` — parameter renamed from `attribute_value_id` to `variant_id`
- `list_by_product()` — orders by `(variant_id, sort_order)`
- `list_by_variant(variant_id)` — new method, returns media for a single variant

### ORM Model: ProductVariant

```python
class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(FK("products.id", ondelete="CASCADE"))
    name_i18n: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB))
    description_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    default_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_currency: Mapped[str] = mapped_column(String(3), FK("currencies.code"), server_default=text("'RUB'"))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    product: Mapped[Product] = relationship("Product", back_populates="variants")
    skus: Mapped[list[SKU]] = relationship("SKU", back_populates="variant", cascade="all, delete-orphan")
    media_assets: Mapped[list[MediaAsset]] = relationship("MediaAsset", back_populates="variant")
```

---

## 5. DB Migration Strategy

Project is NOT in production. Single migration:

1. Create `product_variants` table
2. For each existing Product: insert 1 default variant (`name_i18n = product.title_i18n`)
3. Add `variant_id` column to `skus` (nullable initially)
4. Update all SKU rows: set `variant_id` = default variant for their product
5. Make `variant_id` NOT NULL
6. Add `variant_id` column to `media_assets` (nullable)
7. Assign variant-bound media assets to the default variant (product-generic media stays NULL):
   ```sql
   UPDATE media_assets SET variant_id = (
       SELECT id FROM product_variants
       WHERE product_id = media_assets.product_id LIMIT 1
   ) WHERE attribute_value_id IS NOT NULL;
   ```
   Note: Media with `attribute_value_id = NULL` (product-generic, e.g., size_guide) keeps `variant_id = NULL`.
8. Drop `attribute_value_id` column from `media_assets`
9. Remove `color_attribute` relationship and `ix_media_assets_product_attr` index from MediaAsset ORM
9. Update indexes and constraints (rename `uix_media_single_main_per_color` → `uix_media_single_main_per_variant`)

---

## 6. Files to Change

### Domain layer

- `src/modules/catalog/domain/entities.py` — new ProductVariant class; Product.variants replaces .skus; SKU gains variant_id; SKU.price becomes nullable; MediaAsset: attribute_value_id → variant_id
- `src/modules/catalog/domain/events.py` — new ProductVariantCreatedEvent (optional, Phase 2)
- `src/modules/catalog/domain/interfaces.py` — IProductRepository changes (get_with_variants), IMediaAssetRepository changes
- `src/modules/catalog/domain/exceptions.py` — new VariantNotFoundError, LastVariantRemovalError

### Infrastructure layer

- `src/modules/catalog/infrastructure/models.py` — new ProductVariant ORM; **Remove** `Product.skus` relationship (replaced by `Product.variants`); SKU.variant_id + variant relationship; MediaAsset: remove `attribute_value_id`, `color_attribute` relationship, `ix_media_assets_product_attr` index; add `variant_id` + `variant` relationship
- `src/modules/catalog/infrastructure/repositories/product.py` — \_sync_variants, get_with_variants, mapping changes
- `src/modules/catalog/infrastructure/repositories/media_asset.py` — parameter renames, new list_by_variant

### Application layer

- `src/modules/catalog/application/commands/add_sku.py` — takes variant_id; `AddSKUCommand.price_amount` becomes `int | None` (nullable, inherits from variant)
- `src/modules/catalog/application/commands/update_sku.py` — variant_id awareness; needs variant context for price fallback when `sku.price` is None
- `src/modules/catalog/application/commands/delete_sku.py` — variant_id awareness
- `src/modules/catalog/application/commands/add_product_media.py` — `attribute_value_id` → `variant_id` in command, handler, and constraint name `"uix_media_single_main_per_color"` → `"uix_media_single_main_per_variant"`
- `src/modules/catalog/application/commands/add_external_product_media.py` — same rename as add_product_media (command, result, handler, constraint name)
- `src/modules/catalog/application/queries/list_skus.py` — filter by variant_id; `sku_orm_to_read_model()` must handle nullable price
- `src/modules/catalog/application/queries/get_product.py` — load variants with SKUs; price aggregation must use resolve_sku_price()
- `src/modules/catalog/application/queries/list_product_media.py` — `attribute_value_id` → `variant_id` in read model, query, mapping
- `src/modules/catalog/application/queries/read_models.py` — new `ProductVariantReadModel`; `SKUReadModel.price` becomes nullable + add `resolved_price`; `ProductReadModel.skus` → `variants`; `MediaAssetReadModel.attribute_value_id` → `variant_id`
- `src/modules/catalog/presentation/mappers.py` — `to_sku_response()` must handle nullable `model.price` (use resolved_price)
- New: `src/modules/catalog/application/commands/add_variant.py`
- New: `src/modules/catalog/application/commands/update_variant.py`
- New: `src/modules/catalog/application/commands/delete_variant.py`
- New: `src/modules/catalog/application/queries/list_variants.py`

### Presentation layer

- `src/modules/catalog/presentation/schemas.py` — ProductVariantCreateRequest, ProductVariantUpdateRequest, ProductVariantResponse; updated ProductResponse (skus → variants); `SKUResponse` gains `resolved_price: MoneySchema`, `price` becomes nullable; `ProductMediaUploadRequest`, `ProductMediaExternalRequest`, `ProductMediaResponse`: `attribute_value_id` → `variant_id`; `SKUCreateRequest.price_amount` becomes optional
- `src/modules/catalog/presentation/router_skus.py` — rewrite under /variants/{vid}/skus
- New: `src/modules/catalog/presentation/router_variants.py`
- `src/modules/catalog/presentation/router_product_media.py` — attribute_value_id → variant_id
- `src/modules/catalog/presentation/dependencies.py` — register new handlers
- `src/api/router.py` — mount variant router

### Migration

- New: `alembic/versions/YYYY/MM/DD_product_variants.py`

---

## 7. Phasing

**Phase 1 (this spec):**

- Domain entity: ProductVariant with soft-delete
- ORM model + migration
- Product aggregate changes (variants replace skus)
- Repository changes (sync_variants, get_with_variants)
- Variant CRUD endpoints
- SKU endpoints moved under variant
- Media field rename (attribute_value_id → variant_id)
- Product response enriched with variants
- Price resolution (SKU → variant fallback)

**Phase 2 (separate spec):**

- Storefront query adaptation for variant-aware display
- BFF layer impact (new response structure)
- Price resolution caching / denormalization
- ProductVariant domain events
- Performance optimization
