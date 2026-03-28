# Phase 4: Brand, Category & Attribute Command Handlers - Research

**Researched:** 2026-03-28
**Domain:** Python async command handler unit testing with FakeUoW
**Confidence:** HIGH

## Summary

Phase 4 tests the application layer command handlers for Brand, Category, and Attribute entities (including AttributeTemplate, AttributeGroup, and TemplateAttributeBinding). The testing infrastructure (FakeUoW, 10 fake repos, entity builders) was built in Phase 1 and is production-ready. The primary work is writing test files that exercise each handler's happy path, validation rejection paths, and UoW commit/no-commit assertions.

There are **19 distinct command handlers** in scope across three entity domains. Several handlers depend on cross-cutting services (ICacheService, IImageBackendClient, `invalidate_template_effective_cache` utility) that must be mocked with AsyncMock per D-04. Seven fake repository methods currently raise `NotImplementedError` and must be implemented before the corresponding handler tests can pass.

**Primary recommendation:** Implement the 7 missing fake repo methods first (Wave 0), then write 3 test files (one per entity domain) with one test class per handler, using FakeUoW as the sole test double for repositories and UoW.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** One test CLASS per handler (TestCreateBrand, TestUpdateBrand, etc.). Each handler is a separate use case with its own inputs, validations, and side effects -- they deserve isolated test classes.
- **D-02:** One test FILE per entity domain: `test_brand_handlers.py`, `test_category_handlers.py`, `test_attribute_handlers.py`. Classes are per-handler inside the file.
- **D-03:** FakeUoW (from Phase 1) for ALL handlers, no exceptions. No simple AsyncMock even for "trivial" CRUD handlers. FakeUoW validates real repository interactions (adds, commits, event collection). Consistency over convenience -- every handler test follows the same pattern.
- **D-04:** Per-test inline AsyncMock (Phase 1 D-11) only for cross-module dependencies (e.g., ILogger, external services), NOT for repositories or UoW.
- **D-05:** Use Phase 1 builders (BrandBuilder, CategoryBuilder, AttributeBuilder, etc.) for test data.
- **D-06:** Test both happy path AND rejection paths for every handler.
- **D-07:** Verify UoW.commit() called on success, NOT called on validation failure.
- **D-08:** Verify domain events collected by FakeUoW on relevant operations.

### Claude's Discretion
- Number of edge cases per handler
- Whether to test ILogger interactions (bind, info, warning calls)
- Exact error message assertions vs exception type assertions
- Test method naming style within each class

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CMD-01 | Unit tests for all Brand command handlers (create, update, delete, bulk_create) | 4 handlers identified, all source read, FakeUoW + BrandBuilder ready, IImageBackendClient needs AsyncMock for UpdateBrandHandler |
| CMD-02 | Unit tests for all Category command handlers (create, update, delete, reorder, assign_template) | 5 handlers identified (create, update, delete, bulk_create, reorder not present -- see note), ICacheService needs AsyncMock, 2 fake repo methods need implementation |
| CMD-03 | Unit tests for all Attribute command handlers (create_template, update_template, delete_template, create_group, manage_bindings) | 10 handlers identified across Attribute/Template/Binding domains, ICacheService needs AsyncMock, 5 fake repo methods need implementation |
</phase_requirements>

## Standard Stack

### Core (already installed -- test-only)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner | Project standard |
| pytest-asyncio | 1.3.0 | Async test support | `asyncio_mode = auto` in pytest.ini |
| pytest-timeout | (installed) | Per-test timeout safety | 30s default in pytest.ini |

### Supporting (already built in Phase 1)
| Component | Location | Purpose |
|-----------|----------|---------|
| FakeUnitOfWork | `tests/fakes/fake_uow.py` | In-memory UoW with event collection |
| FakeBrandRepository | `tests/fakes/fake_catalog_repos.py` | Dict-backed Brand repo |
| FakeCategoryRepository | `tests/fakes/fake_catalog_repos.py` | Dict-backed Category repo |
| FakeAttributeRepository | `tests/fakes/fake_catalog_repos.py` | Dict-backed Attribute repo |
| FakeAttributeTemplateRepository | `tests/fakes/fake_catalog_repos.py` | Dict-backed Template repo |
| FakeTemplateAttributeBindingRepository | `tests/fakes/fake_catalog_repos.py` | Dict-backed Binding repo |
| FakeAttributeGroupRepository | `tests/fakes/fake_catalog_repos.py` | Dict-backed Group repo |
| BrandBuilder | `tests/factories/brand_builder.py` | Fluent Brand entity builder |
| CategoryBuilder | `tests/factories/builders.py` | Fluent Category entity builder |
| AttributeBuilder | `tests/factories/attribute_builder.py` | Fluent Attribute entity builder |
| AttributeTemplateBuilder | `tests/factories/attribute_template_builder.py` | Fluent Template entity builder |
| TemplateAttributeBindingBuilder | `tests/factories/attribute_template_builder.py` | Fluent Binding entity builder |
| AttributeGroupBuilder | `tests/factories/attribute_group_builder.py` | Fluent Group entity builder |

### No Additional Dependencies
No new packages need to be installed. Everything is already in the project.

## Architecture Patterns

### Test File Structure (per D-01 + D-02)
```
backend/tests/unit/modules/catalog/application/commands/
    __init__.py
    test_brand_handlers.py          # CMD-01: TestCreateBrand, TestUpdateBrand, TestDeleteBrand, TestBulkCreateBrands
    test_category_handlers.py       # CMD-02: TestCreateCategory, TestUpdateCategory, TestDeleteCategory, TestBulkCreateCategories
    test_attribute_handlers.py      # CMD-03: TestCreateAttribute, TestUpdateAttribute, TestDeleteAttribute,
                                    #         TestCreateAttributeTemplate, TestUpdateAttributeTemplate,
                                    #         TestDeleteAttributeTemplate, TestCloneAttributeTemplate,
                                    #         TestBindAttributeToTemplate, TestUnbindAttributeFromTemplate,
                                    #         TestReorderTemplateBindings, TestUpdateTemplateAttributeBinding,
                                    #         TestBulkCreateAttributes
```

### Test Directory Note
The directory `backend/tests/unit/modules/catalog/application/commands/` does NOT exist yet. It must be created with an `__init__.py` file. The parent `backend/tests/unit/modules/catalog/application/` exists and has `__init__.py`.

### Handler Test Pattern (canonical)

Every handler test follows this exact structure:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.fakes.fake_uow import FakeUnitOfWork
from tests.factories.brand_builder import BrandBuilder
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    CreateBrandResult,
)
from src.modules.catalog.domain.events import BrandCreatedEvent
from src.modules.catalog.domain.exceptions import BrandSlugConflictError


def make_logger():
    """Create a MagicMock ILogger with bind() chain support."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


class TestCreateBrand:
    """Tests for CreateBrandHandler."""

    async def test_creates_brand_and_commits(self):
        uow = FakeUnitOfWork()
        logger = make_logger()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=logger,
        )
        command = CreateBrandCommand(name="Nike", slug="nike")

        result = await handler.handle(command)

        # Assert entity persisted
        assert result.brand_id in uow.brands.items
        brand = uow.brands.items[result.brand_id]
        assert brand.name == "Nike"
        assert brand.slug == "nike"

        # Assert UoW committed
        assert uow.committed is True

        # Assert domain event collected
        assert any(
            isinstance(e, BrandCreatedEvent) and e.brand_id == result.brand_id
            for e in uow.collected_events
        )

    async def test_rejects_duplicate_slug(self):
        uow = FakeUnitOfWork()
        existing = BrandBuilder().with_slug("nike").build()
        await uow.brands.add(existing)
        logger = make_logger()
        handler = CreateBrandHandler(
            brand_repo=uow.brands, uow=uow, logger=logger,
        )
        command = CreateBrandCommand(name="Nike Copy", slug="nike")

        with pytest.raises(BrandSlugConflictError):
            await handler.handle(command)

        # UoW must NOT be committed on validation failure
        assert uow.committed is False
```

### Cross-Module Dependency Mocking Pattern (per D-04)

Handlers that depend on ICacheService or IImageBackendClient get inline AsyncMock:

```python
def make_cache():
    """Create an AsyncMock ICacheService."""
    cache = AsyncMock()
    cache.delete = AsyncMock()
    cache.delete_many = AsyncMock()
    return cache


def make_image_backend():
    """Create an AsyncMock IImageBackendClient."""
    return AsyncMock()
```

### FakeUoW Wiring Pattern

FakeUoW auto-creates all 10 repos and wires cross-repo references. Access repos via `uow.brands`, `uow.categories`, etc. Pass the same repo instance to both handler constructor AND pre-seed it for test setup:

```python
uow = FakeUnitOfWork()
# Pre-seed state
existing_brand = BrandBuilder().with_slug("taken").build()
await uow.brands.add(existing_brand)

# Handler uses the SAME repo instance
handler = CreateBrandHandler(brand_repo=uow.brands, uow=uow, logger=make_logger())
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| In-memory repository state | Custom dict wrappers | `FakeUnitOfWork` + its `.brands`, `.categories`, etc. | Already wired with cross-repo references for has_products, has_children |
| Domain entity construction | Manual `Brand(id=..., name=..., ...)` | Builders (BrandBuilder, CategoryBuilder, etc.) | Builders call `Entity.create()` which generates uuid7, validates invariants |
| Async mock for ILogger | Custom logger stub | `MagicMock()` with `bind=MagicMock(return_value=logger)` | Logger is sync Protocol, only bind() needs chaining |
| Async mock for ICacheService | FakeCacheService class | Inline `AsyncMock()` | Cache calls are fire-and-forget best-effort in handlers (wrapped in try/except); don't need stateful behavior |

## Handler Inventory

### CMD-01: Brand Handlers (4 handlers)

| Handler | File | Dependencies | Key Validations |
|---------|------|-------------|-----------------|
| CreateBrandHandler | `create_brand.py` | IBrandRepository, IUnitOfWork, ILogger | Slug uniqueness |
| UpdateBrandHandler | `update_brand.py` | IBrandRepository, IUnitOfWork, **IImageBackendClient**, ILogger | Not-found, slug uniqueness excluding self, old logo cleanup |
| DeleteBrandHandler | `delete_brand.py` | IBrandRepository, IUnitOfWork, ILogger | Not-found, has-products guard |
| BulkCreateBrandsHandler | `bulk_create_brands.py` | IBrandRepository, IUnitOfWork, ILogger | Batch limit (100), intra-batch duplicate slugs/names, per-item slug/name uniqueness, skip_existing mode |

### CMD-02: Category Handlers (4 handlers)

| Handler | File | Dependencies | Key Validations |
|---------|------|-------------|-----------------|
| CreateCategoryHandler | `create_category.py` | ICategoryRepository, IAttributeTemplateRepository, IUnitOfWork, **ICacheService**, ILogger | Template-not-found, slug uniqueness at parent level, parent-not-found, root vs child branching |
| UpdateCategoryHandler | `update_category.py` | ICategoryRepository, IAttributeTemplateRepository, IUnitOfWork, **ICacheService**, ILogger | Template-not-found, not-found, slug uniqueness excluding self, full_slug cascade, effective_template_id propagation, storefront cache invalidation |
| DeleteCategoryHandler | `delete_category.py` | ICategoryRepository, IUnitOfWork, **ICacheService**, ILogger | Not-found, has-children guard, has-products guard |
| BulkCreateCategoriesHandler | `bulk_create_categories.py` | ICategoryRepository, IAttributeTemplateRepository, IUnitOfWork, **ICacheService**, ILogger | Batch limit (200), duplicate refs, parent_id/parent_ref mutual exclusion, intra-batch parent_ref resolution, skip_existing |

**NOTE on CMD-02 scope:** The REQUIREMENTS.md mentions "reorder" and "assign_template" for categories. There is NO dedicated `reorder_categories.py` handler in the codebase. Category reorder is handled via `UpdateCategoryCommand.sort_order`. Template assignment is done via `UpdateCategoryCommand.template_id`. The 4 handlers above cover all category command operations.

### CMD-03: Attribute Handlers (11 handlers)

| Handler | File | Dependencies | Key Validations |
|---------|------|-------------|-----------------|
| CreateAttributeHandler | `create_attribute.py` | IAttributeRepository, IAttributeGroupRepository, IUnitOfWork, ILogger | i18n completeness, group-not-found, code uniqueness, slug uniqueness |
| UpdateAttributeHandler | `update_attribute.py` | IAttributeRepository, IAttributeGroupRepository, ITemplateAttributeBindingRepository, IAttributeTemplateRepository, **ICacheService**, IUnitOfWork, ILogger | Not-found, group-not-found, _provided_fields safe-field intersection, cache key collection |
| DeleteAttributeHandler | `delete_attribute.py` | IAttributeRepository, ITemplateAttributeBindingRepository, IAttributeTemplateRepository, **ICacheService**, IUnitOfWork, ILogger | Not-found, has-template-bindings guard, has-product-values guard, cache key collection |
| BulkCreateAttributesHandler | `bulk_create_attributes.py` | IAttributeRepository, IAttributeGroupRepository, IUnitOfWork, ILogger | Batch limit (100), duplicate codes/slugs in batch, i18n validation, group validation, skip_existing |
| CreateAttributeTemplateHandler | `create_attribute_template.py` | IAttributeTemplateRepository, IUnitOfWork, ILogger | i18n completeness, code uniqueness |
| UpdateAttributeTemplateHandler | `update_attribute_template.py` | IAttributeTemplateRepository, IUnitOfWork, ILogger | Not-found, _provided_fields safe-field intersection |
| DeleteAttributeTemplateHandler | `delete_attribute_template.py` | IAttributeTemplateRepository, IUnitOfWork, ILogger | Not-found, has-category-references guard |
| CloneAttributeTemplateHandler | `clone_attribute_template.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, ILogger | i18n completeness, source-not-found, new-code uniqueness, binding duplication |
| BindAttributeToTemplateHandler | `bind_attribute_to_template.py` | IAttributeTemplateRepository, IAttributeRepository, ITemplateAttributeBindingRepository, IUnitOfWork, **ICacheService**, ILogger | Template-not-found, attribute-not-found, duplicate binding, cache invalidation |
| UnbindAttributeFromTemplateHandler | `unbind_attribute_from_template.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, **ICacheService**, ILogger | Binding not-found OR ownership mismatch, cache invalidation |
| UpdateTemplateAttributeBindingHandler | `update_template_attribute_binding.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, **ICacheService**, ILogger | Binding not-found OR ownership mismatch, _provided_fields safe-field intersection |
| ReorderTemplateBindingsHandler | `reorder_template_bindings.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, **ICacheService**, ILogger | Duplicate binding IDs, template-not-found, binding ownership validation, bulk sort update |

**Total: 19 handlers (4 Brand + 4 Category + 11 Attribute/Template/Binding)**

## Fake Repository Methods Needing Implementation

Seven methods currently raise `NotImplementedError` and are called by Phase 4 handlers. These MUST be implemented before the corresponding handler tests can run.

| Repo Class | Method | Called By | Implementation Complexity |
|------------|--------|-----------|--------------------------|
| FakeCategoryRepository | `update_descendants_full_slug(old_prefix, new_prefix)` | UpdateCategoryHandler | LOW -- iterate `_store`, replace prefix in `full_slug` for matching categories |
| FakeCategoryRepository | `propagate_effective_template_id(category_id, effective_template_id)` | UpdateCategoryHandler | MEDIUM -- BFS/DFS over `_store` finding descendants, update `effective_template_id` on inheriting ones |
| FakeAttributeTemplateRepository | `get_category_ids_by_template_ids(template_ids)` | BindAttributeToTemplate, UnbindAttribute, ReorderBindings, UpdateBinding handlers (via cache invalidation) | MEDIUM -- needs cross-repo reference to category store (like brands._product_store pattern) |
| FakeTemplateAttributeBindingRepository | `get_bindings_for_templates(template_ids)` | CloneAttributeTemplateHandler | LOW -- filter `_store` by template_id, group into dict |
| FakeTemplateAttributeBindingRepository | `bulk_update_sort_order(updates)` | ReorderTemplateBindingsHandler | LOW -- iterate updates, set sort_order on matching bindings |
| FakeTemplateAttributeBindingRepository | `get_template_ids_for_attribute(attribute_id)` | UpdateAttribute, DeleteAttribute handlers (via `collect_attribute_cache_keys`) | LOW -- filter `_store` by attribute_id, return unique template_ids |

**Cross-repo wiring needed:** `FakeAttributeTemplateRepository.get_category_ids_by_template_ids` needs a `_category_store` reference wired in `FakeUnitOfWork.__init__()`, similar to how `brands._product_store` is wired.

**Also note:** `FakeAttributeTemplateRepository.has_category_references()` currently returns `False` always. For DeleteAttributeTemplateHandler tests that verify the guard, this needs real scanning logic (check if any category in category_store has `template_id == template_id` or `effective_template_id == template_id`). This requires a `_category_store` cross-ref which is the same one needed for `get_category_ids_by_template_ids`.

## Common Pitfalls

### Pitfall 1: FakeUoW Context Manager Resets Aggregates
**What goes wrong:** Asserting `uow.committed` inside an `async with uow:` block or checking events before commit.
**Why it happens:** FakeUoW's `__aexit__` clears `_aggregates` list (matching real UoW behavior). The handler calls commit() inside the context manager, so events are already collected. But after the context manager exits on exception, aggregates are cleared.
**How to avoid:** Always assert `uow.committed` and `uow.collected_events` AFTER the handler call returns (outside the handler's context manager scope). For rejection tests, the handler raises inside `async with self._uow:` which triggers rollback; assert `uow.committed is False`.
**Warning signs:** `uow.collected_events` is empty even though handler calls `register_aggregate + commit`.

### Pitfall 2: Cache Calls After UoW Commit (try/except)
**What goes wrong:** Tests asserting cache.delete() was called fail because the handler wraps cache calls in try/except and swallows exceptions.
**Why it happens:** All Category and template-binding handlers call cache invalidation AFTER the `async with self._uow:` block, in a `try/except Exception` that logs a warning but does not re-raise.
**How to avoid:** Use `AsyncMock()` for cache (it never raises). Optionally assert `cache.delete.assert_awaited_once()` or `cache.delete_many.assert_awaited()` to verify cache invalidation happens. BUT: do not test cache failure paths unless explicitly desired -- these are best-effort operations.
**Warning signs:** Test passes even when cache mock is not configured.

### Pitfall 3: _provided_fields on Update Commands
**What goes wrong:** Update handler does nothing because `_provided_fields` is empty.
**Why it happens:** UpdateBrandCommand, UpdateCategoryCommand, UpdateAttributeCommand, UpdateAttributeTemplateCommand, and UpdateTemplateAttributeBindingCommand all have `_provided_fields: frozenset[str]` defaulting to `frozenset()`. The handler intersects this with safe fields to determine what to update. If test creates command without setting `_provided_fields`, no fields are updated.
**How to avoid:** Always construct update commands with explicit `_provided_fields`:
```python
command = UpdateBrandCommand(
    brand_id=brand.id,
    name="New Name",
    slug="new-slug",
    _provided_fields=frozenset({"name", "slug"}),
)
```
**Warning signs:** Handler "succeeds" but entity fields are unchanged.

### Pitfall 4: Ellipsis Sentinel in UpdateCategoryCommand.template_id
**What goes wrong:** Tests for template_id clearing/inheriting don't trigger the right code path.
**Why it happens:** `UpdateCategoryCommand.template_id` defaults to `...` (Ellipsis), not `None`. The handler checks `command.template_id is not ...` to determine if template_id was explicitly provided. Setting `template_id=None` means "clear the template"; leaving it as `...` means "keep current".
**How to avoid:** Explicitly set `template_id=None` when testing template clearing. Use default (`...`) when template_id should not change.
**Warning signs:** Template propagation logic is never triggered.

### Pitfall 5: UpdateBrandHandler Depends on IImageBackendClient
**What goes wrong:** Test instantiation of UpdateBrandHandler fails because constructor requires `image_backend` parameter.
**Why it happens:** UpdateBrandHandler has 4 constructor params: `brand_repo`, `uow`, `image_backend`, `logger`. This is the only Brand handler with a cross-module dependency. The image_backend.delete() is called AFTER uow commit for logo cleanup -- it is best-effort.
**How to avoid:** Always pass `image_backend=AsyncMock()` when constructing UpdateBrandHandler.
**Warning signs:** TypeError on handler construction.

### Pitfall 6: invalidate_template_effective_cache is a Module-Level Function
**What goes wrong:** Attempting to mock `invalidate_template_effective_cache` as an instance method.
**Why it happens:** Several handlers (unbind, reorder, update_binding) call `invalidate_template_effective_cache(self._cache, self._template_repo, template_id)` as a standalone async function from `src.modules.catalog.application.queries.resolve_template_attributes`. This function calls `template_repo.get_category_ids_by_template_ids()` which raises NotImplementedError in the fake.
**How to avoid:** Implement `FakeAttributeTemplateRepository.get_category_ids_by_template_ids()` rather than trying to mock the utility function. The function takes a cache and template_repo -- if the fake repo works, the function works.
**Warning signs:** NotImplementedError at test runtime from fake repo.

### Pitfall 7: BulkCreateBrandsHandler Checks Name Uniqueness
**What goes wrong:** Tests for bulk brand creation miss the name uniqueness check.
**Why it happens:** `BulkCreateBrandsHandler` checks BOTH `check_slug_exists` AND `check_name_exists` for each item. `FakeBrandRepository.check_name_exists()` is already implemented.
**How to avoid:** Test both slug conflict and name conflict rejection paths for bulk brands.
**Warning signs:** Missing test coverage for BrandNameConflictError.

## Code Examples

### Handler Construction with FakeUoW + Cross-Module Mocks

```python
# Category handler with ICacheService
uow = FakeUnitOfWork()
cache = AsyncMock()
logger = make_logger()
handler = CreateCategoryHandler(
    category_repo=uow.categories,
    template_repo=uow.attribute_templates,
    uow=uow,
    cache=cache,
    logger=logger,
)

# Attribute handler with many repos
handler = UpdateAttributeHandler(
    attribute_repo=uow.attributes,
    group_repo=uow.attribute_groups,
    binding_repo=uow.template_bindings,
    template_repo=uow.attribute_templates,
    cache=AsyncMock(),
    uow=uow,
    logger=make_logger(),
)
```

### Testing Domain Event Collection

```python
async def test_emits_brand_created_event(self):
    uow = FakeUnitOfWork()
    handler = CreateBrandHandler(
        brand_repo=uow.brands, uow=uow, logger=make_logger(),
    )
    result = await handler.handle(
        CreateBrandCommand(name="Nike", slug="nike")
    )

    events = [e for e in uow.collected_events if isinstance(e, BrandCreatedEvent)]
    assert len(events) == 1
    assert events[0].brand_id == result.brand_id
    assert events[0].slug == "nike"
```

### Testing Rejection Path (Not-Found)

```python
async def test_rejects_nonexistent_brand(self):
    uow = FakeUnitOfWork()
    handler = DeleteBrandHandler(
        brand_repo=uow.brands, uow=uow, logger=make_logger(),
    )
    command = DeleteBrandCommand(brand_id=uuid.uuid4())

    with pytest.raises(BrandNotFoundError):
        await handler.handle(command)

    assert uow.committed is False
```

### Testing Update with _provided_fields

```python
async def test_partial_update_only_changes_provided_fields(self):
    uow = FakeUnitOfWork()
    brand = BrandBuilder().with_name("Old").with_slug("old").build()
    await uow.brands.add(brand)
    handler = UpdateBrandHandler(
        brand_repo=uow.brands,
        uow=uow,
        image_backend=AsyncMock(),
        logger=make_logger(),
    )
    command = UpdateBrandCommand(
        brand_id=brand.id,
        name="New",
        _provided_fields=frozenset({"name"}),
    )

    result = await handler.handle(command)

    assert result.name == "New"
    assert result.slug == "old"  # Unchanged -- not in _provided_fields
```

### Implementing Missing Fake Repo Method (example)

```python
# In FakeTemplateAttributeBindingRepository:
async def get_bindings_for_templates(
    self, template_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[DomainTemplateAttributeBinding]]:
    result: dict[uuid.UUID, list[DomainTemplateAttributeBinding]] = {}
    tid_set = set(template_ids)
    for binding in self._store.values():
        if binding.template_id in tid_set:
            result.setdefault(binding.template_id, []).append(binding)
    return result
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x -q --no-cov` |
| Full suite command | `cd backend && uv run pytest tests/unit/ -x -q --no-cov` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CMD-01 | Brand create/update/delete/bulk_create handlers | unit | `uv run pytest tests/unit/modules/catalog/application/commands/test_brand_handlers.py -x --no-cov` | Wave 0 |
| CMD-02 | Category create/update/delete/bulk_create handlers | unit | `uv run pytest tests/unit/modules/catalog/application/commands/test_category_handlers.py -x --no-cov` | Wave 0 |
| CMD-03 | Attribute/Template/Binding create/update/delete/clone/bind/unbind/reorder/bulk handlers | unit | `uv run pytest tests/unit/modules/catalog/application/commands/test_attribute_handlers.py -x --no-cov` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x -q --no-cov`
- **Per wave merge:** `cd backend && uv run pytest tests/unit/ -x -q --no-cov`
- **Phase gate:** Full unit suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/unit/modules/catalog/application/commands/__init__.py` -- directory + marker
- [ ] 7 fake repo methods need implementation in `backend/tests/fakes/fake_catalog_repos.py`
- [ ] 1 cross-repo wiring needed in `backend/tests/fakes/fake_uow.py` (attribute_templates._category_store)
- [ ] `has_category_references()` in FakeAttributeTemplateRepository needs real scanning logic (not just `return False`)

## Open Questions

1. **CategoryBuilder lacks `with_template_id` method**
   - What we know: `CategoryBuilder` in `tests/factories/builders.py` does not support `template_id` parameter. Category handlers accept `template_id` in create commands.
   - What's unclear: Whether to extend CategoryBuilder or use `Category.create_root(template_id=...)` directly in tests.
   - Recommendation: Extend CategoryBuilder with `.with_template_id(tid)` if multiple tests need it, otherwise construct Category directly for template-related tests. Claude's discretion per D-05.

2. **BulkCreateCategories: parent_ref intra-batch resolution**
   - What we know: The handler resolves `parent_ref` within the batch, creating trees in a single call. FakeCategoryRepository.add() stores categories, and subsequent items can reference them.
   - What's unclear: Whether the fake repo's `check_slug_exists(slug, parent_id)` correctly handles categories added within the same batch (same transaction).
   - Recommendation: It should work because FakeCategoryRepo stores to `_store` on `add()`, and `check_slug_exists` scans `_store`. But this needs verification during implementation.

3. **UpdateCategoryHandler: effective_template_id propagation complexity**
   - What we know: When template_id changes on a category, the handler calls `propagate_effective_template_id()` which must walk the descendant tree and update `effective_template_id` on categories that inherit (don't have their own `template_id`).
   - What's unclear: The exact inheritance logic for effective_template_id in the fake.
   - Recommendation: Implement a simplified version: find all descendants via parent_id chain, update `effective_template_id` on those with `template_id is None`, return their IDs. Test with a small 2-3 level tree.

## Sources

### Primary (HIGH confidence)
- Direct source code reading of all 19 command handler files in `backend/src/modules/catalog/application/commands/`
- Direct source code reading of `backend/tests/fakes/fake_uow.py` and `backend/tests/fakes/fake_catalog_repos.py`
- Direct source code reading of all 7 builder files in `backend/tests/factories/`
- Direct source code reading of `backend/src/modules/catalog/domain/exceptions.py` (all exception classes)
- Direct source code reading of `backend/src/modules/catalog/domain/interfaces.py` (all repository interfaces)
- Direct source code reading of `backend/src/shared/interfaces/cache.py` (ICacheService protocol)
- Direct reading of `backend/pytest.ini` (test configuration)
- Existing test pattern in `backend/tests/unit/modules/user/application/commands/test_commands.py`

### Secondary (MEDIUM confidence)
- Cross-referencing NotImplementedError stubs against handler call sites

### Tertiary (LOW confidence)
- None -- all findings are from direct source reading.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tooling already installed and configured
- Architecture: HIGH -- test patterns established by existing tests, FakeUoW + builders proven in Phase 1-3
- Handler inventory: HIGH -- every handler file read in full, all dependencies and validations catalogued
- Fake repo gaps: HIGH -- every NotImplementedError cross-referenced against handler call sites
- Pitfalls: HIGH -- identified from actual source code patterns, not speculation

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- no expected changes to handler source during this milestone)
