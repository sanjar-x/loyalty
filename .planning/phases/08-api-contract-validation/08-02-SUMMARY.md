---
phase: 08-api-contract-validation
plan: 02
subsystem: testing
tags: [e2e, api, fastapi, products, variants, skus, media, attributes]

requires:
  - phase: 08-01
    provides: Shared conftest.py with entity creation helpers

provides:
  - 5 test files covering 33 product-aggregate endpoint tests
  - Product status transition tests (valid and invalid FSM paths)
  - SKU matrix generation test with real attribute+value setup
  - External media tests bypassing ImageBackend dependency

affects: [08-03]

tech-stack:
  added: []
  patterns: [Product aggregate test setup chains, external media for ImageBackend bypass]

key-files:
  created:
    - backend/tests/e2e/api/v1/catalog/test_products.py
    - backend/tests/e2e/api/v1/catalog/test_variants.py
    - backend/tests/e2e/api/v1/catalog/test_skus.py
    - backend/tests/e2e/api/v1/catalog/test_product_attributes.py
    - backend/tests/e2e/api/v1/catalog/test_media.py
  modified: []

key-decisions:
  - "Used external media (isExternal=true with URL) to bypass ImageBackend dependency in tests"
  - "Product attribute assignment tests create full prerequisite chain (template -> attribute -> binding -> category -> brand -> product -> value)"

requirements-completed: [API-01]

duration: 5 min
completed: 2026-03-28
---

# Phase 08 Plan 02: Product, Variant, SKU, Product-Attribute, Media E2E Tests Summary

5 test files covering 33 tests for all product-aggregate admin endpoints including product status transitions, SKU matrix generation, product attribute assignment with governance chain, and external media assets.

## Execution Details

- Duration: ~5 min
- Tasks: 2/2 complete
- Files: 5 created
- Tests: 33 (11 product + 5 variant + 6 SKU + 5 product-attribute + 6 media)

## Deviations from Plan

None - plan executed exactly as written.

## Key Artifacts

- Product status transition tests cover DRAFT->ENRICHING (valid) and DRAFT->PUBLISHED (invalid, 422)
- SKU matrix generation test creates attribute+values then generates matrix combinations
- Product attribute tests build full governance chain (template->attribute->binding->category)
- Media tests use external URLs to avoid ImageBackend dependency

## Self-Check: PASSED

- [x] All 5 files created
- [x] All files parse without syntax errors
- [x] Product status transitions tested (happy + error)
- [x] SKU matrix generation tested with real attribute setup
- [x] External media used for ImageBackend independence
