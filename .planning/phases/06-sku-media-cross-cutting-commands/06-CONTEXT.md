# Phase 6: SKU, Media & Cross-Cutting Commands - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Test the remaining command handlers (SKU and Media) and systematically verify cross-cutting concerns across ALL catalog command handlers: domain event emission audit, bulk operation atomicity, and FK/uniqueness error paths. This is the final application-layer testing phase — after this, every handler has been proven correct.

</domain>

<decisions>
## Implementation Decisions

### SKU Handler Scope (CMD-06)
- **D-01:** SKU handlers in scope: AddSKUHandler, UpdateSKUHandler, DeleteSKUHandler, GenerateSKUMatrixHandler.
- **D-02:** GenerateSKUMatrixHandler is the most complex — test matrix generation from variant attribute combinations, including edge cases (empty attributes, single variant, multiple variants).
- **D-03:** Test generate_sku_matrix atomicity (CMD-09): on partial failure, verify NO SKUs are persisted — complete rollback.

### Media Handler Scope (CMD-07)
- **D-04:** Media handlers in scope: AddProductMediaHandler, DeleteProductMediaHandler, UpdateProductMediaHandler, ReorderProductMediaHandler.
- **D-05:** Media handlers depend on IImageBackendClient. Use per-test inline AsyncMock (consistent with Phase 4/5 cross-module dependency pattern). Mock HTTP responses: success, timeout/error, 404.
- **D-06:** Test that DeleteProductMediaHandler calls IImageBackendClient to remove the storage object, not just the domain record.

### Cross-Cutting Event Audit (CMD-08)
- **D-07:** Phase 6 only audits handlers NOT already covered by Phases 4 and 5. Create a systematic checklist from all 46 handlers, mark those verified in prior phases, and test only the remaining gaps (SKU handlers, media handlers, bulk handlers).
- **D-08:** For handlers already tested in Phases 4-5, do NOT re-test event emission — trust the prior phase verification. Phase 6 fills gaps, not duplicates.
- **D-09:** The audit should produce a checklist mapping: handler → event type → phase where tested. Include in SUMMARY.md for traceability.

### Bulk Atomicity (CMD-09)
- **D-10:** Test generate_sku_matrix atomicity in this phase (CMD-06 scope).
- **D-11:** bulk_create_brands atomicity should have been tested in Phase 4 (CMD-01). If Phase 4 missed it, Phase 6 fills the gap. bulk_create_categories and bulk_create_attributes similarly — check Phase 4 coverage first.
- **D-12:** Atomicity test pattern: seed a scenario where the Nth item in the bulk operation fails (e.g., slug conflict), verify ZERO items from the batch were persisted.

### FK/Uniqueness Error Paths (CMD-10)
- **D-13:** Representative sample across handler domains, not exhaustive. Focus on cross-entity FK paths: product→brand (missing brand_id), product→category (missing category_id), SKU→variant (missing variant_id), media→product (missing product_id).
- **D-14:** Uniqueness conflict paths: slug conflicts (brand, category, product), sku_code conflicts, variant hash collisions.
- **D-15:** Target 2-3 FK/uniqueness error tests per handler domain (brand, category, attribute, product, variant, SKU, media) — enough to prove the error handling pattern works without testing every permutation.

### Mock Strategy (carried from Phases 4-5)
- **D-16:** FakeUoW for ALL handlers — same consistency pattern.
- **D-17:** Per-test inline AsyncMock for: ILogger, IImageBackendClient. NOT for repositories or UoW.
- **D-18:** Verify UoW.commit() called on success, NOT called on validation failure.

### Test Organization
- **D-19:** Three test files: `test_sku_handlers.py`, `test_media_handlers.py`, `test_cross_cutting.py` under `backend/tests/unit/modules/catalog/application/commands/`.
- **D-20:** test_cross_cutting.py contains: event audit gap tests, bulk atomicity tests, FK/uniqueness error sample tests.
- **D-21:** One test class per handler in SKU/media files. Cross-cutting file uses TestEventAudit, TestBulkAtomicity, TestFKUniquenessErrors classes.

### Claude's Discretion
- Exact number of FK/uniqueness error tests per domain
- Which specific handlers need event gap testing (depends on Phase 4-5 coverage)
- How to structure the generate_sku_matrix test scenarios (number of variants × attributes)
- Whether bulk_create_brands/categories/attributes need retesting (check Phase 4 SUMMARY first)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### SKU command handlers
- `backend/src/modules/catalog/application/commands/add_sku.py` — AddSKUHandler
- `backend/src/modules/catalog/application/commands/update_sku.py` — UpdateSKUHandler
- `backend/src/modules/catalog/application/commands/delete_sku.py` — DeleteSKUHandler
- `backend/src/modules/catalog/application/commands/generate_sku_matrix.py` — GenerateSKUMatrixHandler (complex, matrix generation)

### Media command handlers
- `backend/src/modules/catalog/application/commands/add_product_media.py` — AddProductMediaHandler (depends on IImageBackendClient)
- `backend/src/modules/catalog/application/commands/delete_product_media.py` — DeleteProductMediaHandler (depends on IImageBackendClient)
- `backend/src/modules/catalog/application/commands/update_product_media.py` — UpdateProductMediaHandler
- `backend/src/modules/catalog/application/commands/reorder_product_media.py` — ReorderProductMediaHandler

### Bulk handlers (atomicity testing)
- `backend/src/modules/catalog/application/commands/bulk_create_brands.py` — BulkCreateBrandsHandler
- `backend/src/modules/catalog/application/commands/bulk_create_categories.py` — BulkCreateCategoriesHandler
- `backend/src/modules/catalog/application/commands/bulk_create_attributes.py` — BulkCreateAttributesHandler
- `backend/src/modules/catalog/application/commands/bulk_add_attribute_values.py` — BulkAddAttributeValuesHandler

### Cross-module dependency
- `backend/src/modules/catalog/domain/interfaces.py` — IImageBackendClient interface
- `backend/src/modules/catalog/infrastructure/image_backend_client.py` — Real implementation (reference for mock behavior)

### Prior phase test patterns and coverage
- `backend/tests/unit/modules/catalog/application/commands/test_brand_handlers.py` — Phase 4 handler test pattern
- `.planning/phases/04-brand-category-attribute-command-handlers/` — Phase 4 SUMMARY (check event coverage)
- `.planning/phases/05-product-variant-command-handlers/` — Phase 5 SUMMARY (check event coverage)

### Test infrastructure
- `backend/tests/fakes/fake_uow.py` — FakeUnitOfWork
- `backend/tests/fakes/fake_catalog_repos.py` — All fake catalog repositories

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- FakeUnitOfWork + 10 fake repos from Phase 1
- All entity builders from Phase 1
- Phase 4/5 handler test patterns (test_brand_handlers.py, test_product_handlers.py)
- `make_logger()` pattern

### Established Patterns
- Media handlers call IImageBackendClient for storage operations (upload, delete)
- GenerateSKUMatrixHandler computes cartesian product of variant attributes, creates SKUs
- Bulk handlers iterate over items, calling entity.create() for each, committing all at once
- All handlers use constructor injection via Dishka

### Integration Points
- New test files: `backend/tests/unit/modules/catalog/application/commands/test_sku_handlers.py`, `test_media_handlers.py`, `test_cross_cutting.py`
- Tests import handlers from `src.modules.catalog.application.commands.*`
- Tests use FakeUoW from `tests.fakes.fake_uow`
- Tests mock IImageBackendClient with per-test AsyncMock

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key insight: Phase 6 is the "sweep" phase that fills gaps across all prior handler testing, so it should reference Phase 4 and 5 SUMMARY files to avoid duplicate work.

</specifics>

<deferred>
## Deferred Ideas

- Performance testing of generate_sku_matrix with large variant/attribute sets — Phase 7+ or v2 PERF requirements
- Concurrent session tests for optimistic locking — v2 ADV-02
- Property-based testing for EAV attribute combinatorial state — v2 ADV-03

</deferred>

---

*Phase: 06-sku-media-cross-cutting-commands*
*Context gathered: 2026-03-28*
