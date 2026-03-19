# Code Review -- MT-2: Add Product and SKU domain entities

> **Reviewer:** senior-reviewer (9/10)
> **Plan:** arch/MT-2-plan.md
> **Verdict:** APPROVED

---

## Summary

The implementation is high-quality and closely follows the architect's plan. Product is correctly modeled as an AggregateRoot with FSM transition table, SKU is a plain child entity with compare_at_price validation. Domain purity is maintained (only stdlib + attrs imports). Three minor linting issues were fixed by the reviewer.

## Plan compliance

The implementation matches the architect's plan in all material aspects:

- **SKU class**: All fields match the plan (id, product_id, sku_code, variant_hash, price, compare_at_price, is_active, version, deleted_at, created_at, updated_at, variant_attributes). Field order and types match exactly.
- **Product class**: All fields match the plan. `_ALLOWED_TRANSITIONS` is correctly annotated as `ClassVar`. FSM table matches the specified transitions.
- **Factory method**: `Product.create()` correctly sets status=DRAFT, version=1, skus=[].
- **`_compute_variant_hash`**: Static method using sorted attribute pairs and SHA-256, matching the plan.
- **Sentinel pattern**: Backend used a module-level `_SENTINEL = object()` instead of inline `...` (Ellipsis) for nullable field sentinels in `update()` methods. This is an acceptable deviation -- it is clearer and avoids `# type: ignore[assignment]` on default parameters (the existing code already uses `...` sentinel in other entities, but the `_SENTINEL` approach is equally valid and arguably more readable).
- **Imports**: Match the plan exactly (hashlib, uuid, datetime/UTC, ClassVar, attr.dataclass/field, Money, ProductStatus, AggregateRoot).
- **File placement**: SKU placed before Product as specified.
- **Deferred imports**: Exception imports use deferred pattern with `# type: ignore[attr-defined]` as recommended by the plan.

## Findings

### Critical

None.

### Major

None.

### Minor

- `src/modules/catalog/domain/entities.py` lines 898-900: Nested `if` statements for compare_at_price validation in `SKU.__attrs_post_init__` triggered ruff SIM102.
  **Fixed:** Combined into single `if` with `and`.

- `src/modules/catalog/domain/entities.py` lines 966-968: Same nested `if` pattern in `SKU.update()` re-validation.
  **Fixed:** Combined into single `if` with `and`.

- `src/modules/catalog/domain/entities.py` lines 1181, 1228, 1278: Deferred exception imports with `# type: ignore[attr-defined]` triggered ruff I001 (import sorting). Ruff auto-fix reformatted them into multi-line imports which broke mypy suppression.
  **Fixed:** Added `# noqa: I001` after `# type: ignore[attr-defined]` to suppress ruff while preserving mypy suppression.

### Suggestions

- The `_SENTINEL` pattern for distinguishing "not provided" from None is clean but creates a module-level object. Consider documenting it with a brief note about its purpose for future developers. (Already has a docstring -- adequate.)

## Acceptance criteria verification

- [x] Product is an attrs dataclass extending AggregateRoot -- MET
- [x] Product has all specified fields (id, slug, title_i18n, description_i18n, status, brand_id, primary_category_id, supplier_id, country_of_origin, tags, version, deleted_at, created_at, updated_at, published_at, skus) -- MET
- [x] Product.create() factory sets status=DRAFT, version=1, empty skus list -- MET
- [x] Product.update() allows updating title_i18n, description_i18n, slug, brand_id, primary_category_id, supplier_id, country_of_origin, tags -- MET
- [x] Product.soft_delete() sets deleted_at timestamp -- MET
- [x] Product has FSM: transition_status validates allowed transitions per table (Draft->Enriching, Enriching->Draft/ReadyForReview, ReadyForReview->Enriching/Published, Published->Archived, Archived->Draft). Sets published_at on transition to PUBLISHED -- MET
- [x] Product.add_sku() creates SKU child, computes variant_hash via SHA-256, checks uniqueness, raises DuplicateVariantCombinationError on collision -- MET
- [x] SKU is an attrs dataclass (not AggregateRoot) with all specified fields -- MET
- [x] SKU validates compare_at_price > price when both are set -- MET
- [x] All existing tests pass -- MET (504 passed)
- [x] Linter/type-checker passes -- MET

## Post-fix checks

| Check            | Result            |
| ---------------- | ----------------- |
| ruff             | PASS              |
| mypy             | PASS              |
| pytest unit+arch | PASS (504 passed) |

## Verdict

**APPROVED** -- all Minor issues fixed, no Critical or Major findings. Checks pass, ready for QA.
