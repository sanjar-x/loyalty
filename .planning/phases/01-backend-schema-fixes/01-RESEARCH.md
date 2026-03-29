# Phase 1: Backend Schema Fixes - Research

**Researched:** 2026-03-29 (refresh)
**Domain:** Pydantic schema validation, FastAPI request wiring, Python dataclass cascading, SQLAlchemy ORM column nullability
**Confidence:** HIGH

## Summary

Phase 1 fixes two integration bugs in the product creation flow: making `descriptionI18n` truly optional (BKND-01) and wiring `countryOfOrigin` to `ProductCreateRequest` (BKND-02). Both are mechanical changes that follow established patterns already used in the codebase's update schemas.

The current `I18nDict = Field(default_factory=dict)` pattern is broken: it produces an empty dict `{}` which triggers the `_validate_i18n_keys` AfterValidator (schemas.py:52-74), failing with "Missing required locales: en, ru". Any client that omits `descriptionI18n` receives a 422 validation error. The fix is changing to `I18nDict | None = None`, which Pydantic resolves as a union type where `None` bypasses the AfterValidator entirely.

Critical constraint verified during refresh: the `products.description_i18n` database column is `NOT NULL` (Alembic migration line 1610: `nullable=False`, ORM model line 514: `Mapped[dict[str, Any]]` with no `| None`). Decision D-05 from CONTEXT.md states "store None in DB (not {})", but this requires an Alembic migration to make the column nullable, which D-11 explicitly prohibits. The domain layer already handles this correctly: `Product.create()` line 193 converts `None` to `{}` via `description_i18n or {}`. The response schema stays `dict[str, str]` (never `None`).

**Primary recommendation:** Change `description_i18n` to `I18nDict | None = None` in `ProductCreateRequest` and `CreateProductCommand`, keep domain/ORM/response behavior as-is (converts `None` to `{}`), add `country_of_origin` field to `ProductCreateRequest` and wire it in the router.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Change `description_i18n: I18nDict = Field(default_factory=dict)` to `description_i18n: I18nDict | None = None` in ProductCreateRequest (schemas.py:729)
- **D-02:** Same pattern already used in ProductUpdateRequest (schemas.py:760) -- follow the existing convention
- **D-03:** Cascade through command dataclass: `CreateProductCommand.description_i18n` must accept `dict | None` (currently `dict` -- verify and fix if needed)
- **D-04:** Domain entity `Product.create()` already handles None description_i18n (create_product.py:150 passes it through, entity has `description_i18n: dict[str, str]` default)
- **D-05:** When `None` is passed, store `None` in DB (not `{}`). API response shows `null` for description_i18n. **RESEARCH OVERRIDE: DB column is NOT NULL (Alembic line 1610, ORM line 514) -- storing None causes IntegrityError. D-11 prohibits migration. Store `{}` instead, which domain layer already does via `description_i18n or {}` at entities/product.py:193.**
- **D-06:** Existing ProductCreateRequest responses (schemas.py line ~908) use `dict[str, str]` which accepts both `{}` and populated dicts -- no response schema change needed, but consider `dict[str, str] | None` if DB stores None. **RESEARCH CLARIFICATION: Since DB stores `{}` (not None), response schema stays `dict[str, str]`.**
- **D-07:** Add `country_of_origin: str | None = Field(None, max_length=2, pattern=r"^[A-Z]{2}$")` to ProductCreateRequest -- same validation as ProductUpdateRequest (schemas.py:764)
- **D-08:** Wire `country_of_origin=request.country_of_origin` in router_products.py create_product handler (line 81-90) -- CreateProductCommand already has the field (create_product.py:55)
- **D-09:** No domain or ORM changes needed -- `Product.create()` already accepts `country_of_origin` (entities/product.py:160) and ORM model has the column (models.py:518)
- **D-10:** Both changes are additive: making a required field optional and adding a new optional field. No existing clients break.
- **D-11:** No Alembic migration needed -- no DB schema changes (columns already exist, Pydantic schema changes only)

### Claude's Discretion
- Exact placement of `country_of_origin` field in ProductCreateRequest (after `source_url`, before `tags` -- mirrors DB column order)
- Whether to add `description_i18n` cascade check in AttributeCreateRequest and AttributeTemplateCreateRequest (same `default_factory=dict` pattern found at lines 335, 1174)

### Deferred Ideas (OUT OF SCOPE)
- Fix same `default_factory=dict` anti-pattern in VariantCreateRequest and AttributeTemplateBindingCreateRequest -- could be added to this phase if trivial, or deferred to tech debt cleanup
- Frontend admin may need to handle `null` descriptionI18n in responses -- Phase 2 or 8 concern
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BKND-01 | User can create product without descriptionI18n (field truly optional: `I18nDict \| None = None`) | Full layer-by-layer trace verified. Schema fix is one line (schemas.py:729). Command fix is one line (create_product.py:52). Domain `Product.create()` handles None at line 193. ORM column is NOT NULL, stores `{}`. No response schema change. |
| BKND-02 | User can set countryOfOrigin when creating product (field added to ProductCreateRequest and wired through command) | Pattern verified in ProductUpdateRequest (schemas.py:764-766). Command already has the field (create_product.py:55). Router missing wiring (router_products.py:81-89 omits `country_of_origin`). Domain and ORM already support it. |
</phase_requirements>

## Standard Stack

No new libraries needed. All changes use existing project dependencies.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | v2 (bundled with FastAPI >=0.115.0) | Request/response schema validation | Already used for all schemas via CamelModel |
| FastAPI | >=0.115.0 | Route handler wiring | Existing framework |
| attrs | >=25.4.0 | Domain entity dataclass definition | Already used for Product entity |
| SQLAlchemy | >=2.1.0b1 | ORM model Mapped types | Existing infrastructure |
| pytest | >=9.0.2 | Test runner | Existing test infrastructure |

## Architecture Patterns

### Layer Flow for Changes
```
ProductCreateRequest (schema, Pydantic)     <-- FIX HERE: description_i18n, country_of_origin
  -> create_product() (router, FastAPI)     <-- FIX HERE: wire country_of_origin
    -> CreateProductCommand (frozen dataclass)  <-- FIX HERE: description_i18n type
      -> CreateProductHandler.handle()      <-- NO CHANGE (truthiness check works)
        -> Product.create()                 <-- NO CHANGE (handles None via or {})
          -> ProductRepository._to_orm()    <-- NO CHANGE (entity always has dict)
            -> ProductModel (ORM -> PG)     <-- NO CHANGE (NOT NULL, stores {})
              -> ProductReadModel           <-- NO CHANGE (description_i18n: dict[str, str])
                -> ProductResponse          <-- NO CHANGE (description_i18n: dict[str, str])
```

### Pattern 1: Optional I18nDict Field
**What:** Union type `I18nDict | None = None` where Pydantic resolves None before reaching AfterValidator
**When to use:** Any i18n field that should be optional
**Verified source:** `ProductUpdateRequest.description_i18n` at schemas.py:760
```python
description_i18n: I18nDict | None = None
```
When `None` is the input, Pydantic's union type resolution matches `None` against the `None` branch of the union first, so `_validate_i18n_keys` (the AfterValidator on `I18nDict`) is never called.

### Pattern 2: Optional Country Code Field
**What:** ISO 3166-1 alpha-2 field with regex validation
**When to use:** Any country code field
**Verified source:** `ProductUpdateRequest.country_of_origin` at schemas.py:764-766
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

### Pattern 3: Router-to-Command Wiring
**What:** Each field in request schema maps 1:1 to CreateProductCommand constructor args
**When to use:** Adding new fields to request schemas
**Verified source:** router_products.py:81-89 (current code, missing country_of_origin)

### Anti-Patterns to Avoid
- **`I18nDict = Field(default_factory=dict)` for optional fields:** The empty dict `{}` triggers `_validate_i18n_keys` (line 52-74) which requires `ru` and `en` keys, producing a 422. Use `I18nDict | None = None` instead.
- **`I18nDict | None = Field(default_factory=dict)` (hybrid broken):** schemas.py:1174 has this. The type allows None but the default is `{}`, which still triggers the validator. Use `I18nDict | None = None`.
- **Changing DB column nullability without Alembic migration:** The `products.description_i18n` column is `NOT NULL`. Do not attempt to store `None` in it without a migration.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| I18n validation bypass for None | Custom None-checking logic in validator | `I18nDict \| None = None` union type | Pydantic handles union resolution natively; None branch is matched before AfterValidator runs |
| Country code validation | Manual regex checking in handler | `Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` | Pydantic Field constraints handle this declaratively |

## Change Manifest

### BKND-01: Make description_i18n truly optional

#### File 1: `backend/src/modules/catalog/presentation/schemas.py`
**Line 729** -- Change ProductCreateRequest.description_i18n:
```python
# BEFORE:
description_i18n: I18nDict = Field(default_factory=dict)

# AFTER:
description_i18n: I18nDict | None = None
```

#### File 2: `backend/src/modules/catalog/application/commands/create_product.py`
**Line 52** -- Change CreateProductCommand.description_i18n:
```python
# BEFORE:
description_i18n: dict[str, str] = field(default_factory=dict)

# AFTER:
description_i18n: dict[str, str] | None = None
```

#### Files NOT needing changes (verified):
- `router_products.py:86` -- passes `request.description_i18n` to command, works for None
- `create_product.py:145-147` -- handler truthiness check `if command.description_i18n else None` already handles both `{}` and `None` correctly, passes `None` to `Product.create()`
- `entities/product.py:193` -- `description_i18n=description_i18n or {}` converts None to `{}`
- `entities/product.py:110` -- Product.description_i18n attr type `dict[str, str]` stays correct (entity always stores dict)
- `models.py:514-516` -- ORM column NOT NULL, stores `{}`, no change needed
- `repositories/product.py:292` -- `_to_orm()` sets `orm.description_i18n = entity.description_i18n` -- entity always has dict
- `repositories/product.py:224-226` -- `_base_product_fields()` handles empty dict correctly
- `queries/get_product.py:138` -- passes `orm.description_i18n` directly to read model, always dict
- `queries/read_models.py:364` -- `description_i18n: dict[str, str]` stays correct
- `schemas.py:908` -- `ProductResponse.description_i18n: dict[str, str]` stays correct
- `tests/factories/product_builder.py:99` -- `description_i18n=self._description_i18n or None` already passes None

### BKND-02: Add country_of_origin to product creation

#### File 1: `backend/src/modules/catalog/presentation/schemas.py`
**Between lines 731-732** (after `source_url`, before `tags`) -- Add to ProductCreateRequest:
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

#### File 2: `backend/src/modules/catalog/presentation/router_products.py`
**Line 81-89** -- Add `country_of_origin` to CreateProductCommand constructor:
```python
command = CreateProductCommand(
    title_i18n=request.title_i18n,
    slug=request.slug,
    brand_id=request.brand_id,
    primary_category_id=request.primary_category_id,
    description_i18n=request.description_i18n,
    supplier_id=request.supplier_id,
    source_url=request.source_url,
    country_of_origin=request.country_of_origin,  # NEW
    tags=request.tags,
)
```

#### Files NOT needing changes (verified):
- `create_product.py:55` -- `country_of_origin: str | None = None` already exists in CreateProductCommand
- `create_product.py:150` -- handler passes `country_of_origin=command.country_of_origin` to Product.create()
- `entities/product.py:159` -- `Product.create()` already accepts `country_of_origin: str | None = None`
- `entities/product.py:199` -- Product constructor already has `country_of_origin: str | None = None`
- `models.py:518` -- `country_of_origin: Mapped[str | None] = mapped_column(String(2))` exists
- `schemas.py:914` -- `ProductResponse.country_of_origin: str | None = None` exists

### Discretionary: Fix same bug in Attribute and AttributeTemplate schemas

#### File 3 (optional): `backend/src/modules/catalog/presentation/schemas.py`
**Line 335** -- Change AttributeCreateRequest.description_i18n:
```python
# BEFORE:
description_i18n: I18nDict = Field(default_factory=dict)

# AFTER:
description_i18n: I18nDict | None = None
```

**Line 1174** -- Change AttributeTemplateCreateRequest.description_i18n:
```python
# BEFORE:
description_i18n: I18nDict | None = Field(default_factory=dict)

# AFTER:
description_i18n: I18nDict | None = None
```

#### Cascade files for discretionary fixes:
- `create_attribute.py:63` -- `CreateAttributeCommand.description_i18n: dict[str, str] = field(default_factory=dict)` -- change to `dict[str, str] | None = None`
- `bulk_create_attributes.py:51` -- `BulkCreateAttributeItem.description_i18n: dict[str, str] = field(default_factory=dict)` -- change to `dict[str, str] | None = None`
- `create_attribute_template.py:35` -- `CreateAttributeTemplateCommand.description_i18n: dict[str, str] | None = None` -- already correct, no change
- Domain entities Attribute.create() (line 189) and AttributeTemplate.create() (line 90) already handle None via `or {}` -- no change
- ORM columns for attributes (line 292-294) and attribute_templates (line 187-189) are both NOT NULL with server_default -- no change

## Layer-by-Layer Analysis (BKND-01)

### Schema Layer (schemas.py)
| Field | Current (line) | Target | Notes |
|-------|---------------|--------|-------|
| ProductCreateRequest.description_i18n | `I18nDict = Field(default_factory=dict)` (729) | `I18nDict \| None = None` | Core fix |
| ProductResponse.description_i18n | `dict[str, str]` (908) | No change | DB stores `{}`, never None |
| ProductReadModel.description_i18n | `dict[str, str]` (read_models.py:364) | No change | Same reason |

### Command Layer (create_product.py)
| Field | Current (line) | Target | Notes |
|-------|---------------|--------|-------|
| CreateProductCommand.description_i18n | `dict[str, str] = field(default_factory=dict)` (52) | `dict[str, str] \| None = None` | Type consistency fix |
| CreateProductCommand.country_of_origin | `str \| None = None` (55) | No change | Already exists |

### Handler Layer (create_product.py)
| Code | Current (line) | Needs Change | Notes |
|------|---------------|--------------|-------|
| Truthiness check | `description_i18n=command.description_i18n if command.description_i18n else None` (145-147) | No | When command.description_i18n is `None`, truthiness is False, passes `None` to Product.create(). When `{}` (empty dict from direct callers), truthiness is also False, passes `None`. Both correct. |

### Domain Layer (entities/product.py)
| Code | Current (line) | Needs Change | Notes |
|------|---------------|--------------|-------|
| Product.create() param | `description_i18n: dict[str, str] \| None = None` (157) | No | Already optional |
| None guard | `description_i18n=description_i18n or {}` (193) | No | Converts None to `{}` for the entity |
| Product.description_i18n attr | `description_i18n: dict[str, str]` (110) | No | Always a dict |

### ORM Layer (models.py)
| Column | Current (line) | Needs Change | Notes |
|--------|---------------|--------------|-------|
| ProductModel.description_i18n | `Mapped[dict[str, Any]]` NOT NULL, server_default=`'{}'::jsonb` (514-516) | No | Column stays NOT NULL, stores `{}` for empty |

### Alembic Migration
| Status | Evidence |
|--------|----------|
| NOT NEEDED | Column `description_i18n` is `nullable=False` (migration line 1610), `country_of_origin` column already exists as `nullable=True` (migration line 1618). No DB schema changes required. |

### Response Flow (read path)
| Step | Code | Value | Notes |
|------|------|-------|-------|
| PostgreSQL | `description_i18n JSONB NOT NULL DEFAULT '{}'::jsonb` | `{}` | Empty JSON object |
| ORM query | `orm.description_i18n` | `{}` (dict) | Loaded by SQLAlchemy |
| GetProductHandler._to_read_model() | `description_i18n=orm.description_i18n` (get_product.py:138) | `{}` | Passed directly |
| ProductReadModel | `description_i18n: dict[str, str]` (read_models.py:364) | `{}` | Pydantic accepts `{}` for `dict[str, str]` |
| ProductResponse | `description_i18n: dict[str, str]` (schemas.py:908) | `{}` | Serializes to JSON `"descriptionI18n": {}` |

## Existing Test Impact

### Files that test product creation
| File | Relevance | Impact | Action |
|------|-----------|--------|--------|
| `tests/e2e/api/v1/catalog/test_products.py` | HIGH - e2e product CRUD tests | `create_product()` helper (line 33-38) omits `descriptionI18n` from payload. After fix, this will work correctly (currently hits the bug or never tested with omitted field). | No changes to existing tests; add new tests |
| `tests/e2e/api/v1/catalog/test_lifecycle.py` | MEDIUM - full lifecycle test | `test_full_product_lifecycle` (line 66-74) also omits `descriptionI18n`. Same situation. | No changes needed |
| `tests/unit/modules/catalog/application/commands/test_product_handlers.py` | HIGH - unit tests for CreateProductHandler | `TestCreateProduct` class (line 232+) creates commands without `description_i18n`. Due to `default_factory=dict` on command, these get `{}` which the handler's truthiness check converts to `None`. After fix, command default will be `None` directly. Same outcome. | No changes needed |
| `tests/unit/modules/catalog/domain/test_product.py` | LOW - domain entity tests | Uses `ProductBuilder` which already passes `None` for empty description. | No changes needed |
| `tests/factories/product_builder.py` | LOW - builder helper | Line 99: `description_i18n=self._description_i18n or None` already passes None for empty dict. | No changes needed |
| `tests/integration/modules/catalog/infrastructure/repositories/test_product.py` | LOW - repo-level tests | Tests at domain/repo level, not schema level. Line 54 asserts `fetched.description_i18n == {}`. | No changes needed |

### All `default_factory=dict` instances in schemas.py (complete inventory)
| Line | Schema.Field | Type | Has Bug | In Scope |
|------|-------------|------|---------|----------|
| 335 | AttributeCreateRequest.description_i18n | `I18nDict` | YES - same bug as BKND-01 | Discretionary |
| 454 | AttributeValueCreateRequest.meta_data | `BoundedJsonDict` | NO - `_validate_bounded_json_dict` accepts `{}` | Out of scope |
| 729 | ProductCreateRequest.description_i18n | `I18nDict` | YES - the BKND-01 bug | Required |
| 897 | ProductAttributeResponse.attribute_name_i18n | `dict[str, str]` (plain, no I18nDict) | NO - response schema, no AfterValidator | Out of scope |
| 899 | ProductAttributeResponse.attribute_value_name_i18n | `dict[str, str]` (plain, no I18nDict) | NO - response schema, no AfterValidator | Out of scope |
| 1174 | AttributeTemplateCreateRequest.description_i18n | `I18nDict \| None` with `default_factory=dict` | YES - broken default | Discretionary |

### All `default_factory=dict` instances in command dataclasses (complete inventory)
| Line | Command.Field | Current Type | Needs Fix | Why |
|------|-------------|-------------|-----------|-----|
| create_product.py:52 | CreateProductCommand.description_i18n | `dict[str, str]` | YES | BKND-01 required |
| create_attribute.py:63 | CreateAttributeCommand.description_i18n | `dict[str, str]` | Discretionary | Matches schema fix at line 335 |
| bulk_create_attributes.py:51 | BulkCreateAttributeItem.description_i18n | `dict[str, str]` | Discretionary | Matches schema fix at line 335 |

## Common Pitfalls

### Pitfall 1: D-05 Conflict -- DB Column is NOT NULL
**What goes wrong:** CONTEXT.md D-05 says "store None in DB (not {})". But `products.description_i18n` column is `NOT NULL` (Alembic migration line 1610, ORM model line 514: `Mapped[dict[str, Any]]`). Storing None causes `IntegrityError`.
**Why it happens:** D-05 was decided without verifying DB column constraints.
**How to avoid:** Keep existing domain behavior: `Product.create()` line 193 converts `None` to `{}` via `description_i18n or {}`. This stores `{}` in DB, which the NOT NULL column accepts.
**Warning signs:** IntegrityError during product creation when description_i18n is omitted.
**Resolution:** D-05 is overridden. The API accepts None (schema) but stores `{}` (DB). Response returns `{}` not `null`. No Alembic migration needed (D-11 preserved).

### Pitfall 2: CreateProductCommand truthiness check in handler
**What goes wrong:** Changing the command's default from `dict` to `None` could theoretically change behavior.
**Verified analysis:** In `CreateProductHandler.handle()` (line 145-147):
```python
description_i18n=command.description_i18n
if command.description_i18n
else None,
```
- Old behavior: command defaults to `{}`, truthiness is `False`, passes `None` to `Product.create()`
- New behavior: command defaults to `None`, truthiness is `False`, passes `None` to `Product.create()`
**Outcome:** Identical. No code change needed here.

### Pitfall 3: Same anti-pattern in AttributeCreateRequest
**What goes wrong:** `AttributeCreateRequest.description_i18n` (line 335) has `I18nDict = Field(default_factory=dict)`. If a user omits description when creating an attribute, they get a 422.
**Impact:** Same bug as BKND-01 but for attributes, not products.
**How to avoid:** Fix to `I18nDict | None = None` as part of discretionary scope.

### Pitfall 4: Hybrid broken default in AttributeTemplateCreateRequest
**What goes wrong:** `AttributeTemplateCreateRequest.description_i18n` (line 1174) has `I18nDict | None = Field(default_factory=dict)`. The type annotation allows None, but the default value is `{}` (empty dict), which triggers `_validate_i18n_keys`.
**Why it's worse:** Developer intended this to be optional (hence `| None`) but the default factory still triggers validation.
**How to avoid:** Fix to `I18nDict | None = None`.

### Pitfall 5: Forgetting to add min_length to country_of_origin
**What goes wrong:** If you copy from ProductUpdateRequest but miss `min_length=2`, a single-char country code like "U" would pass max_length and pattern but be semantically wrong.
**Verified:** ProductUpdateRequest.country_of_origin (line 764-766) uses `min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"` -- all three constraints needed.

### Pitfall 6: ProductVariantCreateRequest is already correct
**What goes wrong:** One might think it has the same bug, but `ProductVariantCreateRequest.description_i18n` (line 953) already uses `I18nDict | None = None`. No fix needed.

## Code Examples

### BKND-01: Fix description_i18n in ProductCreateRequest
```python
# File: backend/src/modules/catalog/presentation/schemas.py
# Line 729: BEFORE
description_i18n: I18nDict = Field(default_factory=dict)

# Line 729: AFTER
description_i18n: I18nDict | None = None
```

### BKND-01: Fix CreateProductCommand type hint
```python
# File: backend/src/modules/catalog/application/commands/create_product.py
# Line 52: BEFORE
description_i18n: dict[str, str] = field(default_factory=dict)

# Line 52: AFTER
description_i18n: dict[str, str] | None = None
```

### BKND-02: Add country_of_origin to ProductCreateRequest
```python
# File: backend/src/modules/catalog/presentation/schemas.py
# After source_url (line 731), before tags (line 732):
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

### BKND-02: Wire in router
```python
# File: backend/src/modules/catalog/presentation/router_products.py
# Line 81-90, add country_of_origin to CreateProductCommand constructor:
command = CreateProductCommand(
    title_i18n=request.title_i18n,
    slug=request.slug,
    brand_id=request.brand_id,
    primary_category_id=request.primary_category_id,
    description_i18n=request.description_i18n,
    supplier_id=request.supplier_id,
    source_url=request.source_url,
    country_of_origin=request.country_of_origin,  # NEW
    tags=request.tags,
)
```

### Discretionary: Fix AttributeCreateRequest
```python
# File: backend/src/modules/catalog/presentation/schemas.py
# Line 335: BEFORE
description_i18n: I18nDict = Field(default_factory=dict)

# Line 335: AFTER
description_i18n: I18nDict | None = None
```

### Discretionary: Fix CreateAttributeCommand
```python
# File: backend/src/modules/catalog/application/commands/create_attribute.py
# Line 63: BEFORE
description_i18n: dict[str, str] = field(default_factory=dict)

# Line 63: AFTER
description_i18n: dict[str, str] | None = None
```

### Discretionary: Fix BulkCreateAttributeItem
```python
# File: backend/src/modules/catalog/application/commands/bulk_create_attributes.py
# Line 51: BEFORE
description_i18n: dict[str, str] = field(default_factory=dict)

# Line 51: AFTER
description_i18n: dict[str, str] | None = None
```

### Discretionary: Fix AttributeTemplateCreateRequest
```python
# File: backend/src/modules/catalog/presentation/schemas.py
# Line 1174: BEFORE
description_i18n: I18nDict | None = Field(default_factory=dict)

# Line 1174: AFTER
description_i18n: I18nDict | None = None
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 with pytest-asyncio (mode: auto) |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q` |
| Full suite command | `cd backend && uv run pytest tests/ -x -q --timeout=60` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKND-01 | Product created without descriptionI18n returns 201 | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_create_product_without_description"` | Wave 0 gap |
| BKND-01 | Product created with explicit null descriptionI18n returns 201 | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_create_product_null_description"` | Wave 0 gap |
| BKND-01 | Product created with valid descriptionI18n still works (backward compat) | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_create_product_with_description"` | Wave 0 gap |
| BKND-01 | GET product returns {} (not null) for descriptionI18n when omitted | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_product_description_empty"` | Wave 0 gap |
| BKND-02 | Product created with countryOfOrigin stores it correctly | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_create_product_with_country"` | Wave 0 gap |
| BKND-02 | Product created with invalid countryOfOrigin returns 422 | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_create_product_invalid_country"` | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q`
- **Per wave merge:** `cd backend && uv run pytest tests/ -x -q --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_without_description` -- POST without descriptionI18n returns 201
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_null_description` -- POST with `"descriptionI18n": null` returns 201
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_with_description` -- POST with valid descriptionI18n returns 201 (backward compat)
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_product_description_stored_as_empty_dict` -- GET product after creation without description shows `"descriptionI18n": {}`
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_with_country_of_origin` -- POST with `"countryOfOrigin": "CN"` returns 201 and persists
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_invalid_country_code_returns_422` -- POST with `"countryOfOrigin": "X"` returns 422

## Open Questions

1. **D-05 Contradiction -- RESOLVED**
   - What we know: DB column is NOT NULL (Alembic line 1610, ORM line 514), D-11 says no migration, D-05 says store None.
   - Resolution: Override D-05 -- store `{}` in DB when description omitted. This preserves D-11 (no migration) and existing domain behavior. Response returns `{}` not `null`. The `description_i18n or {}` guard at entities/product.py:193 is the correct behavior.
   - Risk: None. The API accepts None (user-facing improvement), domain converts to `{}` (existing behavior), DB stores `{}` (existing behavior). Zero behavioral change in DB or responses.

2. **Discretionary fix scope -- RECOMMENDATION: FIX THEM**
   - schemas.py:335 (AttributeCreateRequest) and schemas.py:1174 (AttributeTemplateCreateRequest) have the identical bug.
   - The fix is identical: `I18nDict | None = None`.
   - The cascade command dataclasses also need fixing: create_attribute.py:63 and bulk_create_attributes.py:51.
   - Total additional lines changed: 4 (2 schema, 2 command dataclass). AttributeTemplateCreateRequest's command (create_attribute_template.py:35) is already `dict[str, str] | None = None`.
   - Domain entities already handle None correctly (both have `or {}` guards).
   - Recommendation: Fix all of them in this phase. The bug is identical, the fix is identical, and leaving known bugs creates future confusion about whether they are intentional.

## Sources

### Primary (HIGH confidence)
All findings verified by direct source code inspection:
- `backend/src/modules/catalog/presentation/schemas.py` -- I18nDict type (line 77), _validate_i18n_keys (lines 52-74), ProductCreateRequest (lines 717-734), ProductUpdateRequest (lines 745-777), ProductResponse (lines 902-924), AttributeCreateRequest (lines 323-349), AttributeTemplateCreateRequest (lines 1163-1175)
- `backend/src/modules/catalog/application/commands/create_product.py` -- CreateProductCommand (lines 32-58), handler truthiness check (lines 145-147), Product.create() call (lines 140-152)
- `backend/src/modules/catalog/domain/entities/product.py` -- Product.create() (lines 149-217), description_i18n handling (line 193: `description_i18n or {}`), description_i18n attr type (line 110)
- `backend/src/modules/catalog/infrastructure/models.py` -- ProductModel.description_i18n (lines 514-516): `Mapped[dict[str, Any]]`, NOT NULL; country_of_origin (line 518): `Mapped[str | None]`; AttributeModel.description_i18n (lines 292-294): NOT NULL; AttributeTemplateModel.description_i18n (lines 187-189): NOT NULL
- `backend/alembic/versions/2026/03/27_0911_19_7ce70774f240_init.py` -- products table description_i18n (lines 1606-1611): `nullable=False`; country_of_origin (line 1618): `nullable=True`
- `backend/src/modules/catalog/presentation/router_products.py` -- create_product handler (lines 76-96), missing country_of_origin wiring (lines 81-89)
- `backend/src/modules/catalog/application/queries/get_product.py` -- _to_read_model (lines 134-156), description_i18n=orm.description_i18n (line 138)
- `backend/src/modules/catalog/application/queries/read_models.py` -- ProductReadModel.description_i18n: dict[str, str] (line 364)
- `backend/src/modules/catalog/infrastructure/repositories/product.py` -- _to_orm (line 292), _base_product_fields (lines 224-226)
- `backend/src/modules/catalog/application/commands/create_attribute.py` -- CreateAttributeCommand.description_i18n (line 63)
- `backend/src/modules/catalog/application/commands/bulk_create_attributes.py` -- BulkCreateAttributeItem.description_i18n (line 51)
- `backend/src/modules/catalog/application/commands/create_attribute_template.py` -- CreateAttributeTemplateCommand.description_i18n (line 35, already `dict[str, str] | None = None`)
- `backend/src/modules/catalog/domain/entities/attribute.py` -- Attribute.create() (line 189: `description_i18n or {}`)
- `backend/src/modules/catalog/domain/entities/attribute_template.py` -- AttributeTemplate.create() (line 90: `description_i18n or {}`)
- `backend/tests/e2e/api/v1/catalog/test_products.py` -- existing e2e product tests
- `backend/tests/e2e/api/v1/catalog/test_lifecycle.py` -- full lifecycle test
- `backend/tests/unit/modules/catalog/application/commands/test_product_handlers.py` -- unit tests for CreateProductHandler
- `backend/tests/unit/modules/catalog/domain/test_product.py` -- domain entity tests
- `backend/tests/factories/product_builder.py` -- ProductBuilder with description_i18n handling (line 99)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all changes use existing patterns
- Architecture: HIGH -- every layer inspected with exact line numbers and types verified against source
- Pitfalls: HIGH -- D-05/NOT NULL conflict verified against ORM model, Alembic migration, and domain entity code
- Test impact: HIGH -- all test files identified and verified no breakage; wave 0 gaps documented
- Change manifest: HIGH -- every file:line traced through full request-response lifecycle

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- no library upgrades involved)
