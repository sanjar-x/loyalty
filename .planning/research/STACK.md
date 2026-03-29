# Stack Research: Backend Schema Fixes

**Project:** Loyality -- Backend Pydantic Schema Fixes (ProductCreateRequest)
**Researched:** 2026-03-29
**Overall confidence:** HIGH (all findings verified against actual codebase)

## Problem Statement

Two issues in `ProductCreateRequest` (schemas.py line 717-735):

1. **descriptionI18n** uses `I18nDict = Field(default_factory=dict)` -- the default `{}` immediately fails the `I18nDict` validator which requires both `ru` and `en` keys. Sending a request without `descriptionI18n` triggers a validation error.
2. **countryOfOrigin** is missing from `ProductCreateRequest` but present in `ProductUpdateRequest` (line 764), `CreateProductCommand` (line 55), `Product.create()` (line 159), and `ProductResponse` (line 914). The router (line 81-90) does not pass it to the command either.

## Current Stack (Relevant)

### CamelModel Base
- **File:** `backend/src/shared/schemas.py` (line 20-28)
- Extends `BaseModel` with `ConfigDict(populate_by_name=True, alias_generator=to_camel)`
- `populate_by_name=True` means schemas accept BOTH `snake_case` Python names AND `camelCase` aliases on input
- `alias_generator=to_camel` serializes output as `camelCase`
- All catalog schemas inherit from `CamelModel`

### I18nDict Type
- **File:** `backend/src/modules/catalog/presentation/schemas.py` (line 77)
- Defined as: `I18nDict = Annotated[dict[str, str], AfterValidator(_validate_i18n_keys)]`
- The `_validate_i18n_keys` validator (line 52-74) enforces:
  - Required locales: `{"ru", "en"}` must both be present
  - Max 20 entries
  - Keys must be ISO 639-1 two-letter lowercase
  - Values max 10,000 chars each
- This validator runs on ANY value passing through `I18nDict`, including defaults

### Bug Mechanics
When `default_factory=dict` is used with `I18nDict`:
1. Client sends `{}` body without `descriptionI18n`
2. Pydantic creates `{}` via `default_factory`
3. `AfterValidator(_validate_i18n_keys)` runs on `{}`
4. `_REQUIRED_LOCALES - {}.keys()` = `{"ru", "en"}` -- missing required locales
5. Raises `ValueError("Missing required locales: en, ru")`

This same bug exists in two other schemas:
- `AttributeCreateRequest.description_i18n` (line 335) -- same `I18nDict = Field(default_factory=dict)` pattern
- `AttributeTemplateCreateRequest.description_i18n` (line 1174) -- uses `I18nDict | None = Field(default_factory=dict)` (mixed pattern: Optional type but dict default)

## Patterns Needed

### Pattern 1: Making I18nDict Fields Truly Optional

**Correct pattern (used 13 times in the codebase already):**
```python
description_i18n: I18nDict | None = None
```

This is the established pattern in update schemas throughout the codebase:
- `CategoryUpdateRequest.name_i18n: I18nDict | None = Field(None, min_length=1)` (line 174)
- `AttributeUpdateRequest.description_i18n: I18nDict | None = None` (line 386)
- `ProductUpdateRequest.description_i18n: I18nDict | None = None` (line 760)
- `ProductVariantCreateRequest.description_i18n: I18nDict | None = None` (line 953)
- `CloneAttributeTemplateRequest.new_description_i18n: I18nDict | None = None` (line 1152)
- `AttributeTemplateUpdateRequest.description_i18n: I18nDict | None = None` (line 1199)

**Why `None` not `{}` as default:**
- `None` skips the `AfterValidator` entirely -- Pydantic v2 short-circuits validation for `None` on `Optional` types
- `{}` triggers the validator and fails on required locales check
- The domain layer (`Product.create()` line 193) already handles `None`: `description_i18n=description_i18n or {}`
- The command handler (create_product.py line 145-147) also handles it: `description_i18n=command.description_i18n if command.description_i18n else None`

**Pydantic v2 behavior with `T | None` and `Annotated` validators:**
- When type is `I18nDict | None`, Pydantic generates a union schema: `Union[Annotated[dict, AfterValidator], None]`
- If value is `None`, the `None` branch matches first and `AfterValidator` never executes
- If value is a `dict`, the `Annotated[dict, AfterValidator]` branch runs, including the validator
- This is the correct behavior: `None` means "not provided", a dict means "validate it"

### Pattern 2: Adding New Optional String Fields

**Established pattern from `ProductUpdateRequest` (line 764-766):**
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

For `ProductCreateRequest`, the same field definition applies. Key considerations:
- ISO 3166-1 alpha-2 validation: `min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"`
- Default `None` means the field is optional on input
- CamelModel serializes as `countryOfOrigin` in JSON output
- The command dataclass already accepts it: `country_of_origin: str | None = None` (create_product.py line 55)
- The domain entity accepts it: `country_of_origin: str | None = None` (product.py line 116)
- The `ProductResponse` already returns it: `country_of_origin: str | None = None` (schemas.py line 914)

### Pattern 3: CamelModel alias_generator Behavior with Optional Fields

- `to_camel` from `pydantic.alias_generators` converts `country_of_origin` to `countryOfOrigin`
- `populate_by_name=True` means the API accepts BOTH `country_of_origin` and `countryOfOrigin` in request bodies
- Response serialization always uses the alias (`countryOfOrigin`)
- Optional fields with `None` default are omitted from JSON if `exclude_none=True` is used, but CamelModel does NOT set `exclude_none` -- so `null` values are included in responses
- This is consistent with `ProductResponse` which already includes `country_of_origin: str | None = None`

## Key Findings

### 1. Three Schemas Have the default_factory=dict Bug (Not Just One)

| Schema | Field | Line | Current | Should Be |
|--------|-------|------|---------|-----------|
| `ProductCreateRequest` | `description_i18n` | 729 | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `AttributeCreateRequest` | `description_i18n` | 335 | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `AttributeTemplateCreateRequest` | `description_i18n` | 1174 | `I18nDict \| None = Field(default_factory=dict)` | `I18nDict \| None = None` |

The `AttributeTemplateCreateRequest` case (line 1174) is particularly interesting -- it already has `I18nDict | None` as the type annotation, but the `default_factory=dict` still produces `{}` which passes the `None` check but then fails the `AfterValidator`. This confirms the fix needs to change the default, not just the type.

### 2. Router Mapping Gap for countryOfOrigin

The `create_product` router function (router_products.py line 81-90) maps request fields to `CreateProductCommand` but is missing `country_of_origin`:

```python
command = CreateProductCommand(
    title_i18n=request.title_i18n,
    slug=request.slug,
    brand_id=request.brand_id,
    primary_category_id=request.primary_category_id,
    description_i18n=request.description_i18n,
    supplier_id=request.supplier_id,
    source_url=request.source_url,
    tags=request.tags,
    # MISSING: country_of_origin=request.country_of_origin,
)
```

The fix requires changes in TWO files:
1. `schemas.py` -- add the field to `ProductCreateRequest`
2. `router_products.py` -- add the field mapping to `CreateProductCommand`

### 3. Downstream Layers Already Support Both Changes

| Layer | description_i18n=None | country_of_origin | File |
|-------|----------------------|-------------------|------|
| Command dataclass | `dict[str, str] = field(default_factory=dict)` | `str \| None = None` | create_product.py:52,55 |
| Handler | Converts None/empty to None before passing to entity | Passes through | create_product.py:145-150 |
| Entity factory | `description_i18n: dict[str, str] \| None = None` | `country_of_origin: str \| None = None` | product.py:157,159 |
| Entity constructor | Converts None to `{}` via `description_i18n or {}` | Stores as-is | product.py:193,199 |

No changes needed in command, handler, or domain layers. The presentation layer (schema + router) is the only gap.

### 4. Command Dataclass Type for description_i18n

The `CreateProductCommand.description_i18n` is typed as `dict[str, str]` with `default_factory=dict` (line 52). When the schema sends `None`, the router currently passes `request.description_i18n` directly. After the fix, `request.description_i18n` will be `None` when not provided, and the command field expects `dict[str, str]` (not Optional). Two options:

- **Option A:** Change command type to `dict[str, str] | None = None` (matches the handler's existing None check on line 145-147)
- **Option B:** Convert in the router: `description_i18n=request.description_i18n or {}`

The handler already has a guard (line 145-147): `description_i18n=command.description_i18n if command.description_i18n else None`. This means **both options work**, but Option B (convert in router) is cleaner because it keeps the command dataclass type honest -- a `dict[str, str]` with `default_factory=dict` never receives None.

## Recommendations

### 1. Fix ProductCreateRequest.description_i18n (schemas.py line 729)

Change from:
```python
description_i18n: I18nDict = Field(default_factory=dict)
```
To:
```python
description_i18n: I18nDict | None = None
```

**Rationale:** Matches the 13 existing usages of `I18nDict | None = None` in update schemas. Avoids triggering the `_validate_i18n_keys` validator on empty dicts. The domain layer already handles `None` correctly.

### 2. Add countryOfOrigin to ProductCreateRequest (schemas.py, after line 731)

Add:
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

**Rationale:** Identical definition to `ProductUpdateRequest` (line 764-766). Ensures ISO 3166-1 alpha-2 validation at the API boundary. CamelModel auto-generates the `countryOfOrigin` alias.

### 3. Add countryOfOrigin to router mapping (router_products.py line 81-90)

Add to the `CreateProductCommand(...)` constructor call:
```python
country_of_origin=request.country_of_origin,
```

**Rationale:** Without this, even if the schema accepts the field, the value is silently dropped and never reaches the command handler.

### 4. Handle None in router for description_i18n (router_products.py line 86)

Change from:
```python
description_i18n=request.description_i18n,
```
To:
```python
description_i18n=request.description_i18n or {},
```

**Rationale:** The `CreateProductCommand.description_i18n` is typed as `dict[str, str]` (not Optional). Converting `None` to `{}` in the router keeps the command dataclass contract honest. The handler's existing guard (line 145-147) then converts empty `{}` to `None` before passing to the entity.

### 5. Fix the Same Bug in Two Other Schemas (Bonus, Same Root Cause)

- `AttributeCreateRequest.description_i18n` (line 335): `I18nDict = Field(default_factory=dict)` -> `I18nDict | None = None`
- `AttributeTemplateCreateRequest.description_i18n` (line 1174): `I18nDict | None = Field(default_factory=dict)` -> `I18nDict | None = None`

**Rationale:** Same bug, same fix. These will fail identically when clients omit `descriptionI18n`. Fix all three to avoid recurring the issue.

### 6. No Breaking Changes

All changes are **additive and backward-compatible**:
- `description_i18n` was already accepted (just broken with empty default). Making it `None` default means clients that already send `{"ru": "...", "en": "..."}` still work.
- `country_of_origin` is a new optional field with `None` default. Existing clients that don't send it are unaffected.
- Response schemas (`ProductResponse`) already include `country_of_origin` -- no output format changes.
