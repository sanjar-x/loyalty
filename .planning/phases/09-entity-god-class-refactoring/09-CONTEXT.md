# Phase 9: Entity God-Class Refactoring - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Split the 2,220-line `backend/src/modules/catalog/domain/entities.py` into separate files per entity/aggregate under an `entities/` package directory, with an `__init__.py` that re-exports every public name. Zero import breakage — all 68 existing import sites must continue working unchanged. This phase is pure structural refactoring — no behavior changes.

</domain>

<decisions>
## Implementation Decisions

### File Split Strategy
- **D-01:** Create `backend/src/modules/catalog/domain/entities/` package directory. Move each entity class to its own file: `brand.py`, `category.py`, `product.py`, `product_variant.py`, `sku.py`, `attribute.py`, `attribute_template.py`, `template_attribute_binding.py`, `attribute_group.py`, `product_attribute_value.py`, `media_asset.py`.
- **D-02:** Shared helpers (_validate_slug, _generate_id, _validate_sort_order, _validate_i18n_values, _validate_filter_settings, guarded field sets, GENERAL_GROUP_CODE) go in `entities/_helpers.py` or `entities/_common.py`.
- **D-03:** `entities/__init__.py` re-exports EVERY public name from the original file so that `from src.modules.catalog.domain.entities import Brand` continues working across all 68 import sites.

### Safety Net
- **D-04:** Run the full test suite (all tests from Phases 1-8) before AND after the split. Zero test failures is the success criterion.
- **D-05:** Use `git diff --stat` after the split to verify the original `entities.py` is deleted and replaced by the `entities/` package.

### Import Handling
- **D-06:** Internal cross-entity imports within the package (e.g., Product importing ProductVariant, SKU) use relative imports: `from .product_variant import ProductVariant`.
- **D-07:** No circular import risk: entity dependency graph is acyclic (Product → ProductVariant → SKU, Category standalone, Brand standalone, Attribute → AttributeValue).

### Claude's Discretion
- Exact file names for helper modules
- Whether to keep _GUARDED_FIELDS sets in each entity file or centralize
- Import ordering within __init__.py
- Whether to add module-level docstrings to each new file

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source file (what to split)
- `backend/src/modules/catalog/domain/entities.py` — The 2,220-line god-class with 9+ entity/aggregate classes

### All import sites (must not break)
- 68 files import from `src.modules.catalog.domain.entities` — run `grep -r "from src.modules.catalog.domain.entities import" backend/` to get the full list
- Key importers: all command handlers, all repositories, all test files, domain interfaces

### Test suite (safety net)
- `backend/tests/` — Full test suite must pass before and after split
- Phase 2 tests: `backend/tests/unit/modules/catalog/domain/test_*.py` — Domain entity tests
- Phase 3 tests: `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py` — Aggregate behavior tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Entity Dependency Graph (no cycles)
- Brand: standalone (no entity imports)
- Category: standalone (no entity imports)
- AttributeGroup: standalone
- AttributeTemplate: standalone
- TemplateAttributeBinding: standalone
- Attribute: standalone (has AttributeValue as inner entity)
- ProductAttributeValue: standalone
- MediaAsset: standalone
- SKU: standalone (uses Money value object)
- ProductVariant: imports SKU (child entity)
- Product: imports ProductVariant, SKU (aggregate root)

### Shared Helpers
- `_validate_slug()`, `_generate_id()`, `_validate_sort_order()`, `_validate_i18n_values()`, `_validate_filter_settings()`
- Guarded field sets: `_PRODUCT_GUARDED_FIELDS`, `_BRAND_GUARDED_FIELDS`, etc.
- `GENERAL_GROUP_CODE` constant

### Integration Points
- Delete `entities.py`, create `entities/` package
- `entities/__init__.py` must re-export all public names
- No changes needed in any importing file

</code_context>

<specifics>
## Specific Ideas

No specific requirements — straightforward structural refactoring. The 400+ tests from Phases 2-8 serve as the safety net.

</specifics>

<deferred>
## Deferred Ideas

None — this is the final phase of the milestone.

</deferred>

---

*Phase: 09-entity-god-class-refactoring*
*Context gathered: 2026-03-28*
