# Alembic Linearity Audit — Sprint 0 closure (REFACT-009)

**Status:** ✅ green
**Audited at:** 2026-05-06
**Main HEAD at audit:** `35e790cf` (post-PR-6b merge — REFACT-001 cascade
100% complete)
**Alembic single head:** `c9e4d3f7b502` (`add referral module`)

This document closes REFACT-009 — the final Sprint 0 backend work unit.
The audit confirms that the migration chain is linear from `<base>` to
the current head with no orphaned heads, no missing `down_revision`
links, and no Sprint 0 sibling-head races.

## Audit method

```bash
alembic heads          # → exactly one head
alembic history        # → contiguous chain from <base> to the head
alembic upgrade head   # → applies cleanly on a fresh DB
```

`alembic heads` returns a single revision; `alembic history` walks the
chain in one direction without surfacing parallel branches; the upgrade
applied cleanly during PR-6b's pre-flight verification on a fresh
local Postgres.

## Sprint 0 migrations

REFACT-001 contributed four new migrations during Sprint 0; they form a
clean linear suffix on the chain:

| Order | Revision | PR | Purpose |
| --- | --- | --- | --- |
| 1 | `79792d3c84ee` | PR-S6 | `add_failure_kind_to_sku_pricing_history` (ADR-005a Open Issue #3) |
| 2 | `a7d2c8f1e034` | PR-3a / PR-3b | `unify idempotency keys + consumer inbox into shared tables` |
| 3 | `b8f3c2e6a401` | PR-6b | `drop customers referral columns` (pre-launch posture, no data migration) |
| 4 | `c9e4d3f7b502` | PR-6b | `add referral module` (5 tables: codes, referrals, rewards, loyalty accounts, loyalty transactions) |

`b1c4d7e2a830` (`add dobropost_shipment_mappings`) landed immediately
before Sprint 0 began and is the immediate parent of the first Sprint 0
migration.

## Sibling-head incidents — resolved

PR-3a's migration was originally re-anchored from `b1c4d7e2a830` to
`79792d3c84ee` after PR-S6 merged ahead of PR-3a (sibling-head race).
The protocol established in the cascade — `git pull --rebase origin
main` followed by `alembic heads` and a manual `down_revision` fix-up
— resolved each case before push without introducing parallel heads.
No residual artefacts.

## Pre-Sprint-0 mergepoint — legitimate

```
a91c4f2d8e51 (branchpoint)
├─ d4f7e2a91c83  add_pricing_context_global_values_set_at
└─ c3f9b1d4e7a2  add_shipment_edit_intake_return_state
↘
636505b0c13a (mergepoint)  merge pricing_context_set_at + shipment_edit_intake_return heads
```

This branchpoint and merge were created during pre-Sprint-0 concurrent
feature work and resolved cleanly via an explicit merge migration.
Subsequent migrations descend from `636505b0c13a` as a single parent,
restoring linearity. Out of scope for REFACT-009 — surfaced here only
to document that it is intentional, not drift.

## Chain summary

36 migrations total, single head, one legitimate pre-Sprint-0 merge
migration. The chain root is `31e789139629` (`init`); the chain head
is `c9e4d3f7b502` (`add referral module`).

```
<base>
  → 31e789139629  init
  → ... (29 intermediate migrations) ...
  → b1c4d7e2a830  add dobropost_shipment_mappings (last pre-Sprint-0)
  → 79792d3c84ee  PR-S6
  → a7d2c8f1e034  PR-3a / PR-3b
  → b8f3c2e6a401  PR-6b (drop columns)
  → c9e4d3f7b502  PR-6b (add referral module) — HEAD
```

## Findings & follow-ups

* No fixes required.
* No latent sibling heads.
* `alembic upgrade head` clean on a fresh Postgres (verified by PR-6b's
  pre-flight on `localhost:5432`).

## Sprint 0 backend track — closed

REFACT-001 cascade (10 atomic PRs) and REFACT-009 (this audit) close
the Sprint 0 backend track. The remaining cleanup unit, REFACT-008
(dual-registration shim removal), is calendar-gated to **2026-05-15**
and runs autonomously per the cascade's REFACT-008 schedule note.

REFACT-001 architectural foundation handed off to Sprint 1+:

* 14 bounded contexts wired through `MODULES`-driven bootstrap.
* 4 shared kernels — `ModuleDomainEvent`, idempotency, FSM mixin, and
  the generic `Account[BalanceKindT]` ledger.
* 7 architecture fitness rules (Rule 6 / 6b / 8 / 9 / 10 / 11 + CC-001
  event-naming convention) parametrized over the 14 modules.
* ADRs accepted: ADR-005a (Pricing → Catalog ACL inversion),
  ADR-006 (referral module), ADR-007 (ledger as shared kernel).
* Cashback architectural readiness preserved end-to-end: the loyalty
  wallet is the first concrete `ILedger` consumer, intentionally
  designed as the pattern reference for any future ledger consumer.
