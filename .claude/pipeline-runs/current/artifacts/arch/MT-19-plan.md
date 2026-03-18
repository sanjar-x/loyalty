# Architecture Plan -- MT-19: Add Product Pydantic schemas

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-19 | **Layer:** Presentation | **Module:** catalog | **FR:** FR-001 through FR-006
> **Depends on:** MT-6

## Research findings

Skipped -- Pydantic v2 patterns already well-established in this codebase (`CamelModel`, `Field`, `model_validator`). No new library APIs involved.

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Money in responses | Nested `MoneySchema` with `amount: int` + `currency: str` | Mirrors domain `Money` VO and `MoneyReadModel` |
| Variant attributes in SKU request | `list[VariantAttributePairSchema]` | Matches domain `SKU.variant_attributes` structure |
| ProductUpdateRequest nullable sentinels | `... # type: ignore[assignment]` for `supplier_id`, `country_of_origin` | Follows existing `AttributeUpdateRequest`, `UpdateBindingRequest` pattern |
| Status field type | `str` not enum | Follows existing binding schemas pattern; validation in domain layer |
| SKU create fields | Flat `price_amount` / `price_currency` | Matches MT-19 acceptance criteria explicitly |
| Slug validation | `pattern=r"^[a-z0-9-]+$"` | Identical to Category/Brand slug patterns |

## File plan

### `src/modules/catalog/presentation/schemas.py` -- MODIFY

**Add import** at top: `from datetime import datetime`

**Append after existing Storefront section**, with section separator:

**Classes in order:**

1. **`MoneySchema(CamelModel)`** -- `amount: int = Field(..., ge=0)`, `currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")`

2. **`VariantAttributePairSchema(CamelModel)`** -- `attribute_id: uuid.UUID`, `attribute_value_id: uuid.UUID`

3. **`ProductCreateRequest(CamelModel)`** -- `title_i18n: dict[str, str] = Field(..., min_length=1)`, `slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")`, `brand_id: uuid.UUID`, `primary_category_id: uuid.UUID`, `description_i18n: dict[str, str] = Field(default_factory=dict)`, `supplier_id: uuid.UUID | None = None`, `country_of_origin: str | None = Field(None, max_length=2)`, `tags: list[str] = Field(default_factory=list)`

4. **`ProductCreateResponse(CamelModel)`** -- `id: uuid.UUID`, `message: str`

5. **`ProductUpdateRequest(CamelModel)`** -- All fields optional: `title_i18n`, `slug`, `description_i18n`, `brand_id`, `primary_category_id`, `supplier_id`, `country_of_origin`, `tags`, `version`. Has `@model_validator(mode="after")` `at_least_one_field` that checks non-version fields are not all None/Ellipsis.

6. **`ProductStatusChangeRequest(CamelModel)`** -- `status: str`

7. **`SKUCreateRequest(CamelModel)`** -- `sku_code`, `price_amount`, `price_currency`, `compare_at_price_amount` (optional), `is_active`, `variant_attributes`

8. **`SKUCreateResponse(CamelModel)`** -- `id: uuid.UUID`, `message: str`

9. **`SKUUpdateRequest(CamelModel)`** -- All SKU fields optional plus `version`

10. **`SKUResponse(CamelModel)`** -- All SKU fields including nested `MoneySchema` for price

11. **`ProductAttributeAssignRequest(CamelModel)`** -- `attribute_id`, `attribute_value_id`

12. **`ProductAttributeAssignResponse(CamelModel)`** -- `id`, `message`

13. **`ProductAttributeResponse(CamelModel)`** -- `id`, `product_id`, `attribute_id`, `attribute_value_id`

14. **`ProductResponse(CamelModel)`** -- Full product detail with nested `skus` and `attributes` lists, `min_price`, `max_price`

15. **`ProductListItemResponse(CamelModel)`** -- Lightweight product fields

16. **`ProductListResponse(CamelModel)`** -- `items`, `total`, `offset`, `limit`

## No DI, migration, or integration changes.
