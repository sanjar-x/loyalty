---
phase: 01-test-infrastructure
plan: 02
subsystem: testing
tags: [fake-uow, unit-testing, in-memory-repos, test-doubles, ddd]

# Dependency graph
requires:
  - phase: none
    provides: none
provides:
  - FakeUnitOfWork implementing IUnitOfWork with dict-based storage and event collection
  - FakeRepository[T] generic base class for in-memory CRUD
  - 10 fake catalog repository implementations (Brand, Category, AttributeGroup, Attribute, AttributeValue, Product, ProductAttributeValue, MediaAsset, AttributeTemplate, TemplateAttributeBinding)
  - 11 smoke tests verifying FakeUoW behavior correctness
affects: [04-brand-command-tests, 05-category-command-tests, 06-product-command-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [FakeRepository dict-based CRUD base, cross-repo reference wiring for deletion guards, FakeUoW event collection matching real UoW behavior]

key-files:
  created:
    - backend/tests/fakes/fake_uow.py
    - backend/tests/fakes/fake_catalog_repos.py
    - backend/tests/unit/test_fake_uow_smoke.py
  modified:
    - backend/tests/fakes/__init__.py

key-decisions:
  - "Cross-repo references wired via _product_store/_child_store/_attribute_store for real has_products/has_children/has_attributes scanning instead of stub returns"
  - "Less common methods (update_descendants_full_slug, propagate_effective_template_id, move_attributes_to_group, etc.) raise NotImplementedError as documented stubs to be filled when needed"
  - "Each fake repo implements its own _store dict rather than inheriting from FakeRepository generic base, to correctly satisfy multiple inheritance with ABC interfaces"

patterns-established:
  - "FakeRepository[T] pattern: generic dict-based CRUD with _store property for direct test assertions"
  - "Cross-repo wiring pattern: FakeUoW.__init__() sets _product_store/_child_store/_attribute_store references between repos"
  - "FakeUoW event collection pattern: commit() iterates aggregates, extends collected_events, then clears each aggregate's events"

requirements-completed: [INFRA-03]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 01 Plan 02: Fake UoW and Catalog Repositories Summary

**In-memory FakeUnitOfWork with dict-based storage, event collection matching real UoW behavior, and 10 fake catalog repository implementations with cross-repo reference wiring**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T12:22:01Z
- **Completed:** 2026-03-28T12:27:19Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- FakeUnitOfWork implementing full IUnitOfWork interface with commit/rollback tracking and domain event collection
- FakeRepository[T] generic base providing dict-backed CRUD operations
- All 10 catalog repository interfaces have fake implementations with real dict-scanning logic for commonly-used methods
- Cross-repo references wired so has_products(), has_children(), and has_attributes() actually scan related stores
- 11 smoke tests proving FakeUoW behavior correctness including event collection, aggregate deduplication, context manager semantics, and cross-repo wiring

## Task Commits

Each task was committed atomically:

1. **Task 1: Build FakeUnitOfWork and all fake catalog repositories** - `5e93947` (feat)
2. **Task 2: Create FakeUoW smoke tests** - `753f8f4` (test)

## Files Created/Modified
- `backend/tests/fakes/fake_uow.py` - FakeUnitOfWork and FakeRepository[T] generic base
- `backend/tests/fakes/fake_catalog_repos.py` - All 10 fake catalog repository implementations
- `backend/tests/fakes/__init__.py` - Updated exports for FakeUnitOfWork and FakeRepository
- `backend/tests/unit/test_fake_uow_smoke.py` - 11 smoke tests for FakeUoW behavior

## Decisions Made
- Cross-repo references wired via shared dict references (_product_store, _child_store, _attribute_store) rather than returning stub False values, enabling realistic has_products/has_children/has_attributes behavior in tests
- Each concrete fake repo class has its own _store dict and CRUD methods (not inheriting FakeRepository[T]) to correctly satisfy multiple inheritance with Python ABCs
- Less common query methods raise NotImplementedError with descriptive messages indicating which phase will need them, following the plan's recommendation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Root conftest.py imports Settings which requires environment variables; resolved by copying .env from main repo to worktree (not committed, gitignored)
- 2 pre-existing test failures in test_category_effective_family.py and test_image_backend_client.py unrelated to this plan's changes

## Known Stubs

The following methods in fake repositories intentionally raise NotImplementedError as documented stubs:
- `backend/tests/fakes/fake_catalog_repos.py` - FakeCategoryRepository.update_descendants_full_slug (line ~184)
- `backend/tests/fakes/fake_catalog_repos.py` - FakeCategoryRepository.propagate_effective_template_id (line ~189)
- `backend/tests/fakes/fake_catalog_repos.py` - FakeAttributeGroupRepository.move_attributes_to_group (line ~230)
- `backend/tests/fakes/fake_catalog_repos.py` - FakeAttributeTemplateRepository.get_category_ids_by_template_ids (line ~458)
- `backend/tests/fakes/fake_catalog_repos.py` - FakeTemplateAttributeBindingRepository.get_bindings_for_templates (line ~492)
- `backend/tests/fakes/fake_catalog_repos.py` - FakeTemplateAttributeBindingRepository.bulk_update_sort_order (line ~498)
- `backend/tests/fakes/fake_catalog_repos.py` - FakeTemplateAttributeBindingRepository.get_template_ids_for_attribute (line ~505)

These stubs are intentional per the plan -- they will be implemented when the respective Phase 4/5 tests need them. They do NOT prevent this plan's goal (providing the core FakeUoW test isolation mechanism).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- FakeUoW is ready for use by Phase 4-6 catalog command handler unit tests
- All 10 repository fakes are importable and implement the required interfaces
- Less common query methods will need implementation when specific command tests require them (documented as NotImplementedError stubs)

## Self-Check: PASSED

All created files verified present. All commit hashes verified in git log.

---
*Phase: 01-test-infrastructure*
*Completed: 2026-03-28*
