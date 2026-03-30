# Phase 1: Backend Schema Fixes - Research

**Researched:** 2026-03-29 (forced refresh -- all line references re-verified against source)
**Domain:** Pydantic schema validation, FastAPI request wiring, Python dataclass cascading, SQLAlchemy ORM column nullability
**Confidence:** HIGH

## Summary

Phase 1 fixes two bugs in the product creation API: (1) `descriptionI18n` triggers a 422 validation error when omitted because its default `{}` hits the `_validate_i18n_keys` validator requiring `{ru, en}` keys, and (2) `countryOfOrigin` is accepted by the update endpoint but missing from the create endpoint despite the command and domain already supporting it. Both fixes are mechanical one-line changes in the presentation and router layers, following patterns already established in the update schemas.

The same `I18nDict = Field(default_factory=dict)` anti-pattern exists in `AttributeCreateRequest` (line 335) and `AttributeTemplateCreateRequest` (line 1174). The review flagged that `AttributeTemplateCreateRequest` already has `I18nDict | None` in the type annotation but incorrectly defaults to `dict` instead of `None` -- this was verified and confirmed: line 1174 reads `description_i18n: I18nDict | None = Field(default_factory=dict)`. The critical finding is that **all three DB tables (products, attributes, attribute_templates) have NOT NULL constraints with `server_default='{}'::jsonb`** on their `description_i18n` columns, which means the domain layer's `or {}` conversion pattern (None to empty dict) is load-bearing and must be preserved.

**Primary recommendation:** Change schema defaults from `default_factory=dict` to `None`, add `country_of_origin` wiring in the create router, and add tests covering all three affected endpoints (products, attributes, attribute-templates).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Change `description_i18n: I18nDict = Field(default_factory=dict)` to `description_i18n: I18nDict | None = None` in ProductCreateRequest (schemas.py:729)
- **D-02:** Same pattern already used in ProductUpdateRequest (schemas.py:760) -- follow the existing convention
- **D-03:** Cascade through command dataclass: `CreateProductCommand.description_i18n` must accept `dict | None` (currently `dict` -- verify and fix if needed)
- **D-04:** Domain entity `Product.create()` already handles None description_i18n (create_product.py:150 passes it through, entity has `description_i18n: dict[str, str]` default)
- **D-05:** When `None` is passed, store `None` in DB (not `{}`). API response shows `null` for description_i18n.
- **D-06:** Existing ProductCreateRequest responses (schemas.py line ~908) use `dict[str, str]` which accepts both `{}` and populated dicts -- no response schema change needed, but consider `dict[str, str] | None` if DB stores None
- **D-07:** Add `country_of_origin: str | None = Field(None, max_length=2, pattern=r"^[A-Z]{2}$")` to ProductCreateRequest -- same validation as ProductUpdateRequest (schemas.py:764)
- **D-08:** Wire `country_of_origin=request.country_of_origin` in router_products.py create_product handler (line 81-90) -- CreateProductCommand already has the field (create_product.py:55)
- **D-09:** No domain or ORM changes needed -- `Product.create()` already accepts `country_of_origin` (entities/product.py:160) and ORM model has the column (models.py:518)
- **D-10:** Both changes are additive: making a required field optional and adding a new optional field. No existing clients break.
- **D-11:** No Alembic migration needed -- no DB schema changes (columns already exist, Pydantic schema changes only)

### Claude's Discretion
- Exact placement of `country_of_origin` field in ProductCreateRequest (after `source_url`, before `tags` -- mirrors DB column order)
- Whether to add `description_i18n` cascade check in VariantCreateRequest and AttributeTemplateBindingCreateRequest (same `default_factory=dict` pattern found at lines 335, 1174)

### Deferred Ideas (OUT OF SCOPE)
- Fix same `default_factory=dict` anti-pattern in VariantCreateRequest and AttributeTemplateBindingCreateRequest -- could be added to this phase if trivial, or deferred to tech debt cleanup
- Frontend admin may need to handle `null` descriptionI18n in responses -- Phase 2 or 8 concern
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID      | Description                                                                                                        | Research Support                                                                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BKND-01 | User can create product without descriptionI18n (field truly optional: `I18nDict \| None = None`)                  | Full trace from schema through domain to ORM completed; root cause identified as `_validate_i18n_keys` failing on empty dict; fix verified in existing update-schema pattern |
| BKND-02 | User can set countryOfOrigin when creating product (field added to ProductCreateRequest and wired through command) | Command already has field (create_product.py:55); domain accepts it (product.py:160); ORM column exists (models.py:518); only schema + router wiring missing                 |
</phase_requirements>

## Critical Finding: D-05 Conflict with NOT NULL Constraint

**D-05 states:** "When `None` is passed, store `None` in DB (not `{}`)"

**BUT the DB has a NOT NULL constraint** on `products.description_i18n` (Alembic migration line 1607-1610: `nullable=False` with `server_default='{}'::jsonb`).

**Actual behavior chain when `None` is sent:**

1. Schema: `description_i18n = None` (passes Pydantic, no validator triggered)
2. Router: passes `None` to `CreateProductCommand(description_i18n=None)`
3. **BUT** `CreateProductCommand.description_i18n` has type `dict[str, str]` with `default_factory=dict` -- a `None` value would violate the type annotation
4. Handler line 145-146: `description_i18n=command.description_i18n if command.description_i18n else None` -- passes `None` when input is `None` or `{}`
5. Domain `Product.create()` line 193: `description_i18n=description_i18n or {},` -- converts `None` back to `{}`
6. ORM stores `{}` in the NOT NULL JSONB column

**Conclusion:** D-05 cannot be honored as written. The domain layer converts `None` to `{}` before persistence, and the DB column is NOT NULL. This is correct behavior -- the user sees `{}` (serialized as `{}` or empty object) in the response, never `null`. This is actually safer. The planner should note that D-05 is overridden by the DB constraint and existing domain conversion pattern.

**For AttributeCreateRequest and AttributeTemplateCreateRequest, the same pattern applies:**
- `attributes.description_i18n`: NOT NULL, `server_default='{}'::jsonb` (migration line 629-632)
- `attribute_templates.description_i18n`: NOT NULL, `server_default='{}'::jsonb` (migration line 85-88)
- Both `Attribute.create()` and `AttributeTemplate.create()` use `description_i18n or {}` conversion

**Only `product_variants.description_i18n` is nullable** (migration line 1973: `nullable=True`).

## Full Layer Trace: description_i18n

### Current State (BUGGY) -- ProductCreateRequest

| Layer   | File:Line                 | Type                                           | Value When Omitted | Problem                                                             |
| ------- | ------------------------- | ---------------------------------------------- | ------------------ | ------------------------------------------------------------------- |
| Schema  | schemas.py:729            | `I18nDict = Field(default_factory=dict)`       | `{}`               | `_validate_i18n_keys({})` raises "Missing required locales: en, ru" |
| Router  | router_products.py:86     | `request.description_i18n`                     | never reached      | 422 before router                                                   |
| Command | create_product.py:52      | `dict[str, str] = field(default_factory=dict)` | never reached      | --                                                                  |
| Handler | create_product.py:145-147 | conditional                                    | never reached      | --                                                                  |
| Domain  | product.py:193            | `description_i18n or {}`                       | never reached      | --                                                                  |
| ORM     | models.py:514-515         | `Mapped[dict[str, Any]]` NOT NULL              | never reached      | --                                                                  |
| DB      | migration:1607-1610       | JSONB NOT NULL, default `'{}'::jsonb`          | never reached      | --                                                                  |

### After Fix -- ProductCreateRequest

| Layer   | File:Line                 | Type                                           | Value When Omitted                   | Behavior                                                     |
| ------- | ------------------------- | ---------------------------------------------- | ------------------------------------ | ------------------------------------------------------------ |
| Schema  | schemas.py:729            | `I18nDict \| None = None`                      | `None`                               | Pydantic union: None bypasses `_validate_i18n_keys` entirely |
| Router  | router_products.py:86     | `request.description_i18n`                     | `None`                               | Passed to command                                            |
| Command | create_product.py:52      | `dict[str, str] = field(default_factory=dict)` | `None` (**type mismatch needs fix**) | Needs `dict[str, str] \| None = None`                        |
| Handler | create_product.py:145-147 | `if command.description_i18n`                  | `None` (falsy)                       | Passes `None` to domain                                      |
| Domain  | product.py:193            | `description_i18n or {}`                       | `None or {} = {}`                    | Converts to `{}`                                             |
| ORM     | models.py:514-515         | `Mapped[dict[str, Any]]` NOT NULL              | `{}`                                 | Stored as `'{}'::jsonb`                                      |
| DB      | migration:1607-1610       | JSONB NOT NULL                                 | `{}`                                 | Persisted successfully                                       |

### Current State (BUGGY) -- AttributeCreateRequest

| Layer   | File:Line               | Type                                           | Value When Omitted | Problem                                        |
| ------- | ----------------------- | ---------------------------------------------- | ------------------ | ---------------------------------------------- |
| Schema  | schemas.py:335          | `I18nDict = Field(default_factory=dict)`       | `{}`               | Same bug: `_validate_i18n_keys({})` raises 422 |
| Router  | router_attributes.py:90 | `request.description_i18n`                     | never reached      | --                                             |
| Command | create_attribute.py:63  | `dict[str, str] = field(default_factory=dict)` | never reached      | --                                             |
| Domain  | attribute.py:189        | `description_i18n or {}`                       | never reached      | --                                             |
| ORM     | models.py:292-293       | `Mapped[dict[str, Any]]` NOT NULL              | never reached      | --                                             |

### Current State (SUBTLY BUGGY) -- AttributeTemplateCreateRequest

| Layer   | File:Line                         | Type                                             | Value When Omitted | Problem                                                                                                                         |
| ------- | --------------------------------- | ------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Schema  | schemas.py:1174                   | `I18nDict \| None = Field(default_factory=dict)` | `{}`               | Type allows None, but **default is `dict`** so omitted field gets `{}`, which triggers `_validate_i18n_keys({})` and raises 422 |
| Router  | router_attribute_templates.py:112 | `request.description_i18n`                       | never reached      | --                                                                                                                              |
| Command | create_attribute_template.py:35   | `dict[str, str] \| None = None`                  | never reached      | --                                                                                                                              |
| Domain  | attribute_template.py:90          | `description_i18n or {}`                         | never reached      | --                                                                                                                              |
| ORM     | models.py:187-188                 | `Mapped[dict]` NOT NULL                          | never reached      | --                                                                                                                              |

**Review concern #1 CONFIRMED:** `AttributeTemplateCreateRequest` line 1174 already has `I18nDict | None` in the type but defaults to `dict`. Fix is to change `Field(default_factory=dict)` to `None` (not add `| None` to type).

## Full Layer Trace: country_of_origin (BKND-02)

### Current State -- CreateProductCommand already supports it

| Layer           | File:Line                   | Has Field?    | Notes                                                                                             |
| --------------- | --------------------------- | ------------- | ------------------------------------------------------------------------------------------------- |
| Schema (create) | schemas.py:717-734          | **NO**        | Missing from ProductCreateRequest                                                                 |
| Schema (update) | schemas.py:764-765          | YES           | `country_of_origin: str \| None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` |
| Router (create) | router_products.py:81-90    | **NOT WIRED** | `country_of_origin` not in CreateProductCommand() call                                            |
| Router (update) | Uses `build_update_command` | YES           | Auto-wired via reflection                                                                         |
| Command         | create_product.py:55        | YES           | `country_of_origin: str \| None = None`                                                           |
| Domain          | product.py:160              | YES           | `country_of_origin: str \| None = None` in `Product.create()`                                     |
| ORM             | models.py:518               | YES           | `Mapped[str \| None] = mapped_column(String(2))`                                                  |

**Fix requires exactly 2 changes:** add field to schema, wire in router.

## Change Manifest

### Required Changes (BKND-01 + BKND-02)

| #   | File                                                                 | Line                     | Current                                                          | Target                                                                                            | Reason                               |
| --- | -------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 1   | `backend/src/modules/catalog/presentation/schemas.py`                | 729                      | `description_i18n: I18nDict = Field(default_factory=dict)`       | `description_i18n: I18nDict \| None = None`                                                       | BKND-01: make description optional   |
| 2   | `backend/src/modules/catalog/presentation/schemas.py`                | 731 (after adding field) | --                                                               | `country_of_origin: str \| None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` | BKND-02: add country_of_origin field |
| 3   | `backend/src/modules/catalog/presentation/router_products.py`        | 81-90                    | No `country_of_origin` in `CreateProductCommand()` call          | Add `country_of_origin=request.country_of_origin,`                                                | BKND-02: wire field to command       |
| 4   | `backend/src/modules/catalog/application/commands/create_product.py` | 52                       | `description_i18n: dict[str, str] = field(default_factory=dict)` | `description_i18n: dict[str, str] \| None = None`                                                 | BKND-01: allow None through command  |

### Discretionary Changes (Attribute description_i18n fixes -- reviewer recommended)

| #   | File                                                  | Line | Current                                                            | Target                                      | Reason                                          |
| --- | ----------------------------------------------------- | ---- | ------------------------------------------------------------------ | ------------------------------------------- | ----------------------------------------------- |
| 5   | `backend/src/modules/catalog/presentation/schemas.py` | 335  | `description_i18n: I18nDict = Field(default_factory=dict)`         | `description_i18n: I18nDict \| None = None` | Same anti-pattern as BKND-01                    |
| 6   | `backend/src/modules/catalog/presentation/schemas.py` | 1174 | `description_i18n: I18nDict \| None = Field(default_factory=dict)` | `description_i18n: I18nDict \| None = None` | Type already correct, only default needs change |

### Response Schema Change (conditional on D-05 override)

| #   | File                                                  | Line | Current                            | Target           | Reason                                                               |
| --- | ----------------------------------------------------- | ---- | ---------------------------------- | ---------------- | -------------------------------------------------------------------- |
| 7   | `backend/src/modules/catalog/presentation/schemas.py` | 908  | `description_i18n: dict[str, str]` | No change needed | Domain converts None to `{}`, response will always get `{}` not null |

## Architecture Patterns

### Pattern: Optional I18n Fields in Pydantic

The `I18nDict` type is an `Annotated[dict[str, str], AfterValidator(_validate_i18n_keys)]`. When used in a `Union[I18nDict, None]`, Pydantic's union discriminator tries `None` first (or handles it specially), so `None` values bypass the validator entirely. This is the established pattern for optional i18n fields across all update schemas.

**Correct pattern (from ProductUpdateRequest):**
```python
description_i18n: I18nDict | None = None
```

**Incorrect anti-pattern (currently in ProductCreateRequest):**
```python
description_i18n: I18nDict = Field(default_factory=dict)
```

The anti-pattern fails because `default_factory=dict` produces `{}`, which Pydantic passes to `_validate_i18n_keys({})`, which raises `ValueError("Missing required locales: en, ru")`.

### Pattern: Domain None-to-Empty Conversion

All domain `create()` factory methods use `description_i18n or {}` to convert `None` to empty dict before storing in the entity. This is load-bearing because the ORM columns are NOT NULL.

```python
# Product.create() -- line 193
description_i18n=description_i18n or {},

# Attribute.create() -- line 189
description_i18n=description_i18n or {},

# AttributeTemplate.create() -- line 90
description_i18n=description_i18n or {},
```

### Pattern: Country of Origin Validation

From `ProductUpdateRequest` (line 764-765), the standard pattern:
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

This validates ISO 3166-1 alpha-2 (2 uppercase letters). Note: does not validate against an actual country list -- "XX" and "ZZ" pass. This is acceptable for Phase 1.

## Don't Hand-Roll

| Problem               | Don't Build                     | Use Instead                                   | Why                                                                 |
| --------------------- | ------------------------------- | --------------------------------------------- | ------------------------------------------------------------------- |
| i18n field validation | Custom None-handling middleware | Pydantic union type `I18nDict \| None = None` | Pydantic handles None/validator bypass automatically                |
| Country code regex    | External country-code library   | Pydantic `Field(pattern=r"^[A-Z]{2}$")`       | Already proven in update schema; full ISO validation not needed now |
| Command field wiring  | Auto-mapping utility            | Explicit keyword arguments in router          | CreateProductCommand has only 9 fields; explicit wiring is clearer  |

## Common Pitfalls

### Pitfall 1: NOT NULL Constraint vs None Storage (D-05 Conflict)
**What goes wrong:** Attempting to store `None` in `products.description_i18n` causes `IntegrityError` -- column is NOT NULL.
**Why it happens:** D-05 says "store None in DB" but migration defines NOT NULL with `server_default='{}'::jsonb`.
**How to avoid:** Accept that domain `or {}` conversion is correct behavior. The response shows `{}` (empty object), never `null`. Do NOT attempt to alter the DB constraint -- that would be a migration and is out of scope.
**Warning signs:** `sqlalchemy.exc.IntegrityError: NOT NULL constraint failed` in test output.

### Pitfall 2: AttributeTemplateCreateRequest Already Has Union Type
**What goes wrong:** Adding `| None` to type when it is already there produces `I18nDict | None | None` which is redundant but not harmful -- however it masks that the real fix is changing the default.
**Why it happens:** Line 1174 is `I18nDict | None = Field(default_factory=dict)` -- the type is already a union, only the default is wrong.
**How to avoid:** Fix #6 should ONLY change `Field(default_factory=dict)` to `None`. Do NOT touch the type annotation.

### Pitfall 3: Handler Truthiness Check
**What goes wrong:** Line 145-146 in `create_product.py` uses `if command.description_i18n` which treats both `None` and `{}` as falsy. After the fix, passing `None` from schema through command to handler results in the same code path as before.
**Why it happens:** Python truthiness: `bool(None) == False`, `bool({}) == False`.
**How to avoid:** This is actually fine -- both `None` and `{}` should map to `None` in the domain call, which then gets converted to `{}` by `Product.create()`. No changes needed in handler.

### Pitfall 4: Test Missing country_of_origin Persistence Verification
**What goes wrong:** A test checks the 201 response but never fetches the product back to verify `countryOfOrigin` was actually persisted.
**Why it happens:** Create response only returns `{id, defaultVariantId, message}`.
**How to avoid:** After creating product with `countryOfOrigin`, GET the product and assert `countryOfOrigin` matches.

## Code Examples

### Before/After: ProductCreateRequest (BKND-01 + BKND-02)

**Before (schemas.py:717-734):**
```python
class ProductCreateRequest(CamelModel):
    """Request body for creating a new product."""

    title_i18n: I18nDict = Field(..., min_length=1)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    )
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    description_i18n: I18nDict = Field(default_factory=dict)
    supplier_id: uuid.UUID | None = None
    source_url: str | None = Field(None, max_length=1024, pattern=r"^https?://")
    tags: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=50
    )
```

**After:**
```python
class ProductCreateRequest(CamelModel):
    """Request body for creating a new product."""

    title_i18n: I18nDict = Field(..., min_length=1)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    )
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    description_i18n: I18nDict | None = None
    supplier_id: uuid.UUID | None = None
    source_url: str | None = Field(None, max_length=1024, pattern=r"^https?://")
    country_of_origin: str | None = Field(
        None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
    )
    tags: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=50
    )
```

### Before/After: Router Wiring (BKND-02)

**Before (router_products.py:81-90):**
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
    )
```

**After:**
```python
    command = CreateProductCommand(
        title_i18n=request.title_i18n,
        slug=request.slug,
        brand_id=request.brand_id,
        primary_category_id=request.primary_category_id,
        description_i18n=request.description_i18n,
        supplier_id=request.supplier_id,
        source_url=request.source_url,
        country_of_origin=request.country_of_origin,
        tags=request.tags,
    )
```

### Before/After: CreateProductCommand (BKND-01)

**Before (create_product.py:52):**
```python
    description_i18n: dict[str, str] = field(default_factory=dict)
```

**After:**
```python
    description_i18n: dict[str, str] | None = None
```

### Before/After: AttributeCreateRequest (Discretionary Fix)

**Before (schemas.py:335):**
```python
    description_i18n: I18nDict = Field(default_factory=dict)
```

**After:**
```python
    description_i18n: I18nDict | None = None
```

### Before/After: AttributeTemplateCreateRequest (Discretionary Fix -- REVIEW CONCERN #1)

**Before (schemas.py:1174):**
```python
    description_i18n: I18nDict | None = Field(default_factory=dict)
```

**After (type unchanged, only default changed):**
```python
    description_i18n: I18nDict | None = None
```

## Test Files

### Existing Test Files (relevant to this phase)

| File                                                                                 | Type       | Content                                                                   | Needs Modification                                                         |
| ------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `backend/tests/e2e/api/v1/catalog/test_products.py`                                  | E2E        | Product CRUD endpoints; `create_product` helper omits `descriptionI18n`   | YES -- add tests for optional description and country_of_origin            |
| `backend/tests/e2e/api/v1/catalog/test_attributes.py`                                | E2E        | Attribute CRUD; `create_attribute` helper omits `descriptionI18n`         | YES -- add test for optional description (if discretionary fixes included) |
| `backend/tests/e2e/api/v1/catalog/test_attribute_templates.py`                       | E2E        | Template CRUD; `create_attribute_template` helper omits `descriptionI18n` | YES -- add test for optional description (if discretionary fixes included) |
| `backend/tests/e2e/api/v1/catalog/conftest.py`                                       | E2E shared | Helper functions for creating test entities                               | NO -- helpers already omit optional fields, which will now succeed         |
| `backend/tests/unit/modules/catalog/domain/test_product.py`                          | Unit       | Product entity tests                                                      | NO -- domain already handles None correctly                                |
| `backend/tests/unit/modules/catalog/application/commands/test_product_handlers.py`   | Unit       | Product command handler tests                                             | Optional -- could add None description_i18n case                           |
| `backend/tests/unit/modules/catalog/application/commands/test_attribute_handlers.py` | Unit       | Attribute/Template handler tests                                          | Optional -- could add None description_i18n case                           |
| `backend/tests/unit/modules/catalog/domain/test_attribute.py`                        | Unit       | Attribute entity tests                                                    | NO -- domain already handles None                                          |
| `backend/tests/unit/modules/catalog/domain/test_attribute_template.py`               | Unit       | Template entity tests                                                     | NO -- domain already handles None                                          |

### New Tests Required

The planner should create these test cases (E2E is primary -- exercises full stack):

1. **POST /products without descriptionI18n returns 201** (BKND-01 core)
2. **POST /products with valid descriptionI18n still returns 201** (backward compat)
3. **POST /products with countryOfOrigin returns 201 and persists** (BKND-02 core, requires GET to verify)
4. **POST /products with invalid countryOfOrigin returns 422** (BKND-02 validation)
5. **POST /products with lowercase country code returns 422** (BKND-02 regex case-sensitivity)
6. **POST /attributes without descriptionI18n returns 201** (discretionary fix verification)
7. **POST /attribute-templates without descriptionI18n returns 201** (discretionary fix verification)

## Validation Architecture

### Test Framework
| Property           | Value                                                                         |
| ------------------ | ----------------------------------------------------------------------------- |
| Framework          | pytest 9.x + pytest-asyncio (mode: auto)                                      |
| Config file        | `backend/pyproject.toml` [tool.pytest.ini_options]                            |
| Quick run command  | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q` |
| Full suite command | `cd backend && uv run pytest tests/e2e/api/v1/catalog/ -x -q`                 |

### Phase Requirements to Test Map
| Req ID  | Behavior                                                          | Test Type | Automated Command                                                                     | File Exists? |
| ------- | ----------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------- | ------------ |
| BKND-01 | Create product without descriptionI18n returns 201                | E2E       | `uv run pytest tests/e2e/api/v1/catalog/test_products.py -k "without_description" -x` | Wave 0       |
| BKND-01 | Create product with descriptionI18n still works (backward compat) | E2E       | `uv run pytest tests/e2e/api/v1/catalog/test_products.py -k "with_description" -x`    | Wave 0       |
| BKND-02 | Create product with countryOfOrigin persists value                | E2E       | `uv run pytest tests/e2e/api/v1/catalog/test_products.py -k "country_of_origin" -x`   | Wave 0       |
| BKND-02 | Invalid countryOfOrigin rejected with 422                         | E2E       | `uv run pytest tests/e2e/api/v1/catalog/test_products.py -k "invalid_country" -x`     | Wave 0       |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q`
- **Per wave merge:** `cd backend && uv run pytest tests/e2e/api/v1/catalog/ -x -q`
- **Phase gate:** Full E2E catalog suite green before verify

### Wave 0 Gaps
- [ ] New test cases in `test_products.py` for BKND-01 (optional description) and BKND-02 (country_of_origin)
- [ ] New test cases in `test_attributes.py` for optional description (if discretionary fixes included)
- [ ] New test cases in `test_attribute_templates.py` for optional description (if discretionary fixes included)

## Review Concerns -- Resolution

### HIGH: AttributeTemplateCreateRequest line 1174 already has `I18nDict | None` type

**VERIFIED.** Line 1174 reads:
```python
description_i18n: I18nDict | None = Field(default_factory=dict)
```

The type is already `I18nDict | None`. The bug is the `default_factory=dict` default. Fix is:
```python
description_i18n: I18nDict | None = None
```

Do NOT add `| None` to the type (it is already there). Only change the default value.

### MEDIUM: Trace the full None-to-{} conversion path explicitly

**FULLY TRACED above.** The path is:
1. Schema: `None` bypasses `_validate_i18n_keys`
2. Router: passes `None` to command
3. Command: accepts `None` (after fix to type annotation)
4. Handler: `if command.description_i18n` is `False` for `None`, passes `None` to `Product.create()`
5. Domain: `description_i18n or {}` converts `None` to `{}`
6. ORM: stores `{}` in NOT NULL JSONB column
7. DB: `'{}'::jsonb` persisted

**Response serialization:** `ProductResponse.description_i18n: dict[str, str]` will receive `{}` from read model, serialized as `{}` in JSON. Never `null`.

### MEDIUM: Identify all test files for attribute and attribute-template creation endpoints

**FULLY LISTED in Test Files section above.** Key files:
- `backend/tests/e2e/api/v1/catalog/test_products.py`
- `backend/tests/e2e/api/v1/catalog/test_attributes.py`
- `backend/tests/e2e/api/v1/catalog/test_attribute_templates.py`
- `backend/tests/e2e/api/v1/catalog/conftest.py` (shared helpers)

## Sources

### Primary (HIGH confidence)
- Direct source code reading: `schemas.py`, `router_products.py`, `create_product.py`, `product.py`, `models.py`, `attribute.py`, `attribute_template.py`, `create_attribute.py`, `create_attribute_template.py`, `router_attributes.py`, `router_attribute_templates.py`
- Alembic migration: `27_0911_19_7ce70774f240_init.py` -- verified NOT NULL constraints on all three description_i18n columns
- All test files: `test_products.py`, `test_attributes.py`, `test_attribute_templates.py`, `conftest.py`
- Pydantic validator source: `_validate_i18n_keys()` at schemas.py:52-74

### Secondary (MEDIUM confidence)
- CONTEXT.md user decisions (line numbers verified against actual source)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all changes are in existing files with verified line numbers
- Architecture: HIGH - patterns copied from existing update schemas
- Pitfalls: HIGH - NOT NULL constraint verified in actual migration, None-to-{} path fully traced
- Review concerns: HIGH - all three reviewer concerns verified and resolved with evidence

**Research date:** 2026-03-29
**Valid until:** 2026-04-30 (schema changes are stable; no dependency on external libraries)
