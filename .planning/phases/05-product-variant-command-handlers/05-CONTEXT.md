# Phase 5: Product & Variant Command Handlers - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove all command handlers for the Product aggregate core (product CRUD, status changes, attribute assignment, variant management) orchestrate correctly — calling the right repositories, enforcing preconditions, committing through UoW. This phase tests the APPLICATION layer handlers, not domain entities (Phase 2-3) or infrastructure (Phase 7). Media handlers (CMD-07) belong to Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Handler Scope (CMD-04 + CMD-05)
- **D-01:** Product command handlers in scope: CreateProductHandler, UpdateProductHandler, DeleteProductHandler, ChangeProductStatusHandler, AssignProductAttributeHandler, BulkAssignProductAttributeHandler, DeleteProductAttributeHandler.
- **D-02:** Variant command handlers in scope: AddVariantHandler, UpdateVariantHandler, DeleteVariantHandler.
- **D-03:** Media handlers (AddProductMedia, DeleteProductMedia, UpdateProductMedia, ReorderProductMedia) are explicitly OUT OF SCOPE — they map to CMD-07 in Phase 6 per REQUIREMENTS.md traceability.

### Attribute Governance Handler Testing (DOM-06 handler-side)
- **D-04:** Phase 3 D-01/D-02 explicitly deferred handler-side governance to this phase. AssignProductAttributeHandler and BulkAssignProductAttributeHandler must be tested here — they enforce the template governance chain (Category → effective template → bindings → attribute assignment validation).
- **D-05:** Test both valid assignment (attribute bound to product's category template) and rejection paths (wrong template, unbound attribute, wrong level).

### Supplier Cross-Module Dependency
- **D-06:** CreateProductHandler and UpdateProductHandler depend on ISupplierQueryService.assert_supplier_active(). Use per-test inline AsyncMock (Phase 4 D-04 pattern). Do NOT build a shared fake — keep stubs local to each test.
- **D-07:** Test three supplier paths: (1) no supplier (supplier_id=None — skip validation), (2) active supplier (validation passes), (3) inactive supplier (validation raises SupplierInactiveError). Also test cross-border supplier source_url requirement (SourceUrlRequiredError).

### Mock Strategy (carried from Phase 4)
- **D-08:** FakeUoW for ALL handlers — same consistency pattern as Phase 4 D-03. FakeUoW validates real repository interactions.
- **D-09:** Per-test inline AsyncMock only for: ILogger, ISupplierQueryService, IImageBackendClient (if encountered). NOT for repositories or UoW.
- **D-10:** Verify UoW.commit() called on success, NOT called on validation failure.
- **D-11:** Verify domain events collected by FakeUoW on relevant operations.

### Test Organization (carried from Phase 4)
- **D-12:** Two test files: `test_product_handlers.py` and `test_variant_handlers.py` under `backend/tests/unit/modules/catalog/application/commands/`.
- **D-13:** One test CLASS per handler: TestCreateProduct, TestUpdateProduct, TestDeleteProduct, TestChangeProductStatus, TestAssignProductAttribute, TestBulkAssignProductAttributes, TestDeleteProductAttribute, TestAddVariant, TestUpdateVariant, TestDeleteVariant.
- **D-14:** Use Phase 1 builders (ProductBuilder, VariantBuilder, etc.) for test data. Async tests with FakeUoW.

### Claude's Discretion
- Number of edge cases per handler beyond happy/error paths
- Whether to test ILogger bind/info calls
- Exact test method naming
- How many invalid attribute assignment scenarios to test

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product command handlers (source of truth)
- `backend/src/modules/catalog/application/commands/create_product.py` — CreateProductHandler with ISupplierQueryService dependency
- `backend/src/modules/catalog/application/commands/update_product.py` — UpdateProductHandler
- `backend/src/modules/catalog/application/commands/delete_product.py` — DeleteProductHandler
- `backend/src/modules/catalog/application/commands/change_product_status.py` — ChangeProductStatusHandler
- `backend/src/modules/catalog/application/commands/assign_product_attribute.py` — AssignProductAttributeHandler (attribute governance)
- `backend/src/modules/catalog/application/commands/bulk_assign_product_attributes.py` — BulkAssignProductAttributeHandler
- `backend/src/modules/catalog/application/commands/delete_product_attribute.py` — DeleteProductAttributeHandler

### Variant command handlers
- `backend/src/modules/catalog/application/commands/add_variant.py` — AddVariantHandler
- `backend/src/modules/catalog/application/commands/update_variant.py` — UpdateVariantHandler
- `backend/src/modules/catalog/application/commands/delete_variant.py` — DeleteVariantHandler

### Domain layer (tested in Phases 2-3)
- `backend/src/modules/catalog/domain/entities.py` — Product aggregate, ProductVariant
- `backend/src/modules/catalog/domain/interfaces.py` — Repository interfaces (IProductRepository, etc.)
- `backend/src/modules/catalog/domain/exceptions.py` — Domain exceptions handlers should raise

### Cross-module dependency
- `backend/src/modules/supplier/domain/interfaces.py` — ISupplierQueryService.assert_supplier_active()
- `backend/src/modules/supplier/domain/exceptions.py` — SupplierInactiveError, SourceUrlRequiredError
- `backend/src/modules/supplier/domain/value_objects.py` — SupplierType enum (CROSS_BORDER triggers source_url check)

### Test infrastructure (built in Phase 1, used in Phase 4)
- `backend/tests/fakes/fake_uow.py` — FakeUnitOfWork
- `backend/tests/fakes/fake_catalog_repos.py` — All fake catalog repositories
- `backend/tests/factories/product_builder.py` — ProductBuilder
- `backend/tests/factories/variant_builder.py` — VariantBuilder (if exists)

### Phase 4 handler test pattern (reference)
- `backend/tests/unit/modules/catalog/application/commands/test_brand_handlers.py` — Follow this pattern for Product/Variant handlers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- FakeUnitOfWork + 10 fake repos from Phase 1
- All entity builders from Phase 1
- Phase 4 handler test pattern (test_brand_handlers.py) — copy structure for product/variant handlers
- `make_logger()` pattern from identity tests

### Established Patterns
- CreateProductHandler validates supplier existence via ISupplierQueryService before entity creation
- Cross-border suppliers require source_url (SourceUrlRequiredError)
- AssignProductAttributeHandler does template→binding→attribute chain validation
- All handlers use constructor injection (repos, UoW, logger, optional services)
- Error flow: raise domain exception → UoW NOT committed

### Integration Points
- New test files: `backend/tests/unit/modules/catalog/application/commands/test_product_handlers.py` and `test_variant_handlers.py`
- Tests import handlers from `src.modules.catalog.application.commands.*`
- Tests use FakeUoW from `tests.fakes.fake_uow`
- Tests mock ISupplierQueryService with per-test AsyncMock

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Auto-mode selected recommended defaults. Follows Phase 4 patterns for consistency.

</specifics>

<deferred>
## Deferred Ideas

- Media handlers (AddProductMedia, DeleteProductMedia, UpdateProductMedia, ReorderProductMedia) — Phase 6 scope (CMD-07)
- SKU handlers (add_sku, update_sku, remove_sku, generate_sku_matrix) — Phase 6 scope (CMD-06)
- Shared ISupplierQueryService fake — could be built if multiple phases need it, but per-test inline mocks work for now

</deferred>

---

*Phase: 05-product-variant-command-handlers*
*Context gathered: 2026-03-28*
