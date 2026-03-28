# Phase 3: Product Aggregate Behavior - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 03-Product Aggregate Behavior
**Mode:** auto
**Areas discussed:** Attribute governance scope, Soft-delete restore gap, FSM readiness depth, Event assertion style

---

## Attribute Governance Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Test entity-side only | PAV.create() shape, defer governance to Phase 5 handlers | ✓ |
| Test full governance chain | Template lookup + binding check in domain layer | |
| Skip entirely | Governance not in domain entities | |

**User's choice:** [auto] Test entity-side only (recommended default)
**Notes:** ProductAttributeValue.create() has zero validation — governance is enforced in command handlers (Phase 5). DOM-06 split across Phase 3 (entity surface) and Phase 5 (handler validation).

---

## Soft-Delete Restore Gap

| Option | Description | Selected |
|--------|-------------|----------|
| Test what exists, flag gap | Test soft_delete cascade, flag missing restore() for planner | ✓ |
| Implement restore() first | Add restore method before writing tests | |
| Revise success criteria | Remove restore mention from Phase 3 criteria | |

**User's choice:** [auto] Test what exists, flag gap (recommended default)
**Notes:** No restore() method on Product, ProductVariant, or SKU. Success criteria mentions "restoring reverses the cascade" but implementation doesn't exist. Flagged in CONTEXT.md deferred section for planner decision.

---

## FSM Readiness Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full matrix + readiness | All states × all targets, plus active SKU and priced SKU checks | ✓ |
| Valid paths only | Only test the 7 valid transitions and their readiness checks | |
| Representative sample | Test key paths, skip exhaustive invalid matrix | |

**User's choice:** [auto] Full matrix + readiness (recommended default)
**Notes:** 5 FSM states with specific transition rules. Readiness checks for READY_FOR_REVIEW (needs active SKU) and PUBLISHED (needs priced SKU) require building full Product→Variant→SKU trees.

---

## Event Assertion Style

| Option | Description | Selected |
|--------|-------------|----------|
| Type + key payload fields | Verify event type, aggregate_id, and domain-specific fields | ✓ |
| Type only | Just check isinstance(event, ExpectedEventType) | |
| Full payload match | Assert every field including timestamps | |

**User's choice:** [auto] Type + key payload fields (recommended default)
**Notes:** 8 event types emitted by Product aggregate. Checking key fields (product_id, old_status, new_status, variant_id, sku_id, slug) catches payload bugs without over-coupling to event structure.

---

## Claude's Discretion

- Test method grouping within aggregate test file
- Number of invalid FSM transition combinations
- Edge case selection for variant/SKU operations
- Helper function design for building test trees

## Deferred Ideas

- restore() method implementation — flagged for planner
- Optimistic locking inspection — Phase 7 scope
