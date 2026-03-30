# Phase 1: Backend Schema Fixes - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `descriptionI18n` truly optional in ProductCreateRequest (BKND-01) and add `countryOfOrigin` to ProductCreateRequest with routing to CreateProductCommand (BKND-02). Both changes are additive, non-breaking modifications to the backend catalog module's product creation flow.

</domain>

<decisions>
## Implementation Decisions

### BKND-01: Optional descriptionI18n
- **D-01:** Change `description_i18n: I18nDict = Field(default_factory=dict)` to `description_i18n: I18nDict | None = None` in ProductCreateRequest (schemas.py:729)
- **D-02:** Same pattern already used in ProductUpdateRequest (schemas.py:760) — follow the existing convention
- **D-03:** Cascade through command dataclass: `CreateProductCommand.description_i18n` must accept `dict | None` (currently `dict` — verify and fix if needed)
- **D-04:** Domain entity `Product.create()` already handles None description_i18n (create_product.py:150 passes it through, entity has `description_i18n: dict[str, str]` default)
- **D-05:** When `None` is passed, store `None` in DB (not `{}`). API response shows `null` for description_i18n.
- **D-06:** Existing ProductCreateRequest responses (schemas.py line ~908) use `dict[str, str]` which accepts both `{}` and populated dicts — no response schema change needed, but consider `dict[str, str] | None` if DB stores None

### BKND-02: countryOfOrigin in create
- **D-07:** Add `country_of_origin: str | None = Field(None, max_length=2, pattern=r"^[A-Z]{2}$")` to ProductCreateRequest — same validation as ProductUpdateRequest (schemas.py:764)
- **D-08:** Wire `country_of_origin=request.country_of_origin` in router_products.py create_product handler (line 81-90) — CreateProductCommand already has the field (create_product.py:55)
- **D-09:** No domain or ORM changes needed — `Product.create()` already accepts `country_of_origin` (entities/product.py:160) and ORM model has the column (models.py:518)

### Backward Compatibility
- **D-10:** Both changes are additive: making a required field optional and adding a new optional field. No existing clients break.
- **D-11:** No Alembic migration needed — no DB schema changes (columns already exist, Pydantic schema changes only)

### Claude's Discretion
- Exact placement of `country_of_origin` field in ProductCreateRequest (after `source_url`, before `tags` — mirrors DB column order)
- Whether to add `description_i18n` cascade check in VariantCreateRequest and AttributeTemplateBindingCreateRequest (same `default_factory=dict` pattern found at lines 335, 1174)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product creation spec
- `product-creation-flow.md` — Step 1 defines product creation fields and validation rules
- `audit.md` §7 — Issues #7 (descriptionI18n default) and #8 (countryOfOrigin missing)

### Backend source (exact files to modify)
- `backend/src/modules/catalog/presentation/schemas.py` — ProductCreateRequest (line 717), I18nDict validator (line 52-74)
- `backend/src/modules/catalog/presentation/router_products.py` — create_product handler (line 76-96)
- `backend/src/modules/catalog/application/commands/create_product.py` — CreateProductCommand (line 55)

### Existing patterns to follow
- `backend/src/modules/catalog/presentation/schemas.py` line 760 — ProductUpdateRequest.description_i18n uses `I18nDict | None = None` (target pattern for BKND-01)
- `backend/src/modules/catalog/presentation/schemas.py` line 764 — ProductUpdateRequest.country_of_origin (target pattern for BKND-02)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `I18nDict | None = None` pattern: already used in ProductUpdateRequest, VariantUpdateRequest, AttributeTemplateUpdateRequest — proven safe
- `_validate_i18n_keys`: AfterValidator that requires `{"ru", "en"}` keys — `None` bypasses it entirely via Pydantic union type resolution

### Established Patterns
- All optional i18n fields in update schemas use `I18nDict | None = None`
- All country fields use `str | None = Field(None, max_length=2, pattern=...)` with ISO 3166-1 alpha-2 validation
- Command dataclasses are frozen `@dataclass` with `str | None = None` for optional fields
- Router wiring: each field in ProductCreateRequest maps 1:1 to CreateProductCommand constructor

### Integration Points
- `schemas.py` ProductCreateRequest → router_products.py `create_product()` → `CreateProductCommand` → `CreateProductHandler.handle()` → `Product.create()`
- Same `description_i18n: I18nDict = Field(default_factory=dict)` pattern appears in VariantCreateRequest (line 335) and AttributeTemplateBindingCreateRequest (line 1174) — potential fix cascade

</code_context>

<specifics>
## Specific Ideas

No specific requirements — fixes are mechanical, following existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

- Fix same `default_factory=dict` anti-pattern in VariantCreateRequest and AttributeTemplateBindingCreateRequest — could be added to this phase if trivial, or deferred to tech debt cleanup
- Frontend admin may need to handle `null` descriptionI18n in responses — Phase 2 or 8 concern

</deferred>

---

*Phase: 01-backend-schema-fixes*
*Context gathered: 2026-03-29*
