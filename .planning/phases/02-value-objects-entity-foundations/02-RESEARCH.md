# Phase 2: Value Objects & Entity Foundations - Research

**Researched:** 2026-03-28
**Domain:** Python domain entity unit testing (attrs-based DDD entities, value objects, factory methods)
**Confidence:** HIGH

## Summary

This phase writes pure unit tests for all 9+ catalog domain entities and their value objects. The domain layer is a 2,220-line `entities.py` file using `attrs` dataclasses with a `DDD-01` guarded-fields pattern, an FSM-based `ProductStatus` lifecycle, and hierarchical value objects (`Money`, `BehaviorFlags`). All entities follow a consistent pattern: `Entity.create(...)` factory with validation, `entity.update(**kwargs)` with `_UPDATABLE_FIELDS` whitelisting, and `__setattr__` guards on immutable fields.

Phase 1 delivered all test infrastructure: 8 entity builders (BrandBuilder, ProductBuilder, etc.), Hypothesis strategies, and FakeUoW. This phase consumes that infrastructure to write test files. No new builders or infrastructure are needed. The existing `TestCategoryEffectiveTemplateId` test class (9 tests) already covers one slice of Category behavior and serves as a pattern for the rest.

The critical observation is that every entity shares the same structural patterns (create/update/guard/validate_deletable), so tests follow a repeatable template. The business complexity is concentrated in: (1) Product aggregate with variant/SKU management and FSM transitions, (2) Money value object with cross-currency comparison guards, (3) i18n validation with required locales (ru, en), and (4) slug validation with the `SLUG_RE` regex pattern.

**Primary recommendation:** Write one test file per entity class, using builders for test data construction, with class-per-entity organization (TestBrand, TestProduct, etc.). Prioritize factory method validation and update method rejection paths. Keep tests synchronous and pure -- no database, no async, no mocking.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** One test file per entity: `test_brand.py`, `test_category.py`, `test_product.py`, `test_variant.py`, `test_sku.py`, `test_attribute.py`, `test_attribute_template.py`, `test_attribute_group.py`, `test_value_objects.py`
- **D-02:** All files under `backend/tests/unit/modules/catalog/domain/` mirroring the source structure
- **D-03:** Focus on business-critical validation paths first -- factory methods, state transitions, and invariant enforcement. Exhaustive edge cases can be added later
- **D-04:** Priority order: (1) product creation, (2) variant/SKU generation, (3) EAV attribute assignment, (4) price management, (5) status transitions
- **D-05:** The 2,220-line entities.py is too large to exhaustively test in one phase. Cover the critical business rules, not every possible invalid input
- **D-06:** Use Phase 1 builders (BrandBuilder, ProductBuilder, etc.) for test data construction
- **D-07:** Class-per-entity organization: TestBrand, TestProduct, TestSKU, etc. with descriptive test methods
- **D-08:** Pure unit tests only -- no database, no async, no FakeUoW. Domain entities are sync

### Claude's Discretion
- Exact test method names and grouping within each class
- How many invalid-input test cases per factory method
- Whether to test private helper methods or only public API
- Value object edge case selection (which Unicode, which boundary values)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOM-01 | Unit tests for all entity factory methods and update methods across all 9+ entity/aggregate classes | Full analysis of all entity classes, their create() factory methods, update() methods, validation logic, guarded fields, and deletion guards. Each entity's public API surface is documented in Architecture Patterns below. |
| DOM-05 | Unit tests for all value objects -- immutability, validation rules, edge cases | Complete analysis of Money (@frozen attrs with comparison operators, currency validation), BehaviorFlags (@frozen with search_weight range validation), ProductStatus (StrEnum with FSM transitions), all other StrEnums, SLUG_RE pattern, validate_i18n_completeness, and validate_validation_rules. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner | Already configured in project |
| attrs | 25.4.0 | Domain entity definitions | Entities use `@dataclass` and `@frozen` decorators |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hypothesis | 6.151.9 | Property-based testing | Optional for value object edge case discovery |
| dirty-equals | 0.11 | Flexible assertion matching | For UUID/datetime comparisons where exact values don't matter |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hypothesis for all tests | manual parametrize | Hypothesis is slower; use only where combinatorial state matters (e.g., Money comparison matrix) |
| dirty-equals | manual isinstance checks | dirty-equals reads more fluently for UUID/datetime assertions |

**Installation:** All dependencies already installed via Phase 1 (INFRA-01).

## Architecture Patterns

### Recommended Project Structure
```
backend/tests/unit/modules/catalog/domain/
├── __init__.py                        # empty (exists for pytest discovery)
├── test_brand.py                      # TestBrand
├── test_category.py                   # TestCategory
├── test_product.py                    # TestProduct, TestProductUpdate, TestProductSoftDelete
├── test_variant.py                    # TestProductVariant, TestProductVariantUpdate
├── test_sku.py                        # TestSKU, TestSKUUpdate
├── test_attribute.py                  # TestAttribute, TestAttributeUpdate, TestAttributeValue
├── test_attribute_template.py         # TestAttributeTemplate, TestTemplateAttributeBinding
├── test_attribute_group.py            # TestAttributeGroup
├── test_value_objects.py              # TestMoney, TestBehaviorFlags, TestValidateI18n, TestSlugValidation
└── test_category_effective_family.py  # (already exists -- 9 tests)
```

### Pattern 1: Entity Factory Method Test Class
**What:** A test class covering the `Entity.create(...)` factory -- valid construction, validation rejection, default values.
**When to use:** Every entity with a `create()` classmethod.
**Example:**
```python
# Source: backend/tests/unit/modules/identity/domain/test_entities.py (existing pattern)
import uuid
import pytest
from tests.factories.brand_builder import BrandBuilder
from src.modules.catalog.domain.entities import Brand

class TestBrand:
    def test_create_valid_brand(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        assert brand.name == "Nike"
        assert brand.slug == "nike"
        assert isinstance(brand.id, uuid.UUID)

    def test_create_rejects_empty_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            Brand.create(name="", slug="valid-slug")

    def test_create_rejects_invalid_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Brand.create(name="Nike", slug="INVALID SLUG!")
```

### Pattern 2: Update Method Test Class
**What:** Tests for the `entity.update(...)` method -- successful mutation, rejection of unknown fields, validation of new values.
**When to use:** Every entity with an `update()` method.
**Example:**
```python
class TestBrandUpdate:
    def test_update_name(self):
        brand = BrandBuilder().build()
        brand.update(name="New Name")
        assert brand.name == "New Name"

    def test_update_rejects_empty_name(self):
        brand = BrandBuilder().build()
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            brand.update(name="")
```

### Pattern 3: Guarded Field Test
**What:** Verify that `__setattr__` guards prevent direct mutation of protected fields.
**When to use:** Every entity with `_GUARDED_FIELDS` pattern (Brand, Category, Product, AttributeTemplate, AttributeGroup, Attribute).
**Example:**
```python
    def test_slug_guard_prevents_direct_assignment(self):
        brand = BrandBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'slug' directly"):
            brand.slug = "hacked"

    def test_update_can_change_slug(self):
        brand = BrandBuilder().build()
        brand.update(slug="new-slug")
        assert brand.slug == "new-slug"
```

### Pattern 4: Value Object Immutability Test
**What:** Verify that `@frozen` attrs classes reject mutation after construction.
**When to use:** Money, BehaviorFlags.
**Example:**
```python
from attrs.exceptions import FrozenInstanceError
from src.modules.catalog.domain.value_objects import Money

class TestMoney:
    def test_frozen_rejects_mutation(self):
        money = Money(amount=1000, currency="RUB")
        with pytest.raises(FrozenInstanceError):
            money.amount = 2000
```

### Pattern 5: Deletion Guard Test
**What:** Verify `validate_deletable()` raises on constraint violations.
**When to use:** Brand, Category, AttributeTemplate.
**Example:**
```python
    def test_validate_deletable_rejects_when_has_products(self):
        brand = BrandBuilder().build()
        with pytest.raises(BrandHasProductsError):
            brand.validate_deletable(has_products=True)

    def test_validate_deletable_passes_when_no_products(self):
        brand = BrandBuilder().build()
        brand.validate_deletable(has_products=False)  # should not raise
```

### Anti-Patterns to Avoid
- **Testing attrs internals:** Do not test that attrs generates `__init__`, `__eq__`, `__repr__` -- these are framework guarantees, not business logic.
- **Mocking domain entities:** Domain entities are pure data + logic. Never mock them in unit tests. Construct real instances via builders.
- **Testing private helpers directly:** `_validate_slug`, `_generate_id`, `_validate_sort_order` are tested implicitly through the public API (factory methods). Only test them directly if a public-API test cannot cover a specific branch.
- **Async test functions:** Domain entities are entirely synchronous. Using `async def test_...` wastes time on event loop setup. All tests should be plain `def test_...`.
- **Testing domain event content in this phase:** Phase 2 focus is entity validation correctness, not event emission. Event emission testing belongs to DOM-07 (Phase 3). However, verifying that `Product.create()` emits `ProductCreatedEvent` is acceptable as a sanity check since it's part of the factory method's contract.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test data construction | Manual entity constructors with repeated kwargs | Phase 1 builders (BrandBuilder, ProductBuilder, etc.) | Builders encode sensible defaults; tests only override what they care about |
| i18n test dicts | Repeated `{"en": "...", "ru": "..."}` in every test | A simple `_i18n("Name")` helper (see existing test_category_effective_family.py) | Reduces noise; existing pattern in codebase |
| UUID generation | `uuid.uuid4()` sprinkled everywhere | Builder defaults (builders auto-generate UUIDs) | Builders already handle this |
| Money construction for tests | Repeated `Money(amount=X, currency="RUB")` | Consider a `_money(amount, currency="RUB")` helper within test_value_objects.py | Reduces boilerplate in price-related tests |

**Key insight:** The Phase 1 builders were specifically designed to make this phase's tests concise. Every builder has sensible defaults and calls the entity's own `create()` factory method, so tests automatically exercise the production code path.

## Common Pitfalls

### Pitfall 1: Forgetting Required Locales
**What goes wrong:** Tests pass with `{"en": "Test"}` but the domain requires both `"en"` and `"ru"` locales (REQUIRED_LOCALES = frozenset({"ru", "en"})).
**Why it happens:** English-only i18n dicts seem reasonable but violate the business rule.
**How to avoid:** Always use both locales in test data. Use a helper like `_i18n("Name")` that returns `{"en": "Name", "ru": "Name"}`.
**Warning signs:** `MissingRequiredLocalesError` raised unexpectedly in tests.

### Pitfall 2: Ellipsis Sentinel Confusion
**What goes wrong:** Passing `None` to nullable fields that use `...` (Ellipsis) as default sentinel clears the value instead of keeping it unchanged.
**Why it happens:** Brand.update() uses `logo_url: str | None = ...` where `...` means "keep current" and `None` means "clear". Category.update() uses similar pattern for `template_id`.
**How to avoid:** Test both paths explicitly: (1) omit the kwarg to keep current, (2) pass `None` to clear, (3) pass a value to update.
**Warning signs:** Tests that set a field to `None` and expect it to remain unchanged.

### Pitfall 3: Product Auto-Creates Default Variant
**What goes wrong:** Tests assume `Product.create()` returns a product with zero variants, but it actually auto-creates one default variant and emits `ProductCreatedEvent`.
**Why it happens:** The auto-variant creation is a domain rule easy to forget.
**How to avoid:** After `Product.create()`, always assert `len(product.variants) == 1` and that the default variant's `name_i18n` matches the product's `title_i18n`. Clear domain events after construction if testing subsequent behavior.
**Warning signs:** Assertions about `product.variants` length failing with off-by-one errors.

### Pitfall 4: SKU Only Created Via Product.add_sku()
**What goes wrong:** Attempting to construct SKU directly or expecting a standalone `SKU.create()` factory.
**Why it happens:** SKU is a child entity -- it has no standalone `create()`. The `SKUBuilder` works by calling `product.add_sku()` internally.
**How to avoid:** Always use `SKUBuilder().for_product(product).build()` or `product.add_sku(variant_id, ...)`. Tests for SKU always need a Product aggregate.
**Warning signs:** `SKU(...)` direct construction bypasses variant_hash computation and uniqueness checks.

### Pitfall 5: Guarded Fields Use Name-Mangled Private Attribute
**What goes wrong:** Tests check `hasattr(brand, '__initialized')` instead of the mangled name `_Brand__initialized`.
**Why it happens:** Python name mangling converts `__initialized` to `_ClassName__initialized` in the attrs `__attrs_post_init__`.
**How to avoid:** Test the guard behavior (attempt direct assignment, expect `AttributeError`) rather than inspecting internal state.
**Warning signs:** Tests that poke at internal `__initialized` flags.

### Pitfall 6: attrs @dataclass vs @frozen Difference
**What goes wrong:** Attempting to mutate a `@frozen` value object (Money, BehaviorFlags) and expecting it to work, or expecting `@dataclass` entities to reject mutation.
**Why it happens:** `@frozen` makes all fields immutable. `@dataclass` (used for entities) allows mutation (fields are mutable by default). The entities guard specific fields via custom `__setattr__`.
**How to avoid:** Value object tests should verify `FrozenInstanceError` on mutation. Entity tests should verify `AttributeError` on guarded fields only, and expect normal mutation on non-guarded fields.
**Warning signs:** `FrozenInstanceError` vs `AttributeError` confusion in test assertions.

## Code Examples

### Complete Entity Test Pattern (Brand -- simplest entity)
```python
# Source: entities.py Brand class analysis
import uuid

import pytest
from attrs.exceptions import FrozenInstanceError

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import BrandHasProductsError
from tests.factories.brand_builder import BrandBuilder


class TestBrand:
    """Tests for Brand.create() factory method."""

    def test_create_with_valid_inputs(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        assert brand.name == "Nike"
        assert brand.slug == "nike"
        assert isinstance(brand.id, uuid.UUID)

    def test_create_strips_name_whitespace(self):
        brand = Brand.create(name="  Nike  ", slug="nike")
        assert brand.name == "Nike"

    def test_create_with_logo(self):
        obj_id = uuid.uuid4()
        brand = BrandBuilder().with_logo("https://img.co/logo.png", obj_id).build()
        assert brand.logo_url == "https://img.co/logo.png"
        assert brand.logo_storage_object_id == obj_id

    def test_create_rejects_empty_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            Brand.create(name="", slug="valid")

    def test_create_rejects_blank_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            Brand.create(name="   ", slug="valid")

    def test_create_rejects_invalid_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Brand.create(name="Nike", slug="Bad Slug!")

    def test_create_rejects_empty_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Brand.create(name="Nike", slug="")


class TestBrandUpdate:
    """Tests for Brand.update() method."""

    def test_update_name(self):
        brand = BrandBuilder().build()
        brand.update(name="Updated")
        assert brand.name == "Updated"

    def test_update_slug_via_update_method(self):
        brand = BrandBuilder().build()
        brand.update(slug="new-slug")
        assert brand.slug == "new-slug"

    def test_update_rejects_empty_name(self):
        brand = BrandBuilder().build()
        with pytest.raises(ValueError):
            brand.update(name="")

    def test_update_logo_url_to_none_clears_it(self):
        brand = BrandBuilder().with_logo("https://img.co/logo.png").build()
        brand.update(logo_url=None)
        assert brand.logo_url is None

    def test_update_logo_url_omitted_keeps_current(self):
        brand = BrandBuilder().with_logo("https://img.co/logo.png").build()
        brand.update(name="New Name")
        assert brand.logo_url == "https://img.co/logo.png"


class TestBrandGuard:
    """Tests for DDD-01 guarded field enforcement."""

    def test_direct_slug_assignment_raises(self):
        brand = BrandBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'slug' directly"):
            brand.slug = "hacked"


class TestBrandDeletion:
    """Tests for Brand.validate_deletable()."""

    def test_deletable_when_no_products(self):
        brand = BrandBuilder().build()
        brand.validate_deletable(has_products=False)

    def test_not_deletable_when_has_products(self):
        brand = BrandBuilder().build()
        with pytest.raises(BrandHasProductsError):
            brand.validate_deletable(has_products=True)
```

### Value Object Test Pattern (Money)
```python
# Source: value_objects.py Money class analysis
import pytest
from attrs.exceptions import FrozenInstanceError

from src.modules.catalog.domain.value_objects import Money


class TestMoney:
    def test_create_valid(self):
        m = Money(amount=1000, currency="RUB")
        assert m.amount == 1000
        assert m.currency == "RUB"

    def test_currency_uppercased(self):
        m = Money(amount=100, currency="rub")
        assert m.currency == "RUB"

    def test_rejects_negative_amount(self):
        with pytest.raises(ValueError, match="non-negative"):
            Money(amount=-1, currency="RUB")

    def test_zero_amount_allowed(self):
        m = Money(amount=0, currency="RUB")
        assert m.amount == 0

    def test_rejects_invalid_currency_length(self):
        with pytest.raises(ValueError, match="3-character"):
            Money(amount=100, currency="US")

    def test_frozen_rejects_mutation(self):
        m = Money(amount=1000, currency="RUB")
        with pytest.raises(FrozenInstanceError):
            m.amount = 2000

    def test_equality(self):
        assert Money(amount=100, currency="RUB") == Money(amount=100, currency="RUB")

    def test_inequality_different_amount(self):
        assert Money(amount=100, currency="RUB") != Money(amount=200, currency="RUB")

    def test_comparison_same_currency(self):
        assert Money(amount=100, currency="RUB") < Money(amount=200, currency="RUB")

    def test_comparison_different_currency_raises(self):
        with pytest.raises(ValueError, match="different currencies"):
            Money(amount=100, currency="RUB") < Money(amount=200, currency="USD")

    def test_from_primitives(self):
        price, compare = Money.from_primitives(1000, "RUB", compare_at_amount=2000)
        assert price.amount == 1000
        assert compare is not None
        assert compare.amount == 2000

    def test_from_primitives_rejects_compare_at_not_greater(self):
        with pytest.raises(ValueError, match="compare_at_price must be greater"):
            Money.from_primitives(1000, "RUB", compare_at_amount=500)
```

### i18n Helper Pattern
```python
# Source: test_category_effective_family.py (existing codebase pattern)
def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    """Build a valid i18n dict with both required locales."""
    return {"en": en, "ru": ru or en}
```

## Entity Test Coverage Map

This section maps every entity's testable public API surface, based on direct analysis of `entities.py` (2,220 lines).

### Brand (lines 162-266)
| Method | What to test |
|--------|-------------|
| `Brand.create()` | valid inputs, empty name, blank name, invalid slug, empty slug, name stripping, custom brand_id, logo fields |
| `Brand.update()` | name change, slug change, logo_url set/clear/keep, logo_storage_object_id set/clear/keep, empty name rejection |
| `__setattr__` guard | direct slug assignment raises AttributeError |
| `validate_deletable()` | has_products=True raises, has_products=False passes |

### Category (lines 277-491)
| Method | What to test |
|--------|-------------|
| `Category.create_root()` | valid inputs, i18n validation (empty, blank values, missing locales), invalid slug, negative sort_order, template_id handling |
| `Category.create_child()` | valid inputs, max depth enforcement, full_slug composition, effective_template_id inheritance, parent template override |
| `Category.update()` | name_i18n change, slug change (returns old_full_slug), sort_order change, template_id set/clear, effective_template_id recomputation |
| `__setattr__` guard | direct slug assignment raises AttributeError |
| `validate_deletable()` | has_children=True raises, has_products=True raises, both False passes |
| `set_effective_template_id()` | set to UUID, set to None |

### AttributeTemplate (lines 498-594)
| Method | What to test |
|--------|-------------|
| `AttributeTemplate.create()` | valid inputs, empty name_i18n, blank i18n values, missing required locales, negative sort_order, default description_i18n |
| `AttributeTemplate.update()` | name_i18n change, description_i18n change, sort_order change, unknown fields rejection |
| `__setattr__` guard | direct code assignment raises AttributeError |
| `validate_deletable()` | has_category_refs=True raises, has_category_refs=False passes |

### TemplateAttributeBinding (lines 601-688)
| Method | What to test |
|--------|-------------|
| `TemplateAttributeBinding.create()` | valid inputs, negative sort_order, filter_settings validation (unknown keys, too many keys, non-dict), default requirement_level (OPTIONAL) |
| `TemplateAttributeBinding.update()` | sort_order change, requirement_level change, filter_settings change, unknown fields rejection |

### AttributeGroup (lines 695-786)
| Method | What to test |
|--------|-------------|
| `AttributeGroup.create()` | valid inputs, empty name_i18n, blank i18n values, missing locales, negative sort_order, custom group_id |
| `AttributeGroup.update()` | name_i18n change, sort_order change, empty name_i18n rejection |
| `__setattr__` guard | direct code assignment raises AttributeError |

### Attribute (lines 793-1068)
| Method | What to test |
|--------|-------------|
| `Attribute.create()` | valid inputs (all kwargs), invalid slug, empty name_i18n, behavior flags (both individual and BehaviorFlags object), validation_rules type-checking (string rules on string type, numeric rules on numeric type, invalid rules rejected), default level (PRODUCT) |
| `Attribute.update()` | name_i18n change, ui_type change, level change, group_id set/clear, behavior update (via BehaviorFlags object and via individual flags), validation_rules update, unknown fields rejection, search_weight range enforcement |
| `__setattr__` guard | direct code assignment raises, direct slug assignment raises |
| Properties | is_filterable, is_searchable, search_weight, is_comparable, is_visible_on_card delegate to behavior |

### AttributeValue (lines 1071-1210)
| Method | What to test |
|--------|-------------|
| `AttributeValue.create()` | valid inputs, empty value_i18n, blank i18n values, invalid slug, negative sort_order, defaults (is_active=True, empty lists/dicts) |
| `AttributeValue.update()` | value_i18n change, search_aliases change, meta_data change, value_group set/clear, sort_order change, is_active toggle, unknown fields rejection |

### ProductAttributeValue (lines 1213-1258)
| Method | What to test |
|--------|-------------|
| `ProductAttributeValue.create()` | valid inputs, auto-generated ID |

### SKU (lines 1267-1398)
| Method | What to test |
|--------|-------------|
| `SKU.__attrs_post_init__()` | compare_at_price without price raises, compare_at_price <= price raises, currency mismatch raises, valid price/compare_at pair |
| `SKU.update()` | sku_code change, price change, compare_at_price change, is_active toggle, unknown fields rejection, cross-field validation (compare_at > price after update) |
| `SKU.soft_delete()` | sets deleted_at, idempotent (second call no-op) |

### ProductVariant (lines 1405-1558)
| Method | What to test |
|--------|-------------|
| `ProductVariant.create()` | valid inputs, empty name_i18n, blank i18n values, negative sort_order, default_price/default_currency |
| `ProductVariant.update()` | name_i18n change, sort_order change, default_price + default_currency together, default_price alone, default_currency alone (validation), unknown fields rejection |
| `ProductVariant.soft_delete()` | sets deleted_at, cascades to SKUs, idempotent |
| `ProductVariant.skus` | returns tuple (read-only) |

### Product (lines 1663-2221)
| Method | What to test |
|--------|-------------|
| `Product.create()` | valid inputs, auto-creates default variant, emits ProductCreatedEvent, invalid slug, empty title_i18n, blank i18n values, missing required locales |
| `Product.update()` | title_i18n change, slug change, brand_id change (None rejected), primary_category_id change (None rejected), tags change, supplier_id set/clear, country_of_origin set/clear, unknown fields rejection, emits ProductUpdatedEvent |
| `Product.__setattr__` guard | direct status assignment raises AttributeError |
| `Product.transition_status()` | (NOTE: DOM-02 Phase 3 scope, but basic validation of guard is DOM-01) |
| `Product.add_variant()` | creates variant, emits VariantAddedEvent |
| `Product.find_variant()` | finds active variant, returns None for deleted, returns None for unknown ID |
| `Product.remove_variant()` | soft-deletes variant, emits VariantDeletedEvent, rejects last variant removal, raises VariantNotFoundError |
| `Product.add_sku()` | creates SKU with variant_hash, emits SKUAddedEvent, rejects duplicate variant_hash, rejects unknown variant_id |
| `Product.find_sku()` | finds active SKU, returns None for deleted, returns None for unknown ID |
| `Product.remove_sku()` | soft-deletes SKU, emits SKUDeletedEvent, raises SKUNotFoundError |
| `Product.soft_delete()` | sets deleted_at, cascades to variants/SKUs, rejects published product, emits ProductDeletedEvent, idempotent |
| `Product.compute_variant_hash()` | deterministic for same inputs, order-independent for variant_attributes, different for different variant_ids |
| `Product.tags` | returns tuple (read-only) |
| `Product.variants` | returns tuple (read-only) |

### Value Objects (value_objects.py)
| Object | What to test |
|--------|-------------|
| `Money` | construction, negative amount, zero amount, currency length, currency uppercasing, frozen immutability, equality, all comparison operators, cross-currency comparison rejection, `from_primitives()` |
| `BehaviorFlags` | construction, search_weight range validation (1-10), defaults, frozen immutability |
| `ProductStatus` | enum values, FSM transition table (basic existence check -- full FSM testing is DOM-02/Phase 3) |
| `validate_i18n_completeness()` | missing required locales raises MissingRequiredLocalesError, valid dict passes |
| `validate_validation_rules()` | string rules on string type, numeric rules on numeric type, boolean type rejects rules, invalid keys rejected, None rules passes |
| `SLUG_RE` | valid slugs match, invalid slugs rejected (uppercase, spaces, leading/trailing hyphens, empty) |
| Enums | MediaType, MediaRole, AttributeDataType, AttributeUIType, AttributeLevel, RequirementLevel -- each has correct string values |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| polyfactory ModelFactory | Phase 1 Fluent Builders | Phase 1 (2026-03) | Builders call entity create() factories, ensuring production code paths are tested |
| Direct entity constructor | Builder.build() | Phase 1 (2026-03) | Tests are more readable and maintainable |

**Deprecated/outdated:**
- `tests/factories/catalog_factories.py`: Empty file. Use the new builders instead.
- `tests/factories/storage_factories.py`: Empty file. Not relevant for domain unit tests.

## Open Questions

1. **MediaAsset entity coverage scope**
   - What we know: MediaAsset has a `create()` factory with validation (media_type, role, sort_order, external URL check). It uses `@define` (not `@dataclass`), has no AggregateRoot mixin, and no update method.
   - What's unclear: CONTEXT.md D-01 does not list `test_media_asset.py` in the file list. The entity list in the phase description does not mention MediaAsset explicitly.
   - Recommendation: Skip MediaAsset for Phase 2. It can be covered in a later phase (Phase 6 covers CMD-07 Media handlers). If the planner wants to include it, a `test_media_asset.py` is straightforward.

2. **ProductAttributeValue test depth**
   - What we know: ProductAttributeValue.create() is trivial -- no validation, just ID generation and field assignment.
   - What's unclear: Whether it warrants its own test file or belongs in `test_attribute.py`.
   - Recommendation: Include it in `test_attribute.py` as a `TestProductAttributeValue` class with 1-2 tests. It's too small for its own file.

3. **Private helper function testing**
   - What we know: `_validate_slug`, `_validate_sort_order`, `_validate_i18n_values`, `_validate_filter_settings` are module-level private helpers called by multiple entities.
   - What's unclear: Whether to test them directly or only through public API.
   - Recommendation: Test `_validate_filter_settings` directly in `test_attribute_template.py` (it has complex logic: key whitelist, max keys). Test the others indirectly through entity factory methods.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `backend/pytest.ini` (overrides pyproject.toml) |
| Quick run command | `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -x -q --no-cov` |
| Full suite command | `cd backend && uv run pytest tests/unit/ -x -q --no-cov` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOM-01 | Entity factory methods: valid creation, validation rejection | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_brand.py tests/unit/modules/catalog/domain/test_category.py tests/unit/modules/catalog/domain/test_product.py tests/unit/modules/catalog/domain/test_variant.py tests/unit/modules/catalog/domain/test_sku.py tests/unit/modules/catalog/domain/test_attribute.py tests/unit/modules/catalog/domain/test_attribute_template.py tests/unit/modules/catalog/domain/test_attribute_group.py -x --no-cov` | Wave 0 |
| DOM-01 | Entity update methods: successful mutation, rejection | unit | Same files as above | Wave 0 |
| DOM-01 | Guarded field enforcement | unit | Same files as above | Wave 0 |
| DOM-01 | Deletion guards | unit | Same files as above | Wave 0 |
| DOM-05 | Money: immutability, validation, comparison, from_primitives | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_value_objects.py -x --no-cov` | Wave 0 |
| DOM-05 | BehaviorFlags: immutability, search_weight validation | unit | Same as above | Wave 0 |
| DOM-05 | i18n validation, slug validation, validation_rules | unit | Same as above | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -x -q --no-cov`
- **Per wave merge:** `cd backend && uv run pytest tests/unit/ -x -q --no-cov`
- **Phase gate:** Full unit suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/modules/catalog/domain/test_brand.py` -- covers DOM-01 (Brand)
- [ ] `tests/unit/modules/catalog/domain/test_category.py` -- covers DOM-01 (Category)
- [ ] `tests/unit/modules/catalog/domain/test_product.py` -- covers DOM-01 (Product aggregate)
- [ ] `tests/unit/modules/catalog/domain/test_variant.py` -- covers DOM-01 (ProductVariant)
- [ ] `tests/unit/modules/catalog/domain/test_sku.py` -- covers DOM-01 (SKU)
- [ ] `tests/unit/modules/catalog/domain/test_attribute.py` -- covers DOM-01 (Attribute, AttributeValue, ProductAttributeValue)
- [ ] `tests/unit/modules/catalog/domain/test_attribute_template.py` -- covers DOM-01 (AttributeTemplate, TemplateAttributeBinding)
- [ ] `tests/unit/modules/catalog/domain/test_attribute_group.py` -- covers DOM-01 (AttributeGroup)
- [ ] `tests/unit/modules/catalog/domain/test_value_objects.py` -- covers DOM-05

*(Existing `test_category_effective_family.py` with 9 tests already covers Category effective_template_id behavior -- no changes needed)*

## Sources

### Primary (HIGH confidence)
- `backend/src/modules/catalog/domain/entities.py` -- Direct analysis of all 2,220 lines; complete entity API surface mapped
- `backend/src/modules/catalog/domain/value_objects.py` -- Direct analysis of all value objects, enums, validation functions
- `backend/src/modules/catalog/domain/exceptions.py` -- All domain exceptions reviewed for test assertion targets
- `backend/tests/unit/modules/identity/domain/test_entities.py` -- Canonical test pattern (TestIdentity, TestSession, etc.)
- `backend/tests/unit/modules/catalog/domain/test_category_effective_family.py` -- Existing catalog test pattern
- All 8 Phase 1 builders -- Analyzed for available builder methods and defaults

### Secondary (MEDIUM confidence)
- `backend/pytest.ini` -- Test runner configuration (overrides pyproject.toml)
- `backend/pyproject.toml` -- Dev dependencies (hypothesis, dirty-equals confirmed installed)

### Tertiary (LOW confidence)
- None. All findings are from direct source code analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and configured in project
- Architecture: HIGH -- test patterns derived from existing codebase (identity module tests, Phase 1 builders)
- Pitfalls: HIGH -- derived from direct analysis of entity source code (Ellipsis sentinels, auto-variant creation, guarded fields pattern, SKU child entity constraints)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- domain entities unlikely to change during hardening milestone)
