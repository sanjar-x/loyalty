# Phase 9: Entity God-Class Refactoring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-28
**Phase:** 09-Entity God-Class Refactoring
**Mode:** auto
**Areas discussed:** File split strategy, Safety net, Import handling

---

## File Split Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One file per entity + __init__.py | Clean separation, re-exports preserve compatibility | ✓ |
| Group by aggregate | Product+Variant+SKU in one file | |

**User's choice:** [auto] One file per entity (recommended default)

## Safety Net

| Option | Description | Selected |
|--------|-------------|----------|
| Full test suite before/after | 400+ tests as safety net | ✓ |
| Spot-check only | Run a few key tests | |

**User's choice:** [auto] Full test suite (recommended default)

## Deferred Ideas

None — final phase.
