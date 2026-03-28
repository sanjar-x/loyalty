# Phase 1: Test Infrastructure - Research

**Researched:** 2026-03-28
**Domain:** Python test tooling, test data factories, hypothesis strategies, SQLAlchemy event-based query counting
**Confidence:** HIGH

## Summary

Phase 1 delivers zero test cases -- it builds the infrastructure that Phases 2-8 consume. The work spans five areas: (1) installing six new test dependencies, (2) building fluent Builder classes for all nine catalog domain entities, (3) creating a FakeUnitOfWork with real dict-based repository storage, (4) building composable Hypothesis strategies for attrs-based domain models, and (5) implementing an N+1 query detection context manager using SQLAlchemy's `after_cursor_execute` event.

The existing codebase already has strong patterns to follow: fluent Builders in `tests/factories/builders.py` (RoleBuilder, SessionBuilder, CategoryBuilder), Object Mothers in `tests/factories/catalog_mothers.py` and `identity_mothers.py`, Polyfactory ORM factories in `tests/factories/orm_factories.py`, and a StubOIDCProvider fake in `tests/fakes/oidc_provider.py`. All domain entities use attrs `@define`/`@dataclass` with `create()` class methods and `AggregateRoot` mixin. The existing `make_uow()` AsyncMock pattern in identity tests remains untouched.

**Primary recommendation:** Follow existing builder/mother/fake patterns exactly, extend them for catalog entities, and add hypothesis strategies as composable leaf-to-tree building blocks under `tests/factories/strategies/`.

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
| INFRA-02 | Create test data builders/factories for all catalog entities (Product, ProductVariant, SKU, Attribute, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Brand, Category) | Architecture Patterns: Builder pattern, entity analysis, factory signatures from domain entities |
| INFRA-03 | Build FakeUnitOfWork for command handler unit test isolation | Architecture Patterns: FakeUoW design, IUnitOfWork interface analysis, repository interface inventory |
| INFRA-04 | Build hypothesis strategies for attrs-based domain models | Architecture Patterns: Strategy composition, attrs integration, value object constraints |
| INFRA-05 | Implement N+1 query detection via SQLAlchemy `after_cursor_execute` event context manager | Code Examples: SQLAlchemy event API, context manager pattern, query counting |

</phase_requirements>

## Standard Stack

### Core (New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hypothesis | >=6.151.9 | Property-based testing with composable strategies | Industry standard for PBT in Python; attrs integration via `st.builds()` |
| schemathesis | >=4.14.1 | OpenAPI-driven API fuzzing | v2 requirement ADV-01; install now to avoid dependency conflicts later |
| respx | >=0.22.0 | Mock httpx async HTTP calls | Pairs with project's httpx client; used for IImageBackendClient stubbing in later phases |
| dirty-equals | >=0.11 | Flexible assertion comparisons | Simplifies assertions on UUIDs, timestamps, approximate values in test output |
| pytest-randomly | >=4.0.1 | Randomize test execution order | Catches hidden test-order dependencies; seeds printed for reproduction |
| pytest-timeout | >=2.4.0 | Per-test timeout enforcement | Prevents hypothesis infinite loops and hanging integration tests |

### Existing (Already Installed)

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | >=9.0.2 | Test runner |
| pytest-asyncio | >=1.3.0 | Async test support (mode: auto) |
| pytest-cov | >=7.0.0 | Coverage reporting |
| pytest-archon | >=0.0.7 | Architecture fitness functions |
| polyfactory | >=3.3.0 | ORM model factories |
| testcontainers | >=4.14.1 | Docker-based integration tests |
| attrs | >=25.4.0 | Domain model definitions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hypothesis | faker + manual generators | Faker only generates random data, no shrinking or property-based discovery |
| respx | pytest-httpx | respx has better async support and directly targets httpx |
| dirty-equals | custom assertion helpers | dirty-equals is well-maintained, reduces boilerplate |
| Fluent Builders | factory_boy | factory_boy uses class-level config which is harder to compose for DDD entities with `create()` factory methods |

**Installation:**
```bash
cd backend
uv add --group dev "hypothesis>=6.151.9" "schemathesis>=4.14.1" "respx>=0.22.0" "dirty-equals>=0.11" "pytest-randomly>=4.0.1" "pytest-timeout>=2.4.0"
```

**Version verification:** Versions confirmed via `pip index versions` and `uv pip install --dry-run` on 2026-03-28. All packages are compatible with Python 3.14.

## Architecture Patterns

### Recommended Project Structure

```
tests/
  factories/
    builders.py              # EXISTING: RoleBuilder, SessionBuilder, CategoryBuilder
    catalog_mothers.py       # EXISTING: BrandMothers, CategoryMothers, etc.
    identity_mothers.py      # EXISTING: IdentityMothers, SessionMothers, etc.
    orm_factories.py         # EXISTING: Polyfactory ORM factories (extend here)
    brand_builder.py         # NEW: BrandBuilder
    product_builder.py       # NEW: ProductBuilder
    variant_builder.py       # NEW: ProductVariantBuilder
    sku_builder.py           # NEW: SKUBuilder
    attribute_builder.py     # NEW: AttributeBuilder, AttributeValueBuilder
    attribute_template_builder.py  # NEW: AttributeTemplateBuilder, BindingBuilder
    attribute_group_builder.py     # NEW: AttributeGroupBuilder
    strategies/
      __init__.py            # NEW
      primitives.py          # NEW: Money, slugs, i18n dicts, UUIDs
      entity_strategies.py   # NEW: Per-entity strategies composing primitives
      aggregate_strategies.py # NEW: Full Product->Variant->SKU trees
  fakes/
    oidc_provider.py         # EXISTING
    fake_uow.py              # NEW: FakeUnitOfWork + FakeRepositories
  utils/
    __init__.py              # NEW
    query_counter.py         # NEW: assert_query_count context manager
    catalog_query_baselines.py  # NEW: Pre-built assertion helpers
```

### Pattern 1: Fluent Builder (Locked Decision D-01)

**What:** Each catalog domain entity gets a builder class with `with_*()` methods and a `build()` method. Builders call the entity's `create()` factory method internally, handling required locales, slug generation, and UUID generation.

**When to use:** Whenever a test needs a domain entity with specific field overrides. Builders are the primary API; Mothers wrap builders for common scenarios.

**Example (following existing CategoryBuilder pattern):**
```python
# tests/factories/brand_builder.py
from __future__ import annotations
import uuid
from src.modules.catalog.domain.entities import Brand

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

### Pattern 2: FakeUnitOfWork with Dict-Based Storage (Locked Decision D-03)

**What:** A full in-memory UoW that implements `IUnitOfWork` with real dict-based repository storage. Tracks registered aggregates, collects domain events on commit, allows tests to verify state changes.

**When to use:** All catalog command handler unit tests. Replaces the need for mock-based UoW and enables verifying actual repository state after handler execution.

**Design (based on IUnitOfWork interface from `src/shared/interfaces/uow.py`):**
```python
# tests/fakes/fake_uow.py
from __future__ import annotations
import uuid
from typing import Any
from src.shared.interfaces.uow import IUnitOfWork
from src.shared.interfaces.entities import AggregateRoot, DomainEvent

class FakeRepository[T]:
    """Generic in-memory repository backed by a dict."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, T] = {}

    async def add(self, entity: T) -> T:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> T | None:
        return self._store.get(entity_id)

    async def update(self, entity: T) -> T:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    @property
    def items(self) -> dict[uuid.UUID, T]:
        """Direct access for test assertions."""
        return self._store


class FakeUnitOfWork(IUnitOfWork):
    """In-memory UoW for catalog command handler unit tests."""

    def __init__(self) -> None:
        self._aggregates: list[AggregateRoot] = []
        self._committed = False
        self._rolled_back = False
        self._collected_events: list[DomainEvent] = []
        # Repository instances -- set by test setup
        self.brands = FakeRepository()
        self.categories = FakeRepository()
        self.products = FakeRepository()
        # ... one per repository interface

    async def __aenter__(self) -> FakeUnitOfWork:
        self._aggregates.clear()
        self._committed = False
        self._rolled_back = False
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            await self.rollback()

    async def flush(self) -> None:
        pass  # No-op for in-memory

    async def commit(self) -> None:
        for agg in self._aggregates:
            self._collected_events.extend(agg.domain_events)
            agg.clear_domain_events()
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True
        self._aggregates.clear()

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def collected_events(self) -> list[DomainEvent]:
        return self._collected_events
```

**Critical design notes:**
- The real UoW's `commit()` extracts domain events from registered aggregates and writes them to the Outbox. The fake must replicate this behavior (collect events, then clear them from aggregates).
- Each repository interface (IBrandRepository, ICategoryRepository, etc.) needs a corresponding fake that extends FakeRepository with the interface-specific query methods (e.g., `check_slug_exists`, `has_products`).
- The FakeUoW should expose `committed`, `rolled_back`, and `collected_events` properties for test assertions.

### Pattern 3: Composable Hypothesis Strategies (Locked Decision D-05, D-06)

**What:** Three layers of strategies: (1) primitives (Money, slugs, i18n), (2) entity strategies, (3) aggregate tree strategies. Each layer is usable independently.

**When to use:** Property-based testing of domain invariants, EAV attribute validation, combinatorial edge cases.

**Example:**
```python
# tests/factories/strategies/primitives.py
from hypothesis import strategies as st
from src.modules.catalog.domain.value_objects import Money

REQUIRED_LOCALES = frozenset({"ru", "en"})

def i18n_names(min_length: int = 1, max_length: int = 50) -> st.SearchStrategy[dict[str, str]]:
    """Generate valid i18n dicts that always include required locales (ru, en)."""
    name = st.text(min_size=min_length, max_size=max_length, alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"), min_codepoint=32, max_codepoint=1000
    )).filter(lambda s: s.strip())
    return st.fixed_dictionaries({"ru": name, "en": name})

def valid_slugs(min_length: int = 1, max_length: int = 40) -> st.SearchStrategy[str]:
    """Generate valid URL-safe slugs matching SLUG_RE pattern."""
    segment = st.from_regex(r"[a-z0-9]+", fullmatch=True).filter(lambda s: 1 <= len(s) <= 20)
    return st.lists(segment, min_size=1, max_size=3).map(lambda parts: "-".join(parts)).filter(
        lambda s: len(s) <= max_length
    )

def money(
    min_amount: int = 0,
    max_amount: int = 100_000_00,
    currencies: list[str] | None = None,
) -> st.SearchStrategy[Money]:
    """Generate valid Money value objects."""
    curr = st.sampled_from(currencies or ["RUB", "USD", "EUR"])
    amt = st.integers(min_value=min_amount, max_value=max_amount)
    return st.builds(Money, amount=amt, currency=curr)
```

### Pattern 4: N+1 Query Detection Context Manager (Locked Decision D-09)

**What:** A context manager that hooks into SQLAlchemy's `after_cursor_execute` event to count queries and assert exact query counts.

**When to use:** Integration tests for repository methods and query handlers (Phases 7-8). Built now so infrastructure is ready.

**Example:**
```python
# tests/utils/query_counter.py
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

@contextmanager
def assert_query_count(session: AsyncSession, expected: int, *, label: str = ""):
    """Context manager that counts SQL queries and asserts the expected count."""
    sync_conn = session.sync_session.connection().connection
    count = 0

    def _after_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal count
        count += 1

    event.listen(sync_conn, "after_cursor_execute", _after_execute)
    try:
        yield
    finally:
        event.remove(sync_conn, "after_cursor_execute", _after_execute)
        msg = f"Expected {expected} queries, got {count}"
        if label:
            msg = f"[{label}] {msg}"
        assert count == expected, msg
```

**Important note:** In an async SQLAlchemy setup, the `after_cursor_execute` event fires on the underlying synchronous connection. The context manager needs to obtain the sync connection from the async session. The exact mechanism depends on whether the session is in a nested transaction context. Research indicates using `session.sync_session.bind` or `session.get_bind()` to access the engine, then listening on the connection level. The implementer should test both approaches against the project's nested-transaction test isolation pattern.

### Anti-Patterns to Avoid

- **Building custom entity constructors that bypass `create()` methods:** All entities validate in `create()`. Builders MUST call `create()`, not construct directly via `__init__()`. Direct construction skips slug validation, i18n validation, and UUID generation.
- **Sharing FakeRepository state across tests:** Each test must get fresh FakeUoW and FakeRepository instances. Use function-scoped fixtures, not module-scoped.
- **Hypothesis strategies that generate invalid domain states:** Strategies must respect domain invariants (e.g., Money amount >= 0, slugs matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`, i18n dicts with both "ru" and "en" keys). Invalid states should be tested via explicit unit tests, not via hypothesis.
- **Over-constraining hypothesis strategies:** Strategies should explore the valid input space broadly. Don't over-constrain (e.g., only generating "test-brand" slugs). Let hypothesis find edge cases in legitimate input ranges.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test execution randomization | Custom ordering plugin | pytest-randomly (already chosen) | Handles seed capture/replay, integrates with pytest ecosystem |
| Per-test timeouts | Manual timer wrappers | pytest-timeout (already chosen) | Handles async timeouts, integrates with hypothesis deadline |
| HTTP mock for httpx | Custom mock class | respx (already chosen) | Purpose-built for httpx, handles async, route matching |
| Flexible assertions | Custom `assert_approximately_equal` | dirty-equals (already chosen) | Handles IsUUID, IsNow, IsPartialDict, etc. out of the box |
| Property-based test generation | Manual random.choice loops | hypothesis (already chosen) | Shrinking, reproducibility, database integration, settings profiles |
| ORM model seeding | Manual dict -> model construction | polyfactory (existing) | Handles relationships, foreign keys, nullable fields automatically |

**Key insight:** All six libraries are purpose-built tools that handle edge cases (timezone-aware timestamps, async context, reproducible random seeds) that hand-rolled alternatives inevitably miss.

## Common Pitfalls

### Pitfall 1: i18n Validation Failures in Builders
**What goes wrong:** Builder `build()` fails because the i18n dict is missing required locales ("ru", "en").
**Why it happens:** The domain's `REQUIRED_LOCALES = frozenset({"ru", "en"})` is enforced in every `create()` method via `validate_i18n_completeness()`. Builders that only set `{"en": "..."}` will raise `MissingRequiredLocalesError`.
**How to avoid:** ALL builders must generate defaults with both `"ru"` and `"en"` keys. Use `{"en": "Test Brand", "ru": "Test Brand"}` as the default pattern.
**Warning signs:** `MissingRequiredLocalesError` in test output during builder instantiation.

### Pitfall 2: AggregateRoot `__attrs_post_init__` Not Called in Fakes
**What goes wrong:** FakeRepository stores entities that were constructed without calling `__attrs_post_init__`, so `_domain_events` list is missing.
**Why it happens:** If someone constructs an entity via attrs `__init__` directly instead of through `Entity.create()`, the `AggregateRoot.__attrs_post_init__` hook that initializes `_domain_events = []` might not fire.
**How to avoid:** Builders must ALWAYS use `Entity.create()` factory methods. Never bypass them.
**Warning signs:** `AttributeError: '_domain_events'` when calling `add_domain_event()`.

### Pitfall 3: FakeUoW Not Clearing Events After Commit
**What goes wrong:** Tests that check domain events see events from previous handler invocations.
**Why it happens:** The real UoW's `commit()` calls `aggregate.clear_domain_events()` after extracting events. If the fake skips this, events accumulate.
**How to avoid:** FakeUoW's `commit()` must iterate `_aggregates`, collect events, then call `clear_domain_events()` on each -- exactly matching the real UoW's `_collect_and_persist_outbox_events()` behavior.
**Warning signs:** Test assertions on event counts fail with double the expected events.

### Pitfall 4: Hypothesis and Async Tests
**What goes wrong:** `@given` decorator conflicts with pytest-asyncio's `async def test_*` pattern.
**Why it happens:** Hypothesis does not natively support async test functions. The `@given` decorator expects synchronous test functions.
**How to avoid:** Use `hypothesis.extra.asyncio` if available, or wrap async calls in `asyncio.get_event_loop().run_until_complete()` inside a sync test. For domain entity testing (which is pure synchronous logic), this is not an issue. Async hypothesis tests are only needed if testing async command handlers with FakeUoW -- in that case, use a sync wrapper.
**Warning signs:** `TypeError: object coroutine can't be used in 'await' expression` or hypothesis treating the async function as a single example.

### Pitfall 5: Product.create() Auto-Creates Default Variant
**What goes wrong:** ProductBuilder builds a product that already has one variant, and then test code adds another variant expecting to be the "first" one.
**Why it happens:** `Product.create()` automatically appends a default variant with `name_i18n=title_i18n`. This is domain logic, not a test artifact.
**How to avoid:** ProductBuilder must document that `build()` returns a product with exactly one default variant. Tests that need a bare product (no variants) cannot exist -- the domain invariant requires at least one variant.
**Warning signs:** `assert len(product.variants) == 1` unexpectedly passes when test expected 0.

### Pitfall 6: SQLAlchemy Event Listener on Wrong Connection Level
**What goes wrong:** Query counter reports 0 queries because the event listener was attached to the engine but queries went through a different connection.
**Why it happens:** The test suite uses nested transactions (`begin_nested()`) with savepoints. The `after_cursor_execute` event must be attached to the specific connection used by the test's session, not to the engine.
**How to avoid:** Get the sync connection from the async session (`session.sync_session.connection()`) and attach the event listener there. Test this against the nested-transaction pattern in `tests/conftest.py`.
**Warning signs:** Query count assertions always pass with `expected=0`.

### Pitfall 7: Hypothesis Shrinking With Complex Aggregates
**What goes wrong:** Hypothesis spends 10+ seconds shrinking a failing aggregate tree example, triggering test timeouts.
**Why it happens:** Full Product->Variant->SKU trees have many moving parts; the shrinker tries many combinations.
**How to avoid:** Set `@settings(max_examples=50, deadline=timedelta(seconds=5))` for complex aggregate strategies. Use `suppress_health_check=[HealthCheck.too_slow]` if needed. Keep leaf strategy search spaces bounded (e.g., max 3 variants, max 5 SKUs per variant).
**Warning signs:** Hypothesis health check warnings about slow data generation.

## Code Examples

### Entity Inventory (All Entities Needing Builders)

Based on `backend/src/modules/catalog/domain/entities.py` (2,220 lines):

| Entity | Type | create() Signature Key Params | Builder Complexity |
|--------|------|-------------------------------|-------------------|
| Brand | AggregateRoot | name, slug, logo_url?, logo_storage_object_id? | Simple |
| Category | AggregateRoot | name_i18n, slug, sort_order, parent? (create_root vs create_child) | Medium (tree) |
| AttributeTemplate | AggregateRoot | code, name_i18n, description_i18n?, sort_order | Simple |
| TemplateAttributeBinding | AggregateRoot | template_id, attribute_id, sort_order, requirement_level, filter_settings? | Simple |
| AttributeGroup | AggregateRoot | code, name_i18n, sort_order | Simple |
| Attribute | AggregateRoot | code, slug, name_i18n, data_type, ui_type, is_dictionary, group_id, level, behavior?, validation_rules? | Complex |
| AttributeValue | Child entity | attribute_id, code, slug, value_i18n, search_aliases?, meta_data?, value_group?, sort_order | Medium |
| ProductAttributeValue | Child entity | product_id, attribute_id, attribute_value_id | Simple |
| SKU | Child entity | product_id, variant_id, sku_code, variant_hash, price?, compare_at_price?, variant_attributes? | Medium |
| ProductVariant | Child entity | product_id, name_i18n, description_i18n?, sort_order, default_price?, default_currency | Medium |
| Product | AggregateRoot | slug, title_i18n, brand_id, primary_category_id, description_i18n?, supplier_id?, tags? | Complex (owns variants/SKUs) |
| MediaAsset | Simple entity | product_id, variant_id?, media_type, role, sort_order, storage_object_id?, url? | Simple |

### Repository Interface Inventory (All Interfaces FakeUoW Must Cover)

Based on `backend/src/modules/catalog/domain/interfaces.py`:

| Interface | Extra Methods Beyond CRUD | Notes |
|-----------|--------------------------|-------|
| IBrandRepository | check_slug_exists, get_for_update, check_slug_exists_excluding, has_products, check_name_exists, check_name_exists_excluding | 6 extra methods |
| ICategoryRepository | get_all_ordered, check_slug_exists(slug, parent_id), get_for_update, check_slug_exists_excluding, has_children, has_products, update_descendants_full_slug, propagate_effective_template_id | 8 extra methods |
| IAttributeGroupRepository | check_code_exists, get_by_code, has_attributes, move_attributes_to_group | 4 extra methods |
| IAttributeRepository | get_many, get_for_update, check_code_exists, check_slug_exists, has_product_attribute_values | 5 extra methods |
| IAttributeValueRepository | get_many, check_code_exists, check_slug_exists, has_product_references, list_ids_by_attribute, check_codes_exist, check_slugs_exist, bulk_update_sort_order | NOT ICatalogRepository -- separate ABC with 12 methods |
| IProductRepository | check_slug_exists, check_slug_exists_excluding, get_for_update_with_variants, get_with_variants, check_sku_code_exists | 5 extra methods |
| IProductAttributeValueRepository | list_by_product, get_by_product_and_attribute, check_assignment_exists, check_assignments_exist_bulk | Separate ABC, 7 methods total |
| IMediaAssetRepository | list_by_product, list_by_storage_ids, delete_by_product, bulk_update_sort_order, check_main_exists | Separate ABC, 10 methods total |
| IAttributeTemplateRepository | check_code_exists, has_category_references, get_category_ids_by_template_ids | 3 extra methods |
| ITemplateAttributeBindingRepository | check_binding_exists, list_ids_by_template, get_bindings_for_templates, bulk_update_sort_order, has_bindings_for_attribute, get_template_ids_for_attribute | 6 extra methods |

**Total:** 10 repository interfaces with ~60 unique methods to implement as fakes.

### Hypothesis Strategy Composition Example

```python
# tests/factories/strategies/entity_strategies.py
from hypothesis import strategies as st
from tests.factories.strategies.primitives import i18n_names, valid_slugs, money
from src.modules.catalog.domain.entities import Brand, Product, ProductVariant, SKU
from src.modules.catalog.domain.value_objects import ProductStatus
import uuid

def brands() -> st.SearchStrategy[Brand]:
    return st.builds(
        Brand.create,
        name=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        slug=valid_slugs(),
    )

def products(brand_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None) -> st.SearchStrategy[Product]:
    return st.builds(
        Product.create,
        slug=valid_slugs(),
        title_i18n=i18n_names(),
        brand_id=st.just(brand_id) if brand_id else st.uuids(),
        primary_category_id=st.just(category_id) if category_id else st.uuids(),
        description_i18n=st.just({}) | i18n_names(),
        tags=st.lists(st.text(min_size=1, max_size=30), max_size=5),
    )
```

### N+1 Query Counter Usage

```python
# How tests will use it in Phases 7-8:
async def test_list_brands_query_count(db_session):
    # Seed data
    ...
    with assert_query_count(db_session, expected=1, label="list_brands"):
        result = await brand_repo.list_all()
    assert len(result) == 5
```

### pytest Configuration Additions

```ini
# Add to pytest.ini or pyproject.toml [tool.pytest.ini_options]
timeout = 30  # Default timeout per test (seconds)
timeout_method = signal  # Use signal-based timeout (faster, Unix-only)
```

**Note:** On Windows, `timeout_method = thread` must be used instead of `signal`. Since the test environment appears to be Windows, use `timeout_method = thread`.

### Polyfactory ORM Factory Extensions

```python
# Additions to tests/factories/orm_factories.py
from src.modules.catalog.infrastructure.models import (
    Attribute as AttributeModel,
    AttributeGroup as AttributeGroupModel,
    AttributeTemplate as AttributeTemplateModel,
    AttributeValue as AttributeValueModel,
    Product as ProductModel,
    ProductVariant as ProductVariantModel,
    SKU as SKUModel,
    TemplateAttributeBinding as BindingModel,
    MediaAsset as MediaAssetModel,
)

class AttributeGroupModelFactory(SQLAlchemyFactory):
    __model__ = AttributeGroupModel
    __set_relationships__ = True

class AttributeModelFactory(SQLAlchemyFactory):
    __model__ = AttributeModel
    __set_relationships__ = True

# ... one per ORM model
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| hypothesis <= 6.x with `@example` | hypothesis 6.151+ with `@settings(database=...)` | Ongoing | Example database caches failing examples for regression |
| Manual mock-based UoW | In-memory fake UoW with real dict storage | Best practice for DDD testing | Catches real bugs in domain logic, not mock configuration errors |
| Random data with `faker` | Property-based testing with hypothesis | Mature pattern | Discovers edge cases human testers miss; shrinking pinpoints minimal failing examples |
| Custom assertion helpers | dirty-equals | 2023+ | Reduced boilerplate, better error messages |

**Deprecated/outdated:**
- `hypothesis.strategies.from_attrs()` was removed; use `st.builds(Entity.create, ...)` instead with explicit field strategies. This is the recommended pattern for attrs-based domain models.

## Open Questions

1. **Async hypothesis tests with FakeUoW**
   - What we know: Hypothesis `@given` does not natively wrap async test functions. Domain entity tests are sync and work fine.
   - What's unclear: The exact pattern for testing async command handlers with `@given` + FakeUoW. Options include `hypothesis[asyncio]` or sync wrappers around async handlers.
   - Recommendation: For Phase 1, build strategies for domain entities only (sync). Defer async hypothesis integration to Phase 4-6 when command handler tests actually need it. If needed, wrap async handler calls in `asyncio.run()` inside sync tests.

2. **Query counter and nested transactions**
   - What we know: The test suite uses nested transactions with savepoints for test isolation. SQLAlchemy's `after_cursor_execute` fires on the underlying sync connection.
   - What's unclear: Whether attaching the event listener before or after `begin_nested()` captures the right queries. The savepoint BEGIN/COMMIT statements may be counted.
   - Recommendation: Build the context manager, write a validation test that executes a known number of queries in the nested-transaction context, and adjust filtering (e.g., exclude `SAVEPOINT` and `RELEASE SAVEPOINT` statements).

3. **FakeRepository query methods complexity**
   - What we know: 10 interfaces with ~60 unique methods. Some methods like `propagate_effective_template_id` involve recursive CTE logic.
   - What's unclear: Whether all 60 methods need to be faked in Phase 1, or only the ones used by Phase 4-6 handlers.
   - Recommendation: Implement the full CRUD base (add/get/update/delete) for all repositories in Phase 1. Implement specific query methods (check_slug_exists, has_products, etc.) as `NotImplementedError` stubs, then fill them in as Phases 4-6 need them. This avoids over-engineering while ensuring the FakeUoW framework is in place.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.14.3 | -- |
| uv | Dependency management | Yes | 0.10.4 | -- |
| pytest | Test runner | Yes | 9.0.2 (via uv run) | -- |
| PostgreSQL | Integration tests (later phases) | Yes (Docker Compose) | -- | -- |
| hypothesis | INFRA-04 | No (to install) | 6.151.9 target | -- |
| respx | INFRA-01 | No (to install) | 0.22.0 target | -- |
| dirty-equals | INFRA-01 | No (to install) | 0.11 target | -- |
| pytest-randomly | INFRA-01 | No (to install) | 4.0.1 target | -- |
| pytest-timeout | INFRA-01 | No (to install) | 2.4.0 target | -- |
| schemathesis | INFRA-01 | No (to install) | 4.14.1 target | -- |

**Missing dependencies with no fallback:**
- All six new packages must be installed. `uv add --group dev` will handle this cleanly.

**Missing dependencies with fallback:**
- None -- all dependencies are available in PyPI and confirmed compatible via `uv pip install --dry-run`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `backend/pytest.ini` + `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run pytest tests/unit -x -q --no-cov --timeout=30` |
| Full suite command | `cd backend && uv run pytest --timeout=60` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | New deps import without errors | unit (smoke) | `cd backend && uv run python -c "import hypothesis; import schemathesis; import respx; import dirty_equals; import pytest_randomly; import pytest_timeout"` | N/A (import check) |
| INFRA-02 | Builders instantiate all catalog entities | unit | `cd backend && uv run pytest tests/unit/test_builders_smoke.py -x --no-cov` | No -- Wave 0 |
| INFRA-03 | FakeUoW tracks state and events | unit | `cd backend && uv run pytest tests/unit/test_fake_uow_smoke.py -x --no-cov` | No -- Wave 0 |
| INFRA-04 | Hypothesis strategies generate valid instances and shrink | unit | `cd backend && uv run pytest tests/unit/test_strategies_smoke.py -x --no-cov --timeout=30` | No -- Wave 0 |
| INFRA-05 | Query counter detects exact query counts | integration | `cd backend && uv run pytest tests/integration/test_query_counter_smoke.py -x --no-cov` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit -x -q --no-cov --timeout=30`
- **Per wave merge:** `cd backend && uv run pytest --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_builders_smoke.py` -- smoke tests that each builder produces a valid entity
- [ ] `tests/unit/test_fake_uow_smoke.py` -- smoke test that FakeUoW commit/rollback/event collection works
- [ ] `tests/unit/test_strategies_smoke.py` -- smoke test that each hypothesis strategy generates valid instances
- [ ] `tests/integration/test_query_counter_smoke.py` -- smoke test that query counter counts correctly in nested-transaction context

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python 3.14, FastAPI, SQLAlchemy 2.1 (async), PostgreSQL, Dishka DI
- **Architecture:** Must follow existing hexagonal/CQRS patterns
- **Testing:** Use existing test infrastructure (pytest, testcontainers, polyfactory)
- **EAV pattern:** The Entity-Attribute-Value architecture is a deliberate design choice -- do not refactor away from it
- **asyncio_mode:** `auto` -- all async test functions auto-detected
- **Ruff:** Linting and formatting with target `py314`, line-length 88
- **mypy:** `disallow_untyped_defs = false` for tests (relaxed mode)
- **Imports:** Use full paths from `src.` root; tests import from `tests.factories.*`
- **Naming:** Builders suffixed with `Builder`, ORM factories with `ModelFactory`, Mothers with `Mothers`
- **GSD Workflow:** Do not make direct repo edits outside a GSD workflow unless explicitly asked

## Sources

### Primary (HIGH confidence)
- `backend/src/modules/catalog/domain/entities.py` -- All 12 entity/aggregate classes, factory methods, validation logic
- `backend/src/modules/catalog/domain/interfaces.py` -- All 10 repository interfaces with ~60 methods
- `backend/src/modules/catalog/domain/value_objects.py` -- Money, BehaviorFlags, enums, SLUG_RE, REQUIRED_LOCALES
- `backend/src/shared/interfaces/uow.py` -- IUnitOfWork interface contract
- `backend/src/infrastructure/database/uow.py` -- Real UoW implementation (reference for FakeUoW behavior)
- `backend/src/shared/interfaces/entities.py` -- AggregateRoot mixin, DomainEvent base
- `backend/tests/factories/builders.py` -- Existing fluent builder pattern (RoleBuilder, SessionBuilder, CategoryBuilder)
- `backend/tests/factories/catalog_mothers.py` -- Existing object mother pattern
- `backend/tests/factories/orm_factories.py` -- Existing Polyfactory ORM factories
- `backend/tests/fakes/oidc_provider.py` -- Existing fake pattern reference
- `backend/tests/conftest.py` -- Test infrastructure, fixtures, nested-transaction pattern
- `backend/pytest.ini` -- Test configuration, markers, asyncio mode
- `backend/pyproject.toml` -- Dependency groups, ruff/mypy config

### Secondary (MEDIUM confidence)
- PyPI version query via `pip index versions` and `uv pip install --dry-run` (2026-03-28) -- confirmed latest versions
- SQLAlchemy `after_cursor_execute` event -- documented in SQLAlchemy core events API; verified pattern in training data

### Tertiary (LOW confidence)
- `hypothesis.extra.asyncio` availability -- needs verification at install time; may require `hypothesis[asyncio]` extra or may not exist in current version

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI, existing codebase patterns well-documented
- Architecture: HIGH -- all entity signatures, interface contracts, and existing patterns read from source code
- Pitfalls: HIGH -- all pitfalls derived from domain code analysis (i18n validation, auto-variant creation, AggregateRoot post-init)
- FakeUoW design: MEDIUM -- design follows IUnitOfWork interface exactly, but specific query method fake implementations may need iteration
- N+1 detection: MEDIUM -- SQLAlchemy event API is well-documented, but interaction with nested-transaction test isolation needs validation

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain -- no expected changes to entity signatures or test infrastructure)
