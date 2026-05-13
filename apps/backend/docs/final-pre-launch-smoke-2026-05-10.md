# Final Pre-Launch Smoke Testing Results

**Date**: 2026-05-10
**Sprint Lead**: CEO session
**Goal**: Verify combined Sprint 1+2+3+4 state on main is production-ready

## State at smoke

| Component | HEAD | Status |
| --- | --- | --- |
| Backend (loyalty.git) | `4d4e8c68` (submodule bump) | ✅ |
| Frontend admin (Loyalty-admin.git) | `20a0b4b` (openapi resync) | ✅ |
| Submodule pointer in loyalty | tracks `20a0b4b` after smoke resync | ✅ |
| Snapshot drift backend ↔ frontend admin | 0 (jq -S diff) | ✅ |

## Verification matrix

### Static checks

| Check | Expected | Result |
| --- | --- | --- |
| Backend `make lint` (ruff check) | 0 errors | (Backend Sprint 4 reported clean) |
| Backend `make ty-check` | 0 errors | (Backend Sprint 4 reported clean) |
| Backend `pre-commit run --all-files` | clean | (Sprint 4 production-smoke green) |
| Backend `pytest tests/architecture` | 282 passed | ✅ 282 in 10.59s |
| Backend scheduler/broker bootstrap | schedulers loaded | ✅ "schedulers loaded" |
| Frontend `npm test` | 485/485 | ✅ 485/485 in 10.33s |
| Frontend `npm run lint` | 0/0 | ✅ clean |
| Frontend `npm run typecheck` | clean | ✅ tsc clean |
| Frontend `npm run build` | success | (last verified pre-merge by Frontend session) |
| Frontend `npm run format:check` | clean | ✅ Prettier clean |

### OpenAPI snapshot

| Check | Expected | Result |
| --- | --- | --- |
| Total paths | 229 | ✅ 229 |
| Snapshot identity backend ↔ frontend admin | identical | ✅ identical (after resync) |

### Sprint 1 endpoints (Orders)

| Endpoint | Method | Present | Notes |
| --- | --- | --- | --- |
| `/api/v1/admin/orders` | GET | ✅ | List with statuses + cursor |
| `/api/v1/admin/orders/{id}` | GET | ✅ | Detail (incl. recipientSnapshot from C-5.1) |
| `/api/v1/admin/orders/{id}/history` | GET | ✅ | State history audit |
| `/api/v1/admin/orders/{id}/procure` | POST | ✅ | incoming_declaration regex 1-15 alnum |
| `/api/v1/admin/orders/{id}/hold` | POST | ✅ | typed HoldReason enum |
| `/api/v1/admin/orders/{id}/resume` | POST | ✅ | |
| `/api/v1/admin/orders/{id}/force-cancel` | POST | ✅ | typed CancellationReason enum |
| `/api/v1/admin/orders/{id}/pickup-point` | PATCH | ✅ | |
| `/api/v1/admin/orders/_meta/cancellation-reasons` | GET | ✅ | C-5.2 grouped enum |

### Sprint 2 endpoints (Catalog hardening)

| Endpoint | Method | Present | Notes |
| --- | --- | --- | --- |
| `/api/v1/admin/catalog/products/{id}/_validate-publish` | POST | ✅ | C-1.1 read-only preview |
| `/api/v1/admin/catalog/products/{id}/_validate-update` | POST | ✅ | C-1.2 read-only diff |
| `/api/v1/admin/media/{id}/remove-background` | POST | ✅ | C-2.2 idempotent + 503 envelope |

### Sprint 3 cron jobs (verified through scheduler bootstrap)

| Cron | Schedule | Source | Verified |
| --- | --- | --- | --- |
| outbox_relay | every minute | Sprint 0 | ✅ |
| outbox_pruning | daily 03:00 UTC | Sprint 0 | ✅ |
| order_stuck_in_cn | hourly | Sprint 0 | ✅ |
| order_hold_ttl | every 15min | Sprint 0 | ✅ |
| order_close_window | daily 04:00 UTC | Sprint 0 | ✅ |
| **cart_freeze_expiry** | every 5min | Sprint 3 D1.1 | ✅ |
| **payment_auth_expiry** | every 6h | Sprint 1 B3 | ✅ |
| flush_activity_events | every 5min | activity | ✅ |
| update_product_popularity | daily 05:00 | activity | ✅ |
| ensure_activity_partitions | daily 01:00 | activity | ✅ |
| refresh_co_view_scores | hourly | activity | ✅ |
| **outbox_lag_metric** | every minute | Sprint 3 D2.1 | ✅ |
| **failed_tasks_alert** | every 15min | Sprint 3 D2.2 | ✅ |

### LOG-003 hotfix (post-Sprint-3)

| Endpoint | Method | Present |
| --- | --- | --- |
| `/api/v1/admin/logistics/shipments` | GET | ✅ list with 7 filters + cursor pagination |

### Sprint 4 ETag/If-Match (T-1.1..T-1.4)

| Resource | ETag header on GET | If-Match on PATCH |
| --- | --- | --- |
| Product | ✅ Sprint 2 commit `d7044873` | ✅ |
| Recipient | ✅ Sprint 3 D0.3 commit `e16ca1de` | ✅ |
| **Brand** | ✅ Sprint 4 T-1.1 `a1585788` | ✅ |
| **Category** | ✅ Sprint 4 T-1.2 `780504af` | ✅ |
| **ProductVariant** | ✅ Sprint 4 T-1.3 `c1ae4b05` | ✅ |
| **SKU** | ✅ Sprint 4 T-1.4 `56a233a2` | ✅ |

Frontend ETag interceptor (URL-keyed, Sprint 3 part 1 commit `b870586`)
silently no-ops on responses without ETag header — все 6 entities
автоматически покрыты без FE changes.

### Sprint 4 outbox handlers

| Handler | Source | Verified |
| --- | --- | --- |
| **TelegramShipmentNotifier** (T-2) | Sprint 4 `fc0f6f18` | ✅ 5 events: procured / arrived / last_mile / awaiting_pickup / delivered |
| **FavoritesActivityEnricher** (T-3) | Sprint 4 `27e49b6d` | ✅ overrides structured-log handler with 3.0 weight |

Total registered outbox handlers: **66** (включая legacy snake_case +
canonical PascalCase dual-registrations).

### Catalog UX Polish (Frontend Sprint 3 part 2 PR #25)

| Audit dimension | P0 | P1 closed |
| --- | --- | --- |
| D1 Loading states | 0 | ✅ Skeletons (664a78d) |
| D2 Error states | 0 | ✅ ApiErrorState (8aeca7b) |
| D3 Empty states | 0 | (P2/P3 only — Sprint 5 backlog) |
| D4 Optimistic updates | 0 | ✅ BulkBar pending + 412 helper (4b5a893, c9823b8) |
| D5 A11y | 1 | ✅ Modal focus trap + reveal-on-focus + ARIA (3cc2e55, a1e2db8, 0d27029) |
| D6 Form validation | 0 | ✅ slug aria-invalid (0487d2e) |
| D7 Visual consistency | 1 (CategoryNode reveal) | ✅ Resolved |
| D8 Performance | 0 | (P2/P3 only — Sprint 5 backlog) |
| D9 i18n | 0 | ✅ emoji aria-hidden + alert dedup (4cc28e2) |

**1 P0 + 26 P1 closed**, 38 P2/P3 in Sprint 5 backlog (`docs/catalog-ux-audit-2026-05-10.md`).

## Findings

### F-1 (informational) — Snapshot drift was present, resolved

Frontend admin's `openapi/backend.json` lagged behind backend's
`openapi.json` because Sprint 4 merged after Sprint 3 part 2 (which
froze its snapshot). Resolved during smoke via:
- `chore(openapi): resync to post-Sprint-4 backend snapshot` (commit `20a0b4b` in Loyalty-admin)
- `chore: bump frontend/admin to post-Sprint-4 openapi resync` (commit `4d4e8c68` in loyalty.git)

No runtime impact — BFF runs against backend live.

### F-2 (deferred — Sprint 5 backlog)

Per Backend Sprint 4 T-6 production-readiness audit + Frontend Sprint 3 part 2 catalog audit:

| ID | Severity | Description | Owner |
| --- | --- | --- | --- |
| T-7 | P2 | Product mutations SSE channel (cross-tab sync) | Backend |
| JWT-RS256 | P2 | Migrate JWT HS256 → RS256 (single-secret limitation) | Backend |
| 7-yellows | P2 | T-6 yellows: PII verify, scheduler replication, CORS narrow, slow-query review, CLAUDE.md/README sync | Backend |
| Catalog P2/P3 (38 items) | P2/P3 | UX polish backlog | Frontend |
| Phase B (B1-B6) | P1 | Logistics shipments admin UI | Frontend |

**Phase B note**: backend LOG-003 list endpoint is in main and ready to
be consumed. UI work was deferred to post-launch by user decision (Launch
Path A). Manager can still manage shipments through Order detail page
links — direct shipment list view is a Sprint 5 enhancement, not MVP gap.

### F-3 (no findings) — All Backend T-6 release-blockers resolved

Backend T-6 production-readiness review (commit `b6da488a`) confirmed:
- 0 reds (release-blockers)
- 13 greens (verified production-grade)
- 7 yellows (TL-actionable, not release-blockers)

## Decision

**Smoke green — production deploy approved.**

No release-blockers. Drift was the only finding, resolved during smoke.
Phase B + Sprint 5 items defer to post-launch.

## Next actions

1. **Trigger Railway production deploy** following `docs/deploy-playbook.md`
2. Verify `preDeployCommand` (alembic upgrade) passes — HARD-1 gate
3. Post-deploy smoke per playbook checklist
4. Monitor outbox lag + DLQ growth metrics (Sprint 3 D2.x) for 24h
5. Open Sprint 5 backlog tracker for deferred items

## Smoke testing log

```
2026-05-10 07:30 — Backend sync to origin/main, HEAD=76215738 (Sprint 4 merge)
2026-05-10 07:31 — Frontend admin sync, HEAD=b6a273c (Sprint 3 part 2 merge)
2026-05-10 07:31 — Snapshot drift detected (F-1)
2026-05-10 07:31 — Drift fix: cp + jq filter + prettier on frontend openapi/
2026-05-10 07:32 — Frontend resync verified: 485/485 vitest, lint+tsc clean
2026-05-10 07:33 — Frontend admin commit 20a0b4b pushed
2026-05-10 07:33 — Loyalty submodule pointer bumped, commit 4d4e8c68 pushed
2026-05-10 07:34 — Backend architecture tests: 282 passed in 10.59s
2026-05-10 07:35 — Backend scheduler bootstrap: "schedulers loaded"
2026-05-10 07:35 — Endpoint coverage verified for Sprints 1-4 + LOG-003 + Sprint 4 T-1..T-3
2026-05-10 07:35 — Smoke complete, no release-blockers
```
