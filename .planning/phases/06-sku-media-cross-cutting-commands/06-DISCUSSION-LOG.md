# Phase 6: SKU, Media & Cross-Cutting Commands - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 06-SKU, Media & Cross-Cutting Commands
**Mode:** auto
**Areas discussed:** Image backend mock, Cross-cutting event audit scope, Bulk atomicity, FK/uniqueness errors

---

## Image Backend Mock Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Per-test inline AsyncMock | Consistent with Phase 4/5 cross-module pattern | ✓ |
| Shared FakeImageBackendClient | Build reusable fake in tests/fakes/ | |

**User's choice:** [auto] Per-test inline AsyncMock (recommended default)
**Notes:** Mock HTTP responses: success, timeout/error, 404.

---

## Cross-Cutting Event Audit Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Gap-only audit | Only test handlers not covered by Phases 4-5 | ✓ |
| Full re-audit | Re-verify all 46 handlers | |

**User's choice:** [auto] Gap-only audit (recommended default)
**Notes:** Creates systematic checklist mapping handler → event → phase tested. Avoids duplicating Phases 4-5 work.

---

## Bulk Atomicity Testing

| Option | Description | Selected |
|--------|-------------|----------|
| SKU matrix + fill Phase 4 gaps | Test generate_sku_matrix, check if Phase 4 covered bulk brands | ✓ |
| Only SKU matrix | Only CMD-06 scope | |
| All bulk operations | Re-test everything | |

**User's choice:** [auto] SKU matrix + fill Phase 4 gaps (recommended default)

---

## FK/Uniqueness Error Paths

| Option | Description | Selected |
|--------|-------------|----------|
| Representative sample | 2-3 per handler domain | ✓ |
| Exhaustive | Every FK and uniqueness path | |
| Minimal | One per domain | |

**User's choice:** [auto] Representative sample (recommended default)
**Notes:** Cross-entity FKs + slug/code uniqueness conflicts.

---

## Claude's Discretion

- Exact FK/uniqueness error count per domain
- Event gap identification (depends on Phase 4-5 SUMMARYs)
- generate_sku_matrix scenario design
- Bulk handler gap assessment

## Deferred Ideas

- Performance testing of SKU matrix → v2 PERF
- Concurrent optimistic locking tests → v2 ADV-02
- Property-based EAV combinatorial tests → v2 ADV-03
