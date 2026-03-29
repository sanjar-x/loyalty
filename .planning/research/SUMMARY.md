# Research Summary: Backend Schema Fixes (v1.0)

**Synthesized:** 2026-03-29
**Scope:** Backend workstream — audit issues #7 and #8
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md (layer trace), PITFALLS-schema-fixes.md

## Key Discovery: Scope Larger Than Expected

The `default_factory=dict` bug affects **3 schemas**, not just `ProductCreateRequest`:

| Schema | Line | Field |
|--------|------|-------|
| `ProductCreateRequest` | ~729 | `description_i18n` |
| `AttributeCreateRequest` | ~335 | `description_i18n` |
| `AttributeTemplateCreateRequest` | ~1174 | `description_i18n` |

All three use `I18nDict = Field(default_factory=dict)` where the empty dict `{}` fails the `I18nDict` validator (requires `ru` + `en` keys).

## Change Map (Presentation Layer Only)

### Fix 1: description_i18n → Optional (3 schemas)
- **schemas.py**: Change `I18nDict = Field(default_factory=dict)` → `I18nDict | None = None` in all 3 schemas
- **Pattern already established**: 13 existing usages of `I18nDict | None = None` in update schemas
- **Downstream safe**: Command handlers check falsiness, domain entities convert `None` → `{}`

### Fix 2: countryOfOrigin in ProductCreateRequest
- **schemas.py**: Add `country_of_origin: str | None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")`
- **router_products.py**: Add `country_of_origin=request.country_of_origin` to `CreateProductCommand()` call
- **All downstream layers support it**: Command dataclass, entity `create()`, ORM column — all exist

### No Migration Needed
Both DB columns (`description_i18n` JSONB, `country_of_origin` String(2)) already exist.

## Top Pitfalls

1. **Router wiring gap**: Adding field to schema without passing to command = silently dropped
2. **Constraint consistency**: `country_of_origin` must match `ProductUpdateRequest`'s `Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` exactly
3. **Fix all 3 schemas together**: Leaving 2 broken while fixing 1 creates inconsistency

## Estimated Impact

- **Files changed**: 2 (schemas.py, router_products.py)
- **Lines changed**: ~15
- **Risk**: Very low — pattern already established, all downstream layers support it
- **Tests needed**: ~8 specific tests for new behavior

## Confidence: HIGH

All findings verified against actual codebase. No inference or assumptions.

---
*Research completed: 2026-03-29*
*Ready for requirements definition: yes*
