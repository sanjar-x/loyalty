---
phase: 08-api-contract-validation
plan: 01
subsystem: testing
tags: [e2e, api, fastapi, brands, categories, attributes, templates]

requires:
  - phase: 07-repository-data-integrity
    provides: Repository correctness against real PostgreSQL

provides:
  - Shared conftest.py with 6 helper functions for creating prerequisite entities via API
  - 5 test files covering 40+ brand, category, attribute, value, and template endpoints
  - camelCase response shape assertions for all endpoints

affects: [08-02, 08-03]

tech-stack:
  added: []
  patterns: [E2E API testing with shared helper functions, uuid suffix for test isolation]

key-files:
  created:
    - backend/tests/e2e/api/v1/catalog/__init__.py
    - backend/tests/e2e/api/v1/catalog/conftest.py
    - backend/tests/e2e/api/v1/catalog/test_brands.py
    - backend/tests/e2e/api/v1/catalog/test_categories.py
    - backend/tests/e2e/api/v1/catalog/test_attributes.py
    - backend/tests/e2e/api/v1/catalog/test_attribute_values.py
    - backend/tests/e2e/api/v1/catalog/test_attribute_templates.py
  modified: []

key-decisions:
  - "Used plain async helper functions (not fixtures) in conftest.py to avoid fixture ordering issues"
  - "Each helper generates uuid4 suffix for slugs/codes to prevent inter-test conflicts"

requirements-completed: [API-01]

duration: 5 min
completed: 2026-03-28
---

# Phase 08 Plan 01: Brand, Category, Attribute, Value, Template E2E Tests Summary

Shared E2E conftest with 6 entity creation helpers + 5 test files covering 49 tests for all foundational catalog admin endpoints (brands, categories, attributes, attribute values, attribute templates + bindings).

## Execution Details

- Duration: ~5 min
- Tasks: 3/3 complete
- Files: 7 created
- Tests: 49 (10 brand + 9 category + 9 attribute + 10 value + 11 template/binding)

## Deviations from Plan

None - plan executed exactly as written.

## Key Artifacts

- `conftest.py`: 6 async helper functions (create_brand, create_category, create_attribute, create_attribute_value, create_attribute_template, bind_attribute_to_template)
- Each test file covers happy-path and error-path (404, 409, 422) for every endpoint
- All response shape assertions verify camelCase field names

## Self-Check: PASSED

- [x] All 7 files created
- [x] conftest.py contains all 6 helper functions
- [x] All files parse without syntax errors
- [x] Each test file has happy-path and error-path tests
