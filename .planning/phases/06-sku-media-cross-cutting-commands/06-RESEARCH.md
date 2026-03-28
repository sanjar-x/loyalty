# Phase 6: SKU, Media & Cross-Cutting Commands - Research

**Researched:** 2026-03-28
**Status:** Complete

## Objective

Research what is needed to plan Phase 6: Unit tests for all SKU and Media command handlers, plus a systematic cross-cutting audit of domain event emission, bulk operation atomicity, and FK/uniqueness error paths across ALL catalog command handlers.

## Handler Inventory

### SKU Command Handlers (CMD-06)

| Handler | File | Dependencies | Key Behaviors |
|---------|------|-------------|---------------|
| AddSKUHandler | `add_sku.py` | product_repo, uow, logger | get_for_update_with_variants, check_sku_code_exists, Money.from_primitives, product.add_sku() (computes variant_hash, checks uniqueness, emits SKUAddedEvent), update, register_aggregate, commit |
| UpdateSKUHandler | `update_sku.py` | product_repo, uow, logger | get_for_update_with_variants, product.find_sku(), optimistic locking (version check), check_sku_code_exists (excluding self), Money construction, variant attribute re-hash + uniqueness check, sku.update(), update product, register_aggregate, commit |
| DeleteSKUHandler | `delete_sku.py` | product_repo, uow, logger | get_for_update_with_variants, product.remove_sku() (soft-deletes, emits SKUDeletedEvent), update, register_aggregate, commit |
| GenerateSKUMatrixHandler | `generate_sku_matrix.py` | product_repo, attribute_repo, attribute_value_repo, category_repo, template_repo, template_binding_repo, uow, logger | get_for_update_with_variants, _validate_selections (attribute level, values, template membership), Money.from_primitives, _build_combinations (cartesian product), MAX_SKU_COMBINATIONS=1000 check, auto-generate sku_code from slug+index, DuplicateVariantCombinationError catch → skip, atomic batch update + commit |

### Media Command Handlers (CMD-07)

| Handler | File | Dependencies | Key Behaviors |
|---------|------|-------------|---------------|
| AddProductMediaHandler | `add_product_media.py` | product_repo, media_repo, uow, logger | get_with_variants, validate product exists, validate variant belongs to product (if provided), check MAIN uniqueness via media_repo.check_main_exists, MediaAsset.create(), media_repo.add, commit |
| UpdateProductMediaHandler | `update_product_media.py` | product_repo, media_repo, uow, logger | get_for_update, ownership check (product_id match), variant validation (if changing), MAIN uniqueness check (if changing role to MAIN), _provided_fields filtering for variant_id/role/sort_order, update, commit |
| DeleteProductMediaHandler | `delete_product_media.py` | media_repo, uow, image_backend, logger | get_for_update, ownership check (product_id match), media_repo.delete, commit, THEN best-effort image_backend.delete (after commit) |
| ReorderProductMediaHandler | `reorder_product_media.py` | media_repo, uow, logger | bulk_update_sort_order, count check (updated < expected → MediaAssetNotFoundError), commit |

### Bulk Handlers (CMD-09 atomicity)

| Handler | File | Key Behaviors |
|---------|------|---------------|
| BulkCreateBrandsHandler | `bulk_create_brands.py` | Iterates items, checks slug/name uniqueness, creates Brand + BrandCreatedEvent, all within single UoW. In strict mode, first conflict aborts everything. |
| BulkCreateCategoriesHandler | `bulk_create_categories.py` | Intra-batch parent resolution (ref/parent_ref), slug uniqueness per level, creates Category + CategoryCreatedEvent, single UoW. Also depends on ICacheService. |
| BulkCreateAttributesHandler | `bulk_create_attributes.py` | Code/slug uniqueness, group_id FK validation, creates Attribute + AttributeCreatedEvent, single UoW. |
| BulkAddAttributeValuesHandler | `bulk_add_attribute_values.py` | Attribute must be dictionary type, batch code/slug uniqueness, creates AttributeValue + AttributeValueAddedEvent, single UoW. Also depends on ICacheService. |
| GenerateSKUMatrixHandler | `generate_sku_matrix.py` | (See SKU handlers above) Cartesian product of attribute selections, auto-generates SKU codes, skips duplicate combinations, single UoW. |

## Test Infrastructure Assessment

### Available Fakes (from Phases 1, 4, 5)

- **FakeUnitOfWork**: Full implementation with all 10 catalog repos. Tracks committed, rolled_back, collected_events.
- **FakeProductRepository**: Full CRUD + check_slug_exists, get_for_update_with_variants, get_with_variants, check_sku_code_exists (scans nested variants→SKUs).
- **FakeMediaAssetRepository**: add, get, get_for_update, update, delete, list_by_product, list_by_storage_ids, delete_by_product. **Two stubs still raise NotImplementedError:**
  1. `bulk_update_sort_order()` — needed by ReorderProductMediaHandler
  2. `check_main_exists()` — needed by AddProductMediaHandler and UpdateProductMediaHandler
- **FakeAttributeRepository**: Full implementation including get_many.
- **FakeAttributeValueRepository**: Full implementation including get_many.
- **FakeCategoryRepository**: Full implementation.
- **FakeTemplateAttributeBindingRepository**: Depends on Phase 4/5 execution status. `get_bindings_for_templates()` may or may not be implemented.

### Fake Methods That MUST Be Implemented (Phase 6 Plan Wave 0)

1. **FakeMediaAssetRepository.bulk_update_sort_order(product_id, updates) -> int**: Scan `_store.values()`. For each `(media_id, sort_order)` in updates, if media exists and `media.product_id == product_id`, update `media.sort_order` (via `object.__setattr__`). Return count of updated records.

2. **FakeMediaAssetRepository.check_main_exists(product_id, variant_id, exclude_media_id=None) -> bool**: Scan `_store.values()`. Return True if any media has `media.product_id == product_id` and `media.variant_id == variant_id` and `media.role == MediaRole.MAIN` and (exclude_media_id is None or `media.id != exclude_media_id`).

3. **FakeTemplateAttributeBindingRepository.get_bindings_for_templates()**: If still NotImplementedError from Phase 4/5, must be implemented for GenerateSKUMatrixHandler's `_validate_selections()` which calls `resolve_effective_attribute_ids()`.

### Available Builders (from Phase 1)

- **ProductBuilder**: Fluent builder via Product.create(). Auto-creates default variant.
- **BrandBuilder, CategoryBuilder, AttributeBuilder**: All available in `backend/tests/factories/`.

## Domain Event Emission Audit (CMD-08)

### Events Emitted by Domain Entities (not handlers)

These events are emitted inside entity methods called by handlers:
- `Product.create()` → ProductCreatedEvent
- `Product.transition_status()` → ProductStatusChangedEvent
- `Product.update()` → ProductUpdatedEvent
- `Product.soft_delete()` → ProductDeletedEvent
- `Product.add_variant()` → VariantAddedEvent
- `Product.remove_variant()` → VariantDeletedEvent
- `Product.add_sku()` → SKUAddedEvent
- `Product.remove_sku()` → SKUDeletedEvent

### Events Emitted Explicitly by Handlers

These events are added by handler code (not entity methods):
- CreateBrandHandler → BrandCreatedEvent
- UpdateBrandHandler → BrandUpdatedEvent
- DeleteBrandHandler → BrandDeletedEvent
- BulkCreateBrandsHandler → BrandCreatedEvent (per item)
- CreateCategoryHandler → CategoryCreatedEvent
- UpdateCategoryHandler → CategoryUpdatedEvent
- DeleteCategoryHandler → CategoryDeletedEvent
- BulkCreateCategoriesHandler → CategoryCreatedEvent (per item)
- CreateAttributeHandler → AttributeCreatedEvent
- UpdateAttributeHandler → AttributeUpdatedEvent
- DeleteAttributeHandler → AttributeDeletedEvent
- BulkCreateAttributesHandler → AttributeCreatedEvent (per item)
- CreateAttributeTemplateHandler → AttributeTemplateCreatedEvent
- UpdateAttributeTemplateHandler → AttributeTemplateUpdatedEvent
- DeleteAttributeTemplateHandler → AttributeTemplateDeletedEvent
- BindAttributeToTemplateHandler → TemplateAttributeBindingCreatedEvent
- UpdateTemplateAttributeBindingHandler → TemplateAttributeBindingUpdatedEvent
- UnbindAttributeFromTemplateHandler → TemplateAttributeBindingDeletedEvent
- AddAttributeValueHandler → AttributeValueAddedEvent
- UpdateAttributeValueHandler → AttributeValueUpdatedEvent
- DeleteAttributeValueHandler → AttributeValueDeletedEvent
- ReorderAttributeValuesHandler → AttributeValuesReorderedEvent
- BulkAddAttributeValuesHandler → AttributeValueAddedEvent (per item)

### Handlers That Do NOT Emit Events

- AddSKUHandler — delegates to product.add_sku() which emits SKUAddedEvent (entity-level)
- UpdateSKUHandler — no events (docstring says "deferred to P2")
- DeleteSKUHandler — delegates to product.remove_sku() which emits SKUDeletedEvent (entity-level)
- GenerateSKUMatrixHandler — delegates to product.add_sku() per combination (entity-level SKUAddedEvent)
- AddProductMediaHandler — no events (MediaAsset has no AggregateRoot)
- UpdateProductMediaHandler — no events
- DeleteProductMediaHandler — no events
- ReorderProductMediaHandler — no events
- AssignProductAttributeHandler — no events
- BulkAssignProductAttributesHandler — no events
- DeleteProductAttributeHandler — no events
- ReorderTemplateBindingsHandler — no events
- SetAttributeValueActiveHandler — no events
- CloneAttributeTemplateHandler — AttributeTemplateCreatedEvent + TemplateAttributeBindingCreatedEvent (per binding)
- ChangeProductStatusHandler — delegates to product.transition_status() (entity-level)
- AddVariantHandler — delegates to product.add_variant() (entity-level)
- UpdateVariantHandler — no events (docstring says "deferred")
- DeleteVariantHandler — delegates to product.remove_variant() (entity-level)

### Phase 6 Event Audit Coverage Strategy (D-07, D-08)

Phase 4 will test event emission for: Brand handlers (4), Category handlers (3-4), Attribute handlers (7-8), Template handlers (3), Binding handlers (3).
Phase 5 will test event emission for: Product handlers (CreateProduct, ChangeProductStatus, DeleteProduct - entity events), Variant handlers (AddVariant, DeleteVariant - entity events).

**Phase 6 GAP tests** (handlers NOT already covered by Phase 4/5 event testing):
1. AddSKUHandler → verify SKUAddedEvent emitted via product.add_sku()
2. DeleteSKUHandler → verify SKUDeletedEvent emitted via product.remove_sku()
3. GenerateSKUMatrixHandler → verify N SKUAddedEvents emitted (one per created SKU)
4. BulkCreateBrandsHandler → verify N BrandCreatedEvents emitted (if not covered in Phase 4 bulk test)
5. BulkCreateCategoriesHandler → verify N CategoryCreatedEvents (if not covered in Phase 4)
6. BulkCreateAttributesHandler → verify N AttributeCreatedEvents (if not covered in Phase 4)
7. BulkAddAttributeValuesHandler → verify N AttributeValueAddedEvents (if not covered in Phase 4)

The test should collect events via `uow.collected_events` (post-commit) and verify count and type.

## FK/Uniqueness Error Paths (CMD-10)

### Cross-Entity FK Paths

| Path | Handler | Exception |
|------|---------|-----------|
| product→brand (missing brand_id) | CreateProductHandler | BrandNotFoundError |
| product→category (missing category_id) | CreateProductHandler | CategoryNotFoundError |
| SKU→product (missing product_id) | AddSKUHandler | ProductNotFoundError |
| SKU→variant (missing variant_id) | AddSKUHandler → product.add_sku() | VariantNotFoundError |
| media→product (missing product_id) | AddProductMediaHandler | ProductNotFoundError |
| media→variant (missing variant_id) | AddProductMediaHandler | VariantNotFoundError |
| attribute→group (missing group_id) | BulkCreateAttributesHandler | AttributeGroupNotFoundError |
| category→template (missing template_id) | BulkCreateCategoriesHandler | AttributeTemplateNotFoundError |
| category→parent (missing parent_id) | CreateCategoryHandler | CategoryNotFoundError |

### Uniqueness Conflict Paths

| Conflict | Handler | Exception |
|----------|---------|-----------|
| brand slug | CreateBrandHandler | BrandSlugConflictError |
| brand name | CreateBrandHandler | BrandNameConflictError |
| category slug (at level) | CreateCategoryHandler | CategorySlugConflictError |
| product slug | CreateProductHandler | ProductSlugConflictError |
| SKU code | AddSKUHandler | SKUCodeConflictError |
| variant hash | AddSKUHandler → product.add_sku() | DuplicateVariantCombinationError |
| attribute code | CreateAttributeHandler | AttributeCodeConflictError |
| attribute slug | CreateAttributeHandler | AttributeSlugConflictError |
| template code | CreateAttributeTemplateHandler | AttributeTemplateCodeConflictError |
| MAIN media uniqueness | AddProductMediaHandler | DuplicateMainMediaError |

### Phase 6 FK/Uniqueness Test Strategy (D-13, D-14, D-15)

Test a **representative sample** across handler domains (2-3 per domain):

**SKU domain:**
- AddSKUHandler: ProductNotFoundError (FK), SKUCodeConflictError (uniqueness), DuplicateVariantCombinationError via product.add_sku() (uniqueness)
- UpdateSKUHandler: ProductNotFoundError, SKUNotFoundError, ConcurrencyError, SKUCodeConflictError

**Media domain:**
- AddProductMediaHandler: ProductNotFoundError, VariantNotFoundError, DuplicateMainMediaError
- DeleteProductMediaHandler: MediaAssetNotFoundError, MediaAssetNotFoundError (ownership mismatch)
- UpdateProductMediaHandler: MediaAssetNotFoundError, DuplicateMainMediaError (role change)
- ReorderProductMediaHandler: MediaAssetNotFoundError (partial match)

**Cross-entity (from other domains, spot-check):**
- GenerateSKUMatrixHandler: ProductNotFoundError, AttributeNotFoundError, AttributeValueNotFoundError, AttributeLevelMismatchError, AttributeNotInTemplateError

## Bulk Atomicity Testing (CMD-09)

### Test Pattern (D-12)

Seed a scenario where the Nth item in the bulk operation fails, then verify ZERO items from the batch were persisted.

**GenerateSKUMatrixHandler atomicity** (D-10):
- This handler does NOT explicitly roll back on partial failure. It catches DuplicateVariantCombinationError per combo and skips. Other errors (e.g., from _validate_selections) raise and the UoW context manager triggers rollback.
- Test scenario: Invalid attribute (e.g., non-VARIANT level) should cause _validate_selections to raise BEFORE any SKUs are created, so the entire UoW rolls back.
- Note: GenerateSKUMatrixHandler catches DuplicateVariantCombinationError at the per-combo level. This is intentional (skipping duplicates). The atomicity concern is about NON-skippable errors causing full rollback.

**BulkCreateBrandsHandler atomicity** (D-11):
- Strict mode (skip_existing=False): If the 3rd of 5 brands has a slug conflict, the exception propagates from within the UoW context, triggering rollback. Zero brands from the batch should be in the fake store.
- Test: Pre-seed a brand with slug "conflict". Submit batch of 3 where the 2nd has slug "conflict". Verify BrandSlugConflictError raised. Verify `uow.brands.items` contains only the pre-seeded brand (no new brands).

**BulkCreateCategoriesHandler and BulkCreateAttributesHandler** — same pattern if Phase 4 did not cover it.

## Key Implementation Decisions

### Mock Strategy

- **FakeUoW** for ALL handlers (consistent with Phases 4-5)
- **Per-test inline AsyncMock** for: ILogger (via make_logger()), IImageBackendClient (DeleteProductMediaHandler only)
- **Repositories from FakeUoW**: `uow.products`, `uow.brands`, `uow.categories`, `uow.attributes`, `uow.attribute_values`, `uow.attribute_templates`, `uow.template_bindings`, `uow.media_assets`

### Test File Organization (D-19, D-20, D-21)

1. `test_sku_handlers.py`: TestAddSKU, TestUpdateSKU, TestDeleteSKU, TestGenerateSKUMatrix
2. `test_media_handlers.py`: TestAddProductMedia, TestUpdateProductMedia, TestDeleteProductMedia, TestReorderProductMedia
3. `test_cross_cutting.py`: TestEventAuditGaps, TestBulkAtomicity, TestFKUniquenessErrors

### Dependency Wiring for GenerateSKUMatrixHandler

This handler has 8 constructor dependencies:
```python
GenerateSKUMatrixHandler(
    product_repo=uow.products,
    attribute_repo=uow.attributes,
    attribute_value_repo=uow.attribute_values,
    category_repo=uow.categories,
    template_repo=uow.attribute_templates,
    template_binding_repo=uow.template_bindings,
    uow=uow,
    logger=make_logger(),
)
```

### Dependency for ReorderProductMediaHandler

Uses `media_repo.bulk_update_sort_order()` which currently raises NotImplementedError. Must implement in FakeMediaAssetRepository first.

## Validation Architecture

### Per-Requirement Test Map

| Requirement | Test File | Test Classes | Key Scenarios |
|-------------|-----------|-------------|---------------|
| CMD-06 | test_sku_handlers.py | TestAddSKU, TestUpdateSKU, TestDeleteSKU, TestGenerateSKUMatrix | Happy paths + SKU code conflict + variant hash collision + matrix generation + empty selections |
| CMD-07 | test_media_handlers.py | TestAddProductMedia, TestUpdateProductMedia, TestDeleteProductMedia, TestReorderProductMedia | Happy paths + MAIN uniqueness + variant validation + image_backend cleanup + ownership check |
| CMD-08 | test_cross_cutting.py | TestEventAuditGaps | SKUAddedEvent, SKUDeletedEvent, bulk event counts for brands/categories/attributes |
| CMD-09 | test_cross_cutting.py | TestBulkAtomicity | generate_sku_matrix validation failure → rollback, bulk_create_brands strict conflict → rollback |
| CMD-10 | test_cross_cutting.py | TestFKUniquenessErrors | Representative FK (ProductNotFound, VariantNotFound, AttributeNotFound) + uniqueness (SKUCodeConflict, DuplicateMainMedia) across handler domains |

### Test Infrastructure Requirements

| Item | Status | Action |
|------|--------|--------|
| FakeMediaAssetRepository.bulk_update_sort_order | NotImplementedError | Must implement |
| FakeMediaAssetRepository.check_main_exists | NotImplementedError | Must implement |
| FakeTemplateAttributeBindingRepository.get_bindings_for_templates | May be NotImplementedError | Check; implement if needed |
| ProductBuilder | Available | Use for product setup |
| FakeUnitOfWork | Available | Standard pattern |

## RESEARCH COMPLETE
