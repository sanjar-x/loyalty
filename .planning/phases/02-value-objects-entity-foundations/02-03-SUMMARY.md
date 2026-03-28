---
phase: 02-value-objects-entity-foundations
plan: 03
subsystem: testing
tags: [pytest, attrs, eav, attribute, value-objects, domain-entities]

# Dependency graph
requires:
  - phase: 01-test-infrastructure-builders
    provides: AttributeBuilder, AttributeValueBuilder, ProductAttributeValueBuilder, AttributeTemplateBuilder, TemplateAttributeBindingBuilder, AttributeGroupBuilder
provides:
  - Unit tests for Attribute aggregate (create, update, guard, behavior delegation)
  - Unit tests for AttributeValue entity (create, update)
  - Unit tests for ProductAttributeValue entity (create)
  - Unit tests for AttributeTemplate aggregate (create, update, guard, deletion validation)
  - Unit tests for TemplateAttributeBinding aggregate (create, update, filter_settings validation)
  - Unit tests for AttributeGroup aggregate (create, update, guard)
affects: [03-product-aggregate-behavior, 04-command-handler-testing]

# Tech tracking
tech-stack:
  added: []
  patterns: [_i18n helper for test readability, behavior-flag delegation tests, filter_settings structural validation tests]

key-files:
  created:
    - backend/tests/unit/modules/catalog/domain/test_attribute.py
    - backend/tests/unit/modules/catalog/domain/test_attribute_template.py
    - backend/tests/unit/modules/catalog/domain/test_attribute_group.py
  modified: []

key-decisions:
  - "Skipped test_create_rejects_invalid_code for Attribute/AttributeTemplate/AttributeGroup because source code does not validate code via _validate_slug -- documented as deferred items"
  - "AttributeGroup.update() uses None defaults not Ellipsis sentinels -- test adapted to actual behavior"

patterns-established:
  - "_i18n(en, ru) helper: concise bilingual dict factory used across all 3 test files"
  - "Builder-centric test setup: all happy-path tests use builders, validation tests call create() directly with invalid args"

requirements-completed: [DOM-01]

# Metrics
duration: 4min
completed: 2026-03-28
---

# Phase 02 Plan 03: EAV Attribute Entity Tests Summary

**81 unit tests covering all 6 EAV attribute entities -- Attribute, AttributeValue, ProductAttributeValue, AttributeTemplate, TemplateAttributeBinding, AttributeGroup -- validating factory methods, update logic, immutability guards, behavior delegation, and filter_settings structural validation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T14:25:01Z
- **Completed:** 2026-03-28T14:29:11Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments
- 45 tests for Attribute, AttributeValue, ProductAttributeValue covering create/update/guard/properties
- 25 tests for AttributeTemplate and TemplateAttributeBinding covering create/update/guard/deletion/filter_settings
- 11 tests for AttributeGroup covering create/update/guard with explicit-kwargs update pattern
- All tests use Phase 1 builders (AttributeBuilder, AttributeValueBuilder, etc.) per D-06
- BehaviorFlags delegation thoroughly tested (5 property tests plus create/update paths)
- filter_settings validation: allowed keys whitelist, max key count (20), non-dict rejection

## Task Commits

Each task was committed atomically:

1. **Task 1: Attribute, AttributeValue, ProductAttributeValue tests** - `b02bfcc` (test)
2. **Task 2: AttributeTemplate, TemplateAttributeBinding, AttributeGroup tests** - `7c6d8ce` (test)

## Files Created/Modified
- `backend/tests/unit/modules/catalog/domain/test_attribute.py` - 45 tests: Attribute create (10), update (11), guard (2), properties (5); AttributeValue create (7), update (8); ProductAttributeValue create (2)
- `backend/tests/unit/modules/catalog/domain/test_attribute_template.py` - 25 tests: AttributeTemplate create (6), update (4), guard (1), deletion (2); TemplateAttributeBinding create (8), update (4)
- `backend/tests/unit/modules/catalog/domain/test_attribute_group.py` - 11 tests: AttributeGroup create (6), update (4), guard (1)

## Decisions Made
- Skipped `test_create_rejects_invalid_code` for Attribute, AttributeTemplate, and AttributeGroup: the plan interface stated code is validated via `_validate_slug`, but the actual source code only validates slug (for Attribute) or does not validate code at all (for AttributeTemplate, AttributeGroup). Logged as deferred items for domain hardening.
- AttributeGroup.update() uses `None` defaults (not Ellipsis sentinels as the plan described). Test adapted to actual `None`-default behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test expectations for code validation**
- **Found during:** Task 1 (Attribute tests)
- **Issue:** Plan stated Attribute.create() validates code via _validate_slug, but source only validates slug parameter. Tests for invalid code would fail against actual implementation.
- **Fix:** Replaced test_create_rejects_invalid_code with two slug validation tests (spaces and uppercase). Documented missing code validation in deferred-items.md.
- **Files modified:** test_attribute.py
- **Verification:** All 45 tests pass
- **Committed in:** b02bfcc (Task 1 commit)

**2. [Rule 1 - Bug] Corrected AttributeGroup.update() sentinel assumption**
- **Found during:** Task 2 (AttributeGroup tests)
- **Issue:** Plan described Ellipsis sentinel for name_i18n default, but actual implementation uses None default
- **Fix:** Wrote test using None-default semantics (omit name_i18n, check it remains unchanged)
- **Files modified:** test_attribute_group.py
- **Verification:** All 11 tests pass
- **Committed in:** 7c6d8ce (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 plan-vs-source mismatches)
**Impact on plan:** Tests accurately reflect actual source behavior. Missing code validation documented as deferred items.

## Issues Encountered
- Pre-existing test failure in `test_category_effective_family.py::test_update_clear_template_id_does_not_clear_effective` -- not caused by this plan's changes. Logged to `deferred-items.md`.

## Known Stubs
None -- all tests are fully wired to actual domain entities via builders.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All EAV attribute entity tests complete, ready for Product aggregate behavior testing (Phase 03)
- Builders confirmed working for all 6 attribute-related entities
- Missing code validation on AttributeGroup/AttributeTemplate/Attribute.code should be addressed in a future hardening pass

## Self-Check: PASSED

- [x] test_attribute.py exists
- [x] test_attribute_template.py exists
- [x] test_attribute_group.py exists
- [x] 02-03-SUMMARY.md exists
- [x] Commit b02bfcc found
- [x] Commit 7c6d8ce found

---
*Phase: 02-value-objects-entity-foundations*
*Completed: 2026-03-28*
