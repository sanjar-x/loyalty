# Phase 1: Backend Schema Fixes - Research

**Researched:** 2026-03-29
**Domain:** Pydantic schema validation, FastAPI request wiring, Python dataclass cascading, SQLAlchemy ORM column nullability
**Confidence:** HIGH

## Summary

Phase 1 fixes two integration bugs in the product creation flow: making `descriptionI18n` truly optional (BKND-01) and wiring `countryOfOrigin` to `ProductCreateRequest` (BKND-02). Both are mechanical changes that follow established patterns already used in the codebase's update schemas.

The primary finding is that the current `I18nDict = Field(default_factory=dict)` pattern is broken: it produces an empty dict `{}` which triggers the `_validate_i18n_keys` AfterValidator, failing with "Missing required locales: en, ru". This means any client that omits `descriptionI18n` will receive a 422 validation error. The fix is changing to `I18nDict | None = None`, which Pydantic resolves as a union type where `None` bypasses the AfterValidator entirely.

A critical constraint discovered during research: the `products.description_i18n` database column is `NOT NULL` with `server_default='{}'::jsonb`. Decision D-05 from CONTEXT.md states "store None in DB (not {})", but this would require an Alembic migration to make the column nullable. Since D-11 explicitly states "No Alembic migration needed", the correct approach is to store `{}` in DB when description is omitted (the domain layer already does this via `description_i18n or {}` in `Product.create()`). The response schema should remain `dict[str, str]` (not `dict[str, str] | None`).

**Primary recommendation:** Change `description_i18n` to `I18nDict | None = None` in `ProductCreateRequest`, keep domain/ORM/response behavior as-is (converts `None` to `{}`), add `country_of_origin` field to `ProductCreateRequest` and wire it in the router.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Change `description_i18n: I18nDict = Field(default_factory=dict)` to `description_i18n: I18nDict | None = None` in ProductCreateRequest (schemas.py:729)
- **D-02:** Same pattern already used in ProductUpdateRequest (schemas.py:760) -- follow the existing convention
- **D-03:** Cascade through command dataclass: `CreateProductCommand.description_i18n` must accept `dict | None` (currently `dict` -- verify and fix if needed)
- **D-04:** Domain entity `Product.create()` already handles None description_i18n (create_product.py:150 passes it through, entity has `description_i18n: dict[str, str]` default)
- **D-05:** When `None` is passed, store `None` in DB (not `{}`). API response shows `null` for description_i18n. **RESEARCH OVERRIDE: DB column is NOT NULL -- storing None requires Alembic migration which D-11 prohibits. Store `{}` instead, which domain layer already does.**
- **D-06:** Existing ProductCreateRequest responses (schemas.py line ~908) use `dict[str, str]` which accepts both `{}` and populated dicts -- no response schema change needed, but consider `dict[str, str] | None` if DB stores None. **RESEARCH CLARIFICATION: Since DB stores `{}` (not None), response schema stays `dict[str, str]`.**
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

| ID | Description | Research Support |
|----|-------------|------------------|
| BKND-01 | User can create product without descriptionI18n (field truly optional: `I18nDict \| None = None`) | Full layer-by-layer analysis complete. Schema change is single-line. Command dataclass needs `dict[str, str] \| None` type. Domain and ORM already handle None correctly. No response schema change needed. |
| BKND-02 | User can set countryOfOrigin when creating product (field added to ProductCreateRequest and wired through command) | Field pattern exists in ProductUpdateRequest (line 764). Command already has the field (line 55). Only schema addition + router wiring needed. |
</phase_requirements>

## Standard Stack

No new libraries needed. All changes use existing project dependencies.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | v2 (bundled with FastAPI) | Request/response schema validation | Already used for all schemas via CamelModel |
| FastAPI | >=0.115.0 | Route handler wiring | Existing framework |
| attrs | >=25.4.0 | Domain entity dataclass definition | Already used for Product entity |
| SQLAlchemy | >=2.1.0b1 | ORM model Mapped types | Existing infrastructure |
| pytest | >=9.0.2 | Test runner | Existing test infrastructure |

## Architecture Patterns

### Layer Flow for Changes
```
ProductCreateRequest (schema, Pydantic)
  -> create_product() (router, FastAPI handler)
    -> CreateProductCommand (frozen dataclass)
      -> CreateProductHandler.handle() (application)
        -> Product.create() (domain factory method)
          -> ProductRepository._to_orm() (infrastructure)
            -> ProductModel (ORM -> PostgreSQL)
```

### Pattern 1: Optional I18nDict Field
**What:** Union type `I18nDict | None = None` where Pydantic resolves None before reaching AfterValidator
**When to use:** Any i18n field that should be optional
**Example:**
```python
# Source: backend/src/modules/catalog/presentation/schemas.py:760 (existing pattern)
description_i18n: I18nDict | None = None
```
When `None` is the input, Pydantic's union type resolution matches `None` against the `None` branch of the union first, so `_validate_i18n_keys` (the AfterValidator on `I18nDict`) is never called.

### Pattern 2: Optional Country Code Field
**What:** ISO 3166-1 alpha-2 field with regex validation
**When to use:** Any country code field
**Example:**
```python
# Source: backend/src/modules/catalog/presentation/schemas.py:764 (existing pattern)
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

### Pattern 3: Router-to-Command Wiring
**What:** Each field in request schema maps 1:1 to CreateProductCommand constructor args
**When to use:** Adding new fields to request schemas
**Example:**
```python
# Source: backend/src/modules/catalog/presentation/router_products.py:81-90
command = CreateProductCommand(
    title_i18n=request.title_i18n,
    slug=request.slug,
    brand_id=request.brand_id,
    primary_category_id=request.primary_category_id,
    description_i18n=request.description_i18n,
    supplier_id=request.supplier_id,
    source_url=request.source_url,
    country_of_origin=request.country_of_origin,  # <-- ADD THIS
    tags=request.tags,
)
```

### Anti-Patterns to Avoid
- **`I18nDict = Field(default_factory=dict)` for optional fields:** The empty dict `{}` triggers `_validate_i18n_keys` which requires `ru` and `en` keys, producing a 422 error. Use `I18nDict | None = None` instead.
- **Changing DB column nullability without Alembic migration:** The `products.description_i18n` column is `NOT NULL`. Do not attempt to store `None` in it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| I18n validation bypass for None | Custom None-checking logic in validator | `I18nDict \| None = None` union type | Pydantic handles union resolution natively; None branch is matched before AfterValidator runs |
| Country code validation | Manual regex checking in handler | `Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` | Pydantic Field constraints handle this declaratively |

## Common Pitfalls

### Pitfall 1: D-05 Conflict -- DB Column is NOT NULL
**What goes wrong:** CONTEXT.md D-05 says "store None in DB (not {})". But `products.description_i18n` column is `NOT NULL` (Alembic migration line 1607-1610). Storing None will cause `IntegrityError`.
**Why it happens:** D-05 was decided without verifying DB column constraints.
**How to avoid:** Keep existing domain behavior: `Product.create()` line 193 already converts `None` to `{}` via `description_i18n=description_i18n or {}`. This stores `{}` in DB, which the NOT NULL column accepts.
**Warning signs:** IntegrityError during product creation when description_i18n is omitted.
**Resolution:** D-05 is overridden. The API accepts None (schema) but stores {} (DB). Response returns `{}` not `null`. No Alembic migration needed (D-11 preserved).

### Pitfall 2: CreateProductCommand truthiness check in handler
**What goes wrong:** In `CreateProductHandler.handle()` (line 145-147), there is a truthiness check:
```python
description_i18n=command.description_i18n
if command.description_i18n
else None,
```
This converts empty dict `{}` to `None`, which is correct for the domain layer. But if `command.description_i18n` is already `None` (after our schema fix), the truthiness check also passes it as `None` to `Product.create()`. This is correct -- `Product.create()` handles None by converting to `{}`.
**How to avoid:** No code change needed here. The existing truthiness check works correctly for both `{}` and `None`.

### Pitfall 3: Same anti-pattern in other Create schemas
**What goes wrong:** Two other schemas have the same `default_factory=dict` pattern:
- `AttributeCreateRequest.description_i18n` (line 335): `I18nDict = Field(default_factory=dict)`
- `AttributeTemplateCreateRequest.description_i18n` (line 1174): `I18nDict | None = Field(default_factory=dict)` -- note this one has `| None` but still uses `default_factory=dict`, which means the default is `{}` not `None`, so it still triggers the validator.
**How to avoid:** These are noted in Claude's Discretion area. If fixing them, change to `I18nDict | None = None` pattern.

### Pitfall 4: ProductVariantCreateRequest is already correct
**What goes wrong:** One might think VariantCreateRequest has the same bug, but it already uses `I18nDict | None = None` (line 953). No fix needed there.
**Warning signs:** Checking line 335 shows AttributeCreateRequest (not VariantCreateRequest) has the bug.

### Pitfall 5: Response schema type mismatch if DB stores None
**What goes wrong:** If someone changes the ORM model to store None, `ProductResponse.description_i18n: dict[str, str]` would fail Pydantic serialization when the DB returns NULL.
**How to avoid:** Since we keep `{}` in DB, this is not an issue. But if D-05 is ever revisited: change response to `dict[str, str] | None = None`, the ProductReadModel to `dict[str, str] | None`, and add an Alembic migration.

## Code Examples

### BKND-01: Fix description_i18n in ProductCreateRequest
```python
# File: backend/src/modules/catalog/presentation/schemas.py
# Line 729: BEFORE
description_i18n: I18nDict = Field(default_factory=dict)

# Line 729: AFTER
description_i18n: I18nDict | None = None
```

### BKND-01: Fix CreateProductCommand type hint (if needed)
```python
# File: backend/src/modules/catalog/application/commands/create_product.py
# Line 52: BEFORE
description_i18n: dict[str, str] = field(default_factory=dict)

# Line 52: AFTER
description_i18n: dict[str, str] | None = None
```
NOTE: The command dataclass CURRENTLY has `dict[str, str] = field(default_factory=dict)`. Changing to `dict[str, str] | None = None` makes the types consistent. The handler's truthiness check (line 145-147) already handles both None and {} correctly.

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

## Layer-by-Layer Analysis

### Schema Layer (schemas.py)
| Field | Current Type | Target Type | Notes |
|-------|-------------|-------------|-------|
| ProductCreateRequest.description_i18n | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` | Core fix for BKND-01 |
| ProductCreateRequest.country_of_origin | (does not exist) | `str \| None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` | Core fix for BKND-02 |
| ProductResponse.description_i18n | `dict[str, str]` | `dict[str, str]` (unchanged) | DB stores {} not None |

### Command Layer (create_product.py)
| Field | Current Type | Target Type | Notes |
|-------|-------------|-------------|-------|
| CreateProductCommand.description_i18n | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` | Type consistency fix |
| CreateProductCommand.country_of_origin | `str \| None = None` | `str \| None = None` (unchanged) | Already exists |

### Domain Layer (entities/product.py)
| Field | Current Type | Needs Change | Notes |
|-------|-------------|--------------|-------|
| Product.create() description_i18n param | `dict[str, str] \| None = None` | No | Already handles None (line 193: `description_i18n or {}`) |
| Product.description_i18n attr | `dict[str, str]` | No | Always stores a dict (never None) |
| Product.create() country_of_origin param | `str \| None = None` | No | Already exists (line 158) |

### ORM/Repository Layer (models.py, repositories/product.py)
| Field | Current State | Needs Change | Notes |
|-------|--------------|--------------|-------|
| ProductModel.description_i18n | `Mapped[dict[str, Any]]`, NOT NULL | No | Column stays NOT NULL, stores {} for empty |
| ProductRepository._to_orm() | Sets `orm.description_i18n = entity.description_i18n` | No | Entity always has dict, never None |
| ProductRepository._base_product_fields() | `"description_i18n": dict(orm.description_i18n) if orm.description_i18n else {}` | No | Already handles empty dict |

### Router Layer (router_products.py)
| Change | Current | Target | Notes |
|--------|---------|--------|-------|
| create_product handler | Missing country_of_origin in CreateProductCommand constructor | Add `country_of_origin=request.country_of_origin` | Single line addition |

## Existing Test Impact

### Files that test product creation:
| File | Impact | Action |
|------|--------|--------|
| `tests/unit/modules/catalog/domain/test_product.py` | No impact. Tests use `ProductBuilder` which passes `description_i18n or None` already. | No changes needed |
| `tests/factories/product_builder.py` | No impact. Line 99: `description_i18n=self._description_i18n or None` already passes None when empty dict. | No changes needed |
| `tests/e2e/api/v1/catalog/test_products.py` | No impact. `create_product()` helper omits `descriptionI18n` from payload (line 33-38), which will now work correctly. | No changes needed; optionally add test for explicit null |
| `tests/e2e/api/v1/catalog/test_lifecycle.py` | No impact. Also omits `descriptionI18n` from payload (line 68-73). | No changes needed |
| `tests/integration/modules/catalog/infrastructure/repositories/test_product.py` | No impact. Tests country_of_origin at domain/repo level, not schema level. | No changes needed |

### Other `default_factory=dict` locations (same anti-pattern):
| File:Line | Schema | Current | Status |
|-----------|--------|---------|--------|
| schemas.py:335 | AttributeCreateRequest.description_i18n | `I18nDict = Field(default_factory=dict)` | Same bug -- Claude's discretion whether to fix |
| schemas.py:1174 | AttributeTemplateCreateRequest.description_i18n | `I18nDict \| None = Field(default_factory=dict)` | Broken default -- Claude's discretion |
| schemas.py:454 | AttributeValueCreateRequest.meta_data | `BoundedJsonDict = Field(default_factory=dict, ...)` | Different type (BoundedJsonDict), different validator -- not the same bug |
| schemas.py:897 | ProductAttributeResponse.attribute_name_i18n | `dict[str, str] = Field(default_factory=dict)` | Response schema, not I18nDict type -- no AfterValidator runs on response |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 with pytest-asyncio (mode: auto) |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product.py -x -q` |
| Full suite command | `cd backend && uv run pytest tests/ -x -q --timeout=60` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKND-01 | Product created without descriptionI18n returns 201 | e2e | `cd backend && uv run pytest tests/e2e/api/v1/catalog/test_products.py -x -q -k "test_create"` | Existing tests cover this implicitly (create_product helper omits descriptionI18n) |
| BKND-01 | Product created with explicit null descriptionI18n returns 201 | e2e | (same file, new test) | Wave 0 gap |
| BKND-01 | Product created with valid descriptionI18n still works | e2e | (same file, new test) | Wave 0 gap |
| BKND-02 | Product created with countryOfOrigin stores it correctly | e2e | (same file, new test) | Wave 0 gap |
| BKND-02 | Product created with invalid countryOfOrigin returns 422 | e2e | (same file, new test) | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product.py tests/e2e/api/v1/catalog/test_products.py -x -q`
- **Per wave merge:** `cd backend && uv run pytest tests/ -x -q --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_without_description` -- covers BKND-01 (explicit null)
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_with_description` -- covers BKND-01 (with valid i18n)
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_with_country_of_origin` -- covers BKND-02
- [ ] `tests/e2e/api/v1/catalog/test_products.py::test_create_product_invalid_country_code_returns_422` -- covers BKND-02 validation

## Open Questions

1. **D-05 Contradiction**
   - What we know: DB column is NOT NULL, D-11 says no migration, D-05 says store None.
   - What's unclear: Whether user intended None in DB (requiring migration) or None in API input (which domain converts to {}).
   - Recommendation: Override D-05 -- store `{}` in DB when description omitted. This preserves D-11 (no migration) and existing domain behavior. Response returns `{}` not `null`. If user wants `null` in responses, that is a separate phase requiring Alembic migration.

2. **Discretionary fix scope**
   - What we know: Lines 335 and 1174 have the same `default_factory=dict` anti-pattern with I18nDict.
   - What's unclear: Whether fixing them is worth the additional test surface in this phase.
   - Recommendation: Fix them. The change is identical to BKND-01 (single line each), and the pattern is already proven safe in update schemas. The alternative is leaving known bugs in the codebase.

## Sources

### Primary (HIGH confidence)
- `backend/src/modules/catalog/presentation/schemas.py` -- direct source code inspection of I18nDict type (line 77), _validate_i18n_keys (line 52-74), ProductCreateRequest (line 717-734), ProductUpdateRequest (line 745-777), ProductResponse (line 902-924)
- `backend/src/modules/catalog/application/commands/create_product.py` -- CreateProductCommand (line 32-58), handler truthiness check (line 145-147)
- `backend/src/modules/catalog/domain/entities/product.py` -- Product.create() (line 149-217), description_i18n handling (line 193: `description_i18n or {}`)
- `backend/src/modules/catalog/infrastructure/models.py` -- ProductModel.description_i18n (line 514-516): `Mapped[dict[str, Any]]`, NOT NULL
- `backend/alembic/versions/2026/03/27_0911_19_7ce70774f240_init.py` -- products table (line 1593-1610): `description_i18n` JSONB `nullable=False`
- `backend/src/modules/catalog/infrastructure/repositories/product.py` -- _to_orm (line 292), _base_product_fields (line 224)
- `backend/src/modules/catalog/presentation/router_products.py` -- create_product handler (line 76-96)
- `backend/tests/e2e/api/v1/catalog/test_products.py` -- existing e2e product tests
- `backend/tests/unit/modules/catalog/domain/test_product.py` -- existing unit tests for Product.create()
- `backend/tests/factories/product_builder.py` -- ProductBuilder with description_i18n handling

### Secondary (MEDIUM confidence)
- Python test confirming `_validate_i18n_keys({})` raises "Missing required locales" -- validated the core bug

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all changes use existing patterns
- Architecture: HIGH -- every layer inspected with exact line numbers and types verified
- Pitfalls: HIGH -- D-05/NOT NULL conflict verified against both ORM model and Alembic migration
- Test impact: HIGH -- all test files identified and verified no breakage

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- no library upgrades involved)
