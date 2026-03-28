# Phase 9: Entity God-Class Refactoring — Research

**Researched:** 2026-03-28
**Status:** Complete

## Objective

Determine the safest, most mechanical approach to split the 2,220-line `backend/src/modules/catalog/domain/entities.py` into an `entities/` package with one file per entity class, preserving all 68+ import sites and passing the full test suite with zero changes.

## Source File Analysis

### File Structure (line ranges)

| Section | Lines | Description |
|---------|-------|-------------|
| Module docstring + imports | 1-71 | Standard library, attrs, domain events/exceptions/value_objects, AggregateRoot |
| Helper functions | 72-137 | `GENERAL_GROUP_CODE`, `_validate_slug()`, `_generate_id()`, `_validate_sort_order()`, `_validate_i18n_values()`, `_validate_filter_settings()`, `_FILTER_SETTINGS_MAX_KEYS`, `_FILTER_SETTINGS_ALLOWED_KEYS` |
| Guarded field sets | 139-149 | `_PRODUCT_GUARDED_FIELDS`, `_BRAND_GUARDED_FIELDS`, `_CATEGORY_GUARDED_FIELDS`, `_TEMPLATE_GUARDED_FIELDS`, `_ATTRIBUTE_GROUP_GUARDED_FIELDS`, `_ATTRIBUTE_GUARDED_FIELDS` |
| Brand | 158-266 | Standalone aggregate (~108 lines) |
| Category | 268-491 | Standalone aggregate (~223 lines), includes `MAX_CATEGORY_DEPTH` |
| AttributeTemplate | 493-594 | Standalone aggregate (~101 lines) |
| TemplateAttributeBinding | 596-688 | Standalone aggregate (~92 lines) |
| AttributeGroup | 690-786 | Standalone aggregate (~96 lines) |
| Attribute | 788-1069 | Standalone aggregate (~281 lines), complex with BehaviorFlags |
| AttributeValue | 1071-1209 | Child entity of Attribute (~138 lines) |
| ProductAttributeValue | 1211-1258 | Child entity (~47 lines) |
| SKU | 1260-1398 | Child entity of ProductVariant (~138 lines) |
| ProductVariant | 1400-1558 | Child entity of Product (~158 lines), imports SKU via `_skus` |
| MediaAsset | 1560-1654 | Standalone entity using `@define` (~94 lines) |
| Product | 1656-2220 | Aggregate root (~564 lines), imports ProductVariant and SKU |

### Entity Dependency Graph

```
Brand           (standalone)
Category        (standalone, has MAX_CATEGORY_DEPTH constant)
AttributeTemplate (standalone)
TemplateAttributeBinding (standalone)
AttributeGroup  (standalone)
Attribute       (standalone)
AttributeValue  (standalone, child of Attribute conceptually but no code import)
ProductAttributeValue (standalone)
MediaAsset      (standalone, uses @define not @dataclass)
SKU             (standalone, uses Money value object)
ProductVariant  (depends on: SKU — via _skus list and soft_delete cascade)
Product         (depends on: ProductVariant, SKU — via variant/sku management methods)
```

**Key finding:** The dependency graph is strictly acyclic: `Product -> ProductVariant -> SKU`. No other entity depends on another entity. This means we can split files cleanly with relative imports going in one direction only.

### Shared Dependencies (must go in `_common.py`)

1. **Constants:** `GENERAL_GROUP_CODE`
2. **Helper functions:**
   - `_validate_slug(slug, entity_name)` — used by Brand, Category, Attribute, AttributeValue, Product
   - `_generate_id()` — used by all entities with factory methods
   - `_validate_sort_order(sort_order, entity_name)` — used by Category, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, AttributeValue, ProductVariant
   - `_validate_i18n_values(i18n_dict, field_name)` — used by Brand (name only indirectly), Category, AttributeTemplate, AttributeGroup, Attribute, AttributeValue, ProductVariant, Product
   - `_validate_filter_settings(settings)` — used by TemplateAttributeBinding only
   - `_FILTER_SETTINGS_MAX_KEYS` and `_FILTER_SETTINGS_ALLOWED_KEYS` — used by `_validate_filter_settings`
3. **Guarded field sets:** Each is used only by its own entity class, so they can live in respective entity files. However, keeping them together in `_common.py` maintains the DDD-01 pattern documentation in one place.

**Decision:** Guarded fields go into each entity's own file (they are private constants used only within that file). Only truly shared helpers go into `_common.py`.

### Import Site Inventory

**68 unique import statements** across the codebase, all using the pattern:
```python
from src.modules.catalog.domain.entities import SomeName
```

No file uses `from src.modules.catalog.domain import entities` (module-level import). This means `entities/__init__.py` re-exports work perfectly.

**Imported names (complete list):**

| Name | Import Count | Used By |
|------|-------------|---------|
| Product | 15+ | Commands, repos, tests, fakes, interfaces |
| Brand | 10+ | Commands, repos, tests, fakes, interfaces |
| Category | 10+ | Commands, repos, tests, fakes, interfaces |
| SKU | 5+ | Commands, repos, tests, fakes, interfaces |
| ProductVariant | 5+ | Repos, tests, fakes, interfaces |
| Attribute | 5+ | Commands, repos, tests, fakes, interfaces |
| AttributeValue | 5+ | Commands, repos, interfaces |
| AttributeTemplate | 4+ | Commands, repos, tests, interfaces |
| AttributeGroup | 4+ | Commands, repos, tests, interfaces |
| MediaAsset | 4+ | Commands, repos, tests, interfaces |
| TemplateAttributeBinding | 3+ | Commands, repos, interfaces |
| ProductAttributeValue | 3+ | Commands, repos, tests |
| GENERAL_GROUP_CODE | 1 | constants.py (redundant?) |

**Names NOT directly imported but must be re-exported:**
- `MAX_CATEGORY_DEPTH` — check if imported externally

```
grep result: MAX_CATEGORY_DEPTH is only used inside entities.py itself (Category.create_child). Not imported elsewhere.
```

### Proposed File Layout

```
backend/src/modules/catalog/domain/entities/
    __init__.py          # Re-exports ALL public names
    _common.py           # Shared helpers + constants
    brand.py             # Brand aggregate
    category.py          # Category aggregate + MAX_CATEGORY_DEPTH
    attribute_template.py # AttributeTemplate aggregate
    template_attribute_binding.py  # TemplateAttributeBinding aggregate
    attribute_group.py   # AttributeGroup aggregate
    attribute.py         # Attribute aggregate
    attribute_value.py   # AttributeValue child entity
    product_attribute_value.py  # ProductAttributeValue child entity
    sku.py               # SKU child entity
    product_variant.py   # ProductVariant child entity (imports SKU)
    media_asset.py       # MediaAsset entity
    product.py           # Product aggregate root (imports ProductVariant, SKU)
```

**Total: 14 files** (1 init + 1 common + 12 entity files)

### Import Strategy Within Package

Each entity file imports from `_common.py` using relative imports:
```python
from ._common import _validate_slug, _generate_id, _validate_sort_order, ...
```

Cross-entity imports (only 2 cases):
```python
# product_variant.py
from .sku import SKU

# product.py
from .product_variant import ProductVariant
from .sku import SKU
```

### `__init__.py` Re-export Strategy

```python
from .brand import Brand
from .category import Category, MAX_CATEGORY_DEPTH
from .attribute_template import AttributeTemplate
from .template_attribute_binding import TemplateAttributeBinding
from .attribute_group import AttributeGroup
from .attribute import Attribute
from .attribute_value import AttributeValue
from .product_attribute_value import ProductAttributeValue
from .sku import SKU
from .product_variant import ProductVariant
from .media_asset import MediaAsset
from .product import Product
from ._common import GENERAL_GROUP_CODE
```

Plus `__all__` for explicitness.

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Circular imports | Very Low | Dependency graph is acyclic; verified above |
| Missing re-export in `__init__.py` | Low | Comprehensive `__all__` list + test suite as safety net |
| `__pycache__` stale bytecode | Medium | Delete `__pycache__` directories before running tests |
| Guarded field `__initialized` mangling | None | Python name mangling uses the class name, not module — moving class to new file changes nothing |
| `@dataclass` vs `@define` confusion | None | MediaAsset uses `@define`, all others use `@dataclass` from attrs — both work identically in separate files |

### Validation Architecture

**Pre-split baseline:** Run full test suite, record pass count.
**Post-split verification:** Run full test suite, confirm identical pass count and zero failures.
**Import verification:** `grep -r "from src.modules.catalog.domain.entities import" backend/` output must be identical before and after (no consuming code changes needed).

## RESEARCH COMPLETE
