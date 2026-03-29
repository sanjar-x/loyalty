# Phase 2: Frontend i18n & Spec Alignment - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin form always sends valid i18n payloads (both ru and en locales in every i18n field) and spec documentation (`product-creation-flow.md`) matches actual backend behavior. Scope includes full audit of all write-path forms in admin frontend, not just product creation.

</domain>

<decisions>
## Implementation Decisions

### I18N-01: En locale fallback in product form
- **D-01:** When user doesn't fill in `en`, copy `ru` value to `en` before sending to backend. This ensures backend never receives incomplete i18n dicts.
- **D-02:** Apply in `useProductForm.js` `productPayload` useMemo — both `titleI18N` and `descriptionI18N` must always include `{ru, en}` keys when sent.
- **D-03:** Current bug: lines 323-326 conditionally include `en` only if `state.titleEn` is truthy; lines 332-335 same for description. Both need fixing.

### I18N-02: Scope — full write-path audit
- **D-04:** Audit ALL POST/PATCH requests in admin frontend for i18n payload correctness, not just product creation.
- **D-05:** Known write forms to audit:
  - `useProductForm.js` — `titleI18N`, `descriptionI18N` (confirmed bug)
  - `CategoryModal.jsx` — sends `{ name, slug }` plain string (line 66-68). Check if backend CategoryCreateRequest expects i18n dict or plain name.
  - `BrandSelect.jsx` — sends `{ name, slug }` plain string (line 189). Check if backend BrandCreateRequest expects i18n dict or plain name.
  - `RoleModal.jsx` — sends role data (line 37). Check for i18n fields.
- **D-06:** For each form: if backend expects i18n dict but frontend sends plain string, add i18n wrapper. If backend accepts plain string, no change needed.

### I18N-03: Spec update — full review
- **D-07:** Replace all 19 occurrences of `I18n` (lowercase n) with `I18N` (uppercase N) in `product-creation-flow.md`.
- **D-08:** Update the incorrect note at lines 36-37 that explains Pydantic `to_camel` behavior — the current explanation is wrong about `.capitalize()`.
- **D-09:** Full review of all JSON examples in the spec (921 lines) for accuracy against current backend behavior — not just the naming convention fix.

### Claude's Discretion
- Whether to extract i18n payload building into a shared helper function (e.g., `buildI18nPayload(ru, en)`) or keep inline in each form
- Exact wording of the corrected spec note about to_camel behavior
- Order of fixes (product form first, then audit, then spec — or different sequence)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product creation spec (PRIMARY — full review target)
- `product-creation-flow.md` — Full spec with 19 I18n references to fix, JSON examples to verify. Lines 36-37 contain incorrect to_camel explanation.

### Audit results
- `audit.md` — Integration audit with 14 issues. Issues #4 (i18n locales), #14 (spec naming) are Phase 2 scope.

### Backend i18n validation (understand what frontend must comply with)
- `backend/src/modules/catalog/presentation/schemas.py` — I18nDict validator (lines 52-74), CamelModel alias generator. Defines required locales `{"ru", "en"}`.
- `backend/src/modules/catalog/domain/value_objects.py` — `validate_i18n_completeness()` — domain-level locale enforcement.

### Frontend source (files to modify)
- `frontend/admin/src/hooks/useProductForm.js` — Lines 321-358: `productPayload` builder with i18n bug.
- `frontend/admin/src/components/admin/settings/categories/CategoryModal.jsx` — Lines 66-68: category create/update payload (plain name, no i18n).
- `frontend/admin/src/app/admin/products/add/details/BrandSelect.jsx` — Line 189: brand create payload (plain name, no i18n).
- `frontend/admin/src/lib/utils.js` — `i18n()` helper (line 48) — reads i18n, not a write concern.

### Backend entity schemas (audit targets — check what each expects)
- `backend/src/modules/catalog/presentation/schemas.py` — BrandCreateRequest, CategoryCreateRequest — verify if they expect i18n dicts or plain strings.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `i18n(obj, fallback)` in `lib/utils.js` — reads i18n from responses. Could inspire a write-side helper.
- `transliterate()` in `useProductForm.js` — ru→latin for slug generation. Established pattern for locale-aware transforms.

### Established Patterns
- Product form uses `useReducer` with `useMemo` for payload building — payloads are derived state, not stored.
- All admin services use `fetch()` with `credentials: 'include'` — no axios or other HTTP client.
- BFF routes (`/api/*`) proxy to backend with `backendFetch()` — pass JSON body through without transformation.
- CategoryModal and BrandSelect build payloads inline (no shared form hook) — simpler forms, different pattern from product form.

### Integration Points
- `useProductForm.js` → `services/products.js` `createProduct()` → BFF `/api/catalog/products` → backend `POST /api/v1/catalog/products`
- `CategoryModal.jsx` → BFF `/api/categories` → backend `POST /api/v1/catalog/categories`
- `BrandSelect.jsx` → BFF `/api/catalog/brands` → backend `POST /api/v1/catalog/brands`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — fixes are driven by backend contract compliance and spec accuracy.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-frontend-i18n-spec-alignment*
*Context gathered: 2026-03-29*
