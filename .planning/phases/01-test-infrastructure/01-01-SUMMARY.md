---
phase: 01-test-infrastructure
plan: 01
subsystem: testing
tags: [pytest, hypothesis, schemathesis, respx, dirty-equals, polyfactory, builders, test-factories]

# Dependency graph
requires: []
provides:
  - Six new PyPI test dependencies installed and configured
  - Fluent Builder classes for all 13 catalog domain entities
  - Polyfactory ORM factories for all catalog infrastructure models
  - Builder smoke test suite (16 tests) proving all builders work
affects: [01-02, 01-03, 02-command-handler-tests, 03-repository-tests, 04-api-tests]

# Tech tracking
tech-stack:
  added: [hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout]
  patterns: [fluent-builder-per-entity, builder-calls-create-factory, sku-via-product-add-sku]

key-files:
  created:
    - backend/tests/factories/brand_builder.py
    - backend/tests/factories/product_builder.py
    - backend/tests/factories/variant_builder.py
    - backend/tests/factories/sku_builder.py
    - backend/tests/factories/attribute_builder.py
    - backend/tests/factories/attribute_template_builder.py
    - backend/tests/factories/attribute_group_builder.py
    - backend/tests/factories/media_asset_builder.py
    - backend/tests/unit/test_builders_smoke.py
  modified:
    - backend/pyproject.toml
    - backend/pytest.ini
    - backend/uv.lock
    - backend/tests/factories/orm_factories.py
    - backend/tests/factories/catalog_mothers.py

key-decisions:
  - "pytest-timeout uses thread method (not signal) for Windows compatibility"
  - "SKUBuilder uses Product.add_sku() because SKU has no standalone create()"
  - "Existing builders.py CategoryBuilder left untouched to avoid breaking existing tests"
  - "All i18n defaults include both ru and en keys per REQUIRED_LOCALES validation"

patterns-established:
  - "Fluent Builder per entity: one builder file per domain entity with with_*() chaining and build() calling create()"
  - "Auto-generated slugs: f'prefix-{uuid.uuid4().hex[:6]}' pattern for unique test slugs"
  - "Mothers as builder wrappers: Object Mothers delegate to builders for common scenarios"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: 10min
completed: 2026-03-28
---

# Phase 01 Plan 01: Test Dependencies and Entity Builders Summary

**Six test libraries installed, 8 fluent Builder files for all catalog entities, 11 ORM factories, and 16 smoke tests confirming every builder produces valid domain objects**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-28T12:21:18Z
- **Completed:** 2026-03-28T12:31:44Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments
- Installed hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout as dev dependencies
- Configured pytest-timeout at 30s with thread method (Windows-compatible)
- Created 8 builder files covering all 13 catalog domain entities (Brand, Product, ProductVariant, SKU, Attribute, AttributeValue, ProductAttributeValue, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, MediaAsset)
- Extended ORM factories from 6 to 17 (added 11 catalog model factories)
- Updated catalog_mothers to use builders where appropriate
- Created 16 smoke tests proving every builder produces valid entities

## Task Commits

Each task was committed atomically:

1. **Task 1: Install test dependencies and configure pytest-timeout** - `f55b9b5` (chore)
2. **Task 2: Build fluent Builders for all catalog entities and extend ORM factories** - `4d6e650` (feat)
3. **Task 3: Create builder smoke tests** - `c02fae9` (test)

## Files Created/Modified
- `backend/pyproject.toml` - Added 6 new test dependencies to dev group
- `backend/pytest.ini` - Added pytest-timeout config (30s, thread method)
- `backend/uv.lock` - Updated lockfile with new dependencies
- `backend/tests/factories/brand_builder.py` - BrandBuilder fluent builder
- `backend/tests/factories/product_builder.py` - ProductBuilder (auto-creates variant)
- `backend/tests/factories/variant_builder.py` - ProductVariantBuilder (calls create())
- `backend/tests/factories/sku_builder.py` - SKUBuilder (calls Product.add_sku())
- `backend/tests/factories/attribute_builder.py` - AttributeBuilder, AttributeValueBuilder, ProductAttributeValueBuilder
- `backend/tests/factories/attribute_template_builder.py` - AttributeTemplateBuilder, TemplateAttributeBindingBuilder
- `backend/tests/factories/attribute_group_builder.py` - AttributeGroupBuilder
- `backend/tests/factories/media_asset_builder.py` - MediaAssetBuilder (supports external URL)
- `backend/tests/factories/orm_factories.py` - Extended with 11 new catalog model factories
- `backend/tests/factories/catalog_mothers.py` - Updated to use builders, fixed i18n locales
- `backend/tests/unit/test_builders_smoke.py` - 16 smoke tests for all builders

## Decisions Made
- Used `timeout_method = thread` instead of `signal` because the dev environment is Windows where signal-based timeout is not supported
- SKUBuilder works differently from other builders: it requires a Product aggregate and calls `product.add_sku()` internally, since SKU has no standalone `create()` method
- Kept existing `builders.py` CategoryBuilder untouched to avoid breaking existing tests; new builders live in separate per-entity files
- All builder i18n defaults include both "ru" and "en" keys per REQUIRED_LOCALES validation in entities

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing "ru" locale in CategoryMothers and AttributeMothers**
- **Found during:** Task 2 (catalog_mothers update)
- **Issue:** CategoryMothers.root(), .child(), .deep_nested() and AttributeMothers.numeric_non_dictionary(), .boolean_attribute() had i18n dicts with only "en" key, but entity validation requires both "ru" and "en" locales (REQUIRED_LOCALES)
- **Fix:** Added "ru" translations to all affected mother methods
- **Files modified:** backend/tests/factories/catalog_mothers.py
- **Verification:** All mothers produce valid entities without MissingRequiredLocalesError
- **Committed in:** 4d6e650 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correctness -- mothers would crash without both locale keys.

## Issues Encountered
- Two pre-existing test failures detected (not caused by this plan's changes): `test_update_clear_template_id_does_not_clear_effective` and `test_delete_sends_correct_request`. Both fail identically in the main repo. Logged as out-of-scope.
- ORM factories require the full model registry to be loaded (via `src.infrastructure.database.registry`) due to SQLAlchemy relationship resolution. This is expected behavior -- integration tests load the registry via conftest.py.

## Known Stubs
None - all builders are fully functional with real domain entity creation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All builder infrastructure is ready for Plans 01-02 (conftest and fixtures) and 01-03 (test helpers)
- Every subsequent test phase can use builders to construct entities fluently
- Pre-existing test failures should be addressed in future phases (catalog domain testing)

## Self-Check: PASSED

All 12 expected files exist. All 3 task commits verified (f55b9b5, 4d6e650, c02fae9).

---
*Phase: 01-test-infrastructure*
*Completed: 2026-03-28*
