# Phase 7: Repository & Data Integrity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-28
**Phase:** 07-Repository & Data Integrity
**Mode:** auto
**Areas discussed:** Test scope, Product roundtrip, Schema constraints, Soft-delete audit, N+1 detection

---

## Test Scope (Existing vs New)

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing + create new | Don't duplicate passing tests | ✓ |
| Rewrite everything | Fresh test files for all repos | |

**User's choice:** [auto] Extend existing + create new (recommended default)

## Schema Constraint Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Direct DB constraint testing | INSERT invalid data, assert IntegrityError | ✓ |
| Via repository rejection | Test through application layer | |

**User's choice:** [auto] Direct DB constraint testing (recommended default)

## Soft-Delete Filter Audit

| Option | Description | Selected |
|--------|-------------|----------|
| Systematic audit | Every repo method that returns entities | ✓ |
| Spot-check | Representative sample | |

**User's choice:** [auto] Systematic audit (recommended default)

## N+1 Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Product repo only | 3-level eager loading is the risk | ✓ |
| All repos | Overkill for single-level entities | |

**User's choice:** [auto] Product repo only (recommended default)

## Deferred Ideas

- Performance benchmarking → v2 PERF-01
- Cursor pagination → v2 PERF-02
- Concurrent locking → v2 ADV-02
