# Sprint 2 + Sprint 3 Pre-Merge Smoke Results

**Date**: 2026-05-09
**Sprint Lead**: CEO session
**PR cascade**:
- PR #22 (Sprint 1 Orders) — pending merge
- PR #23 (Sprint 3 part 1: bg-removal + publish gate + ETag + brands) — stacked on PR #22

## Verification matrix

| Check | Expected | Actual | Status |
| --- | --- | --- | --- |
| `backend/openapi.json` mtime | post-Backend-push | 2026-05-09 21:01 | ✅ |
| `frontend/admin/openapi/backend.json` mtime | post-Frontend-sync | 2026-05-09 22:45 | ✅ |
| Snapshot identity (jq -S diff) | identical content | exit 0 | ✅ |
| OpenAPI total paths | ≥220 (after C-1, C-5, LOG-003) | 229 | ✅ |
| `_validate-publish` endpoint | present | `/api/v1/admin/catalog/products/{id}/_validate-publish` | ✅ |
| `_validate-update` endpoint | present | `/api/v1/admin/catalog/products/{id}/_validate-update` | ✅ |
| `recipientSnapshot` in AdminOrderResponse | present | (verified via jq) | ✅ |
| `_meta/cancellation-reasons` endpoint | present | `/api/v1/admin/orders/_meta/cancellation-reasons` | ✅ |
| `bg-removal` endpoint | present | `/api/v1/admin/media/{id}/remove-background` | ✅ |
| Backend architecture tests | 282 passed | 282 passed in 11.26s | ✅ |
| Backend `git status` | clean, 0 ahead origin | 0 commits ahead origin/main | ✅ |
| Frontend `npm test` | 386/386 passing | 386/386 in 11.23s | ✅ |
| Frontend `npm run build` | clean production build | success (80+ routes) | ✅ |
| Frontend `npm run lint` | 0 errors | 0/0 (Frontend reported) | ✅ |
| Frontend `npm run typecheck` | clean | clean (Frontend reported) | ✅ |

## Findings

### F-1 (HIGH severity) — Missing GET /admin/logistics/shipments list endpoint

**Status**: NOT in Backend Sprint 3 push. Hotfix LOG-003 was assigned but not executed.

**Impact**: Frontend Sprint 3 part 2 cannot start B1-B5 (shipments admin UI). Other tracks (A2 catch-up, A3.2/A3.3, Phase C polish) are not blocked.

**Resolution**: Backend hotfix task (LOG-003) to be re-issued post-cascade. Estimated 1.5h.

### F-2 (LOW severity) — D0.3 partial scope

**Status**: D0.3 commit `e16ca1de` wired ETag only for Recipient. Brand/Category/Variant/SKU deferred → Sprint 4 (need DDL for `version` column, see `docs/sprint-3-deferred.md`).

**Impact**: Frontend A6 verify limited to Recipient. ETag interceptor (Frontend A4) is URL-keyed and silently no-ops on responses without ETag header — no regression for Brand/Category/Variant/SKU.

**Resolution**: Sprint 4 backlog (Backend).

### F-3 (LOW severity) — Open backend PRs #29, #30 not reconciled

**Status**:
- PR #29 (REC-024 GHA cleanup) — overlaps with already-removed workflow
- PR #30 (HARD-2 Telegram alerter) — overlaps with D2.1+D2.2 (commit `bc491d87`)

**Impact**: Risk of duplicate observability implementation.

**Resolution**: Backend session to review PR #29/#30 against current main, close as obsolete or merge as complement.

## Decision

**Cascade merge approved** — F-1/F-2/F-3 are post-merge backlog items, not merge blockers.

## Next actions

1. Merge PR #22 (Sprint 1 Orders) into main
2. Frontend rebase PR #23 onto fresh main
3. Merge PR #23 (Sprint 3 part 1) into main
4. Issue Backend hotfix task (LOG-003 list endpoint)
5. Frontend starts Sprint 3 part 2 — Phase A2 + A3 + Phase C work first, B1-B5 blocked until Backend LOG-003 ships

## Test execution log

```
Backend architecture: 282 passed in 11.26s
Frontend vitest: 42 files, 386/386 tests, 11.23s duration
Frontend production build: clean, all routes prerendered
OpenAPI snapshot diff: jq -S deep diff exit 0 (identical contracts)
```
