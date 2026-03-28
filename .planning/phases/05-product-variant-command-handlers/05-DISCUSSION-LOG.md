# Phase 5: Product & Variant Command Handlers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 05-Product & Variant Command Handlers
**Mode:** auto
**Areas discussed:** Handler scope, Attribute governance handler-side, Supplier cross-module stub, Test file organization

---

## Handler Scope (CMD-04 + CMD-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Include all product + variant handlers, exclude media | CMD-04 + CMD-05 only, media in Phase 6 | ✓ |
| Include media handlers too | All product-related handlers in one phase | |

**User's choice:** [auto] Exclude media handlers (recommended default)
**Notes:** REQUIREMENTS.md traceability maps CMD-07 (media) to Phase 6. Phase 5 covers CMD-04 (product) and CMD-05 (variant) only.

---

## Attribute Governance Handler-Side

| Option | Description | Selected |
|--------|-------------|----------|
| Test governance here | Phase 3 D-01/D-02 deferred handler-side to Phase 5 | ✓ |
| Defer to separate phase | Create Phase 5.5 for governance only | |

**User's choice:** [auto] Test governance here (recommended default)
**Notes:** AssignProductAttributeHandler and BulkAssignProductAttributeHandler enforce the template governance chain. Phase 3 explicitly deferred this to Phase 5.

---

## Supplier Cross-Module Stub

| Option | Description | Selected |
|--------|-------------|----------|
| Per-test inline AsyncMock | Follow Phase 4 D-04 pattern, local stubs | ✓ |
| Shared fake in tests/fakes/ | Build FakeSupplierQueryService | |
| Skip supplier validation tests | Only test no-supplier path | |

**User's choice:** [auto] Per-test inline AsyncMock (recommended default)
**Notes:** Tests 3 paths: no supplier, active supplier, inactive supplier. Cross-border supplier source_url check also tested.

---

## Test File Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Two files: product + variant | Follow Phase 4 pattern | ✓ |
| Single file for all | All 10 handlers in one file | |
| Three files: product + variant + attribute | Split attribute governance separately | |

**User's choice:** [auto] Two files (recommended default)
**Notes:** test_product_handlers.py (7 handler classes) and test_variant_handlers.py (3 handler classes).

---

## Claude's Discretion

- Edge case count per handler
- ILogger interaction testing
- Test method naming
- Attribute governance scenario count

## Deferred Ideas

- Media handlers → Phase 6 (CMD-07)
- SKU handlers → Phase 6 (CMD-06)
- Shared ISupplierQueryService fake → per-test mocks sufficient for now
