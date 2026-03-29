# Phase 2: Frontend i18n & Spec Alignment - Research

**Researched:** 2026-03-29
**Domain:** Admin frontend i18n payload correctness + specification accuracy
**Confidence:** HIGH

## Summary

Phase 2 fixes the critical i18n locale bug in the admin product form and aligns the specification with actual backend behavior. Research verified the exact Pydantic `to_camel` behavior (produces `nameI18N` with uppercase N, NOT `nameI18n`), audited all admin write-path forms, and discovered a **previously unidentified critical bug** in CategoryModal -- it sends `{name, slug}` (plain strings) but the backend `CategoryCreateRequest` expects `nameI18N: {"ru": "...", "en": "..."}` (i18n dict). The category tree display is also broken because `CategoryNode` renders `node.name` but the backend returns `nameI18N`.

The spec file (`product-creation-flow.md`) has 19 occurrences of incorrect `I18n` (lowercase n) that must become `I18N`. Lines 36-37 contain a factually wrong explanation of how Pydantic's `to_camel` works. Additionally, the spec does not reflect Phase 1 changes (`descriptionI18N` now truly optional, `countryOfOrigin` added to create request).

**Primary recommendation:** Fix product form i18n fallback, fix CategoryModal to send `nameI18N` dict, fix category tree display to read `nameI18N`, and do a full spec accuracy pass -- all as separate focused tasks.

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
| I18N-01 | Admin form always sends both ru+en locales in all i18n fields (fallback: ru value used for empty en) | Verified bug at useProductForm.js:323-326 and 330-335. Also discovered CategoryModal sends plain `name` instead of `nameI18N` dict -- same class of bug. |
| I18N-02 | Spec product-creation-flow.md updated to reflect actual backend naming convention (titleI18N, uppercase N) | Verified: `to_camel("name_i18n")` = `nameI18N`. Spec has 19 wrong occurrences, 1 factually wrong explanation at lines 36-37, and missing Phase 1 changes. |
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

**Key insight:** BFF routes pass JSON body through WITHOUT transformation. Whatever the form sends is exactly what the backend receives. There is no middleware that fixes i18n payloads.

### Pattern: Payload Building

Two patterns exist in the codebase:

1. **Hook-based (useProductForm.js):** `useReducer` + `useMemo` derives payload from state. I18n fields built inline in the memo.
2. **Inline (CategoryModal, BrandSelect):** Payload constructed directly in `handleSubmit` / `handleCreateBrand` functions.

Both patterns pass the payload to `fetch()` via `JSON.stringify(body)`.

### Pattern: CamelModel i18n Aliasing

Backend uses `pydantic.alias_generators.to_camel` with `populate_by_name=True`:

```python
# src/shared/schemas.py
class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
```

This means:
- **Input:** Backend accepts BOTH `titleI18N` (alias) and `title_i18n` (field name) -- `populate_by_name=True`
- **Output:** Backend serializes as `titleI18N` (alias) -- always uppercase N
- **Verified empirically:**
  ```
  to_camel("name_i18n")        -> "nameI18N"
  to_camel("title_i18n")       -> "titleI18N"
  to_camel("description_i18n") -> "descriptionI18N"
  to_camel("value_i18n")       -> "valueI18N"
  ```

### Anti-Patterns to Avoid
- **Conditional locale inclusion:** `...(state.titleEn ? { en: state.titleEn } : {})` -- this omits `en` when empty, causing backend 422. Always include both locales.
- **Plain string where i18n dict expected:** `{ name: "..." }` when backend schema has `name_i18n: I18nDict` -- the field is silently ignored, creating a 422 for the required field.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| i18n payload with fallback | Copy-paste fallback logic in each form | Shared `buildI18nPayload(ru, en)` helper in `lib/utils.js` | DRY across 2+ forms, prevents future regressions |

**Key insight:** A shared helper function (`buildI18nPayload`) is recommended (Claude's discretion per CONTEXT.md). It ensures consistent behavior: always returns `{ru, en}` with `en` falling back to `ru` if empty.

## Common Pitfalls

### Pitfall 1: Backend Accepts Both Input Formats but Outputs Only One
**What goes wrong:** Developers test with `titleI18n` (lowercase n) input, it works due to `populate_by_name=True`, then assume the backend outputs `titleI18n` too. It doesn't -- output is always `titleI18N`.
**Why it happens:** Pydantic CamelModel serializes using the alias (`to_camel` result), not the field name.
**How to avoid:** Always use `titleI18N` (uppercase N) in frontend code for consistency with responses.
**Warning signs:** Frontend reads i18n field from response and gets `undefined`.

### Pitfall 2: CategoryModal Name Mismatch (Discovered During Research)
**What goes wrong:** `CategoryModal` sends `{ name: "...", slug: "..." }` but `CategoryCreateRequest` expects `nameI18N: {"ru": "...", "en": "..."}`. The backend ignores the `name` field (no such alias/field), leaving `nameI18N` missing, which triggers a 422.
**Why it happens:** CategoryModal was written before the i18n dict was added to the category schema, or was written assuming a plain string field.
**How to avoid:** Check backend schema for every form -- `CategoryCreateRequest.name_i18n` is `I18nDict` (required).
**Warning signs:** Category creation always fails with 422 in admin panel.

### Pitfall 3: Category Tree Display Broken
**What goes wrong:** `CategoryNode` renders `node.name` but the backend `CategoryTreeResponse` returns `nameI18N: {"ru": "...", "en": "..."}`. So `node.name` is `undefined` and nothing displays.
**Why it happens:** Frontend assumes a flat `name` field; backend returns an i18n dict.
**How to avoid:** Use the `i18n()` helper from `lib/utils.js` to extract the display name from the dict.
**Warning signs:** Category tree shows blank names or `[object Object]`.

### Pitfall 4: CategoryUpdate Also Affected
**What goes wrong:** `CategoryUpdateRequest` expects `nameI18N: {"ru": "...", "en": "..."}` (optional, PATCH semantics), but CategoryModal sends `{ name: "...", slug: "..." }` for edits too.
**Why it happens:** Same root cause as Pitfall 2.
**How to avoid:** Fix the edit payload to also use `nameI18N`.

## Code Examples

### Current Bug: useProductForm.js (lines 321-344)
```javascript
// BROKEN: en is conditionally included
const productPayload = useMemo(
  () => ({
    titleI18N: {
      ru: state.titleRu,
      ...(state.titleEn ? { en: state.titleEn } : {}),  // BUG: en omitted when empty
    },
    // ...
    ...(state.descriptionRu
      ? {
          descriptionI18N: {
            ru: state.descriptionRu,
            ...(state.descriptionEn ? { en: state.descriptionEn } : {}),  // BUG: same
          },
        }
      : {}),
    // ...
  }),
  [/* deps */],
);
```

### Fix: useProductForm.js i18n payload
```javascript
// FIXED: en always included, falls back to ru
const productPayload = useMemo(
  () => ({
    titleI18N: {
      ru: state.titleRu,
      en: state.titleEn || state.titleRu,  // fallback to ru
    },
    // ...
    ...(state.descriptionRu
      ? {
          descriptionI18N: {
            ru: state.descriptionRu,
            en: state.descriptionEn || state.descriptionRu,  // fallback to ru
          },
        }
      : {}),
    // ...
  }),
  [/* deps */],
);
```

### Fix: Shared i18n helper (recommended)
```javascript
// lib/utils.js -- add near existing i18n() read helper
export function buildI18nPayload(ru, en) {
  return { ru, en: en || ru };
}
```

### Current Bug: CategoryModal (lines 66-68)
```javascript
// BROKEN: sends plain {name} but backend expects {nameI18N: {ru, en}}
const body = isEdit
  ? { name, slug, sortOrder }
  : { name, slug, parentId, sortOrder };
```

### Fix: CategoryModal payload
```javascript
// FIXED: wraps name in i18n dict
const body = isEdit
  ? { nameI18N: buildI18nPayload(name, ''), slug, sortOrder }
  : { nameI18N: buildI18nPayload(name, ''), slug, parentId, sortOrder };
```

### Current Bug: CategoryNode display (line 29)
```javascript
// BROKEN: reads node.name but response has node.nameI18N
<span>{node.name}</span>
```

### Fix: CategoryNode display
```javascript
// FIXED: extract display name from i18n dict
import { i18n } from '@/lib/utils';
// ...
<span>{i18n(node.nameI18N)}</span>
```

### Fix: CategoriesPage handleEdit (line 42-44)
```javascript
// BROKEN: reads category.name (undefined from i18n dict)
name: category.name,

// FIXED: extract ru locale for edit form
name: i18n(category.nameI18N),
```

### BrandSelect -- No Fix Needed
```javascript
// BrandCreateRequest uses plain `name: str`, NOT i18n dict
// This is CORRECT as-is:
body: JSON.stringify({ name: newBrandName.trim(), slug: slug || `brand-${Date.now()}` })
```

### RoleModal -- No Fix Needed
```javascript
// CreateRoleRequest uses plain `name: str` and `description: str | None`
// No i18n fields -- CORRECT as-is
body.name = name;
body.description = description || undefined;
```

## Audit Results: All Admin Write-Path Forms

| Form | Endpoint | Backend Schema | i18n Issue? | Action |
|------|----------|---------------|-------------|--------|
| `useProductForm.js` | `POST /catalog/products` | `ProductCreateRequest` -- `title_i18n: I18nDict`, `description_i18n: I18nDict \| None` | YES -- `en` omitted when empty | Fix: always include `{ru, en}` with fallback |
| `CategoryModal.jsx` (create) | `POST /categories` | `CategoryCreateRequest` -- `name_i18n: I18nDict` | YES -- sends plain `name` string instead of `nameI18N` dict | Fix: wrap in i18n dict |
| `CategoryModal.jsx` (edit) | `PATCH /categories/{id}` | `CategoryUpdateRequest` -- `name_i18n: I18nDict \| None` | YES -- sends plain `name` string | Fix: wrap in i18n dict |
| `BrandSelect.jsx` | `POST /catalog/brands` | `BrandCreateRequest` -- `name: str` (plain) | NO -- backend accepts plain string | No change needed |
| `RoleModal.jsx` (create) | `POST /admin/roles` | `CreateRoleRequest` -- `name: str`, `description: str \| None` | NO -- no i18n fields | No change needed |
| `RoleModal.jsx` (edit) | `PATCH /admin/roles/{id}` | `UpdateRoleRequest` -- `name: str \| None`, `description: str \| None` | NO -- no i18n fields | No change needed |

### Display-Side Issues (Read Path)
| Component | Reads | Backend Returns | Issue? | Action |
|-----------|-------|----------------|--------|--------|
| `CategoryNode.jsx` | `node.name` | `nameI18N: {"ru": "...", "en": "..."}` | YES -- shows undefined | Fix: use `i18n(node.nameI18N)` |
| `CategoriesPage.jsx` | `category.name` (for edit) | `nameI18N` dict | YES -- passes undefined to modal | Fix: use `i18n(category.nameI18N)` |

## Spec Inaccuracies in product-creation-flow.md

### Category 1: i18n Naming (19 occurrences)
All camelCase i18n field references use `I18n` (lowercase n) but backend produces `I18N` (uppercase N). Every JSON example and validation table entry needs updating.

### Category 2: Incorrect Technical Explanation (lines 36-37)
**Current (WRONG):**
> Pydantic `to_camel("name_i18n")` = `nameI18n` (`.capitalize()` делает первую букву заглавной, остальные -- строчными, поэтому `i18n` -> `I18n`, а не `I18N`)

**Correct:**
> Pydantic `to_camel("name_i18n")` = `nameI18N`. The `to_camel` function splits on `_`, capitalizes the first letter of each segment, and joins. For `i18n`, the entire segment becomes `I18N` (first letter uppercased, rest preserved as-is -- NOT lowercased).

### Category 3: Missing Phase 1 Changes
1. **`countryOfOrigin`** -- now exists in `ProductCreateRequest` (added in Phase 1). Not mentioned in Step 1 request JSON or validation table.
2. **`descriptionI18N`** -- spec validation table (line 183) should note it's truly optional (`I18nDict | None = None`), which matches the current text but the note about the old `default_factory=dict` bug (audit issue #7) is now resolved.

### Category 4: JSON Example Field Completeness
The Step 1 request JSON example (lines 159-173) does not include `countryOfOrigin`, `supplierId`, or `sourceUrl` in the example. These are optional fields and their omission from the example is acceptable, but `countryOfOrigin` should at least be mentioned in the validation table since it was added in Phase 1.

### Category 5: Storefront Response Examples Missing `en` Locale
Lines 93, 102, 113-114: The storefront response JSON examples show `groupNameI18N` and `valueI18N` with only `{"ru": "..."}` -- missing the `en` key. While these are response examples (not request), they should show both locales for accuracy.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `description_i18n: I18nDict = Field(default_factory=dict)` | `description_i18n: I18nDict \| None = None` | Phase 1 (2026-03-29) | descriptionI18N truly optional now |
| No `country_of_origin` in ProductCreateRequest | `country_of_origin: str \| None = Field(None, ...)` | Phase 1 (2026-03-29) | Spec must document this field |

## Open Questions

1. **Category edit flow: single-language input**
   - What we know: CategoryModal has a single `name` input field (Russian only). Backend requires `{ru, en}`.
   - What's unclear: Should we add an English name field to CategoryModal, or always duplicate ru into en?
   - Recommendation: For consistency with product form D-01 decision, copy ru to en. Adding a second input field would be a UI enhancement beyond Phase 2 scope.

2. **Storefront response examples in spec**
   - What we know: Some JSON examples show i18n dicts with only `{"ru": "..."}` (missing en)
   - What's unclear: Whether to add en to all examples or leave as-is (responses can validly have only ru if that's what was stored)
   - Recommendation: Add both locales to examples for consistency and documentation clarity.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 (backend), no test framework for admin frontend |
| Config file | `backend/pyproject.toml` |
| Quick run command | N/A for frontend -- manual browser testing |
| Full suite command | N/A for frontend |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| I18N-01 | Admin forms always send both ru+en locales | manual | Browser: create product with empty en, verify no 422 | N/A -- frontend JS changes, no test runner |
| I18N-01 | CategoryModal sends nameI18N dict | manual | Browser: create category, verify no 422 | N/A |
| I18N-02 | Spec uses I18N (uppercase N) naming | manual | `grep -c 'I18n' product-creation-flow.md` should return 0 | N/A |

### Sampling Rate
- **Per task commit:** `grep -c 'I18n' product-creation-flow.md` (should be 0 after spec fix)
- **Per wave merge:** Manual: create product in admin with empty en fields, verify 201 response
- **Phase gate:** All i18n forms verified via browser, grep confirms 0 lowercase I18n in spec

### Wave 0 Gaps
- No automated frontend test infrastructure exists for the admin app (JavaScript, no TypeScript, no Jest/Vitest)
- Validation relies on manual browser testing and grep-based checks for the spec
- Backend e2e tests from Phase 1 already verify that the backend accepts proper i18n payloads

## Sources

### Primary (HIGH confidence)
- **Pydantic `to_camel` empirical verification:** Ran `python -c "from pydantic.alias_generators import to_camel; ..."` -- confirmed `nameI18N` (uppercase N) output
- **Backend schemas:** `backend/src/modules/catalog/presentation/schemas.py` -- read `CategoryCreateRequest`, `BrandCreateRequest`, `ProductCreateRequest` directly
- **Backend identity schemas:** `backend/src/modules/identity/presentation/schemas.py` -- confirmed `CreateRoleRequest` uses plain `name: str`
- **Frontend source files:** Read all 4 audited forms (`useProductForm.js`, `CategoryModal.jsx`, `BrandSelect.jsx`, `RoleModal.jsx`) line-by-line
- **CamelModel source:** `backend/src/shared/schemas.py` -- confirmed `alias_generator=to_camel` with `populate_by_name=True`
- **BFF proxy routes:** Read all relevant route files -- confirmed pass-through behavior (no payload transformation)

### Secondary (MEDIUM confidence)
- **Audit findings:** `audit.md` -- issues #4 and #14 confirmed by direct code inspection
- **Category display chain:** `CategoriesPage.jsx` -> `CategoryTree.jsx` -> `CategoryNode.jsx` -- traced data flow to confirm `node.name` reads undefined from i18n dict response

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, only existing code modifications
- Architecture: HIGH -- traced exact data flow from form to backend for all 4 forms
- Pitfalls: HIGH -- all bugs verified by reading source code directly, Pydantic behavior confirmed empirically
- Spec inaccuracies: HIGH -- all 19 I18n occurrences counted, lines 36-37 verified wrong against actual `to_camel` output

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable -- no library upgrades expected)
