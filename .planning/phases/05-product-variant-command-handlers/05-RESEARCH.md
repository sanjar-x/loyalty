# Phase 5: Product & Variant Command Handlers - Research

**Researched:** 2026-03-28
**Status:** Complete

## Objective

Research what is needed to plan Phase 5: Unit tests for all Product and Variant command handlers, proving they orchestrate correctly with repositories, UoW, and cross-module dependencies.

## Handler Inventory

### Product Command Handlers (CMD-04)

| Handler | File | Dependencies | Key Behaviors |
|---------|------|-------------|---------------|
| CreateProductHandler | `create_product.py` | product_repo, brand_repo, category_repo, supplier_query_service, media_repo, uow, logger | FK validation (brand, category), supplier active check, cross-border source_url check, slug uniqueness, Product.create(), media attachment, register_aggregate, commit |
| UpdateProductHandler | `update_product.py` | product_repo, brand_repo, category_repo, media_repo, image_backend, uow, logger | get_for_update_with_variants, optimistic locking (version check), FK validation for changed fields, slug uniqueness excluding self, _provided_fields filtering, Product.update(), media diff (compute_media_diff), register_aggregate, commit, best-effort image backend cleanup |
| DeleteProductHandler | `delete_product.py` | product_repo, uow, logger | get_for_update_with_variants, product.soft_delete(), update, register_aggregate, commit |
| ChangeProductStatusHandler | `change_product_status.py` | product_repo, media_repo, uow, logger | get_for_update_with_variants, PUBLISHED requires media check (ProductNotReadyError), product.transition_status(), update, register_aggregate, commit |
| AssignProductAttributeHandler | `assign_product_attribute.py` | product_repo, pav_repo, attribute_repo, attribute_value_repo, category_repo, template_repo, template_binding_repo, uow, logger | Template governance chain (resolve_effective_attribute_ids), attribute exists + is_dictionary + PRODUCT level, value exists + belongs to attribute, duplicate assignment check, ProductAttributeValue.create(), commit |
| BulkAssignProductAttributesHandler | `bulk_assign_product_attributes.py` | (same as above) | >100 items limit, batch-within-batch duplicate check, batch-prefetch attrs/values (get_many), bulk-check existing assignments, same validation per item as single assign, atomic all-or-nothing |
| DeleteProductAttributeHandler | `delete_product_attribute.py` | pav_repo, uow, logger | get_by_product_and_attribute, delete by PAV id, commit |

### Variant Command Handlers (CMD-05)

| Handler | File | Dependencies | Key Behaviors |
|---------|------|-------------|---------------|
| AddVariantHandler | `add_variant.py` | product_repo, uow, logger | get_for_update_with_variants, Money construction from amount+currency, product.add_variant(), update, register_aggregate, commit |
| UpdateVariantHandler | `update_variant.py` | product_repo, uow, logger | get_for_update_with_variants, product.find_variant(), _provided_fields filtering, currency validation (3 uppercase ASCII), Money construction, variant.update(), update product, register_aggregate, commit |
| DeleteVariantHandler | `delete_variant.py` | product_repo, uow, logger | get_for_update_with_variants, product.remove_variant() (raises VariantNotFoundError, LastVariantRemovalError), update, register_aggregate, commit |

## Test Infrastructure Assessment

### Available Fakes (from Phase 1)
- **FakeUnitOfWork**: Full implementation with all 10 catalog repos. Tracks committed, rolled_back, collected_events. De-duplicates aggregates.
- **FakeProductRepository**: Full CRUD + check_slug_exists, check_slug_exists_excluding, get_for_update_with_variants, get_with_variants, check_sku_code_exists.
- **FakeProductAttributeValueRepository**: add, get, delete, list_by_product, get_by_product_and_attribute, check_assignment_exists, check_assignments_exist_bulk.
- **FakeMediaAssetRepository**: add, get, get_for_update, update, delete, list_by_product, list_by_storage_ids, delete_by_product. Note: bulk_update_sort_order and check_main_exists raise NotImplementedError (Phase 6).
- **FakeBrandRepository**: Full implementation including has_products.
- **FakeCategoryRepository**: Full implementation including has_products, has_children.
- **FakeAttributeRepository**: Full implementation including get_many.
- **FakeAttributeValueRepository**: Full implementation including get_many.
- **FakeTemplateAttributeBindingRepository**: check_binding_exists, list_ids_by_template, has_bindings_for_attribute. **ISSUE**: `get_bindings_for_templates()` raises NotImplementedError -- needed by `resolve_effective_attribute_ids()` which is called by both AssignProductAttributeHandler and BulkAssignProductAttributesHandler. Must implement this before tests.

### Available Builders (from Phase 1)
- **ProductBuilder**: Fluent builder via Product.create(). Auto-creates default variant.
- **ProductVariantBuilder**: Standalone variant via ProductVariant.create(). NOT added to a product aggregate -- for standalone tests only.
- **BrandBuilder, CategoryBuilder, AttributeBuilder, etc.**: Available in `backend/tests/factories/`.

### Missing Infrastructure (must be added in Phase 5 plans)
1. **FakeTemplateAttributeBindingRepository.get_bindings_for_templates()**: Currently raises NotImplementedError. Required by resolve_effective_attribute_ids() used in attribute assignment handlers. Must return `dict[UUID, list[TemplateAttributeBinding]]` scanning the internal store.
2. **No existing handler test pattern in codebase**: The CONTEXT.md references `test_brand_handlers.py` as a Phase 4 reference, but it does not exist yet (Phase 4 has not been executed). Tests must be written from scratch following the established project patterns.

## Cross-Module Dependencies

### ISupplierQueryService (CreateProductHandler only)
- Interface: `assert_supplier_active(supplier_id: UUID) -> SupplierInfo`
- SupplierInfo dataclass: `id, name, type: SupplierType, is_active: bool`
- SupplierType enum: `CROSS_BORDER = "cross_border"`, `LOCAL = "local"`
- Exceptions: `SupplierInactiveError(supplier_id)`, `SourceUrlRequiredError()`
- **Mock strategy (D-06)**: Per-test inline AsyncMock. Three paths: (1) supplier_id=None (skip), (2) active local supplier, (3) active cross-border supplier without source_url.

### IImageBackendClient (UpdateProductHandler only)
- Interface: `delete(storage_object_id: UUID) -> None`
- Called AFTER commit for best-effort cleanup of deleted media storage objects.
- **Mock strategy (D-09)**: Per-test inline AsyncMock.

### resolve_effective_attribute_ids (AssignProductAttribute, BulkAssignProductAttributes)
- Calls `binding_repo.get_bindings_for_templates([template_id])` -- hits the fake repo.
- Returns `set[UUID]` of attribute IDs bound to the template.
- The fake implementation needs to scan `_store` and group by `template_id`.

## Key Test Scenarios

### CreateProductHandler
1. Happy path: brand exists, category exists, no supplier, slug unique -> product created, committed, events collected
2. Happy path with local supplier: supplier active, type=LOCAL -> success
3. Happy path with cross-border supplier + source_url -> success
4. Error: brand not found -> BrandNotFoundError, not committed
5. Error: category not found -> CategoryNotFoundError, not committed
6. Error: slug conflict -> ProductSlugConflictError, not committed
7. Error: inactive supplier -> SupplierInactiveError (raised by mock), not committed
8. Error: cross-border supplier without source_url -> SourceUrlRequiredError, not committed

### UpdateProductHandler
1. Happy path: product exists, update title -> committed
2. Happy path with slug change (no conflict) -> committed
3. Error: product not found -> ProductNotFoundError
4. Error: version mismatch -> ConcurrencyError
5. Error: slug conflict -> ProductSlugConflictError
6. Error: brand_id in provided_fields but brand not found -> BrandNotFoundError
7. Error: brand_id=None in provided_fields -> UnprocessableEntityError
8. _provided_fields filtering: only safe_fields passed to entity.update()

### DeleteProductHandler
1. Happy path: product exists -> soft_delete called, committed
2. Error: product not found -> ProductNotFoundError, not committed

### ChangeProductStatusHandler
1. Happy path: valid transition (draft -> published with media) -> committed
2. Error: product not found -> ProductNotFoundError
3. Error: publish without media -> ProductNotReadyError
4. Error: invalid FSM transition -> InvalidStatusTransitionError (from domain)

### AssignProductAttributeHandler
1. Happy path: all validations pass, attribute assigned
2. Error: product not found -> ProductNotFoundError
3. Error: attribute not in template -> AttributeNotInTemplateError
4. Error: attribute not found -> AttributeNotFoundError
5. Error: attribute wrong level (VARIANT instead of PRODUCT) -> AttributeLevelMismatchError
6. Error: attribute not dictionary -> AttributeNotDictionaryError
7. Error: attribute value not found -> AttributeValueNotFoundError
8. Error: value belongs to different attribute -> AttributeValueNotFoundError
9. Error: duplicate assignment -> DuplicateProductAttributeError
10. Edge: category has no template (effective_template_id=None) -> template check skipped

### BulkAssignProductAttributesHandler
1. Happy path: multiple items assigned atomically
2. Error: >100 items -> ValueError
3. Error: duplicate within batch -> DuplicateProductAttributeError
4. Error: any single item validation failure -> entire batch rejected
5. All single-assign errors also apply per-item

### DeleteProductAttributeHandler
1. Happy path: assignment exists, deleted
2. Error: assignment not found -> ProductAttributeValueNotFoundError

### AddVariantHandler
1. Happy path: product exists, variant added with name_i18n
2. Happy path with price: Money constructed from amount+currency
3. Happy path without price: default_price=None
4. Error: product not found -> ProductNotFoundError

### UpdateVariantHandler
1. Happy path: variant found, fields updated
2. Error: product not found -> ProductNotFoundError
3. Error: variant not found -> VariantNotFoundError
4. Error: invalid currency format -> ValueError
5. _provided_fields filtering: only provided fields passed

### DeleteVariantHandler
1. Happy path: variant deleted
2. Error: product not found -> ProductNotFoundError
3. Error: variant not found -> VariantNotFoundError (from domain)
4. Error: last variant -> LastVariantRemovalError (from domain)

## Validation Architecture

### Test File Organization
Per CONTEXT.md D-12: Two test files under `backend/tests/unit/modules/catalog/application/commands/`:
- `test_product_handlers.py` — 7 handler test classes
- `test_variant_handlers.py` — 3 handler test classes

### Test Pattern
Each test class:
1. Creates FakeUoW in setup
2. Seeds required entities via builder pattern (or direct entity creation)
3. Creates handler with FakeUoW repos + AsyncMock for external deps
4. Calls handler.handle(command)
5. Asserts: return value, entity state in fake repo, uow.committed, uow.collected_events

### Boundary Definition
- Domain entity behavior (Product.create, Product.transition_status, etc.) is NOT re-tested here -- that's Phases 2-3
- Repository correctness against real DB is NOT tested here -- that's Phase 7
- Media handling complexity (compute_media_diff) in UpdateProductHandler is Phase 6 scope (CMD-07), but basic media attachment in CreateProductHandler is in scope since it's part of the create flow

## Risks & Mitigations

1. **FakeTemplateAttributeBindingRepository.get_bindings_for_templates() NotImplementedError**: Must be implemented before attribute assignment handler tests can run. Mitigation: Add implementation in Plan 01 as prerequisite task.

2. **resolve_effective_attribute_ids calls into binding_repo**: This function is a shared query helper that the fake must support. Since it just calls `get_bindings_for_templates` and extracts attribute IDs, the fix is straightforward once the fake method is implemented.

3. **UpdateProductHandler media diff complexity**: The handler imports `compute_media_diff` from `sync_media.py`. Testing media update scenarios is Phase 6 scope. Phase 5 tests should focus on the non-media update paths (title, slug, brand_id, etc.) and either skip media or provide minimal media=None cases.

4. **Missing commands/ subdirectory**: `backend/tests/unit/modules/catalog/application/commands/` does not exist yet. Must create it with `__init__.py`.

---

## RESEARCH COMPLETE

All handler signatures, dependencies, error paths, and test infrastructure assessed. Ready for planning.
