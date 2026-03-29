# Phase 2: Frontend i18n & Spec Alignment - Research

**Researched:** 2026-03-29 (re-research: deeper verification)
**Domain:** Admin frontend i18n payload correctness + specification accuracy
**Confidence:** HIGH

## Summary

Phase 2 fixes three classes of i18n bugs in the admin frontend and corrects the product creation spec. Research verified every claim from the previous iteration by reading all source files line-by-line, running the backend `to_camel` function empirically, and tracing data flow from form through BFF to backend schemas.

**Bug class 1 -- Conditional locale inclusion (useProductForm.js):** The product form conditionally includes the `en` locale using spread syntax (`...(state.titleEn ? { en: state.titleEn } : {})`). When the user leaves `en` empty, the backend receives only `{ru: "..."}` and returns 422 "Missing required locales" because `_REQUIRED_LOCALES = {"ru", "en"}` in `schemas.py:49`.

**Bug class 2 -- Plain string where i18n dict expected (CategoryModal.jsx):** The category modal sends `{ name, slug, sortOrder }` but `CategoryCreateRequest` requires `name_i18n: I18nDict` (camelCase alias: `nameI18N`). The backend ignores the unknown `name` field and returns 422 for missing `nameI18N`. Additionally, the edit flow reads `category.name` from the tree response, but the backend returns `nameI18N` (an i18n dict), so `category.name` is always `undefined`.

**Bug class 3 -- Display reading wrong field (CategoryNode.jsx, CategoriesPage.jsx):** `CategoryNode` renders `node.name` (line 29) but `CategoryTreeResponse` serializes `name_i18n` as `nameI18N`. The display shows `undefined`. `CategoriesPage.handleEdit` at line 44 passes `category.name` to the modal, which is also `undefined`.

The spec file (`product-creation-flow.md`, 921 lines) has 19 occurrences of incorrect `I18n` (lowercase n), a factually wrong explanation of `to_camel` at lines 36-37, and is missing Phase 1 changes (`countryOfOrigin` added, `descriptionI18N` now truly optional).

**Primary recommendation:** Fix product form i18n fallback, fix CategoryModal to send `nameI18N` dict and read `nameI18N` for edit, fix CategoryNode display, extract a shared `buildI18nPayload` helper, and do a full spec accuracy pass -- as two focused plans (code + spec).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** When user doesn't fill in `en`, copy `ru` value to `en` before sending to backend. This ensures backend never receives incomplete i18n dicts.
- **D-02:** Apply in `useProductForm.js` `productPayload` useMemo -- both `titleI18N` and `descriptionI18N` must always include `{ru, en}` keys when sent.
- **D-03:** Current bug: lines 323-326 conditionally include `en` only if `state.titleEn` is truthy; lines 332-335 same for description. Both need fixing.
- **D-04:** Audit ALL POST/PATCH requests in admin frontend for i18n payload correctness, not just product creation.
- **D-05:** Known write forms to audit: useProductForm.js, CategoryModal.jsx, BrandSelect.jsx, RoleModal.jsx.
- **D-06:** For each form: if backend expects i18n dict but frontend sends plain string, add i18n wrapper. If backend accepts plain string, no change needed.
- **D-07:** Replace all 19 occurrences of `I18n` (lowercase n) with `I18N` (uppercase N) in `product-creation-flow.md`.
- **D-08:** Update the incorrect note at lines 36-37 that explains Pydantic `to_camel` behavior.
- **D-09:** Full review of all JSON examples in the spec (921 lines) for accuracy against current backend behavior.

### Claude's Discretion
- Whether to extract i18n payload building into a shared helper function (e.g., `buildI18nPayload(ru, en)`) or keep inline in each form
- Exact wording of the corrected spec note about to_camel behavior
- Order of fixes (product form first, then audit, then spec -- or different sequence)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| I18N-01 | Admin form always sends both ru+en locales in all i18n fields (fallback: ru value used for empty en) | Verified 3 bugs: (1) useProductForm.js lines 325, 334 conditionally omit `en`; (2) CategoryModal.jsx line 66-68 sends plain `name` instead of `nameI18N` dict; (3) CategoryNode.jsx line 29 and CategoriesPage.jsx line 44 read `name` but response has `nameI18N`. BrandSelect and RoleModal confirmed clean. |
| I18N-02 | Spec product-creation-flow.md updated to reflect actual backend naming convention (titleI18N, uppercase N) | Verified empirically: `to_camel("name_i18n")` = `nameI18N`. Spec has exactly 19 `I18n` occurrences (confirmed via grep), 1 `I18N` occurrence (in the incorrect explanation). Lines 36-37 wrong: says `.capitalize()` but Pydantic uses `.title()`. Phase 1 changes (countryOfOrigin, truly optional descriptionI18N) not reflected. |
</phase_requirements>

## Standard Stack

No new libraries needed. Phase only modifies existing frontend JavaScript files and a Markdown spec file.

### Core (existing, no additions)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | ^16.1.x | Admin frontend framework (App Router) | Already in use |
| React | 19.x | UI rendering | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Prettier | ^3.6.2 | Code formatting (admin frontend) | Run after edits to ensure formatting compliance |

## Architecture Patterns

### Admin Frontend Write-Path Architecture
```
User Form (component)
  --> builds payload (useMemo / inline object)
    --> service function (services/*.js)
      --> fetch() to BFF route (/api/*)
        --> backendFetch() proxies to backend (/api/v1/*)
          --> Pydantic CamelModel validates + aliases
```

**Key insight:** BFF routes pass JSON body through WITHOUT transformation. Verified by reading all three category BFF routes:
- `frontend/admin/src/app/api/categories/route.js` (POST) -- line 42: `body: JSON.stringify(body)` -- pass-through
- `frontend/admin/src/app/api/categories/[id]/route.js` (PATCH) -- line 44: `body: JSON.stringify(body)` -- pass-through
- `frontend/admin/src/app/api/categories/tree/route.js` (GET) -- line 28: `return NextResponse.json(data)` -- pass-through

Whatever the form sends is exactly what the backend receives. There is no middleware that fixes i18n payloads.

### Pattern: Payload Building

Two patterns exist in the codebase:

1. **Hook-based (useProductForm.js):** `useReducer` + `useMemo` derives payload from state. I18n fields built inline in the memo.
2. **Inline (CategoryModal, BrandSelect):** Payload constructed directly in `handleSubmit` / `handleCreateBrand` functions.

Both patterns pass the payload to `fetch()` via `JSON.stringify(body)`.

### Pattern: CamelModel i18n Aliasing

Backend uses `pydantic.alias_generators.to_camel` with `populate_by_name=True`:

```python
# src/shared/schemas.py (line 20-28)
class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
```

**Verified empirically (ran in backend venv):**
```
to_camel("name_i18n")        -> "nameI18N"
to_camel("title_i18n")       -> "titleI18N"
to_camel("description_i18n") -> "descriptionI18N"
to_camel("value_i18n")       -> "valueI18N"
to_camel("group_name_i18n")  -> "groupNameI18N"
```

**Actual algorithm** (verified by reading source):
1. `to_pascal(snake)` calls `snake.title()` -- Python's `.title()` capitalizes every letter after a non-alpha character (including digits and underscores)
2. For `i18n`: `_` -> `I` (after underscore), `1` stays, `8` stays, `n` -> `N` (after digit 8, which is non-alpha)
3. Regex removes `_` between alphanumeric and uppercase: `Name_I18N` -> `NameI18N`
4. `to_camel` lowercases the first letter: `nameI18N`

This means:
- **Input:** Backend accepts BOTH `titleI18N` (alias) and `title_i18n` (field name) -- `populate_by_name=True`
- **Output:** Backend serializes as `titleI18N` (alias) -- always uppercase N

### Existing i18n Read Helper
`lib/utils.js` line 48-51 already has a read-side i18n helper:
```javascript
export function i18n(obj, fallback = '') {
  if (!obj || typeof obj !== 'object') return fallback;
  return obj.ru ?? obj.en ?? Object.values(obj)[0] ?? fallback;
}
```

Some components already use this correctly:
- `services/categories.js:36` -- `i18n(node.nameI18N, node.label ?? fallback)` -- CORRECT pattern
- `DynamicAttributes.jsx` -- `i18n(attribute.nameI18N)` -- CORRECT pattern
- `ProductDetailsForm.jsx:54` -- `i18n(attr.nameI18N, attr.code)` -- CORRECT pattern

But `CategoryNode.jsx` and `CategoriesPage.jsx` do NOT use it -- they read `node.name` directly.

### Anti-Patterns to Avoid
- **Conditional locale inclusion:** `...(state.titleEn ? { en: state.titleEn } : {})` -- this omits `en` when empty, causing backend 422. Always include both locales.
- **Plain string where i18n dict expected:** `{ name: "..." }` when backend schema has `name_i18n: I18nDict` -- the field is silently ignored by Pydantic (extra fields are discarded), creating a 422 for the missing required field.
- **Reading `.name` from i18n response:** Backend returns `nameI18N: { "ru": "...", "en": "..." }`. Reading `.name` gives `undefined`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| i18n payload with fallback | Copy-paste fallback logic in each form | Shared `buildI18nPayload(ru, en)` helper in `lib/utils.js` | DRY across 2+ forms, prevents future regressions |

**Recommendation (Claude's discretion):** Extract a `buildI18nPayload(ru, en)` helper to `lib/utils.js` next to the existing `i18n()` read helper. This creates a symmetric pair: `i18n()` for reading, `buildI18nPayload()` for writing. Used by `useProductForm.js` (2 call sites) and `CategoryModal.jsx` (1 call site), with potential for future forms.

## Verified Bug Inventory

### Bug 1: useProductForm.js -- Conditional `en` in titleI18N (line 325)

**File:** `frontend/admin/src/hooks/useProductForm.js`
**Exact code (lines 321-326):**
```javascript
const productPayload = useMemo(
  () => ({
    titleI18N: {
      ru: state.titleRu,
      ...(state.titleEn ? { en: state.titleEn } : {}),  // BUG: line 325
    },
```
**Impact:** When `state.titleEn` is empty string or falsy, `en` key is omitted. Backend `_validate_i18n_keys` at `schemas.py:58-63` checks `_REQUIRED_LOCALES - value.keys()` and returns 422 "Missing required locales: en".

### Bug 2: useProductForm.js -- Conditional `en` in descriptionI18N (line 334)

**File:** `frontend/admin/src/hooks/useProductForm.js`
**Exact code (lines 330-335):**
```javascript
...(state.descriptionRu
  ? {
      descriptionI18N: {
        ru: state.descriptionRu,
        ...(state.descriptionEn ? { en: state.descriptionEn } : {}),  // BUG: line 334
      },
    }
  : {}),
```
**Impact:** Same as Bug 1 but for description. Note: `descriptionI18N` is only sent when `state.descriptionRu` is truthy (correct -- it's optional). But when sent, it must have both locales.

### Bug 3: CategoryModal.jsx -- Sends plain `name` instead of `nameI18N` dict (lines 66-68)

**File:** `frontend/admin/src/components/admin/settings/categories/CategoryModal.jsx`
**Exact code (lines 66-68):**
```javascript
const body = isEdit
  ? { name, slug, sortOrder }
  : { name, slug, parentId, sortOrder };
```
**Backend expects (schemas.py:118-136):**
```python
class CategoryCreateRequest(CamelModel):
    name_i18n: I18nDict = Field(...)  # Required, serialized as "nameI18N"
    slug: str = Field(...)
    parent_id: uuid.UUID | None = Field(None)
    sort_order: int = Field(0, ge=0)
    template_id: uuid.UUID | None = Field(None)
```
**Impact:** Pydantic ignores unknown field `name` (CamelModel default behavior) and `nameI18N` is missing -> 422. Category creation is completely broken.

**CategoryUpdateRequest (schemas.py:171-187):**
```python
class CategoryUpdateRequest(CamelModel):
    name_i18n: I18nDict | None = Field(None, min_length=1)  # Optional for PATCH
    slug: str | None = Field(None)
    sort_order: int | None = Field(None, ge=0)
    template_id: uuid.UUID | None = Field(None)
```
**Impact for edit:** Edit sends `{ name, slug, sortOrder }`. Pydantic ignores `name`, receives only `slug` and `sortOrder`. The name update is silently lost (not a 422, but data loss).

### Bug 4: CategoryModal.jsx -- Edit loads `category.name` which is undefined (line 42)

**File:** `frontend/admin/src/components/admin/settings/categories/CategoryModal.jsx`
**Exact code (lines 41-42):**
```javascript
if (isEdit && category) {
  setName(category.name);  // BUG: category.name is undefined
```
**Root cause:** `CategoriesPage.handleEdit` at line 44 passes `name: category.name` where `category` is a tree node from the backend response. Backend `CategoryTreeResponse` (schemas.py:145-156) has `name_i18n: dict[str, str]` which serializes as `nameI18N`. So `category.name` is `undefined`, and `category.nameI18N` is `{ "ru": "...", "en": "..." }`.

### Bug 5: CategoriesPage.jsx -- handleEdit passes `category.name` (line 44)

**File:** `frontend/admin/src/app/admin/settings/categories/page.jsx`
**Exact code (lines 39-48):**
```javascript
function handleEdit(category) {
  setModal({
    mode: 'edit',
    category: {
      id: category.id,
      name: category.name,        // BUG: undefined (should use i18n(category.nameI18N))
      slug: category.slug,
      sortOrder: category.sortOrder,
    },
  });
}
```
**Impact:** Modal opens with empty name field because `category.name` is `undefined`.

### Bug 6: CategoryNode.jsx -- Displays `node.name` (line 29)

**File:** `frontend/admin/src/components/admin/settings/categories/CategoryNode.jsx`
**Exact code (line 28-29):**
```javascript
<span className="flex-1 truncate text-sm text-[#22252b]">
  {node.name}
</span>
```
**Impact:** Category tree shows blank/undefined names because `node.name` is `undefined`. Should be `i18n(node.nameI18N)`.

## Audit Results: All Admin Write-Path Forms

### Write-Path (POST/PATCH) Forms
| Form | Endpoint | Backend Schema | i18n Issue? | Action |
|------|----------|---------------|-------------|--------|
| `useProductForm.js` | `POST /catalog/products` | `ProductCreateRequest` -- `title_i18n: I18nDict`, `description_i18n: I18nDict | None` | YES -- `en` omitted when empty (lines 325, 334) | Fix: always include `{ru, en}` with fallback |
| `CategoryModal.jsx` (create) | `POST /categories` | `CategoryCreateRequest` -- `name_i18n: I18nDict` (required) | YES -- sends plain `name` string (line 67-68) | Fix: send `nameI18N: buildI18nPayload(name, '')` |
| `CategoryModal.jsx` (edit) | `PATCH /categories/{id}` | `CategoryUpdateRequest` -- `name_i18n: I18nDict | None` | YES -- sends plain `name` string (line 67) | Fix: send `nameI18N: buildI18nPayload(name, '')` |
| `BrandSelect.jsx` | `POST /catalog/brands` | `BrandCreateRequest` -- `name: str` (plain) | NO | Confirmed: `BrandCreateRequest` at schemas.py:244-251 uses `name: str`, not i18n dict |
| `RoleModal.jsx` (create) | `POST /admin/roles` | `CreateRoleRequest` -- `name: str`, `description: str | None` | NO | Confirmed: identity schemas.py:132-133 uses `name: str` |
| `RoleModal.jsx` (edit) | `PATCH /admin/roles/{id}` | `UpdateRoleRequest` -- `name: str | None`, `description: str | None` | NO | Confirmed: identity schemas.py:291-292 uses `name: str` |
| `RolePermissionsModal.jsx` | `PUT /admin/roles/{id}/permissions` | `{ permissionIds: [...] }` | NO | No i18n fields -- sends UUIDs only |
| `UserDetailModal.jsx` | `POST /admin/identities/{id}/roles` | `{ roleId: "..." }` | NO | No i18n fields -- sends UUID only |

### Display-Side Issues (Read Path)
| Component | File:Line | Reads | Backend Returns | Issue? | Action |
|-----------|-----------|-------|----------------|--------|--------|
| `CategoryNode.jsx` | line 29 | `node.name` | `nameI18N: {"ru": "...", "en": "..."}` | YES -- shows undefined | Fix: `i18n(node.nameI18N)` |
| `CategoriesPage.jsx` | line 44 | `category.name` (for edit modal) | `nameI18N` dict | YES -- passes undefined to modal | Fix: `i18n(category.nameI18N)` |
| `CategoryModal.jsx` | line 42 | `category.name` (from parent prop) | via CategoriesPage bug above | YES -- sets empty name in edit | Fix chain: CategoriesPage extracts ru string, passes to modal |
| `services/categories.js` | line 36 | `node.nameI18N` | `nameI18N` dict | NO -- CORRECT | Already uses `i18n()` helper |

## Spec Inaccuracies in product-creation-flow.md

### Category 1: i18n Naming Convention (19 occurrences, 0 correct)
All camelCase i18n field references use `I18n` (lowercase n) but backend produces `I18N` (uppercase N). Every JSON example and validation table entry needs updating.

**Exact occurrences by line:**
| Line | Current | Should Be |
|------|---------|-----------|
| 36 | `nameI18n`, `titleI18n`, `descriptionI18n`, `valueI18n` (4 occurrences) | `nameI18N`, `titleI18N`, `descriptionI18N`, `valueI18N` |
| 93 | `groupNameI18n` | `groupNameI18N` |
| 100 | `nameI18n` | `nameI18N` |
| 102 | `descriptionI18n` | `descriptionI18N` |
| 113 | `valueI18n` (2 occurrences) | `valueI18N` |
| 160 | `titleI18n` | `titleI18N` |
| 167 | `descriptionI18n` | `descriptionI18N` |
| 179 | `titleI18n` (2 occurrences) | `titleI18N` |
| 183 | `descriptionI18n` (2 occurrences), `titleI18n` | `descriptionI18N`, `titleI18N` |
| 206 | `titleI18n` | `titleI18N` |
| 245 | `titleI18n` | `titleI18N` |
| 624 | `nameI18n` | `nameI18N` |
| 625 | `descriptionI18n` | `descriptionI18N` |
| 632 | `descriptionI18n` | `descriptionI18N` |
| 714 | `nameI18n` | `nameI18N` |
| 717 | `nameI18n` | `nameI18N` |
| 854 | `titleI18n` | `titleI18N` |

**Total: 19 `I18n` occurrences confirmed by grep.**

### Category 2: Incorrect Technical Explanation (lines 36-37)
**Current (WRONG):**
> Pydantic `to_camel("name_i18n")` = `nameI18n` (`.capitalize()` makes first letter uppercase, rest lowercase, so `i18n` -> `I18n`, not `I18N`)

**Problems:**
1. Result is `nameI18N`, not `nameI18n`
2. Pydantic uses `.title()`, not `.capitalize()` -- completely different methods
3. `.title()` capitalizes every letter after a non-alpha character (including digits)

**Correct explanation:**
> Pydantic `to_camel("name_i18n")` = `nameI18N`. Internally, `to_pascal` calls `.title()` which capitalizes every letter after a non-alphabetic character. For `i18n`: `i` is capitalized after `_`, and `n` is capitalized after digit `8`. Then `to_camel` lowercases only the first letter.

### Category 3: Missing Phase 1 Changes
1. **`countryOfOrigin`** -- now exists in `ProductCreateRequest` (added in Phase 1, `schemas.py:732-734`). Not mentioned in Step 1 request JSON example (line 158-172) or validation table (lines 177-186).
2. **`descriptionI18N`** -- validation table at line 183 says "Опционально" which is correct, but the note about the old `default_factory=dict` behavior (audit issue #7) is now resolved. The schema now shows `description_i18n: I18nDict | None = None`.

### Category 4: Storefront Response Examples Missing `en` Locale
Lines 93, 102, 113-114: JSON examples show i18n dicts with only `{"ru": "..."}` -- missing the `en` key. While the backend does not enforce required locales on response models (only on request `I18nDict`), showing single-locale examples is misleading for a document that emphasizes "both ru and en are required." Recommend adding both locales for documentation consistency.

### Category 5: JSON Example Completeness
The Step 1 request JSON example (lines 158-172) does not include `countryOfOrigin`. As an optional field, its omission from the example is acceptable, but it should at least appear in the validation table with its constraints (`^[A-Z]{2}$`, 2 chars, ISO 3166-1 alpha-2).

## Code Examples

### Recommended: Shared i18n helper
```javascript
// lib/utils.js -- add near existing i18n() read helper (line 48)
export function buildI18nPayload(ru, en) {
  return { ru, en: en || ru };
}
```

### Fix: useProductForm.js (lines 323-335)
```javascript
// BEFORE (buggy):
titleI18N: {
  ru: state.titleRu,
  ...(state.titleEn ? { en: state.titleEn } : {}),
},

// AFTER (fixed):
titleI18N: buildI18nPayload(state.titleRu, state.titleEn),

// BEFORE (buggy):
descriptionI18N: {
  ru: state.descriptionRu,
  ...(state.descriptionEn ? { en: state.descriptionEn } : {}),
},

// AFTER (fixed):
descriptionI18N: buildI18nPayload(state.descriptionRu, state.descriptionEn),
```

### Fix: CategoryModal.jsx (line 66-68)
```javascript
// BEFORE (buggy):
const body = isEdit
  ? { name, slug, sortOrder }
  : { name, slug, parentId, sortOrder };

// AFTER (fixed):
import { buildI18nPayload } from '@/lib/utils';
const body = isEdit
  ? { nameI18N: buildI18nPayload(name, ''), slug, sortOrder }
  : { nameI18N: buildI18nPayload(name, ''), slug, parentId, sortOrder };
```

### Fix: CategoryModal.jsx (line 42) -- edit initialization
```javascript
// BEFORE (buggy):
setName(category.name);  // undefined from i18n dict

// AFTER (fixed):
setName(category.name);  // CategoriesPage now passes extracted ru string
```
Note: The fix is in CategoriesPage.jsx where `category.name` is constructed, not in CategoryModal itself.

### Fix: CategoriesPage.jsx (lines 39-48) -- handleEdit
```javascript
// BEFORE (buggy):
import { i18n } from '@/lib/utils';
function handleEdit(category) {
  setModal({
    mode: 'edit',
    category: {
      id: category.id,
      name: i18n(category.nameI18N),  // extract ru string for the form
      slug: category.slug,
      sortOrder: category.sortOrder,
    },
  });
}
```

### Fix: CategoryNode.jsx (line 29)
```javascript
// BEFORE (buggy):
{node.name}

// AFTER (fixed):
import { i18n } from '@/lib/utils';
{i18n(node.nameI18N)}
```

### BrandSelect -- No Fix Needed
```javascript
// BrandCreateRequest uses plain `name: str`, NOT i18n dict (schemas.py:247)
// This is CORRECT as-is:
body: JSON.stringify({ name: newBrandName.trim(), slug: slug || `brand-${Date.now()}` })
```

### RoleModal -- No Fix Needed
```javascript
// CreateRoleRequest uses plain `name: str` and `description: str | None` (identity schemas.py:132-133)
// No i18n fields -- CORRECT as-is
body.name = name;
body.description = description || undefined;
```

## Common Pitfalls

### Pitfall 1: Backend Accepts Both Input Formats but Outputs Only One
**What goes wrong:** Developers test with `titleI18n` (lowercase n) input, it works due to `populate_by_name=True`, then assume the backend outputs `titleI18n` too. It doesn't -- output is always `titleI18N`.
**Why it happens:** Pydantic CamelModel serializes using the alias (`to_camel` result), not the field name.
**How to avoid:** Always use `titleI18N` (uppercase N) in frontend code for consistency with responses.
**Warning signs:** Frontend reads i18n field from response and gets `undefined`.

### Pitfall 2: Pydantic Silently Ignores Unknown Fields
**What goes wrong:** `CategoryModal` sends `{ name: "...", slug: "..." }` but `CategoryCreateRequest` expects `nameI18N`. Pydantic does NOT raise an error for the unknown `name` field -- it silently ignores it. The error is about the MISSING `nameI18N` field, not the extra `name` field.
**Why it happens:** CamelModel inherits Pydantic's default `model_config` which ignores extra fields.
**How to avoid:** Always verify the backend schema's field names before building a payload. Use exact camelCase alias from `to_camel()`.
**Warning signs:** 422 error for a "missing" field when you thought you sent it.

### Pitfall 3: Category Edit Data Loss (Silent Bug)
**What goes wrong:** `CategoryModal` edit sends `{ name: "...", slug: "...", sortOrder: 0 }`. Pydantic ignores `name`, receives only `slug` and `sortOrder`. The name update is silently dropped. The `at_least_one_field` validator passes because `slug` and `sortOrder` are present.
**Why it happens:** Same root cause as Pitfall 2 but PATCH semantics make it worse -- it's data loss, not a 422.
**How to avoid:** Same as Pitfall 2 -- use correct field names.
**Warning signs:** Category name never changes when editing, but slug updates work fine.

### Pitfall 4: The `.title()` vs `.capitalize()` Confusion
**What goes wrong:** Developers assume Python `.capitalize()` behavior (only first letter uppercase, rest lowercase) when Pydantic actually uses `.title()` (capitalize after every non-alpha character).
**Why it happens:** The spec at line 37 explicitly states `.capitalize()` which is wrong.
**How to avoid:** Read Pydantic source or test empirically: `to_camel("name_i18n")` = `nameI18N`.
**Warning signs:** Code uses `nameI18n` (lowercase n) everywhere and gets `undefined` when reading responses.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `description_i18n: I18nDict = Field(default_factory=dict)` | `description_i18n: I18nDict \| None = None` | Phase 1 (2026-03-29) | descriptionI18N truly optional now |
| No `country_of_origin` in ProductCreateRequest | `country_of_origin: str \| None = Field(None, ...)` | Phase 1 (2026-03-29) | Spec must document this field |

## Open Questions

1. **Category edit flow: single-language input**
   - What we know: CategoryModal has a single `name` input field (Russian only). Backend requires `{ru, en}` for both `CategoryCreateRequest` and `CategoryUpdateRequest`.
   - What's unclear: Should we add an English name field to CategoryModal, or always duplicate ru into en?
   - Recommendation: For consistency with product form D-01 decision ("copy ru to en"), duplicate ru into en. Adding a second input field would be a UI enhancement beyond Phase 2 scope.

2. **Storefront response examples in spec**
   - What we know: Some JSON examples show i18n dicts with only `{"ru": "..."}` (missing en). This is technically valid for response models (no `I18nDict` validator on responses, just `dict[str, str]`).
   - What's unclear: Whether to add en to all examples or leave as-is.
   - Recommendation: Add both locales to examples for documentation clarity and consistency.

3. **Import of `i18n` in CategoryNode.jsx**
   - What we know: CategoryNode is a pure component that doesn't currently import anything from `lib/utils`. Adding `import { i18n } from '@/lib/utils'` adds a dependency.
   - What's unclear: Whether to accept the import or pass a pre-extracted string label via prop.
   - Recommendation: Direct import is cleaner -- the `i18n()` utility is already used broadly across the admin app (DynamicAttributes, ProductDetailsForm, VariantSelect, services/categories). This is the established pattern.

## Sources

### Primary (HIGH confidence)
- **Pydantic `to_camel` empirical verification:** Ran `uv run python -c "from pydantic.alias_generators import to_camel; print(to_camel('name_i18n'))"` in backend venv -- confirmed `nameI18N` (uppercase N)
- **Pydantic `to_camel` source code:** Read via `inspect.getsource()` -- confirmed algorithm: `to_pascal(snake)` calls `.title()`, NOT `.capitalize()`
- **Backend catalog schemas:** `backend/src/modules/catalog/presentation/schemas.py` -- read `CategoryCreateRequest` (line 118), `CategoryUpdateRequest` (line 171), `CategoryTreeResponse` (line 145), `BrandCreateRequest` (line 244), `ProductCreateRequest` (line 717), i18n validator (line 52-74)
- **Backend identity schemas:** `backend/src/modules/identity/presentation/schemas.py` -- read `CreateRoleRequest` (line 124), `UpdateRoleRequest` (line 281)
- **CamelModel source:** `backend/src/shared/schemas.py` (line 20-28) -- confirmed `alias_generator=to_camel` with `populate_by_name=True`
- **Frontend source files:** Read line-by-line: `useProductForm.js` (lines 310-370), `CategoryModal.jsx` (all 231 lines), `CategoryNode.jsx` (all 69 lines), `CategoriesPage.jsx` (all 101 lines), `CategoryTree.jsx` (all 22 lines), `BrandSelect.jsx` (lines 175-204), `RoleModal.jsx` (all 189 lines), `RolePermissionsModal.jsx` (lines 66-85), `UserDetailModal.jsx` (lines 70-89), `lib/utils.js` (all 81 lines)
- **BFF route files:** Read all 3 category BFF routes (POST, PATCH/DELETE, tree GET) -- confirmed JSON pass-through
- **Spec file:** `product-creation-flow.md` -- 921 lines, 19 `I18n` occurrences confirmed by grep
- **i18n usage scan:** grep for `nameI18N`, `nameI18n`, `node.name`, `category.name` across entire admin frontend

### Secondary (MEDIUM confidence)
- **Audit findings:** `audit.md` -- issues #4 and #14 confirmed by direct code inspection
- **services/categories.js pattern:** Shows `i18n(node.nameI18N)` as the correct read pattern already established in the codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, only existing code modifications
- Architecture: HIGH -- traced exact data flow from form through BFF to backend for all audited forms; read all 3 BFF route files
- Pitfalls: HIGH -- all 6 bugs verified by reading source code directly; Pydantic `to_camel` behavior confirmed empirically AND by reading source; backend schema field types verified directly
- Spec inaccuracies: HIGH -- all 19 `I18n` occurrences confirmed by grep; `to_camel` algorithm verified by reading source code; Phase 1 changes verified against actual schema code
- Write-path audit: HIGH -- all 8 write-path forms in admin frontend audited; backend schema for each verified

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- no library upgrades expected)
