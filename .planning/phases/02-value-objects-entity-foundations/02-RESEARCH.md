# Phase 2: Value Objects & Entity Foundations - Research

**Researched:** 2026-03-28
**Domain:** Domain entity unit testing (Python/attrs/pytest)
**Confidence:** HIGH

## Summary

Phase 2 writes pure unit tests for all 9+ catalog domain entities and value objects, proving that factory methods, update methods, validation logic, and value object invariants are correct. The domain layer uses `attrs` dataclasses (not stdlib dataclasses) with `@dataclass` for mutable entities and `@frozen` for immutable value objects. All entities live in a single 2,220-line `entities.py` file with well-defined `create()` factory methods and `update()` methods.

The existing Phase 1 infrastructure provides all 8 entity builders (BrandBuilder, ProductBuilder, etc.), Hypothesis strategies for primitives and entities, and an established test pattern (class-per-entity with descriptive test methods, as seen in `test_entities.py` from the identity module). There is one existing test file in the target directory (`test_category_effective_family.py`) with 9 tests. One of those tests is currently failing (`test_update_clear_template_id_does_not_clear_effective`) due to a behavior change in `Category.update()` -- the test expectation no longer matches the code behavior when `parent_effective_template_id` defaults to `...`. This should be fixed as part of this phase.

**Primary recommendation:** Write one test file per entity class following the class-per-entity pattern from Phase 1 decisions. Use builders for happy paths, direct construction with `pytest.raises` for validation rejection paths. Tests are pure sync Python -- no async, no database, no FakeUoW.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** One test file per entity, consistent with Phase 1 D-12 (class-per-entity). Files: `test_brand.py`, `test_category.py`, `test_product.py`, `test_variant.py`, `test_sku.py`, `test_attribute.py`, `test_attribute_template.py`, `test_attribute_group.py`, `test_value_objects.py`.
- **D-02:** All files under `backend/tests/unit/modules/catalog/domain/` mirroring the source structure.
- **D-03:** Focus on business-critical validation paths first -- factory methods, state transitions, and invariant enforcement. Exhaustive edge cases can be added later.
- **D-04:** Priority order for test coverage: (1) product creation, (2) variant/SKU generation, (3) EAV attribute assignment, (4) price management, (5) status transitions.
- **D-05:** The 2,220-line entities.py is too large to exhaustively test in one phase. Cover the critical business rules, not every possible invalid input.
- **D-06:** Use Phase 1 builders (BrandBuilder, ProductBuilder, etc.) for test data construction.
- **D-07:** Class-per-entity organization: TestBrand, TestProduct, TestSKU, etc. with descriptive test methods.
- **D-08:** Pure unit tests only -- no database, no async, no FakeUoW. Domain entities are sync.

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
| DOM-01 | Unit tests for all entity factory methods and update methods across all 9+ entity/aggregate classes | Every entity class has `create()` factory + `update()` method documented; builder patterns exist for all entities; test pattern established in identity module |
| DOM-05 | Unit tests for all value objects -- immutability, validation rules, edge cases | Money (`@frozen`, ordering, currency validation), BehaviorFlags (`@frozen`, search_weight range), SLUG_RE pattern, validate_i18n_completeness, validate_validation_rules, all StrEnum classes documented |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner | Already installed and configured in `backend/pytest.ini` |
| attrs | 26.1.0 | Domain entity definitions | All entities use `@dataclass` / `@frozen` from attrs |
| hypothesis | 6.151.9 | Property-based testing | Strategies already built in Phase 1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-randomly | 4.0.1 | Randomize test order | Already installed; catches hidden order dependencies |
| pytest-timeout | 2.4.0 | Per-test timeout (30s) | Already configured; prevents hung tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hypothesis | Pure pytest parametrize | Hypothesis gives better edge case discovery but slower; use parametrize for explicit business rule cases, hypothesis for property-based validation |

**Installation:**
No new packages needed. All dependencies are already installed from Phase 1.

## Architecture Patterns

### Recommended Project Structure
```
backend/tests/unit/modules/catalog/domain/
  __init__.py                             # existing (empty marker)
  test_category_effective_family.py       # existing (9 tests, 1 failing)
  test_brand.py                           # NEW
  test_category.py                        # NEW
  test_product.py                         # NEW
  test_variant.py                         # NEW
  test_sku.py                             # NEW
  test_attribute.py                       # NEW
  test_attribute_template.py              # NEW
  test_attribute_group.py                 # NEW
  test_value_objects.py                   # NEW
```

### Pattern 1: Entity Test Class Structure
**What:** Each test file contains one or more test classes named `TestEntityName` with descriptive method names.
**When to use:** For every entity being tested.
**Example:**
```python
# Source: backend/tests/unit/modules/identity/domain/test_entities.py (existing pattern)
import uuid
import pytest
from tests.factories.brand_builder import BrandBuilder

class TestBrand:
    def test_create_valid_brand(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        assert brand.name == "Nike"
        assert brand.slug == "nike"
        assert isinstance(brand.id, uuid.UUID)

    def test_create_rejects_empty_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            BrandBuilder().with_name("").build()

    def test_update_name(self):
        brand = BrandBuilder().build()
        brand.update(name="New Name")
        assert brand.name == "New Name"

    def test_slug_guard_prevents_direct_assignment(self):
        brand = BrandBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'slug' directly"):
            brand.slug = "hacked"
```

### Pattern 2: Validation Rejection Tests
**What:** Use `pytest.raises` with `match` parameter to verify error messages.
**When to use:** For every factory method and update method validation path.
**Example:**
```python
class TestBrandValidation:
    def test_create_rejects_invalid_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Brand.create(name="Valid", slug="INVALID SLUG!")

    def test_update_rejects_empty_name(self):
        brand = BrandBuilder().build()
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            brand.update(name="   ")
```

### Pattern 3: Value Object Immutability Tests
**What:** Verify that `@frozen` attrs classes reject attribute mutation.
**When to use:** For Money, BehaviorFlags.
**Example:**
```python
import attrs

class TestMoney:
    def test_immutable(self):
        m = Money(amount=1000, currency="RUB")
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            m.amount = 2000
```

### Pattern 4: Using Builders vs Direct Construction
**What:** Use builders for happy paths where defaults simplify setup; use direct `Entity.create()` for testing specific validation paths.
**When to use:** Builders when you need a valid entity with specific overrides; direct construction when testing that validation rejects bad input.
**Example:**
```python
# Builder for happy path (don't care about exact slug, just need a valid brand)
brand = BrandBuilder().with_name("Nike").build()

# Direct construction for testing specific validation
with pytest.raises(ValueError):
    Brand.create(name="", slug="valid-slug")
```

### Anti-Patterns to Avoid
- **Testing attrs internals:** Do not test that `@dataclass` generates `__init__`, `__eq__`, etc. Test business behavior only.
- **Mocking domain entities:** Domain entities are pure data. Never mock them -- create real instances.
- **Testing private helpers directly:** Test `_validate_slug`, `_validate_sort_order` only through the public API (`create()`, `update()`) unless the helper has non-trivial logic not reachable through public API.
- **Async test functions:** All domain entity tests are sync. Do not use `async def test_*`.
- **Database involvement:** Never import ORM models, sessions, or repositories in these tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test data construction | Manual entity creation with all fields | Phase 1 Builders (BrandBuilder, ProductBuilder, etc.) | Builders handle defaults, call `create()` factory, ensure valid state |
| Random valid slugs/i18n | String generation inline in tests | Hypothesis strategies from `tests.factories.strategies.primitives` | Strategies already validated in Phase 1 to produce valid domain values |
| UUID generation | `uuid.uuid4()` sprinkled everywhere | Builder defaults (auto-generate) or `strategies.primitives.uuids()` | Consistent, less noise in test code |

**Key insight:** Phase 1 built extensive test infrastructure specifically for this phase. Every builder calls the entity's `create()` factory method, so using builders already validates the happy path. The real value of Phase 2 is testing rejection paths and edge cases.

## Common Pitfalls

### Pitfall 1: Ellipsis Sentinel Confusion
**What goes wrong:** The `update()` methods use `...` (Ellipsis) as default for nullable fields (e.g., `logo_url: str | None = ...`). Testing `update(logo_url=None)` should CLEAR the field, but `update()` with no argument should KEEP it.
**Why it happens:** Python's Ellipsis is used as a sentinel to distinguish "not provided" from "explicitly None".
**How to avoid:** Test both paths: (1) `update(logo_url=None)` sets to None, (2) `update()` preserves current value.
**Warning signs:** Tests that pass None accidentally when they meant "keep current".

### Pitfall 2: Guarded Field `__setattr__` Pattern
**What goes wrong:** Entities use `__setattr__` guards with name-mangled `_ClassName__initialized` flags. The guard is not active during `__init__` (before `__attrs_post_init__` sets the flag), so `create()` works. But after creation, direct assignment raises `AttributeError`.
**Why it happens:** DDD pattern to force mutations through domain methods only.
**How to avoid:** Test both: (1) that direct assignment raises `AttributeError`, (2) that `update()` successfully changes the guarded field via `object.__setattr__`.
**Warning signs:** Tests that modify guarded fields directly and pass (they shouldn't after initialization).

### Pitfall 3: Product Auto-Creates Default Variant
**What goes wrong:** `Product.create()` automatically creates one default variant and appends it to `_variants`. Tests that expect zero variants after creation will fail.
**Why it happens:** Business rule: every product must have at least one variant.
**How to avoid:** Assert `len(product.variants) == 1` after `Product.create()`. The default variant uses the product's `title_i18n` as its `name_i18n`.
**Warning signs:** Tests that assume empty variant list after product creation.

### Pitfall 4: Product.create() Emits ProductCreatedEvent
**What goes wrong:** After `Product.create()`, `product.domain_events` already contains one `ProductCreatedEvent`. Tests checking domain event counts must account for this.
**Why it happens:** Domain event is emitted inside the factory method.
**How to avoid:** Clear events with `product.clear_domain_events()` before testing update/transition events if you need a clean slate, or account for the creation event in assertions.
**Warning signs:** Off-by-one errors in domain event count assertions.

### Pitfall 5: REQUIRED_LOCALES = {"ru", "en"}
**What goes wrong:** All i18n fields require both "ru" and "en" locales. Tests providing only one locale will be rejected by `validate_i18n_completeness`.
**Why it happens:** Business rule for bilingual platform (Russian + English).
**How to avoid:** Always provide both locales in test i18n dicts: `{"en": "Foo", "ru": "Фу"}`. Builders already do this by default.
**Warning signs:** `MissingRequiredLocalesError` in tests that use single-locale dicts.

### Pitfall 6: Failing Existing Test
**What goes wrong:** `test_update_clear_template_id_does_not_clear_effective` in `test_category_effective_family.py` is currently failing. The test expects that clearing `template_id` via `update(template_id=None)` preserves `effective_template_id`, but the code now clears it because `parent_effective_template_id` defaults to `...` and the else-branch sets `effective_template_id = None`.
**Why it happens:** The `Category.update()` logic was changed after the test was written. When `template_id=None` and `parent_effective_template_id` is `...` (default), the code falls through to `self.effective_template_id = None`.
**How to avoid:** Fix the test to match current behavior, OR fix the entity code if the original behavior was correct. Investigation needed: the test comment says "handler must explicitly set effective" suggesting the test documents intended behavior that the code broke.
**Warning signs:** CI failures from this pre-existing test.

### Pitfall 7: Money Currency Auto-Uppercased
**What goes wrong:** `Money.__attrs_post_init__` uppercases currency via `object.__setattr__`. Creating `Money(amount=100, currency="rub")` results in `currency == "RUB"`.
**Why it happens:** Defensive normalization in the value object.
**How to avoid:** Test that lowercase input is normalized: `assert Money(amount=100, currency="rub").currency == "RUB"`.
**Warning signs:** Equality comparison failures when comparing `Money` objects created with different case currencies.

## Code Examples

Verified patterns from the actual codebase:

### Entity Factory Method Pattern
```python
# Source: backend/src/modules/catalog/domain/entities.py
@classmethod
def create(cls, name: str, slug: str, ...) -> Brand:
    _validate_slug(slug, "Brand")
    if not name or not name.strip():
        raise ValueError("Brand name must be non-empty")
    return cls(id=brand_id or _generate_id(), name=name.strip(), slug=slug, ...)
```

### Guarded Field Pattern
```python
# Source: backend/src/modules/catalog/domain/entities.py
def __setattr__(self, name: str, value: object) -> None:
    if name in _BRAND_GUARDED_FIELDS and getattr(self, "_Brand__initialized", False):
        raise AttributeError(
            f"Cannot set '{name}' directly on Brand. Use the update() method instead."
        )
    super().__setattr__(name, value)
```

### Update with Ellipsis Sentinel
```python
# Source: backend/src/modules/catalog/domain/entities.py
def update(self, ..., logo_url: str | None = ...) -> None:
    if logo_url is not ...:
        self.logo_url = logo_url  # None clears, any str sets
```

### Value Object with Validation
```python
# Source: backend/src/modules/catalog/domain/value_objects.py
@frozen
class Money:
    amount: int
    currency: str

    def __attrs_post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount must be non-negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-character ISO code")
        object.__setattr__(self, "currency", self.currency.upper())
```

### Builder Usage (from Phase 1)
```python
# Source: backend/tests/factories/brand_builder.py
brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
product = ProductBuilder().with_slug("nike-air-max").build()
sku = SKUBuilder().for_product(product).with_price(Money(10000, "RUB")).build()
```

### Test Class Pattern (from Identity Module)
```python
# Source: backend/tests/unit/modules/identity/domain/test_entities.py
class TestIdentity:
    def test_register_creates_active_identity(self):
        identity = Identity.register(IdentityType.LOCAL)
        assert identity.is_active is True

    def test_deactivate_emits_event(self):
        identity = Identity.register(IdentityType.LOCAL)
        identity.deactivate(reason="user_request")
        events = identity.domain_events
        assert len(events) == 1
        assert isinstance(events[0], IdentityDeactivatedEvent)
```

## Entity-by-Entity Testing Surface

Detailed inventory of what each entity needs tested, derived from source code analysis.

### Brand (entities.py lines 163-266)
- **Factory:** `Brand.create(name, slug, brand_id?, logo_url?, logo_storage_object_id?)`
- **Validations:** slug format (SLUG_RE), name non-empty/non-blank
- **Update:** `update(name?, slug?, logo_url=..., logo_storage_object_id=...)`
- **Guards:** `slug` guarded via `__setattr__`
- **Other:** `validate_deletable(has_products=)` raises `BrandHasProductsError`
- **Builder:** `BrandBuilder`

### Category (entities.py lines 277-491)
- **Factory:** `Category.create_root(name_i18n, slug, sort_order?, template_id?)` and `Category.create_child(name_i18n, slug, parent, sort_order?, template_id?)`
- **Validations:** slug format, i18n completeness (both locales), i18n non-blank values, sort_order non-negative, max depth (3), name_i18n non-empty
- **Update:** `update(name_i18n?, slug?, sort_order?, template_id=..., parent_effective_template_id=...)` returns old_full_slug or None
- **Guards:** `slug` guarded
- **Other:** `validate_deletable(has_children=, has_products=)`, `set_effective_template_id()`, full_slug recomputation on slug change
- **Builder:** Test patterns exist in `test_category_effective_family.py` with `_i18n()` helper

### AttributeTemplate (entities.py lines 498-594)
- **Factory:** `AttributeTemplate.create(code=, name_i18n=, description_i18n?, sort_order?)`
- **Validations:** name_i18n non-empty/completeness/non-blank, sort_order non-negative
- **Update:** `update(**kwargs)` with `_UPDATABLE_FIELDS` whitelist (name_i18n, description_i18n, sort_order)
- **Guards:** `code` guarded
- **Other:** `validate_deletable(has_category_refs=)`
- **Builder:** `AttributeTemplateBuilder`

### TemplateAttributeBinding (entities.py lines 601-688)
- **Factory:** `TemplateAttributeBinding.create(template_id=, attribute_id=, sort_order?, requirement_level?, filter_settings?, binding_id?)`
- **Validations:** sort_order non-negative, filter_settings structural validation (max 20 keys, allowed key whitelist)
- **Update:** `update(**kwargs)` with `_UPDATABLE_FIELDS` (sort_order, requirement_level, filter_settings)
- **Builder:** `TemplateAttributeBindingBuilder`

### AttributeGroup (entities.py lines 696-786)
- **Factory:** `AttributeGroup.create(code, name_i18n, sort_order?, group_id?)`
- **Validations:** name_i18n non-empty/completeness/non-blank, sort_order non-negative
- **Update:** `update(name_i18n?, sort_order?)`
- **Guards:** `code` guarded
- **Builder:** `AttributeGroupBuilder`

### Attribute (entities.py lines 794-1069)
- **Factory:** `Attribute.create(code=, slug=, name_i18n=, data_type=, ui_type=, is_dictionary=, group_id=, ...)` with BehaviorFlags or individual flags
- **Validations:** slug format, name_i18n, i18n completeness, search_weight range (1-10), validation_rules compatible with data_type
- **Update:** `update(**kwargs)` with complex behavior: BehaviorFlags object OR individual flag kwargs merged
- **Guards:** `code` and `slug` guarded
- **Properties:** backward-compat properties `is_filterable`, `is_searchable`, etc. delegate to `behavior`
- **Builder:** `AttributeBuilder`

### AttributeValue (entities.py lines 1072-1210)
- **Factory:** `AttributeValue.create(attribute_id=, code=, slug=, value_i18n=, ...)`
- **Validations:** value_i18n non-empty/completeness/non-blank, slug format, sort_order non-negative
- **Update:** `update(**kwargs)` with `_UPDATABLE_FIELDS`
- **Builder:** `AttributeValueBuilder`

### ProductAttributeValue (entities.py lines 1213-1258)
- **Factory:** `ProductAttributeValue.create(product_id=, attribute_id=, attribute_value_id=, pav_id?)`
- **Validations:** None (simple pivot entity)
- **Builder:** `ProductAttributeValueBuilder`

### SKU (entities.py lines 1267-1398)
- **Not standalone:** Created via `Product.add_sku()` only
- **Validations in `__attrs_post_init__`:** compare_at_price > price, currency match, compare_at_price amount > 0, cannot have compare_at_price without price
- **Update:** `update(**kwargs)` with price/compare_at_price cross-validation (validate-then-mutate pattern)
- **Other:** `soft_delete()`, `_UPDATABLE_FIELDS` (sku_code, price, compare_at_price, is_active)
- **Builder:** `SKUBuilder` (calls `Product.add_sku()` internally)

### ProductVariant (entities.py lines 1406-1558)
- **Factory:** `ProductVariant.create(product_id=, name_i18n=, ...)`
- **Validations:** name_i18n non-empty/completeness/non-blank, sort_order non-negative
- **Update:** `update(**kwargs)` with complex default_price/default_currency interaction (both together, price-only, currency-only paths)
- **Other:** `soft_delete()` cascades to SKUs, read-only `skus` property tuple
- **Builder:** `ProductVariantBuilder`

### MediaAsset (entities.py lines 1566-1654)
- **Factory:** `MediaAsset.create(product_id=, media_type=, role=, ...)`
- **Validations:** media_type/role string-to-enum conversion and invalid string rejection, sort_order non-negative, external assets require URL
- **No update method** -- simple record entity using `@define` (not AggregateRoot)
- **Builder:** `MediaAssetBuilder`

### Product (entities.py lines 1663-2221)
- **Factory:** `Product.create(slug=, title_i18n=, brand_id=, primary_category_id=, ...)`
- **Validations:** slug format, title_i18n non-empty/completeness/non-blank
- **Update:** `update(**kwargs)` with `_UPDATABLE_FIELDS`, brand_id/primary_category_id cannot be set to None
- **Guards:** `status` guarded (must use `transition_status()`)
- **Aggregate methods:** `add_variant()`, `remove_variant()`, `add_sku()`, `remove_sku()`, `find_variant()`, `find_sku()`, `soft_delete()`, `transition_status()`
- **FSM:** DRAFT->ENRICHING, ENRICHING->DRAFT|READY_FOR_REVIEW, READY_FOR_REVIEW->ENRICHING|PUBLISHED, PUBLISHED->ARCHIVED, ARCHIVED->DRAFT
- **Readiness checks:** Transition to READY_FOR_REVIEW or PUBLISHED requires active SKUs; PUBLISHED also requires at least one priced SKU
- **Other:** `compute_variant_hash()` (static), auto-creates default variant on `create()`, emits domain events (ProductCreatedEvent, ProductUpdatedEvent, ProductStatusChangedEvent, ProductDeletedEvent, VariantAddedEvent, VariantDeletedEvent, SKUAddedEvent, SKUDeletedEvent)
- **Builder:** `ProductBuilder`

### Value Objects (value_objects.py)
- **Money:** `@frozen`, amount >= 0, currency 3 chars, auto-uppercase, ordering comparisons with currency check (`__lt__`, `__le__`, `__gt__`, `__ge__`), `from_primitives()` factory, `_check_currency()` guard
- **BehaviorFlags:** `@frozen`, search_weight range 1-10 validation in `__attrs_post_init__`, default values (all False, search_weight=5)
- **SLUG_RE:** `^[a-z0-9]+(?:-[a-z0-9]+)*$` compiled regex -- test valid/invalid patterns
- **validate_i18n_completeness:** Checks REQUIRED_LOCALES `{"ru", "en"}`, raises `MissingRequiredLocalesError`
- **validate_validation_rules:** data_type-specific rule key validation (STRING: min_length/max_length/pattern, NUMERIC: min_value/max_value, BOOLEAN: no rules), type checks on values, cross-field checks (min <= max)
- **Enums:** ProductStatus (5 values), AttributeDataType (4), AttributeUIType (5), AttributeLevel (2), RequirementLevel (3), MediaType (4), MediaRole (6) -- all StrEnum with lowercase string values

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Individual boolean flags on Attribute | BehaviorFlags value object | Current codebase | Attribute.create() accepts both; test both paths |
| No Ellipsis sentinel | Ellipsis for "keep current" | Current codebase | Tests must distinguish None (clear) from unset (keep) |

**Deprecated/outdated:**
- None -- this is a greenfield test-writing phase, no deprecated approaches relevant.

## Open Questions

1. **Failing test in `test_category_effective_family.py`**
   - What we know: `test_update_clear_template_id_does_not_clear_effective` fails because `Category.update(template_id=None)` now clears `effective_template_id` when `parent_effective_template_id` is `...` (default)
   - What's unclear: Was this an intentional code change or a regression? The test comment says "handler must explicitly set effective"
   - Recommendation: Investigate during implementation. If the code behavior is intentional, fix the test assertion. If it's a regression, fix the entity code. Either way, document the decision.

2. **MediaAsset: No update method**
   - What we know: MediaAsset uses `@define` (not `@dataclass` from attr), has no `update()` method, and does not extend `AggregateRoot`
   - What's unclear: Should we test update scenarios for MediaAsset?
   - Recommendation: Test only `create()` factory and its validation. No update tests needed since there's no update method.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + hypothesis 6.151.9 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -x --tb=short -q --no-cov` |
| Full suite command | `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOM-01 | Entity factory methods create valid entities | unit | `uv run pytest tests/unit/modules/catalog/domain/test_brand.py tests/unit/modules/catalog/domain/test_category.py tests/unit/modules/catalog/domain/test_product.py -x --no-cov` | Wave 0 |
| DOM-01 | Entity update methods mutate correctly | unit | `uv run pytest tests/unit/modules/catalog/domain/ -k "update" -x --no-cov` | Wave 0 |
| DOM-01 | Factory methods reject invalid inputs | unit | `uv run pytest tests/unit/modules/catalog/domain/ -k "reject or invalid" -x --no-cov` | Wave 0 |
| DOM-05 | Money immutability and validation | unit | `uv run pytest tests/unit/modules/catalog/domain/test_value_objects.py -x --no-cov` | Wave 0 |
| DOM-05 | BehaviorFlags immutability and range validation | unit | `uv run pytest tests/unit/modules/catalog/domain/test_value_objects.py -x --no-cov` | Wave 0 |
| DOM-05 | Slug regex validation | unit | `uv run pytest tests/unit/modules/catalog/domain/test_value_objects.py -k "slug" -x --no-cov` | Wave 0 |
| DOM-05 | i18n completeness validation | unit | `uv run pytest tests/unit/modules/catalog/domain/test_value_objects.py -k "i18n" -x --no-cov` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -x --tb=short -q --no-cov`
- **Per wave merge:** `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -v --no-cov`
- **Phase gate:** Full suite green before `/gsd:verify-work`

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
- [ ] Fix failing test in `test_category_effective_family.py`

## Project Constraints (from CLAUDE.md)

- **GSD Workflow:** Use GSD commands for all file changes (enforced)
- **Tech Stack:** Python 3.14, attrs for domain models, pytest for testing
- **Architecture:** Hexagonal/CQRS -- domain layer has zero infrastructure imports
- **Testing conventions:** `test_*.py` naming, `Test*` classes, `test_*` functions
- **pytest markers:** `@pytest.mark.unit` marker available but not required (tests under `tests/unit/` are implicitly unit tests)
- **Ruff:** Linting with line-length 88, target py314
- **Imports:** Full paths from `src.` root, tests import from `tests.factories.*`
- **No async in domain tests:** Domain entities are pure sync Python
- **asyncio_mode = auto:** pytest-asyncio will auto-detect async tests; since all these tests are sync, no special handling needed

## Sources

### Primary (HIGH confidence)
- `backend/src/modules/catalog/domain/entities.py` -- All entity factory/update methods, validation logic (2,220 lines, read in full)
- `backend/src/modules/catalog/domain/value_objects.py` -- Money, BehaviorFlags, enums, validators (436 lines, read in full)
- `backend/src/modules/catalog/domain/exceptions.py` -- All domain exceptions (645 lines, read in full)
- `backend/src/modules/catalog/domain/events.py` -- All 27 catalog events (558 lines, read in full)
- `backend/tests/unit/modules/identity/domain/test_entities.py` -- Established test pattern (310 lines, read in full)
- `backend/tests/unit/modules/catalog/domain/test_category_effective_family.py` -- Existing test (9 tests, 1 failing, read in full)
- `backend/tests/factories/brand_builder.py` -- Builder pattern reference (read in full)
- `backend/tests/factories/product_builder.py` -- ProductBuilder with auto-variant (read in full)
- `backend/tests/factories/sku_builder.py` -- SKUBuilder using Product.add_sku() (read in full)
- `backend/tests/factories/attribute_builder.py` -- Attribute, AttributeValue, PAV builders (read in full)
- `backend/tests/factories/attribute_template_builder.py` -- Template and binding builders (read in full)
- `backend/tests/factories/attribute_group_builder.py` -- Group builder (read in full)
- `backend/tests/factories/variant_builder.py` -- Variant builder (read in full)
- `backend/tests/factories/strategies/primitives.py` -- Hypothesis strategies (read in full)
- `backend/src/shared/interfaces/entities.py` -- AggregateRoot, DomainEvent bases (read in full)
- `backend/src/modules/catalog/application/constants.py` -- REQUIRED_LOCALES, DEFAULT_CURRENCY (read in full)

### Secondary (MEDIUM confidence)
- `backend/pytest.ini` -- Full pytest configuration (read in full, verified test run works)
- `backend/pyproject.toml` -- Pytest markers, ruff/mypy config (read relevant sections)

### Tertiary (LOW confidence)
- None -- all findings are from direct source code inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- verified all packages installed and working via test run
- Architecture: HIGH -- patterns derived from existing test file and project conventions
- Pitfalls: HIGH -- all pitfalls discovered from actual source code analysis
- Entity testing surface: HIGH -- complete inventory from reading full entities.py (2,220 lines)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no planned entity changes)
