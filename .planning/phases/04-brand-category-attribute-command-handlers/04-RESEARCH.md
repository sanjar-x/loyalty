# Phase 4: Brand, Category & Attribute Command Handlers - Research

**Researched:** 2026-03-28
**Domain:** Python async command handler unit testing with FakeUoW
**Confidence:** HIGH

## Summary

Phase 4 tests the application layer command handlers for Brand, Category, and Attribute entities. The testing infrastructure (FakeUoW, 10 fake repos, entity builders) was built in Phase 1 and is ready. The primary work is writing test files that exercise each handler's happy path, validation rejection paths, and UoW commit/no-commit assertions.

There are **19 distinct command handlers** in scope across three entity domains. Several handlers depend on cross-cutting concerns (ICacheService, IImageBackendClient, `invalidate_template_effective_cache` utility) that must be mocked with AsyncMock per D-04. Four fake repository methods currently raise `NotImplementedError` with "Phase 4 needs it" markers and must be implemented before tests can pass. Three additional methods marked "Phase 5" are also called by handlers in scope and need implementation.

**Primary recommendation:** Implement the 7 missing fake repo methods first, then write 3 test files (one per entity domain) with one test class per handler, using FakeUoW as the sole test double for repositories and UoW.

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
| CMD-01 | Unit tests for all Brand command handlers (create, update, delete, bulk_create) | 4 handlers identified with full source code; FakeUoW + FakeBrandRepository ready; BrandBuilder available |
| CMD-02 | Unit tests for all Category command handlers (create, update, delete, reorder, assign_template) | 5 handlers identified (create, update, delete, bulk_create; "reorder" and "assign_template" are within update_category); FakeUoW + FakeCategoryRepository ready but needs 2 method implementations; CategoryBuilder available |
| CMD-03 | Unit tests for all Attribute command handlers (create_template, update_template, delete_template, create_group, manage_bindings) | 10 handlers identified covering templates, attributes, and bindings; FakeUoW + 4 fake repos ready but need 5 method implementations; AttributeTemplateBuilder + AttributeBuilder + TemplateAttributeBindingBuilder + AttributeGroupBuilder available |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner | Already installed, configured in `backend/pytest.ini` |
| pytest-asyncio | >=1.3.0 | Async test support | `asyncio_mode = auto` configured -- all async tests auto-detected |
| pytest-timeout | (installed) | Test timeout | 30s default timeout per test |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock (MagicMock/AsyncMock) | stdlib | Mock cross-module deps | Only for ILogger, ICacheService, IImageBackendClient per D-04 |

### Not Used in This Phase
| Library | Reason |
|---------|--------|
| polyfactory | Entity builders already exist; no ORM factory needed |
| hypothesis | Property-based testing not needed for handler orchestration tests |
| testcontainers | Unit tests only; no real DB |

**No installation needed.** All dependencies are already in the project.

## Architecture Patterns

### Test File Structure (per D-01, D-02)
```
backend/tests/unit/modules/catalog/application/commands/
    __init__.py                          # exists
    test_brand_handlers.py               # NEW - CMD-01
    test_category_handlers.py            # NEW - CMD-02
    test_attribute_handlers.py           # NEW - CMD-03
```

### Handler-to-Test-Class Mapping

**test_brand_handlers.py (4 handlers)**
| Handler | Test Class | Key Tests |
|---------|------------|-----------|
| CreateBrandHandler | TestCreateBrand | happy path, slug conflict |
| UpdateBrandHandler | TestUpdateBrand | happy path, not found, slug conflict, logo cleanup |
| DeleteBrandHandler | TestDeleteBrand | happy path, not found, has products |
| BulkCreateBrandsHandler | TestBulkCreateBrands | happy path, skip existing, slug conflict strict, name conflict strict, batch limit, duplicate slugs, duplicate names |

**test_category_handlers.py (5 handlers)**
| Handler | Test Class | Key Tests |
|---------|------------|-----------|
| CreateCategoryHandler | TestCreateCategory | root happy path, child happy path, slug conflict, parent not found, template_id not found |
| UpdateCategoryHandler | TestUpdateCategory | happy path, not found, slug conflict, template change propagation, slug change descendant cascade |
| DeleteCategoryHandler | TestDeleteCategory | happy path, not found, has children, has products |
| BulkCreateCategoriesHandler | TestBulkCreateCategories | happy path flat, parent_ref tree, skip existing, batch limit, duplicate refs |

**test_attribute_handlers.py (10 handlers)**
| Handler | Test Class | Key Tests |
|---------|------------|-----------|
| CreateAttributeTemplateHandler | TestCreateAttributeTemplate | happy path, code conflict |
| UpdateAttributeTemplateHandler | TestUpdateAttributeTemplate | happy path, not found |
| DeleteAttributeTemplateHandler | TestDeleteAttributeTemplate | happy path, not found, has category references |
| CloneAttributeTemplateHandler | TestCloneAttributeTemplate | happy path (bindings copied), source not found, code conflict |
| CreateAttributeHandler | TestCreateAttribute | happy path, code conflict, slug conflict, group not found |
| UpdateAttributeHandler | TestUpdateAttribute | happy path, not found, group not found |
| DeleteAttributeHandler | TestDeleteAttribute | happy path, not found, has template bindings, has product values |
| BindAttributeToTemplateHandler | TestBindAttributeToTemplate | happy path, template not found, attribute not found, already bound |
| UnbindAttributeFromTemplateHandler | TestUnbindAttributeFromTemplate | happy path, binding not found, wrong template ownership |
| UpdateTemplateAttributeBindingHandler | TestUpdateTemplateAttributeBinding | happy path, not found, wrong template ownership |

### Pattern: Handler Test Setup (canonical pattern for ALL tests)

```python
"""Unit tests for Brand command handlers."""

import uuid
from unittest.mock import MagicMock

import pytest

from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
)
from src.modules.catalog.domain.events import BrandCreatedEvent
from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from tests.factories.brand_builder import BrandBuilder
from tests.fakes.fake_uow import FakeUnitOfWork


def make_logger():
    """Create a MagicMock logger satisfying ILogger protocol."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def make_cache():
    """Create an AsyncMock cache satisfying ICacheService protocol."""
    from unittest.mock import AsyncMock
    return AsyncMock()


class TestCreateBrand:
    async def test_creates_brand_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )
        command = CreateBrandCommand(name="Nike", slug="nike")

        result = await handler.handle(command)

        assert result.brand_id in uow.brands.items
        assert uow.committed is True

    async def test_rejects_duplicate_slug(self):
        uow = FakeUnitOfWork()
        # Pre-seed a brand with the same slug
        existing = BrandBuilder().with_slug("nike").build()
        await uow.brands.add(existing)

        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )
        command = CreateBrandCommand(name="Nike 2", slug="nike")

        with pytest.raises(BrandSlugConflictError):
            await handler.handle(command)

        assert uow.committed is False

    async def test_emits_brand_created_event(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )
        command = CreateBrandCommand(name="Nike", slug="nike")

        await handler.handle(command)

        assert len(uow.collected_events) == 1
        assert isinstance(uow.collected_events[0], BrandCreatedEvent)
```

### Pattern: Handler with External Dependencies (UpdateBrand with IImageBackendClient)

```python
class TestUpdateBrand:
    async def test_updates_brand_and_commits(self):
        uow = FakeUnitOfWork()
        brand = BrandBuilder().with_name("Old Name").with_slug("old-slug").build()
        await uow.brands.add(brand)

        handler = UpdateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            image_backend=AsyncMock(),  # D-04: AsyncMock for cross-module dep
            logger=make_logger(),
        )
        command = UpdateBrandCommand(
            brand_id=brand.id,
            name="New Name",
            _provided_fields=frozenset({"name"}),
        )

        result = await handler.handle(command)

        assert result.name == "New Name"
        assert uow.committed is True
```

### Pattern: Validation Failure Prevents Commit (D-07)

```python
    async def test_not_found_does_not_commit(self):
        uow = FakeUnitOfWork()
        handler = DeleteBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )
        command = DeleteBrandCommand(brand_id=uuid.uuid4())

        with pytest.raises(BrandNotFoundError):
            await handler.handle(command)

        assert uow.committed is False
```

### Anti-Patterns to Avoid
- **AsyncMock for repos/UoW:** D-03 explicitly forbids this. Use FakeUoW.brands / FakeUoW.categories / etc.
- **Constructing entities manually:** Use builders (BrandBuilder, CategoryBuilder, etc.) from Phase 1.
- **Testing domain logic in handler tests:** Handler tests verify orchestration (repo calls, commit, events). Domain logic correctness was verified in Phase 2-3.
- **Testing cache invalidation side effects:** Cache is an AsyncMock -- don't assert cache.delete was called with specific keys. The handler's purpose is orchestration, not cache key correctness.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Repository test doubles | Custom mock classes | FakeUoW (Phase 1) | Already has all 10 repos with cross-repo wiring |
| Entity construction | Manual field setting | Builders (BrandBuilder, etc.) | Builders call .create() factory, ensuring valid entities |
| Logger mock | Complex protocol mock | `make_logger()` MagicMock | ILogger is sync protocol; MagicMock suffices |
| Cache service mock | Real Redis | AsyncMock() | Cache calls are fire-and-forget; handler catches exceptions |
| IImageBackendClient mock | HTTP client mock | AsyncMock() | Only UpdateBrand uses it; best-effort delete after commit |

## Fake Repository Methods Requiring Implementation

**CRITICAL: These `NotImplementedError` methods MUST be implemented in `fake_catalog_repos.py` before tests can pass.**

### Phase 4 Tagged (already identified for this phase)
| Repo | Method | Called By | Implementation |
|------|--------|-----------|---------------|
| FakeCategoryRepository | `update_descendants_full_slug(old_prefix, new_prefix)` | UpdateCategoryHandler | Scan `_store`, replace `full_slug` prefix for matching categories |
| FakeCategoryRepository | `propagate_effective_template_id(category_id, effective_template_id)` | UpdateCategoryHandler | Recursive scan of `_store` for children with `template_id IS NULL` |
| FakeAttributeGroupRepository | `move_attributes_to_group(source_group_id, target_group_id)` | Not directly in scope handlers -- but tagged Phase 4; implement if needed |
| FakeAttributeTemplateRepository | `get_category_ids_by_template_ids(template_ids)` | BindAttributeToTemplateHandler, unbind (via invalidate_template_effective_cache) |

### Phase 5 Tagged (but called by handlers in scope)
| Repo | Method | Called By | Implementation |
|------|--------|-----------|---------------|
| FakeTemplateAttributeBindingRepository | `get_bindings_for_templates(template_ids)` | CloneAttributeTemplateHandler | Group `_store` values by `template_id` |
| FakeTemplateAttributeBindingRepository | `bulk_update_sort_order(updates)` | ReorderTemplateBindingsHandler | Update `sort_order` on matching bindings in `_store` |
| FakeTemplateAttributeBindingRepository | `get_template_ids_for_attribute(attribute_id)` | UpdateAttributeHandler, DeleteAttributeHandler (via `collect_attribute_cache_keys`) |

**Note:** ReorderTemplateBindingsHandler is not explicitly in CMD-03 scope ("reorder" in CMD-02 refers to category reorder, which is actually handled by `update_category`). However, `reorder_template_bindings` and `update_template_attribute_binding` are part of "manage_bindings" in CMD-03.

## Common Pitfalls

### Pitfall 1: FakeUoW `committed` Resets on __aenter__
**What goes wrong:** If you create a FakeUoW, call a handler (which enters `async with self._uow`), and then try to assert `uow.committed`, it could be reset if you accidentally enter the context again.
**Why it happens:** `FakeUoW.__aenter__()` resets `_committed = False`.
**How to avoid:** Create one FakeUoW per test. Never reuse between handler invocations.
**Warning signs:** `uow.committed is False` even after a successful handler call.

### Pitfall 2: Exceptions Raised Inside `async with self._uow` Prevent Commit
**What goes wrong:** Domain exceptions (NotFoundError, ConflictError) are raised inside the `async with self._uow:` block. The `__aexit__` detects `exc_type` and calls rollback, clearing aggregates.
**Why it happens:** This is correct behavior -- FakeUoW mirrors real UoW: exception -> rollback -> no commit.
**How to avoid:** Assert `uow.committed is False` for rejection paths. This is the D-07 pattern.
**Warning signs:** None -- this is expected.

### Pitfall 3: `_provided_fields` Must Be Set for Update Commands
**What goes wrong:** Update handlers (UpdateBrand, UpdateCategory, UpdateAttributeTemplate) use `command._provided_fields` to determine which fields were explicitly sent by the client. If you forget to set `_provided_fields`, the handler passes an empty dict to `entity.update()`, causing no changes.
**Why it happens:** The `_provided_fields` frozenset is intersected with `_SAFE_FIELDS` to determine what to update. Empty intersection = no update.
**How to avoid:** Always include `_provided_fields=frozenset({"name", "slug"})` (or whichever fields you're updating) in test UpdateCommand instances.
**Warning signs:** Test passes but entity state doesn't change.

### Pitfall 4: `template_id` Uses Ellipsis Sentinel in UpdateCategoryCommand
**What goes wrong:** `UpdateCategoryCommand.template_id` defaults to `...` (Ellipsis), not `None`. Setting it to `None` means "clear the template". Leaving it as `...` means "don't change".
**Why it happens:** Three-state semantics: absent (keep) vs None (clear) vs UUID (set new).
**How to avoid:** When testing template assignment changes, explicitly set `template_id=some_uuid` or `template_id=None`. When testing non-template updates, leave it as default `...`.
**Warning signs:** Template propagation tests fail because the handler sees `...` and skips the template logic.

### Pitfall 5: Cache and IImageBackendClient Are Post-Commit Side Effects
**What goes wrong:** Tests fail because cache.delete or image_backend.delete raises an exception.
**Why it happens:** Handlers call these after `await self._uow.commit()` and wrap them in try/except.
**How to avoid:** Use `AsyncMock()` which returns coroutines by default. The handler swallows exceptions from cache/image calls.
**Warning signs:** Handler raises unexpected error from mock not being properly async.

### Pitfall 6: `invalidate_template_effective_cache` and `collect_attribute_cache_keys` Call Repo Methods
**What goes wrong:** Several attribute handlers import utility functions from `resolve_template_attributes.py` that make additional repo calls (`get_category_ids_by_template_ids`, `get_template_ids_for_attribute`). These are called AFTER commit and wrapped in try/except, but the fake repo methods currently raise `NotImplementedError`.
**Why it happens:** These utility functions run outside the UoW context manager but still call repo methods.
**How to avoid:** Implement the missing fake repo methods OR ensure the handler's try/except catches the error. Implementing is cleaner.
**Warning signs:** Tests crash with `NotImplementedError` from unimplemented fake methods.

### Pitfall 7: Domain Events Cleared After Commit
**What goes wrong:** After `uow.commit()`, aggregate events are cleared (moved to `collected_events`). Trying to read `brand.domain_events` after commit returns empty.
**Why it happens:** FakeUoW.commit() calls `aggregate.clear_domain_events()` after extending `collected_events`.
**How to avoid:** Assert events via `uow.collected_events`, not via entity's `domain_events`.
**Warning signs:** `assert len(brand.domain_events) == 1` fails.

## Code Examples

### make_logger() Helper (reuse across all 3 test files)

```python
from unittest.mock import MagicMock

def make_logger():
    """MagicMock satisfying ILogger protocol (sync methods + bind)."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger
```

### make_cache() Helper (for Category and Attribute handlers)

```python
from unittest.mock import AsyncMock

def make_cache():
    """AsyncMock satisfying ICacheService protocol."""
    return AsyncMock()
```

### FakeCategoryRepository.update_descendants_full_slug (implementation needed)

```python
async def update_descendants_full_slug(
    self, old_prefix: str, new_prefix: str
) -> None:
    """Replace full_slug prefix for all descendants matching old_prefix."""
    for cat in self._store.values():
        if cat.full_slug.startswith(old_prefix + "/"):
            new_full_slug = new_prefix + cat.full_slug[len(old_prefix):]
            # Use object.__setattr__ since attrs entities may guard fields
            object.__setattr__(cat, 'full_slug', new_full_slug)
```

### FakeCategoryRepository.propagate_effective_template_id (implementation needed)

```python
async def propagate_effective_template_id(
    self, category_id: uuid.UUID, effective_template_id: uuid.UUID | None
) -> list[uuid.UUID]:
    """Propagate effective_template_id to children with template_id=None."""
    affected: list[uuid.UUID] = []
    queue = [category_id]
    while queue:
        parent_id = queue.pop(0)
        for cat in self._store.values():
            if cat.parent_id == parent_id and cat.id != category_id:
                if cat.template_id is None:
                    object.__setattr__(cat, 'effective_template_id', effective_template_id)
                    affected.append(cat.id)
                    queue.append(cat.id)
                # If cat has its own template_id, stop propagation down that branch
    return affected
```

### FakeTemplateAttributeBindingRepository.get_bindings_for_templates (implementation needed)

```python
async def get_bindings_for_templates(
    self, template_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[DomainTemplateAttributeBinding]]:
    """Group bindings by template_id for the requested templates."""
    result: dict[uuid.UUID, list[DomainTemplateAttributeBinding]] = {
        tid: [] for tid in template_ids
    }
    for binding in self._store.values():
        if binding.template_id in result:
            result[binding.template_id].append(binding)
    return result
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio (auto mode) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x --no-cov -q` |
| Full suite command | `cd backend && uv run pytest tests/unit/ -x --no-cov -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CMD-01 | Brand handlers: create, update, delete, bulk_create | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_brand_handlers.py -x --no-cov -q` | Wave 0 |
| CMD-02 | Category handlers: create, update, delete, bulk_create | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_category_handlers.py -x --no-cov -q` | Wave 0 |
| CMD-03 | Attribute handlers: templates, attributes, bindings | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_attribute_handlers.py -x --no-cov -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x --no-cov -q`
- **Per wave merge:** `cd backend && uv run pytest tests/unit/ -x --no-cov -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/unit/modules/catalog/application/commands/test_brand_handlers.py` -- covers CMD-01
- [ ] `backend/tests/unit/modules/catalog/application/commands/test_category_handlers.py` -- covers CMD-02
- [ ] `backend/tests/unit/modules/catalog/application/commands/test_attribute_handlers.py` -- covers CMD-03
- [ ] Implement 4 `NotImplementedError` methods in `backend/tests/fakes/fake_catalog_repos.py` tagged for Phase 4
- [ ] Implement 3 `NotImplementedError` methods in `backend/tests/fakes/fake_catalog_repos.py` tagged for Phase 5 but needed by in-scope handlers

## Handler Inventory (Complete Scope)

### Brand Domain (CMD-01) -- 4 handlers
| Handler | File | Dependencies | Exceptions |
|---------|------|-------------|------------|
| CreateBrandHandler | `create_brand.py` | IBrandRepository, IUnitOfWork, ILogger | BrandSlugConflictError |
| UpdateBrandHandler | `update_brand.py` | IBrandRepository, IUnitOfWork, IImageBackendClient, ILogger | BrandNotFoundError, BrandSlugConflictError |
| DeleteBrandHandler | `delete_brand.py` | IBrandRepository, IUnitOfWork, ILogger | BrandNotFoundError, BrandHasProductsError |
| BulkCreateBrandsHandler | `bulk_create_brands.py` | IBrandRepository, IUnitOfWork, ILogger | ValidationError, BrandSlugConflictError, BrandNameConflictError |

### Category Domain (CMD-02) -- 4 handlers (update covers reorder + assign_template)
| Handler | File | Dependencies | Exceptions |
|---------|------|-------------|------------|
| CreateCategoryHandler | `create_category.py` | ICategoryRepository, IAttributeTemplateRepository, IUnitOfWork, ICacheService, ILogger | CategorySlugConflictError, CategoryNotFoundError, AttributeTemplateNotFoundError |
| UpdateCategoryHandler | `update_category.py` | ICategoryRepository, IAttributeTemplateRepository, IUnitOfWork, ICacheService, ILogger | CategoryNotFoundError, CategorySlugConflictError, AttributeTemplateNotFoundError |
| DeleteCategoryHandler | `delete_category.py` | ICategoryRepository, IUnitOfWork, ICacheService, ILogger | CategoryNotFoundError, CategoryHasChildrenError, CategoryHasProductsError |
| BulkCreateCategoriesHandler | `bulk_create_categories.py` | ICategoryRepository, IAttributeTemplateRepository, IUnitOfWork, ICacheService, ILogger | ValidationError, CategoryNotFoundError, CategorySlugConflictError, AttributeTemplateNotFoundError |

### Attribute Domain (CMD-03) -- 10 handlers
| Handler | File | Dependencies | Exceptions |
|---------|------|-------------|------------|
| CreateAttributeTemplateHandler | `create_attribute_template.py` | IAttributeTemplateRepository, IUnitOfWork, ILogger | AttributeTemplateCodeAlreadyExistsError |
| UpdateAttributeTemplateHandler | `update_attribute_template.py` | IAttributeTemplateRepository, IUnitOfWork, ILogger | AttributeTemplateNotFoundError |
| DeleteAttributeTemplateHandler | `delete_attribute_template.py` | IAttributeTemplateRepository, IUnitOfWork, ILogger | AttributeTemplateNotFoundError, AttributeTemplateHasCategoryReferencesError |
| CloneAttributeTemplateHandler | `clone_attribute_template.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, ILogger | AttributeTemplateNotFoundError, AttributeTemplateCodeAlreadyExistsError |
| CreateAttributeHandler | `create_attribute.py` | IAttributeRepository, IAttributeGroupRepository, IUnitOfWork, ILogger | AttributeCodeConflictError, AttributeSlugConflictError, AttributeGroupNotFoundError |
| UpdateAttributeHandler | `update_attribute.py` | IAttributeRepository, IAttributeGroupRepository, ITemplateAttributeBindingRepository, IAttributeTemplateRepository, ICacheService, IUnitOfWork, ILogger | AttributeNotFoundError, AttributeGroupNotFoundError |
| DeleteAttributeHandler | `delete_attribute.py` | IAttributeRepository, ITemplateAttributeBindingRepository, IAttributeTemplateRepository, ICacheService, IUnitOfWork, ILogger | AttributeNotFoundError, AttributeHasTemplateBindingsError, AttributeInUseByProductsError |
| BindAttributeToTemplateHandler | `bind_attribute_to_template.py` | IAttributeTemplateRepository, IAttributeRepository, ITemplateAttributeBindingRepository, IUnitOfWork, ICacheService, ILogger | AttributeTemplateNotFoundError, AttributeNotFoundError, TemplateAttributeBindingAlreadyExistsError |
| UnbindAttributeFromTemplateHandler | `unbind_attribute_from_template.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, ICacheService, ILogger | TemplateAttributeBindingNotFoundError |
| UpdateTemplateAttributeBindingHandler | `update_template_attribute_binding.py` | IAttributeTemplateRepository, ITemplateAttributeBindingRepository, IUnitOfWork, ICacheService, ILogger | TemplateAttributeBindingNotFoundError |

**Not in scope for this phase (despite existing):**
- ReorderTemplateBindingsHandler (`reorder_template_bindings.py`) -- Consider including under CMD-03 "manage_bindings" since it manages template bindings. If planner includes it, the `bulk_update_sort_order` fake method must be implemented.

## Cross-Module Dependencies Requiring AsyncMock

| Interface | Handlers Using It | Mock Pattern |
|-----------|-------------------|-------------|
| ILogger | ALL handlers | `make_logger()` -- MagicMock with `.bind()` returning self |
| ICacheService | All Category handlers, BindAttribute, UnbindAttribute, UpdateAttribute, DeleteAttribute, UpdateBinding | `make_cache()` -- AsyncMock() |
| IImageBackendClient | UpdateBrandHandler only | `AsyncMock()` inline |
| `invalidate_template_effective_cache` | UnbindAttributeFromTemplate, UpdateTemplateAttributeBinding, ReorderTemplateBindings | Calls `template_repo.get_category_ids_by_template_ids` internally -- fake method must be implemented |
| `collect_attribute_cache_keys` | UpdateAttribute, DeleteAttribute | Calls `binding_repo.get_template_ids_for_attribute` and `template_repo.get_category_ids_by_template_ids` -- fake methods must be implemented |

## Open Questions

1. **ReorderTemplateBindingsHandler scope inclusion**
   - What we know: CMD-03 says "manage_bindings" which could include reorder. The handler exists and is a binding management operation.
   - What's unclear: Whether "manage_bindings" in CMD-03 includes reorder or just CRUD (bind/unbind/update).
   - Recommendation: Include it under CMD-03 since it's a binding management operation. Implementing `bulk_update_sort_order` fake is straightforward.

2. **CategoryBuilder template_id support**
   - What we know: The existing `CategoryBuilder` in `builders.py` doesn't have `.with_template_id()`.
   - What's unclear: Whether we need to extend it or just use `Category.create_root(..., template_id=...)` directly.
   - Recommendation: Use `Category.create_root()` / `Category.create_child()` directly for tests needing template_id, since it's only a few tests.

3. **attrs entity field mutation in fake repos**
   - What we know: Domain entities use `attrs @define` which may guard fields. The `update_descendants_full_slug` and `propagate_effective_template_id` implementations need to mutate `full_slug` and `effective_template_id` on existing entities.
   - What's unclear: Whether `object.__setattr__` works or if we need to use the entity's own update mechanism.
   - Recommendation: Use `object.__setattr__` since fake repos need to simulate DB-level bulk updates that bypass domain entity methods.

## Project Constraints (from CLAUDE.md)

- **Architecture:** Must follow existing hexagonal/CQRS patterns -- commands through domain, queries direct to ORM
- **Testing:** Use existing test infrastructure (pytest, testcontainers, polyfactory) -- in this phase, pytest only
- **asyncio_mode = auto:** No need for `@pytest.mark.asyncio` decorators; all async tests auto-detected
- **Test discovery:** `python_classes = Test*`, `python_functions = test_*` -- follow these naming conventions
- **Code style:** Ruff linting with line-length 88, target Python 3.14
- **Imports:** Full paths from `src.` root (e.g., `from src.modules.catalog.application.commands.create_brand import ...`)
- **Test imports:** `from tests.factories.*` and `from tests.fakes.*`
- **GSD Workflow:** Do not make direct repo edits outside a GSD workflow unless explicitly asked

## Sources

### Primary (HIGH confidence)
- Source code: All 19 command handler files read directly
- Source code: `backend/tests/fakes/fake_uow.py` and `fake_catalog_repos.py` -- complete implementation reviewed
- Source code: All 6 builder files reviewed (brand, category, attribute, attribute_template, attribute_group, attribute_value)
- Source code: `backend/src/modules/catalog/domain/exceptions.py` -- all exception classes reviewed
- Source code: `backend/src/modules/catalog/domain/interfaces.py` -- all repository interfaces reviewed
- Source code: `backend/src/shared/interfaces/` (ILogger, ICacheService, IUnitOfWork) -- protocols reviewed
- Config: `backend/pytest.ini` -- pytest configuration reviewed
- Existing pattern: `backend/tests/unit/modules/user/application/commands/test_commands.py` -- handler test pattern with make_uow()/make_logger()

### Secondary (MEDIUM confidence)
- Code examples for fake repo implementations are estimates; the exact `object.__setattr__` approach for attrs entities may need verification during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and configured
- Architecture: HIGH - existing handler test pattern observed in user module, FakeUoW fully reviewed
- Pitfalls: HIGH - all pitfalls identified from reading actual handler source code and FakeUoW implementation
- Fake repo gaps: HIGH - all `NotImplementedError` methods identified with exact handler call sites

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- all research is based on existing source code, not external libraries)
