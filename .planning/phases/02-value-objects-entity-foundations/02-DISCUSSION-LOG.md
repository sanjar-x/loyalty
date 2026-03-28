# Phase 2: Value Objects & Entity Foundations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 02-value-objects-entity-foundations
**Areas discussed:** Test file structure, Coverage depth

---

## Test File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| One file per entity | test_brand.py, test_product.py, etc. — consistent with D-12 | ✓ |
| Grouped files | test_entities.py, test_value_objects.py — fewer files | |

**User's choice:** One file per entity
**Notes:** Consistent with Phase 1 D-12 decision.

---

## Coverage Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Business-critical paths first | Factory methods, state transitions, invariant enforcement | ✓ |
| Every possible invalid input | Exhaustive edge cases for 2,220 lines | |

**User's choice:** Business-critical paths first
**Notes:** Priority: product creation, variant/SKU generation, EAV attribute assignment, price management, status transitions. Exhaustive edge cases can be added later.

---

## Claude's Discretion

- Exact test method names
- Number of invalid-input cases per factory
- Private helper testing decisions
- Value object edge case selection

## Deferred Ideas

None — discussion stayed within phase scope.
