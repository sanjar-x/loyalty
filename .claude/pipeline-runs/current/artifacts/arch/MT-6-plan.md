# Architecture Plan -- MT-6: Add Product read models

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-6
> **Layer:** Application
> **Module:** catalog
> **FR Reference:** FR-001, FR-003, FR-004
> **Depends on:** MT-2, MT-3

---

## Research findings

- **Pydantic v2**: `BaseModel` supports nested models, `list[SubModel]`, optional fields with `| None = None`, and `computed_field` via `@property` decorator. All read models in this codebase inherit directly from `BaseModel` (not `CamelModel` -- that is presentation-layer only).
- **Existing pattern**: All read models in `read_models.py` follow a consistent convention: flat `BaseModel` classes with explicit field types, paginated list models with `items: list[ItemModel]`, `total: int`, `offset: int`, `limit: int`.
- **No domain imports**: Existing read models use only `uuid.UUID`, `str`, `int`, `dict[str, Any]`, `list[...]` -- never domain entities or value objects. Money is represented as nested sub-model with `amount: int` and `currency: str`.

---

## Design decisions

| Decision                                  | Choice                                                                                                           | Rationale                                                                                                                                              |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Money representation in read models       | Dedicated `MoneyReadModel(BaseModel)` with `amount: int`, `currency: str`                                        | Avoids importing domain `Money` VO; keeps read models framework-agnostic from domain. Consistent with CQRS read-side independence.                     |
| SKU variant attributes in read model      | `list[VariantAttributePairReadModel]` with `attribute_id` + `attribute_value_id`                                 | Matches domain SKU's `variant_attributes: list[tuple[uuid.UUID, uuid.UUID]]` but uses a named model instead of raw tuple for clarity in serialization. |
| min_price / max_price on ProductReadModel | Plain `int                                                                                                       | None` fields (not Money)                                                                                                                               | These are computed aggregations across SKUs. Query handler will compute them. Keeping as `int | None` is simpler; currency is implicit from the SKU prices. |
| ProductListItemReadModel fields           | Lightweight subset: id, slug, title_i18n, status, brand_id, primary_category_id, version, created_at, updated_at | Matches MT-6 acceptance criteria. Includes timestamps for admin list sorting.                                                                          |
| Datetime fields                           | `datetime` type (from stdlib)                                                                                    | Consistent with domain entities; serialization handled by Pydantic.                                                                                    |

---

## File plan

### `src/modules/catalog/application/queries/read_models.py` -- MODIFY

**Purpose:** Add Product-related read models (DTOs) for CQRS query handlers.
**Layer:** Application

#### Classes / functions:

**`MoneyReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `amount: int` -- monetary amount in smallest currency units
  - `currency: str` -- 3-character ISO 4217 code

**`VariantAttributePairReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `attribute_id: uuid.UUID`
  - `attribute_value_id: uuid.UUID`

**`SKUReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `id: uuid.UUID`
  - `product_id: uuid.UUID`
  - `sku_code: str`
  - `variant_hash: str`
  - `price: MoneyReadModel`
  - `compare_at_price: MoneyReadModel | None = None`
  - `is_active: bool`
  - `version: int`
  - `deleted_at: datetime | None = None`
  - `created_at: datetime`
  - `updated_at: datetime`
  - `variant_attributes: list[VariantAttributePairReadModel]`

**`ProductAttributeValueReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `id: uuid.UUID`
  - `product_id: uuid.UUID`
  - `attribute_id: uuid.UUID`
  - `attribute_value_id: uuid.UUID`

**`ProductReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `id: uuid.UUID`
  - `slug: str`
  - `title_i18n: dict[str, str]`
  - `description_i18n: dict[str, str]`
  - `status: str` -- string value of ProductStatus enum (not the enum itself, to avoid domain import)
  - `brand_id: uuid.UUID`
  - `primary_category_id: uuid.UUID`
  - `supplier_id: uuid.UUID | None = None`
  - `country_of_origin: str | None = None`
  - `tags: list[str]`
  - `version: int`
  - `deleted_at: datetime | None = None`
  - `created_at: datetime`
  - `updated_at: datetime`
  - `published_at: datetime | None = None`
  - `min_price: int | None = None` -- computed from active SKUs (smallest amount)
  - `max_price: int | None = None` -- computed from active SKUs (largest amount)
  - `skus: list[SKUReadModel]`
  - `attributes: list[ProductAttributeValueReadModel]`

**`ProductListItemReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `id: uuid.UUID`
  - `slug: str`
  - `title_i18n: dict[str, str]`
  - `status: str`
  - `brand_id: uuid.UUID`
  - `primary_category_id: uuid.UUID`
  - `version: int`
  - `created_at: datetime`
  - `updated_at: datetime`

**`ProductListReadModel`** (new)

- Inherits from: `BaseModel` (from `pydantic`)
- Fields:
  - `items: list[ProductListItemReadModel]`
  - `total: int`
  - `offset: int`
  - `limit: int`

#### Imports:

```python
# Already present in file:
from __future__ import annotations
import uuid
from typing import Any
from pydantic import BaseModel

# New import needed:
from datetime import datetime
```

#### Structural sketch (pseudo-code only):

```python
# Append after the existing Storefront read models section:

# ---------------------------------------------------------------------------
# Product read models
# ---------------------------------------------------------------------------

class MoneyReadModel(BaseModel):
    """Read model for a monetary value."""
    amount: int
    currency: str

class VariantAttributePairReadModel(BaseModel):
    """A single variant attribute pair (attribute + value)."""
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID

class SKUReadModel(BaseModel):
    """Read model for a single SKU (product variant)."""
    id: uuid.UUID
    product_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: MoneyReadModel
    compare_at_price: MoneyReadModel | None = None
    is_active: bool
    version: int
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    variant_attributes: list[VariantAttributePairReadModel]

class ProductAttributeValueReadModel(BaseModel):
    """Read model for a product-attribute assignment."""
    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID

class ProductReadModel(BaseModel):
    """Full read model for a single product with nested SKUs and attributes."""
    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    description_i18n: dict[str, str]
    status: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str]
    version: int
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    min_price: int | None = None
    max_price: int | None = None
    skus: list[SKUReadModel]
    attributes: list[ProductAttributeValueReadModel]

class ProductListItemReadModel(BaseModel):
    """Lightweight read model for product list items."""
    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    status: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime

class ProductListReadModel(BaseModel):
    """Paginated product list read model."""
    items: list[ProductListItemReadModel]
    total: int
    offset: int
    limit: int
```

#### Placement in file:

Append all new classes **after** the existing `StorefrontFormReadModel` class (line ~306), following the established section comment pattern with a separator block.

---

## Dependency registration

No DI changes required for this micro-task. Read models are plain data classes, not injected services.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. Read models are consumed by query handlers (MT-15) and presentation schemas (MT-19).

## Risks & edge cases

| Risk                                                                     | Impact                                                                      | Mitigation                                                                                          |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------ |
| `datetime` import may conflict with `from __future__ import annotations` | No impact -- Pydantic v2 resolves string annotations at validation time     | Verified: Pydantic v2 handles `from __future__ import annotations` correctly with `datetime` types  |
| `status` as `str` instead of enum                                        | Query handlers must convert `ProductStatus.value` to string when populating | This is intentional -- avoids domain import in read models. Document in query handler plan (MT-15). |
| `min_price`/`max_price` without currency                                 | Consumer must infer currency from SKU prices                                | Acceptable for MVP admin API. Future enhancement could add `price_currency: str                     | None`. |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**

- [ ] `MoneyReadModel` has `amount: int` and `currency: str` fields
- [ ] `SKUReadModel` has all SKU fields including `price: MoneyReadModel` and `variant_attributes: list[VariantAttributePairReadModel]`
- [ ] `ProductAttributeValueReadModel` has `id`, `product_id`, `attribute_id`, `attribute_value_id`
- [ ] `ProductReadModel` has all product fields plus `min_price`, `max_price`, `skus`, `attributes`
- [ ] `ProductListItemReadModel` is lightweight (id, slug, title_i18n, status, brand_id, primary_category_id, version)
- [ ] `ProductListReadModel` has `items`, `total`, `offset`, `limit`
- [ ] No domain entity imports in read_models.py (status is `str`, not `ProductStatus`)
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports
- [ ] All read models inherit from `BaseModel` (not `CamelModel`)
- [ ] File passes `ruff check` and `mypy`
