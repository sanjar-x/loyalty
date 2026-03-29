# Features Research: Backend Schema Fixes

**Domain:** Pydantic request schema alignment (ProductCreateRequest)
**Researched:** 2026-03-29
**Scope:** Milestone v1.0 -- two backend-only fixes to ProductCreateRequest

---

## Feature 1: Optional Description I18n

### Problem

`ProductCreateRequest.description_i18n` is declared as:

```python
description_i18n: I18nDict = Field(default_factory=dict)
```

When the frontend omits this field, Pydantic uses `default_factory=dict` to produce `{}`, then the `I18nDict` aftervalidator (`_validate_i18n_keys`) runs and requires `{"ru", "en"}` keys. Empty dict `{}` fails with:

```
ValueError: Missing required locales: en, ru
```

This makes it impossible to create a product without a description, even though description is semantically optional for draft products.

### E-Commerce Convention for Optional I18n Descriptions

Standard e-commerce APIs (Shopify, Medusa, Saleor) treat product description as optional at creation time. Products begin as drafts and get enriched over time. The common pattern:

- **Omitted/null**: No description yet (valid for drafts, enrichment comes later)
- **Provided with all locales**: Validated and stored as-is
- **Provided with partial locales**: Rejected (data integrity: either provide all required locales or none)

Empty dict `{}` is NOT a valid "no description" state -- it's ambiguous. `None`/null is the correct representation.

### What the Domain Entity Already Supports

`Product.create()` in `backend/src/modules/catalog/domain/entities/product.py` (line 157):

```python
description_i18n: dict[str, str] | None = None,
```

And handles it at line 193:

```python
description_i18n=description_i18n or {},
```

So the domain accepts `None` and coerces it to `{}` internally. Fully compatible.

### What the Create Command Already Supports

`CreateProductCommand` in `backend/src/modules/catalog/application/commands/create_product.py` (line 52):

```python
description_i18n: dict[str, str] = field(default_factory=dict)
```

The handler (lines 145-147) passes it through:

```python
description_i18n=command.description_i18n if command.description_i18n else None,
```

This means an empty dict `{}` is already converted to `None` before reaching the domain. However, the command type itself should be `dict[str, str] | None = None` for semantic clarity.

### What the Update Schema Already Does (Correctly)

`ProductUpdateRequest` (line 760):

```python
description_i18n: I18nDict | None = None
```

`ProductVariantCreateRequest` (line 953):

```python
description_i18n: I18nDict | None = None
```

Both use the `I18nDict | None = None` pattern already. The create request is the outlier.

### All Affected Locations (Same Bug)

| File | Class | Field | Current | Fix |
|------|-------|-------|---------|-----|
| `catalog/presentation/schemas.py:729` | `ProductCreateRequest` | `description_i18n` | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `catalog/presentation/schemas.py:335` | `AttributeCreateRequest` | `description_i18n` | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `catalog/presentation/schemas.py:1174` | `AttributeTemplateCreateRequest` | `description_i18n` | `I18nDict \| None = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `catalog/application/commands/create_product.py:52` | `CreateProductCommand` | `description_i18n` | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` |
| `catalog/application/commands/create_attribute.py` | `CreateAttributeCommand` | `description_i18n` | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` |
| `catalog/application/commands/bulk_create_attributes.py` | `BulkCreateAttributeItem` | `description_i18n` | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` |

### Semantic: Three-State Model

After the fix, the field has three clear states:

1. **Not provided** (`None`) -- no description yet, valid for drafts. Domain stores `{}`
2. **Provided with all required locales** (`{"ru": "...", "en": "..."}`) -- I18nDict validator runs, validates both locales present, stored as-is
3. **Provided with partial/empty locales** (`{}` or `{"ru": "..."}`) -- I18nDict validator rejects (correct -- partial translations are bad data)

---

## Feature 2: Country of Origin in Create

### Problem

The admin frontend sends `countryOfOrigin` in the product creation payload, but `ProductCreateRequest` does not declare this field. Pydantic silently discards unknown fields (default `extra='ignore'` behavior). The country of origin is lost on create.

### Country of Origin Convention

ISO 3166-1 alpha-2 codes (2 uppercase letters like `CN`, `RU`, `US`, `KR`) are the universal standard for e-commerce country-of-origin fields. This is what the codebase already uses.

The `ProductUpdateRequest` already validates this (line 764-766):

```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

This is sufficient validation -- full ISO 3166-1 enum validation is overkill for this field (would require maintaining a 249-item list). The regex ensures format correctness; the actual country code correctness is a UI/frontend concern.

### What the Domain Entity Already Supports

`Product.create()` (line 160):

```python
country_of_origin: str | None = None,
```

`Product._UPDATABLE_FIELDS` includes `"country_of_origin"` (line 226).

`Product.update()` handles it (lines 288-289):

```python
if "country_of_origin" in kwargs:
    self.country_of_origin = kwargs["country_of_origin"]  # can be None
```

The ORM model (`models.py:518`):

```python
country_of_origin: Mapped[str | None] = mapped_column(String(2))
```

Full domain/infrastructure support already exists.

### What the Create Command Already Supports

`CreateProductCommand` (line 55):

```python
country_of_origin: str | None = None
```

The handler passes it directly to `Product.create()` (line 150):

```python
country_of_origin=command.country_of_origin,
```

The command is fully wired. Only two things are missing:

### What's Missing

1. **Schema field**: `ProductCreateRequest` does not declare `country_of_origin`
2. **Router mapping**: `router_products.py:81-89` does not pass `country_of_origin` to the command

The update endpoint already has both (schema field + router mapping via `build_update_command`).

---

## Key Findings

### Already Fully Supported (No Changes Needed)

| Layer | Feature 1 (description_i18n) | Feature 2 (country_of_origin) |
|-------|------------------------------|-------------------------------|
| Domain entity (`Product.create()`) | Accepts `None`, coerces to `{}` | Accepts `str \| None` |
| Domain entity (`Product.update()`) | Accepts `None`, coerces to `{}` | Accepts `str \| None` |
| Command (`CreateProductCommand`) | Has field (wrong default) | Has field |
| Handler (`CreateProductHandler`) | Passes through (handles None) | Passes through |
| ORM model | `JSONB` column with `'{}'::jsonb` default | `VARCHAR(2)` nullable |
| Update schema | Uses correct `I18nDict \| None = None` | Has field with regex validation |

### Needs Changing

| Layer | Feature 1 (description_i18n) | Feature 2 (country_of_origin) |
|-------|------------------------------|-------------------------------|
| `ProductCreateRequest` schema | Change type from `I18nDict` to `I18nDict \| None`, default from `Field(default_factory=dict)` to `None` | Add field: `str \| None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` |
| Router `create_product()` | No change (already passes `description_i18n`) | Add `country_of_origin=request.country_of_origin` |
| `CreateProductCommand` | Change type to `dict[str, str] \| None = None` | No change (already has it) |
| Other create schemas (Attribute, Template) | Same fix as ProductCreateRequest | N/A |
| Other create commands (Attribute, BulkAttribute) | Same fix as CreateProductCommand | N/A |

---

## Recommendations

### 1. Both fixes are non-breaking, additive backend changes

- Feature 1 makes an existing field more permissive (was: required locales on create; now: truly optional)
- Feature 2 adds a new optional field to the request schema (existing payloads unaffected)
- No API contract breakage. No coordinated frontend deploy needed.

### 2. Apply the same description_i18n fix to all three create schemas

`AttributeCreateRequest` and `AttributeTemplateCreateRequest` have the identical bug. Fix all three for consistency, not just `ProductCreateRequest`.

### 3. Match country_of_origin validation exactly with ProductUpdateRequest

Copy the same `Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` constraint. Consistency between create and update schemas is important -- a value accepted on create must also pass on update.

### 4. Update the command dataclasses for type accuracy

While `CreateProductCommand.description_i18n` currently works (the handler converts `{}` to `None`), changing it to `dict[str, str] | None = None` is the correct semantic representation and avoids the confusing `field(default_factory=dict)` that implies "always provide a dict".

### 5. Estimated scope

- **Files changed:** 3 (schemas.py, create_product.py router, create_product.py command) + 2 bonus (create_attribute.py, bulk_create_attributes.py)
- **Lines changed:** ~15
- **Risk:** Minimal -- adding optional fields and relaxing required ones cannot break existing callers

---

## Sources

- `backend/src/modules/catalog/presentation/schemas.py` -- ProductCreateRequest (line 717), I18nDict validator (line 52), ProductUpdateRequest (line 745)
- `backend/src/modules/catalog/application/commands/create_product.py` -- CreateProductCommand (line 33), handler (line 98)
- `backend/src/modules/catalog/application/commands/update_product.py` -- UpdateProductCommand (line 36) for reference
- `backend/src/modules/catalog/domain/entities/product.py` -- Product.create() (line 149), Product.update() (line 230)
- `backend/src/modules/catalog/infrastructure/models.py` -- ORM columns (lines 514, 518)
- `backend/src/modules/catalog/presentation/router_products.py` -- create_product router (line 76), update_product router (line 225)
- `backend/src/modules/catalog/presentation/update_helpers.py` -- build_update_command helper
