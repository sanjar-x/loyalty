# Phase 1: Test Infrastructure - Research

**Researched:** 2026-03-28
**Domain:** Python test tooling, property-based testing, in-memory fakes, query profiling
**Confidence:** HIGH

## Summary

Phase 1 builds the test infrastructure consumed by Phases 2-8. It delivers zero test cases -- only libraries, builders, fakes, strategies, and utilities. The codebase already has a mature test setup (pytest, pytest-asyncio, polyfactory, testcontainers, Dishka DI, nested-transaction rollback) plus established factory patterns (fluent Builders with `.with_*()` / `.build()`, Object Mothers, Polyfactory ORM factories). The phase adds six new dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) and builds five categories of infrastructure: (1) per-entity fluent Builders, (2) Polyfactory ORM factories for new catalog models, (3) a full in-memory FakeUnitOfWork with dict-based repositories, (4) Hypothesis strategies composable from leaf to aggregate tree level, and (5) an `assert_query_count` context manager using SQLAlchemy's connection event system.

The project uses `attrs` `@define` and `@dataclass` decorators for all domain entities. Hypothesis has built-in support for attrs classes via `st.builds()` and `st.from_type()`, which infer required arguments from type annotations and attrs validators. The key complexity is building composable strategies that handle the EAV domain's combinatorial nature -- generating valid i18n dicts (requiring both `"ru"` and `"en"` keys), valid slugs matching `^[a-z0-9]+(-[a-z0-9]+)*$`, Money value objects with non-negative amounts and 3-character currency codes, and full Product->Variant->SKU hierarchies with computed variant hashes.

**Primary recommendation:** Follow the locked decisions from CONTEXT.md exactly -- one builder file per entity, hypothesis strategies in `tests/factories/strategies/`, FakeUoW in `tests/fakes/`, and N+1 detection in `tests/utils/`. Use `st.builds()` with explicit strategy arguments (not `from_type()` auto-inference) for domain entities since the factory `create()` class methods have complex validation that auto-inference cannot handle.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use fluent Builders as the primary factory pattern for all catalog domain entities (ProductBuilder, SKUBuilder, BrandBuilder, etc.). Mothers become thin wrappers calling builders with sensible defaults.
- **D-02:** Expand Polyfactory ORM factories (orm_factories.py) for new catalog ORM models. Builders are for domain entities, Polyfactory for ORM-level seeding.
- **D-03:** Build a full in-memory FakeUnitOfWork with real dict-based repository storage. It must track registered aggregates, collect domain events on commit, and allow tests to verify actual state changes (not mock interactions).
- **D-04:** The existing `make_uow()` AsyncMock pattern in identity/user tests remains untouched -- FakeUoW is for new catalog tests only.
- **D-05:** Build full aggregate tree strategies -- generate complete Product->Variant->SKU hierarchies with attribute values. This catches EAV combinatorial edge cases that targeted tests miss.
- **D-06:** Strategies must compose: leaf strategies (Money, slugs, i18n names) combine into entity strategies, which combine into aggregate trees. Each level usable independently.
- **D-07:** One builder file per entity: `product_builder.py`, `brand_builder.py`, `category_builder.py`, `attribute_builder.py`, `sku_builder.py`, `variant_builder.py`, etc. Placed under `tests/factories/`.
- **D-08:** One hypothesis strategy file per entity domain, co-located with builders: `tests/factories/strategies/` directory.
- **D-09:** Build an `assert_query_count(session, expected)` context manager using SQLAlchemy's `after_cursor_execute` event.
- **D-10:** Also build pre-built catalog query count assertions for common patterns (list_products, get_product_detail, storefront queries). These become reference baselines for Phases 7-8.
- **D-11:** Use per-test inline AsyncMock for cross-module dependencies (ISupplierQueryService, IImageBackendClient). Keep stubs simple and local to each test rather than building shared fakes directory.
- **D-12:** Use class-per-entity organization: TestBrand, TestProduct, TestSKU classes with descriptive test methods. This matches the existing identity module pattern (TestIdentity, TestCustomer).

### Claude's Discretion
- Exact Builder API design (method names, chaining style)
- Internal structure of FakeUnitOfWork (dict keys, collection types)
- Hypothesis strategy shrinking configuration
- Whether to add pytest fixtures wrapping builders for common test setups

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Install and configure new test dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) | Standard Stack section: verified versions, installation command, pyproject.toml integration |
| INFRA-02 | Create test data builders/factories for all catalog entities (Product, ProductVariant, SKU, Attribute, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Brand, Category) | Architecture Patterns: Builder pattern analysis, entity signatures catalog, existing pattern reference |
| INFRA-03 | Build FakeUnitOfWork for command handler unit test isolation | Architecture Patterns: FakeUoW design, IUnitOfWork contract, real UoW behavior reference |
| INFRA-04 | Build hypothesis strategies for attrs-based domain models | Architecture Patterns: Strategy composition, attrs integration, domain constraint mapping |
| INFRA-05 | Implement N+1 query detection via SQLAlchemy `after_cursor_execute` event context manager | Architecture Patterns: Event listener API, async session binding, context manager design |
</phase_requirements>

## Standard Stack

### Core (New Dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hypothesis | >=6.151.5 | Property-based testing / strategy composition | De facto PBT library for Python; built-in attrs support via `st.builds()` |
| schemathesis | >=4.13.0 | OpenAPI schema fuzzing (installed now, used in Phase 8 / v2) | Only tool that auto-generates API test cases from OpenAPI spec |
| respx | >=0.22.0 | Mock httpx async HTTP requests | Purpose-built for httpx mocking; the project uses httpx for service-to-service calls |
| dirty-equals | >=0.11 | Declarative assertion helpers (`IsUUID()`, `IsDatetime()`, `IsPartialDict()`) | Eliminates boilerplate in dict/JSON assertions; by pydantic's author |
| pytest-randomly | >=4.0.1 | Randomize test execution order per session | Exposes hidden test-order dependencies; controlled via seed |
| pytest-timeout | >=2.4.0 | Per-test timeout enforcement | Prevents stuck tests in CI; configurable default + per-test override |

### Existing (Already Installed)
| Library | Version | Purpose |
|---------|---------|---------|
| pytest | 9.0.2 | Test runner |
| pytest-asyncio | >=1.3.0 | Async test support (mode: auto) |
| pytest-cov | >=7.0.0 | Coverage reporting |
| pytest-archon | >=0.0.7 | Architecture fitness functions |
| polyfactory | 3.3.0 | ORM model test data factories |
| testcontainers | >=4.14.1 | Docker-based integration test infrastructure |
| attrs | 26.1.0 | Domain model definitions |
| sqlalchemy | 2.1.0b1 | ORM + event system for N+1 detection |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hypothesis `st.builds()` | hypothesis `st.from_type()` | `from_type()` auto-infers but fails on complex factory methods with business validation; `st.builds()` with explicit args is more predictable |
| Custom FakeUoW | Extending `make_uow()` AsyncMock | AsyncMock verifies mock interactions, not actual state -- FakeUoW enables state-based testing per D-03 |
| `after_cursor_execute` event | `echo=True` SQL logging | Event-based counting is programmatic and assertable; logging is manual inspection |

**Installation:**
```bash
cd backend
uv add --group dev hypothesis schemathesis respx dirty-equals pytest-randomly pytest-timeout
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
+-- conftest.py                    # Root conftest (existing -- unchanged)
+-- factories/
|   +-- __init__.py                # Existing
|   +-- builders.py                # Existing (RoleBuilder, SessionBuilder, CategoryBuilder)
|   +-- brand_builder.py           # NEW: BrandBuilder
|   +-- product_builder.py         # NEW: ProductBuilder
|   +-- variant_builder.py         # NEW: ProductVariantBuilder
|   +-- sku_builder.py             # NEW: SKUBuilder
|   +-- attribute_builder.py       # NEW: AttributeBuilder + AttributeValueBuilder
|   +-- attribute_template_builder.py  # NEW: AttributeTemplateBuilder
|   +-- attribute_group_builder.py # NEW: AttributeGroupBuilder
|   +-- binding_builder.py         # NEW: TemplateAttributeBindingBuilder
|   +-- media_asset_builder.py     # NEW: MediaAssetBuilder
|   +-- pav_builder.py             # NEW: ProductAttributeValueBuilder
|   +-- catalog_mothers.py         # Existing -- will be updated to delegate to builders
|   +-- identity_mothers.py        # Existing -- unchanged
|   +-- orm_factories.py           # Existing -- will be expanded with catalog ORM models
|   +-- schema_factories.py        # Existing -- unchanged
|   +-- strategies/
|       +-- __init__.py            # NEW
|       +-- primitives.py          # NEW: Money, slug, i18n_dict, BehaviorFlags strategies
|       +-- brand_strategies.py    # NEW: Brand strategy
|       +-- category_strategies.py # NEW: Category + tree strategies
|       +-- attribute_strategies.py # NEW: Attribute, AttributeValue, AttributeGroup strategies
|       +-- template_strategies.py # NEW: AttributeTemplate, TemplateAttributeBinding strategies
|       +-- product_strategies.py  # NEW: Product -> Variant -> SKU aggregate tree strategy
+-- fakes/
|   +-- __init__.py                # Existing
|   +-- oidc_provider.py           # Existing -- unchanged
|   +-- catalog_uow.py            # NEW: FakeCatalogUnitOfWork + FakeRepositories
+-- utils/
    +-- __init__.py                # NEW
    +-- query_counter.py           # NEW: assert_query_count context manager + catalog presets
```

### Pattern 1: Fluent Builder (Entity Factories)
**What:** Each catalog entity gets a builder class with `.with_*()` mutators and `.build()` terminal
**When to use:** Every time a test needs a domain entity instance with specific or default values
**Example:**
```python
# Source: Existing tests/factories/builders.py CategoryBuilder pattern
class BrandBuilder:
    """Fluent builder for Brand entities with sensible defaults."""

    def __init__(self) -> None:
        self._name = "Test Brand"
        self._slug: str | None = None
        self._logo_url: str | None = None
        self._logo_storage_object_id: uuid.UUID | None = None

    def with_name(self, name: str) -> BrandBuilder:
        self._name = name
        return self

    def with_slug(self, slug: str) -> BrandBuilder:
        self._slug = slug
        return self

    def with_logo(self, url: str, storage_id: uuid.UUID | None = None) -> BrandBuilder:
        self._logo_url = url
        self._logo_storage_object_id = storage_id
        return self

    def build(self) -> Brand:
        slug = self._slug or f"{self._name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        return Brand.create(
            name=self._name,
            slug=slug,
            logo_url=self._logo_url,
            logo_storage_object_id=self._logo_storage_object_id,
        )
```

**Key design rule:** Builders always call `Entity.create()` factory methods (not raw `__init__`), so all domain validation runs. Default values must satisfy all validation rules (i18n requires both "ru" and "en" keys, slugs must match `^[a-z0-9]+(-[a-z0-9]+)*$`).

### Pattern 2: FakeUnitOfWork (State-Based Test Double)
**What:** In-memory implementation of IUnitOfWork with dict-based fake repositories
**When to use:** Command handler unit tests that need to verify state changes without a database
**Example:**
```python
# Source: IUnitOfWork interface at backend/src/shared/interfaces/uow.py
class FakeCatalogUnitOfWork(IUnitOfWork):
    """In-memory UoW for catalog command handler unit tests."""

    def __init__(self) -> None:
        self.brands: FakeBrandRepository = FakeBrandRepository()
        self.categories: FakeCategoryRepository = FakeCategoryRepository()
        self.products: FakeProductRepository = FakeProductRepository()
        # ... all 10 repo interfaces
        self._aggregates: list[AggregateRoot] = []
        self._committed = False
        self.collected_events: list[DomainEvent] = []

    async def __aenter__(self) -> FakeCatalogUnitOfWork:
        self._aggregates.clear()
        self._committed = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        self._aggregates.clear()

    async def flush(self) -> None:
        pass  # No-op for in-memory

    async def commit(self) -> None:
        for agg in self._aggregates:
            self.collected_events.extend(agg.domain_events)
            agg.clear_domain_events()
        self._committed = True

    async def rollback(self) -> None:
        self._committed = False
        self._aggregates.clear()

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)


class FakeBrandRepository(IBrandRepository):
    """Dict-based in-memory Brand repository."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Brand] = {}

    async def add(self, entity: Brand) -> Brand:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> Brand | None:
        return self._store.get(entity_id)

    async def update(self, entity: Brand) -> Brand:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    # ... additional IBrandRepository methods
```

**Critical behavior to replicate from real UoW:**
1. `register_aggregate()` tracks aggregates for event collection
2. `commit()` extracts domain events from all registered aggregates and clears them
3. `__aexit__` calls `rollback()` on exception
4. Fake repos use `dict[uuid.UUID, Entity]` for storage -- enables state assertions

### Pattern 3: Composable Hypothesis Strategies
**What:** Layered strategies from primitives to full aggregate trees
**When to use:** Property-based tests for domain model invariants (Phase 2+)
**Example:**
```python
# Source: Hypothesis st.builds() + attrs integration
from hypothesis import strategies as st

# Layer 1: Primitive strategies
def i18n_dict(min_size: int = 2) -> st.SearchStrategy[dict[str, str]]:
    """Strategy for valid i18n dicts with required 'ru' and 'en' keys."""
    return st.fixed_dictionaries({
        "ru": st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        "en": st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    })

def valid_slug() -> st.SearchStrategy[str]:
    """Strategy for valid slugs matching ^[a-z0-9]+(-[a-z0-9]+)*$."""
    segment = st.from_regex(r"[a-z0-9]+", fullmatch=True)
    return st.lists(segment, min_size=1, max_size=4).map("-".join)

def money(
    min_amount: int = 0,
    max_amount: int = 1_000_000_00,
    currency: str = "RUB",
) -> st.SearchStrategy[Money]:
    return st.builds(
        Money,
        amount=st.integers(min_value=min_amount, max_value=max_amount),
        currency=st.just(currency),
    )

# Layer 2: Entity strategies
@st.composite
def brand_strategy(draw):
    return Brand.create(
        name=draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip())),
        slug=draw(valid_slug()),
    )

# Layer 3: Aggregate tree strategies
@st.composite
def product_with_skus(draw, min_skus=1, max_skus=5):
    brand = draw(brand_strategy())
    category = draw(category_strategy())
    product = Product.create(
        slug=draw(valid_slug()),
        title_i18n=draw(i18n_dict()),
        brand_id=brand.id,
        primary_category_id=category.id,
    )
    variant = product.variants[0]  # default variant from create()
    for _ in range(draw(st.integers(min_value=min_skus, max_value=max_skus))):
        product.add_sku(
            variant.id,
            sku_code=draw(st.text(
                min_size=3, max_size=20,
                alphabet=st.characters(whitelist_categories=("L", "N")),
            )),
            price=draw(money()),
        )
    return product
```

**Critical constraint:** All i18n dicts MUST include both `"ru"` and `"en"` keys (see `REQUIRED_LOCALES` in `src/modules/catalog/application/constants.py`). Strategies that omit this will generate entities that fail validation.

### Pattern 4: N+1 Query Detection Context Manager
**What:** Context manager that counts SQL queries via SQLAlchemy connection events
**When to use:** Integration tests validating query efficiency (Phase 7-8)
**Example:**
```python
# Source: SQLAlchemy 2.1 ConnectionEvents API
from contextlib import asynccontextmanager
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

@asynccontextmanager
async def assert_query_count(session: AsyncSession, expected: int):
    """Assert that exactly `expected` SQL queries execute within the block.

    Uses SQLAlchemy's after_cursor_execute connection event to count queries.
    Works with async sessions by binding to the underlying sync connection.
    """
    counter = {"count": 0}
    sync_conn = await session.connection()
    raw_conn = sync_conn.connection  # underlying sync connection

    def _count_queries(conn, cursor, statement, parameters, context, executemany):
        counter["count"] += 1

    event.listen(raw_conn, "after_cursor_execute", _count_queries)
    try:
        yield counter
    finally:
        event.remove(raw_conn, "after_cursor_execute", _count_queries)

    assert counter["count"] == expected, (
        f"Expected {expected} queries, got {counter['count']}"
    )
```

**Important async caveat:** SQLAlchemy 2.1 async sessions wrap a sync connection. The `after_cursor_execute` event must be registered on the sync connection, not the async session. Access via `await session.connection()` then `.connection` property.

### Anti-Patterns to Avoid
- **Building entities via raw `__init__` instead of `Entity.create()`:** Bypasses domain validation (slug format, i18n completeness, sort_order non-negative). Builders MUST use factory methods.
- **Sharing mutable builder state across tests:** Each test must instantiate its own builder. Never store builders as class-level fixtures.
- **Auto-generating i18n dicts without required locales:** All i18n strategies must produce dicts with both `"ru"` and `"en"` keys. The `validate_i18n_completeness()` function raises `MissingRequiredLocalesError` otherwise.
- **Registering SQLAlchemy events on the Engine globally:** Use connection-scoped events (not engine-scoped) to avoid cross-test interference. Register on the specific connection, not the global engine.
- **FakeUoW that skips event collection:** The real UoW extracts domain events from registered aggregates on commit and clears them. FakeUoW MUST replicate this behavior or downstream event-emission tests will give false positives.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP mocking for httpx | Custom mock transport | respx | Handles async, route matching, assertions, error simulation |
| Approximate assertions | Custom `assertAlmostEqual` wrappers | dirty-equals (`IsUUID()`, `IsDatetime()`, `IsPartialDict()`) | Composable, readable, handles edge cases |
| Test randomization | Custom random seed management | pytest-randomly | Integrates with pytest, seed logging, reproducible ordering |
| Test timeouts | Custom `asyncio.wait_for` wrappers | pytest-timeout | Per-test and global configuration, signal/thread methods |
| ORM model factories | Manual model instantiation | polyfactory `SQLAlchemyFactory` | Auto-populates required columns, handles relationships |

**Key insight:** The phase installs libraries now that are consumed in later phases (schemathesis in Phase 8+, respx in Phase 5-6 for external client mocking, dirty-equals everywhere). Installing them in Phase 1 means later phases just use them.

## Catalog Entity Inventory (What Builders Must Cover)

Each entity listed below needs a builder. The table documents the `create()` signature to guide builder design.

| Entity | Module | Factory Method | Required Args | Optional Args | Notes |
|--------|--------|---------------|---------------|---------------|-------|
| Brand | AggregateRoot | `Brand.create()` | name, slug | brand_id, logo_url, logo_storage_object_id | Guarded field: slug |
| Category | AggregateRoot | `Category.create_root()` / `Category.create_child()` | name_i18n, slug, [parent for child] | sort_order, template_id | Two factory methods; builder needs `.under(parent)` |
| AttributeGroup | AggregateRoot | `AttributeGroup.create()` | code, name_i18n | sort_order, group_id | Guarded field: code |
| Attribute | AggregateRoot | `Attribute.create()` | code, slug, name_i18n, data_type, ui_type, is_dictionary, group_id | description_i18n, level, behavior flags, validation_rules, attribute_id | Complex -- 12+ params. Builder essential. |
| AttributeValue | Child entity | `AttributeValue.create()` | attribute_id, code, slug, value_i18n | search_aliases, meta_data, value_group, sort_order, is_active, value_id | Belongs to Attribute |
| AttributeTemplate | AggregateRoot | `AttributeTemplate.create()` | code, name_i18n | description_i18n, sort_order | Guarded field: code |
| TemplateAttributeBinding | AggregateRoot | `TemplateAttributeBinding.create()` | template_id, attribute_id | sort_order, requirement_level, filter_settings, binding_id | Links template to attribute |
| Product | AggregateRoot | `Product.create()` | slug, title_i18n, brand_id, primary_category_id | description_i18n, supplier_id, source_url, country_of_origin, tags, product_id | Auto-creates 1 default variant. Emits ProductCreatedEvent. |
| ProductVariant | Child entity | `ProductVariant.create()` | product_id, name_i18n | description_i18n, sort_order, default_price, default_currency, variant_id | Created via `Product.add_variant()` |
| SKU | Child entity | Via `Product.add_sku()` | variant_id, sku_code | price, compare_at_price, is_active, variant_attributes | Created via aggregate method, not standalone create() |
| ProductAttributeValue | Child entity | `ProductAttributeValue.create()` | product_id, attribute_id, attribute_value_id | pav_id | EAV pivot entity |
| MediaAsset | Entity (not AR) | `MediaAsset.create()` | product_id, media_type, role | variant_id, sort_order, is_external, storage_object_id, url, image_variants | Uses @define (not @dataclass) |

**Existing builders to preserve:** `CategoryBuilder` in `builders.py` already exists but is minimal. Per D-07, create a new `category_builder.py` with an expanded builder and update the existing `builders.py` CategoryBuilder to delegate or co-exist.

## FakeUnitOfWork: Repository Interface Map

The FakeUoW must provide fake implementations for all 10 catalog repository interfaces:

| Interface | Key Methods Beyond CRUD | Storage Key Type |
|-----------|------------------------|------------------|
| IBrandRepository | check_slug_exists, check_slug_exists_excluding, has_products, check_name_exists, check_name_exists_excluding, get_for_update | dict[UUID, Brand] |
| ICategoryRepository | get_all_ordered, check_slug_exists(slug, parent_id), has_children, has_products, update_descendants_full_slug, propagate_effective_template_id, get_for_update | dict[UUID, Category] |
| IAttributeGroupRepository | check_code_exists, get_by_code, has_attributes, move_attributes_to_group | dict[UUID, AttributeGroup] |
| IAttributeRepository | get_many, check_code_exists, check_slug_exists, has_product_attribute_values, get_for_update | dict[UUID, Attribute] |
| IAttributeValueRepository | get_many, check_code_exists, check_slug_exists, has_product_references, list_ids_by_attribute, bulk_update_sort_order | dict[UUID, AttributeValue] |
| IProductRepository | check_slug_exists, get_for_update_with_variants, get_with_variants, check_sku_code_exists | dict[UUID, Product] |
| IProductAttributeValueRepository | list_by_product, get_by_product_and_attribute, check_assignment_exists, check_assignments_exist_bulk | dict[UUID, PAV] |
| IMediaAssetRepository | list_by_product, list_by_storage_ids, delete_by_product, bulk_update_sort_order, check_main_exists | dict[UUID, MediaAsset] |
| IAttributeTemplateRepository | check_code_exists, has_category_references, get_category_ids_by_template_ids | dict[UUID, AttributeTemplate] |
| ITemplateAttributeBindingRepository | check_binding_exists, list_ids_by_template, get_bindings_for_templates, has_bindings_for_attribute | dict[UUID, TAB] |

**Design recommendation:** Implement fake repos as inner classes or separate classes within `tests/fakes/catalog_uow.py`. Each fake repo should implement the full interface (not just CRUD) since command handler tests will call check methods like `has_products()` and `check_slug_exists()`.

## Common Pitfalls

### Pitfall 1: i18n Validation Breaks Builders
**What goes wrong:** Builder defaults use `{"en": "Test Value"}` -- missing "ru" key causes `MissingRequiredLocalesError`.
**Why it happens:** `REQUIRED_LOCALES = frozenset({"ru", "en"})` is enforced in every entity `create()` method.
**How to avoid:** All builder defaults MUST include both locales: `{"en": "Test Value", "ru": "Tестовое значение"}`.
**Warning signs:** `MissingRequiredLocalesError` in any test that uses a builder.

### Pitfall 2: Product.create() Auto-Creates Default Variant
**What goes wrong:** ProductBuilder builds a product expecting zero variants, then tries to add variants manually.
**Why it happens:** `Product.create()` auto-appends one default variant to `_variants` (line 1811-1815 of entities.py).
**How to avoid:** ProductBuilder must account for the auto-created default variant. The builder's `with_variant()` / `with_sku()` methods should operate on the existing default variant or add additional ones.
**Warning signs:** Tests expecting empty variant list after Product construction.

### Pitfall 3: Hypothesis Strategy for Slugs Generates Invalid Patterns
**What goes wrong:** `st.text()` generates strings with spaces, uppercase, or special characters that fail `_validate_slug()`.
**Why it happens:** Slug validation uses `SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")` -- strict lowercase alphanumeric with hyphens, no leading/trailing hyphens, no consecutive hyphens.
**How to avoid:** Use `st.from_regex(r"[a-z][a-z0-9]{0,9}(-[a-z0-9]{1,10}){0,3}", fullmatch=True)` or build from segments.
**Warning signs:** `ValueError: ... slug must be non-empty and match pattern` during hypothesis shrinking.

### Pitfall 4: FakeUoW Event Collection Timing
**What goes wrong:** Tests check `uow.collected_events` before calling `commit()`, getting empty list.
**Why it happens:** Real UoW collects events during `commit()`, not when `register_aggregate()` is called. Events live on the aggregate until commit extracts them.
**How to avoid:** FakeUoW must replicate the same timing: `commit()` iterates aggregates, copies events to `collected_events`, then calls `clear_domain_events()`.
**Warning signs:** Event-assertion tests pass with FakeUoW but fail with real UoW, or vice versa.

### Pitfall 5: Async Context Manager Signature Mismatch
**What goes wrong:** FakeUoW used as `async with uow:` fails because `__aenter__` returns wrong type.
**Why it happens:** Real UoW returns `UnitOfWork` from `__aenter__`, and command handlers rely on `uow` variable having repo attributes.
**How to avoid:** `__aenter__` must return `self` (the FakeUoW instance). The FakeUoW exposes repositories as direct attributes (`.brands`, `.categories`, etc.) unlike the real UoW where repos are injected separately via Dishka.
**Warning signs:** `AttributeError: 'FakeCatalogUnitOfWork' has no attribute 'brands'` or similar in handler tests.

### Pitfall 6: SQLAlchemy Async Event Registration
**What goes wrong:** `event.listen(async_session, "after_cursor_execute", ...)` fails silently or raises.
**Why it happens:** SQLAlchemy events are sync-only and must be registered on the sync connection object, not the async wrapper.
**How to avoid:** Access the underlying sync connection: `sync_conn = await session.connection(); raw_conn = sync_conn.connection`.
**Warning signs:** Query counter stays at 0 even though queries execute.

### Pitfall 7: Guarded Field Assignment in Builders
**What goes wrong:** Builder tries `brand.slug = "new-slug"` and gets `AttributeError`.
**Why it happens:** All entities have `__setattr__` guards on specific fields (slug, status, code). Direct assignment raises after `__initialized` flag is set in `__attrs_post_init__`.
**How to avoid:** Builders MUST use `Entity.create()` factory methods which set fields before the guard activates, or use `Entity.update()` domain methods. Never assign guarded fields directly.
**Warning signs:** `AttributeError: Cannot set 'slug' directly on Brand. Use the update() method instead.`

## Code Examples

### Builder Default Values Reference (i18n-Safe)
```python
# All builders must use these patterns for i18n defaults
DEFAULT_I18N_NAME = {"en": "Test Item", "ru": "Tестовый элемент"}
DEFAULT_I18N_DESCRIPTION = {"en": "Test description", "ru": "Tестовое описание"}

# Slug generation from name
def _default_slug(name: str) -> str:
    base = name.lower().replace(" ", "-")
    return f"{base}-{uuid.uuid4().hex[:6]}"
```

### Hypothesis attrs Integration
```python
# Hypothesis supports attrs @define classes via st.builds()
# For entities with factory methods, use @composite instead of from_type()

from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import timedelta

@given(brand=brand_strategy())
def test_brand_has_valid_slug(brand: Brand):
    assert SLUG_RE.match(brand.slug)

# Shrinking configuration for expensive aggregate strategies
settings(
    max_examples=50,           # Reduce for slow aggregate trees
    suppress_health_check=[HealthCheck.too_slow],
    deadline=timedelta(seconds=5),
)
```

### FakeRepository Pattern for check_* Methods
```python
# Fake repos must implement all check methods using dict iteration
class FakeBrandRepository(IBrandRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Brand] = {}

    async def check_slug_exists(self, slug: str) -> bool:
        return any(b.slug == slug for b in self._store.values())

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        return any(
            b.slug == slug and b.id != exclude_id
            for b in self._store.values()
        )

    async def has_products(self, brand_id: uuid.UUID) -> bool:
        # Cross-repo check -- FakeUoW must provide product_store reference
        # or this returns False (configurable per test)
        return False

    async def get_for_update(self, brand_id: uuid.UUID) -> Brand | None:
        # In-memory -- no locking needed, same as get()
        return self._store.get(brand_id)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `make_uow()` AsyncMock | FakeUoW with real storage | Phase 1 (D-03) | Enables state-based assertions instead of mock-call verification |
| Individual flag params on Attribute | `BehaviorFlags` value object | Already done (QUAL-01) | Builders must set `behavior=BehaviorFlags(...)` |
| Single `entities.py` (2,220 lines) | Will be split in Phase 9 | Phase 9 (REF-01) | Builders import from single file now; Phase 9 adds backward-compatible re-exports |

**Deprecated/outdated:**
- `tests/factories/catalog_factories.py`: Empty file (0 bytes). Can be ignored or deleted.
- `tests/factories/storage_factories.py`: Empty file (0 bytes). Can be ignored or deleted.

## Open Questions

1. **FakeUoW cross-repository references**
   - What we know: `has_products(brand_id)` on FakeBrandRepository needs access to the product store
   - What's unclear: Whether to pass cross-repo references at construction time or provide a `configure()` method
   - Recommendation: Inject all fake repos into FakeUoW first, then set cross-references in `__init__` (e.g., `self.brands._product_store = self.products._store`). This is an internal implementation detail per Claude's discretion.

2. **Existing CategoryBuilder coexistence**
   - What we know: `builders.py` already has a `CategoryBuilder` with minimal API
   - What's unclear: Whether to extend it in-place or create a separate expanded builder in `category_builder.py`
   - Recommendation: Create the new `category_builder.py` with the full-featured builder. Keep the existing one in `builders.py` as-is to avoid breaking existing tests. Future cleanup can consolidate.

3. **Hypothesis settings profile for CI vs local**
   - What we know: Full aggregate tree strategies are slow (many combinations)
   - What's unclear: Whether to configure a CI profile with more examples
   - Recommendation: Use default settings (100 examples) for now. Add `@settings(max_examples=50)` on slow aggregate tree strategies. This can be tuned in later phases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio (auto mode) |
| Config file | `backend/pytest.ini` + `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && python -m pytest tests/unit/ -x -q --no-header --no-cov -p no:randomly` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | New deps install without import errors | smoke | `cd backend && python -c "import hypothesis; import schemathesis; import respx; import dirty_equals; import pytest_randomly; import pytest_timeout"` | N/A (import check) |
| INFRA-02 | Builders create valid entities with defaults | unit | `cd backend && python -m pytest tests/unit/test_builders_smoke.py -x --no-cov` | Wave 0 |
| INFRA-03 | FakeUoW tracks aggregates and collects events | unit | `cd backend && python -m pytest tests/unit/test_fake_uow_smoke.py -x --no-cov` | Wave 0 |
| INFRA-04 | Hypothesis strategies generate valid instances | unit | `cd backend && python -m pytest tests/unit/test_strategies_smoke.py -x --no-cov` | Wave 0 |
| INFRA-05 | Query counter detects exact query count | integration | `cd backend && python -m pytest tests/integration/test_query_counter_smoke.py -x --no-cov` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/unit/ -x -q --no-header --no-cov -p no:randomly`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_builders_smoke.py` -- covers INFRA-02 (one test per builder verifying `.build()` produces valid entity)
- [ ] `tests/unit/test_fake_uow_smoke.py` -- covers INFRA-03 (commit collects events, rollback clears, repos store/retrieve)
- [ ] `tests/unit/test_strategies_smoke.py` -- covers INFRA-04 (each strategy generates valid instances, shrinking works)
- [ ] `tests/integration/test_query_counter_smoke.py` -- covers INFRA-05 (counter matches actual query count on real DB)

## Sources

### Primary (HIGH confidence)
- `backend/src/modules/catalog/domain/entities.py` -- Full entity inventory, create() signatures, validation rules (2,221 lines read)
- `backend/src/modules/catalog/domain/value_objects.py` -- Money, BehaviorFlags, enums, SLUG_RE pattern
- `backend/src/modules/catalog/domain/interfaces.py` -- All 10 repository ABCs with full method signatures
- `backend/src/shared/interfaces/uow.py` -- IUnitOfWork interface contract
- `backend/src/infrastructure/database/uow.py` -- Real UoW implementation (event collection behavior reference)
- `backend/src/shared/interfaces/entities.py` -- AggregateRoot mixin, DomainEvent base
- `backend/tests/factories/builders.py` -- Existing builder pattern (RoleBuilder, SessionBuilder, CategoryBuilder)
- `backend/tests/factories/catalog_mothers.py` -- Existing Mother pattern
- `backend/tests/factories/orm_factories.py` -- Existing Polyfactory pattern
- `backend/tests/fakes/oidc_provider.py` -- Existing fake pattern reference
- `backend/pyproject.toml` -- Current dependency groups
- `backend/pytest.ini` -- Current test configuration
- SQLAlchemy 2.1 docs -- `after_cursor_execute` event API for query counting

### Secondary (MEDIUM confidence)
- [PyPI hypothesis](https://pypi.org/project/hypothesis/) -- Version 6.151.5, attrs support confirmed
- [PyPI schemathesis](https://pypi.org/project/schemathesis/) -- Version 4.13.0
- [PyPI respx](https://pypi.org/project/respx/) -- Version 0.22.0
- [PyPI dirty-equals](https://pypi.org/project/dirty-equals/) -- Version 0.11
- [PyPI pytest-randomly](https://pypi.org/project/pytest-randomly/) -- Version 4.0.1
- [PyPI pytest-timeout](https://pypi.org/project/pytest-timeout/) -- Version 2.4.0
- [SQLAlchemy 2.1 Performance FAQ](https://docs.sqlalchemy.org/en/21/faq/performance.html) -- Query profiling patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified on PyPI, versions confirmed
- Architecture: HIGH -- based on full codebase reading of existing patterns and all entity signatures
- Pitfalls: HIGH -- derived from direct reading of entity validation code and factory methods

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain -- test infrastructure libraries rarely break)
