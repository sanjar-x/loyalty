# Production Readiness Checklist (T-6 / Sprint 4)

Final pre-launch gate. Walk through every item in this doc;
findings (any item not green) feed into
`docs/production-readiness-findings-2026-05.md`. The deploy is
green only when every check passes OR has a documented exception
with an owner and an expiry date.

## 1. Verification stack (REC-020)

- [ ] **pre-push hooks** active and green on the developer's
      machine. Verified via `make precommit-install` then a dummy
      `git push --dry-run`.
- [ ] **CodeRabbit** GitHub App configured for the repo. Check
      `Settings → Integrations` on GitHub; expected reviewer login
      `coderabbitai[bot]`.
- [ ] **Manual TL review gate** — every PR merged into `main`
      this sprint shows "approved by TL" in the merge commit
      trailer or PR conversation.

## 2. Data integrity

- [ ] FSM aggregates each have `tests/.../test_*_fsm.py` with
      transition coverage (Order 14-state, PaymentIntent 6-state,
      Shipment 6-state, Cart 4-state, Recipient 3-state, Product
      5-state).
- [ ] Every cross-module event has either a real consumer or a
      structured-log-only handler — no event lands in the relay's
      "unknown event_type, skipping" branch. Check via
      `grep register_event_handler src -r`.
- [ ] Idempotency on 4 levels:
      1. HTTP `Idempotency-Key` (CreateOrderFromCart, refund flows).
      2. Outbox at-least-once (UoW commits both aggregate + event
         in one DB transaction).
      3. Consumer inbox UNIQUE `(event_id, consumer)` (every
         `run_inbox_idempotent`-wrapped task).
      4. Domain `inputs_hash` (SKU pricing recompute, ADR-005).

## 3. Observability

- [ ] **Outbox lag metric** (D2.1) — confirm
      `outbox_lag_metric_task` cron schedule fires every minute on
      the scheduler service. Check Railway logs for `outbox_lag` /
      `outbox_lag_high` lines.
- [ ] **DLQ growth alert** (D2.2) — `failed_tasks_alert_task` runs
      every 15 min; threshold = 10 failures / 15 min. Verify in
      scheduler logs.
- [ ] **PII redaction** (D2.3) — verify on staging-equivalent that
      `recipient_phone`, `passport_serial`, `passport_number`, `inn`
      do NOT appear unredacted in production logs. Run:
      `grep -E "passport|phone|inn" railway-prod-logs | grep -v "REDACTED"`.
- [ ] Structured logs include `correlation_id` end-to-end (HTTP →
      outbox → TaskIQ task body). Random spot-check on a recent
      order — search by `correlation_id`, expect 5+ events from
      different services.

## 4. Security

- [ ] **Argon2id** password hashing — confirm `IPasswordHasher`
      bound to `Argon2idPasswordHasher` in DI. Verified via
      `infrastructure/security/provider.py`.
- [ ] **JWT HS256 + token_version** — `IdentityTokenVersionBumped`
      flow tested at least once on staging (force-logout via
      admin API).
- [ ] **RBAC permissions cache** — Redis `perms:{session_id}` TTL
      = 300s; cache invalidation fires on `RoleAssignmentChanged`
      via the `iam_events` consumer. Verified by changing a role
      and watching the admin dashboard refresh under 5s.
- [ ] **DobroPost webhook IP whitelist** — `DOBROPOST_ALLOWED_IPS`
      contains the partner's documented IP range. Empty list rejects
      all webhooks (default).
- [ ] **CORS_ORIGINS** — production frontends only. Run:
      `railway run -s backend echo $CORS_ORIGINS` and confirm
      no `localhost:` entries.
- [ ] **Telegram Mini App init_data** — `TELEGRAM_INIT_DATA_MAX_AGE=300`
      (5 min) — replay window short enough to bound stolen-init-data
      attacks.

## 5. Performance

- [ ] **DB pool sizing** — `DB_POOL_SIZE=8`, `DB_POOL_MAX_OVERFLOW=4`.
      4 services × 12 conns peak = 48 ≤ Railway Postgres add-on's
      `max_connections=100`. Bump only after measured contention.
- [ ] **PG max_connections** ≥ 100 — verify on the Railway Postgres
      add-on dashboard.
- [ ] **Redis flush per test** disabled in production env — check
      `tests/conftest.py` opt-in fixture is NOT autouse globally.
- [ ] **Query plans** — review the slowest 10 queries on Railway
      `Metrics → Database → Slow queries` after 24h of traffic.
      Expected: storefront list / search ≤ 50ms p95, order detail
      ≤ 80ms p95.

## 6. Cron jobs (TaskIQ Beat — every entry must be live)

Sourced from `grep '@broker.task' src/ -r | grep schedule`. Every
row below MUST appear in scheduler logs after first 24h of traffic.

| Task | Cron | Module |
| --- | --- | --- |
| `outbox_relay_task` | `* * * * *` | infrastructure/outbox |
| `outbox_pruning_task` | `0 3 * * *` | infrastructure/outbox |
| `outbox_lag_metric_task` | `* * * * *` | infrastructure/outbox (OBS-001) |
| `failed_tasks_alert_task` | `*/15 * * * *` | infrastructure/outbox (OBS-002) |
| `order_stuck_in_cn_cron` | `0 * * * *` | order |
| `order_hold_ttl_cron` | `*/15 * * * *` | order |
| `order_close_window_cron` | `0 4 * * *` | order |
| `cart_freeze_expiry_cron` | `*/5 * * * *` | cart |
| `payment_auth_expiry_cron` | `0 */6 * * *` | payment |
| `flush_activity_events_task` | `*/5 * * * *` | activity |
| `update_product_popularity_task` | `0 5 * * *` | activity |
| `ensure_activity_partitions_task` | `0 1 * * *` | activity |
| `refresh_co_view_scores_task` | `17 * * * *` | activity |
| `tracking_poll_task` | `*/5 * * * *` | logistics |
| `cleanup_expired_quotes_task` | `0 * * * *` | logistics |
| `edit_task_poll_task` | `* * * * *` | logistics |
| `image_cleanup_orphans_task` | `0 */6 * * *` | image |

Note: TaskIQ requires exactly ONE scheduler instance per cron. If
Railway runs >1 scheduler replica, every cron fires N times. Verify
`scheduler` service is `Replicas: 1`.

## 7. Module test coverage

Target ≥ 80% on the modules below. Sourced from `make test` →
coverage report.

- [ ] `catalog` — largest module, EAV + per-SKU pricing FSM
- [ ] `order` — 14-state FSM, dual-leg shipments, async DobroPost booking
- [ ] `payment` — provider abstraction + auth-expiry cron
- [ ] `logistics` — 3 providers + 18 events
- [ ] `cart` — checkout snapshot + 4-state FSM
- [ ] `identity` — 20 commands, RBAC, OIDC + Telegram + email auth
- [ ] `pricing` — formula AST evaluator + recompute pipeline
- [ ] `recipient` — customs validation FSM
- [ ] `image` — presigned upload + Pillow processing
- [ ] `activity` — Redis hot path + co-view matrix

## 8. Documentation

- [ ] `backend/CLAUDE.md` reflects every module change shipped
      this sprint (T-1 ETag, T-2 Telegram push, T-3 favorites
      enrichment).
- [ ] `README.md` (root) — counts and table updated if a new
      router / module landed.
- [ ] OpenAPI snapshot — `jq '.paths | keys | length' openapi.json`
      matches the latest commit's count from
      `make openapi-sync`.
- [ ] Sprint tracker — `docs/sprint-4-tracker.md` marked closed
      with all commit hashes recorded.

## 9. How to use this checklist

1. Walk through every item in the order listed; tick what passes.
2. For every unticked item, drop a line into
   `docs/production-readiness-findings-2026-05.md` with:
    * **What**: the failing check.
    * **Owner**: who's fixing it.
    * **Expiry**: when this becomes a release blocker (e.g.
      "before Wave 2 launch").
3. Findings doc gates the deploy: TL review checks every item is
   either green here or has an active expiry that hasn't passed.
4. When Sprint 5 starts, archive this checklist as
   `docs/production-readiness-2026-05.md` and start a fresh one.

## 10. Cross-references

* `docs/secrets-rotation.md` — pre-launch credential generation.
* `docs/deploy-playbook.md` — release-day procedure & rollback.
* `docs/sprint-4-tracker.md` — what shipped this sprint.
* `tests/architecture/test_boundaries.py` — what the build enforces.
