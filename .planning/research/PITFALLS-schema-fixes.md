# Pitfalls Research: Backend Schema Fixes

**Context:** Fixing 2 issues in `ProductCreateRequest` (schemas.py line 717-735):
1. Changing `description_i18n` from `I18nDict` with `default_factory=dict` to `Optional[I18nDict] = None`
2. Adding `country_of_origin` as a new optional field

**Files analyzed:**
- `backend/src/modules/catalog/presentation/schemas.py` (lines 717-735)
- `backend/src/shared/schemas.py` (CamelModel base)
- `backend/src/modules/catalog/application/commands/create_product.py`
- `backend/src/modules/catalog/presentation/router_products.py` (lines 76-96)
- `backend/src/modules/catalog/domain/entities/product.py` (Product.create factory)

---

## Pitfall 1: I18nDict validator rejects empty dict -- the current code is ALREADY broken

**Risk:** The current `description_i18n: I18nDict = Field(default_factory=dict)` on line 729 is a latent bug. When a client omits `descriptionI18n` from the JSON body, Pydantic fills it with `{}` via `default_factory=dict`. Then the `I18nDict` AfterValidator (`_validate_i18n_keys`) runs and checks `_REQUIRED_LOCALES - value.keys()`, finding `{"ru", "en"}` missing from the empty dict. This raises a `ValueError`: "Missing required locales: en, ru".

This means **no product can currently be created without explicitly providing `descriptionI18n` with both `ru` and `en` keys** -- the field is not truly optional despite having a default.

The same bug exists on:
- `AttributeCreateRequest.description_i18n` (line 335)
- `AttributeTemplateCreateRequest.description_i18n` (line 1174, but typed as `I18nDict | None` which partially mitigates it -- see Pitfall 2)

**Prevention:** Changing to `Optional[I18nDict] = None` correctly fixes this. When the client omits the field, Pydantic sets it to `None`. The `I18nDict` AfterValidator only runs when a dict value is actually provided. When it IS provided, it must still contain `ru` and `en`, which is the correct business rule.

## Pitfall 2: None vs {} reaches different code paths in the handler and domain

**Risk:** The router (line 86) passes `request.description_i18n` directly to `CreateProductCommand.description_i18n`. When changing from `default_factory=dict` to `Optional[...] = None`, this value changes from `{}` to `None` for omitted fields.

The handler (create_product.py line 145) does:
```python
description_i18n=command.description_i18n if command.description_i18n else None,
```

The `if command.description_i18n` check is falsy for both `None` and `{}`, so both cases pass `None` to `Product.create()`. This is safe -- the handler already handles the None case correctly.

`Product.create()` (entities/product.py line 193) does:
```python
description_i18n=description_i18n or {},
```

This converts `None` back to `{}` for storage. So the domain entity always stores a dict, never None.

**Prevention:** This chain (`None` -> handler checks falsy -> passes `None` -> entity converts to `{}`) already works correctly. No additional changes needed. But verify this by tracing the full path in a test.

## Pitfall 3: Router does NOT pass country_of_origin to CreateProductCommand

**Risk:** This is the critical missing wiring. The current router (line 81-90) builds `CreateProductCommand` but does NOT include `country_of_origin`:

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
    # country_of_origin is MISSING
)
```

Adding `country_of_origin` to `ProductCreateRequest` without also adding it to the router's command construction means the field is silently ignored. The client sends `countryOfOrigin: "CN"`, Pydantic validates it, but it never reaches the command or domain entity.

`CreateProductCommand` already has `country_of_origin: str | None = None` (line 47), and `Product.create()` already accepts it (line 160). The only gap is the router wiring.

**Prevention:** When adding `country_of_origin` to the schema, ALSO add `country_of_origin=request.country_of_origin` to the `CreateProductCommand(...)` constructor call in `router_products.py` line 81-90.

## Pitfall 4: CamelCase alias for country_of_origin must be verified

**Risk:** With `alias_generator=to_camel`, `country_of_origin` becomes `countryOfOrigin` in JSON. This is a three-word field, and `to_camel` from pydantic must handle it correctly. Since `to_camel` converts `country_of_origin` -> `countryOfOrigin`, this works as expected.

However, `ProductUpdateRequest` already has this field (line 764-766) with validation:
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

The new `ProductCreateRequest` field MUST use the same validation constraints for consistency. If the create schema omits `min_length`/`max_length`/`pattern`, invalid country codes (e.g., `"x"`, `"usa"`) will pass schema validation at create time but be caught at update time, creating an inconsistent API experience.

**Prevention:** Copy the exact field definition from `ProductUpdateRequest`:
```python
country_of_origin: str | None = Field(
    None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
)
```

## Pitfall 5: OpenAPI schema changes are backward-incompatible for existing clients

**Risk:** Two OpenAPI changes happen simultaneously:
1. `descriptionI18n` changes from required (with default `{}`) to optional (nullable). Some OpenAPI client generators treat "required with default" differently from "optional nullable". Clients regenerating from the spec may see type changes.
2. `countryOfOrigin` is added as a new optional field. This is additive and safe for existing clients (they simply don't send it).

The real risk is (1): if any frontend code explicitly sends `descriptionI18n: {}` (because the old schema required it or because a form initializes with the default), the request will now fail with a 422 because `I18nDict` validation rejects `{}` (missing `ru` and `en`).

**Prevention:** Check all frontend code that constructs product creation payloads. Search for `descriptionI18n` in `frontend/admin/` and `frontend/main/`. If any code sends `descriptionI18n: {}`, it must be updated to either omit the field or provide valid locales.

## Pitfall 6: The same default_factory=dict bug exists in AttributeCreateRequest

**Risk:** `AttributeCreateRequest.description_i18n` (line 335) uses the identical broken pattern:
```python
description_i18n: I18nDict = Field(default_factory=dict)
```

If we fix only `ProductCreateRequest`, the same bug remains in `AttributeCreateRequest`. This is inconsistent and confusing for API consumers.

**Prevention:** Fix both schemas simultaneously. Also fix `AttributeTemplateCreateRequest.description_i18n` (line 1174) which uses `I18nDict | None = Field(default_factory=dict)` -- a mixed pattern where the type allows None but the default is `{}`, meaning the AfterValidator still runs on the empty dict default.

## Pitfall 7: model_fields_set behavior changes for description_i18n

**Risk:** In PATCH schemas (like `ProductUpdateRequest`), `model_fields_set` is used to distinguish "not sent" from "explicitly sent as null". For the CREATE schema, `model_fields_set` is not currently used in the router. However, if future code or tests check `model_fields_set` on `ProductCreateRequest`, the behavior changes:

- Old: `description_i18n` is always in `model_fields_set` (because Pydantic v2 includes fields with `default_factory` in `model_fields_set` only when explicitly provided by the caller -- actually, with `default_factory`, it is NOT in `model_fields_set` when omitted). Correction: in Pydantic v2, `default_factory` fields omitted from input are NOT in `model_fields_set`.
- New: `description_i18n` with `Optional[I18nDict] = None` -- when omitted, it is NOT in `model_fields_set`. When sent as `null`, it IS in `model_fields_set` with value `None`.

This distinction matters if the router ever uses `model_fields_set` (it currently does not for create, only for update).

**Prevention:** No action needed for current code. But document that `None` means "not provided" for the create schema, and the handler correctly treats falsy values as "use empty dict".

---

## Test Implications

### Tests that will NOT break:
- **Unit tests** (`test_product.py`): These test `Product.create()` directly, not the schema. They pass dicts directly, bypassing Pydantic validation. No impact.
- **Builder tests** (`product_builder.py`): The builder passes `description_i18n=self._description_i18n or None` -- already handles the None case.

### Tests that MIGHT break:
- **E2E tests** (`tests/e2e/api/v1/catalog/test_products.py`): The `create_product` helper (line 22-41) does NOT send `descriptionI18n` in the payload. Under the current buggy schema, this would fail with a 422 (I18nDict validator rejects `{}`). If these tests are currently passing, it means either:
  - (a) The tests are not actually running against a live server, OR
  - (b) There is middleware or error handling that silently catches this, OR
  - (c) The Pydantic AfterValidator does not run on default_factory values (this needs verification -- in Pydantic v2, validators DO run on defaults unless `validate_default=False` is set, but `AfterValidator` on `Annotated` types may behave differently).

  **Action:** Run the E2E test `test_create_product_success` to verify current behavior. If it passes, investigate why the validator does not reject `{}`.

### Tests that SHOULD be added:
1. **Schema unit test**: `ProductCreateRequest` with `descriptionI18n` omitted -> should parse successfully with `description_i18n = None`
2. **Schema unit test**: `ProductCreateRequest` with `descriptionI18n: null` -> should parse successfully with `description_i18n = None`
3. **Schema unit test**: `ProductCreateRequest` with valid `descriptionI18n: {"ru": "...", "en": "..."}` -> should parse and validate
4. **Schema unit test**: `ProductCreateRequest` with `descriptionI18n: {"ru": "..."}` (missing `en`) -> should fail validation
5. **Schema unit test**: `ProductCreateRequest` with `countryOfOrigin: "CN"` -> should parse
6. **Schema unit test**: `ProductCreateRequest` with `countryOfOrigin: "usa"` -> should fail (pattern `^[A-Z]{2}$`)
7. **E2E test**: Create product with `countryOfOrigin`, then GET product and verify it appears in response
8. **Integration test**: Verify the router passes `country_of_origin` through to the command and it persists to DB

---

## Summary

**Top 3 things to watch out for:**

1. **Router wiring gap (Pitfall 3):** Adding `country_of_origin` to the schema without adding it to the `CreateProductCommand(...)` call in `router_products.py` line 81-90 means the field is silently dropped. This is the most likely oversight.

2. **Validation constraint consistency (Pitfall 4):** The `country_of_origin` field in `ProductCreateRequest` must use the same `Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` as `ProductUpdateRequest` (line 764-766). Missing this creates asymmetric validation between create and update.

3. **Same bug in sibling schemas (Pitfall 6):** The `I18nDict = Field(default_factory=dict)` pattern is broken in three places: `ProductCreateRequest`, `AttributeCreateRequest`, and `AttributeTemplateCreateRequest`. Fix all three to avoid inconsistency and repeated bug reports.
