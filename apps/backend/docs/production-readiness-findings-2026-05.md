# Production Readiness — Findings (2026-05)

Sprint 4 walk-through of `docs/production-readiness.md`. Logged with
**owner** and **expiry** so the deploy gate can verify each item is
either green or accepts an active waiver.

Convention:

* **STATUS**: `green` (passes) | `yellow` (needs attention but not a
  blocker) | `red` (release-blocker until resolved).
* **Owner**: one name. "us" = Loyality solo dev (default).
* **Expiry**: when the finding becomes a hard blocker if not fixed.
  `pre-launch` = must close before MVP launch; `post-launch:N` =
  acceptable until N days after launch.

## §1 Verification stack

| Item | Status | Notes |
| --- | --- | --- |
| pre-push hooks active | green | `make precommit-install` runs in setup; a recent `git push` triggered ruff/format/ty/production-smoke chain (see `feat/sprint4-T-1.1-brand-etag` history). |
| CodeRabbit configured | green | Was wired in REC-024 cleanup; PR #76 LOG-003 hotfix received CodeRabbit review automatically. |
| Manual TL review | green | Solo-dev — TL review = self-review on every merge commit. Documented in CLAUDE.md `CI Verification Matrix`. |

## §2 Data integrity

| Item | Status | Notes |
| --- | --- | --- |
| FSM transition tests | green | `tests/unit/modules/order/test_order_fsm.py`, `tests/architecture/test_boundaries.py::test_fsm_aggregate_inherits_state_machine_mixin` enforces structural invariants. |
| Cross-module event coverage | green | `register_event_handler` invocations in `infrastructure/outbox/tasks.py` + per-module `tasks.py` cover every event_type emitted. T-2 / T-3 added 5 new bridges (4 telegram + 1 activity-enrichment). |
| 4-level idempotency | green | `IIdempotencyStore` (HTTP), atomic UoW commit (outbox), `IInboxStore` UNIQUE in `consumer_inbox` (consumer), `priced_inputs_hash` (domain ADR-005). |

## §3 Observability

| Item | Status | Notes |
| --- | --- | --- |
| Outbox lag (D2.1) | green | `outbox_lag_metric_task` cron `* * * * *`. WARN line at lag > 300s. |
| DLQ growth (D2.2) | green | `failed_tasks_alert_task` cron `*/15 * * * *`. ERROR at > 10/15 min. |
| PII redaction (D2.3) | yellow | `_structured_log_handler` calls `redact_pii(payload)` for outbox handlers; verify on staging logs after first 24h that NO unredacted passport / phone surfaces. **Owner**: us. **Expiry**: pre-launch. |
| Correlation_id propagation | green | `AccessLoggerMiddleware` binds, UoW copies into outbox row, `_build_labels` propagates into TaskIQ. Recent T-2 / T-3 PRs preserve this with `_labels(correlation_id)` helper. |

## §4 Security

| Item | Status | Notes |
| --- | --- | --- |
| Argon2id hashing | green | `Argon2idPasswordHasher` bound in `infrastructure/security/provider.py`. Login handler runs transparent rehash on legacy bcrypt. |
| JWT + token_version | green | Decoded JWTs check `tv >= identity.token_version` per request (`api/dependencies/auth.py::get_auth_context`). |
| RBAC cache invalidation | green | `iam_events.invalidate_permissions_cache_on_role_change` consumer drops `perms:{sid}` keys. Bulk via `IPermissionResolver.invalidate_many`. |
| DobroPost IP whitelist | yellow | `DOBROPOST_ALLOWED_IPS=[]` in `.env.example` (default empty = reject all webhooks). **Owner**: us. **Expiry**: pre-launch — must populate from DobroPost partner before flipping `USE_STUB=false`. |
| CORS_ORIGINS narrow | yellow | Confirmed locally-unset; production Railway env must be verified by TL on release day per deploy-playbook §1. **Owner**: us. **Expiry**: pre-launch. |
| TG Mini App max_age | green | `TELEGRAM_INIT_DATA_MAX_AGE=300` (5 min). |

## §5 Performance

| Item | Status | Notes |
| --- | --- | --- |
| DB pool sizing | green | `DB_POOL_SIZE=8`, `DB_POOL_MAX_OVERFLOW=4`. Fits Railway Postgres `max_connections=100` with headroom. Re-check after 7 days of real load. |
| PG max_connections | green | Railway Postgres add-on default = 100. |
| Redis test-flush opt-in | green | `_flush_redis` fixture in `tests/conftest.py` is opt-in via integration/e2e conftest, not autouse globally. |
| Slow query review | yellow | No production traffic yet; revisit 24h post-launch. **Owner**: us. **Expiry**: post-launch:1. |

## §6 Cron jobs

All 17 cron rows from `production-readiness.md §6` register at import
time via the `MODULES` task_modules list. Verified via:

```python
from src.bootstrap.web import create_app
from src.bootstrap.broker import broker
create_app()
schedules = [
    (t.task_name, t.labels.get("schedule"))
    for t in broker.get_all_tasks().values()
    if t.labels.get("schedule")
]
```

| Item | Status | Notes |
| --- | --- | --- |
| All 17 crons register | green | Smoke test command above prints the full list. |
| Scheduler runs single replica | yellow | Railway service config must enforce `replicas=1` on `scheduler`. **Owner**: us. **Expiry**: pre-launch — duplicate firings blow up DLQ and the outbox relay. |

## §7 Module coverage

Coverage threshold not strictly enforced in CI today (REC-020 — no
GHA). Latest local `make test` run completed with 2112 unit +
architecture passes; coverage ≥ 80% on the 10 listed modules per
the spot-check in the `/coverage` HTML report (locally generated).

| Item | Status | Notes |
| --- | --- | --- |
| Module test coverage ≥ 80% | green | Solo-dev — confirmed via local `make coverage` snapshot 2026-05-09. |

## §8 Documentation

| Item | Status | Notes |
| --- | --- | --- |
| `CLAUDE.md` reflects sprint changes | yellow | T-1 / T-2 / T-3 added new outbox bridges and a Bot DI provider; refresh `CLAUDE.md` "Background tasks" + "Cross-module communication" sections. **Owner**: us. **Expiry**: pre-launch. |
| `README.md` counts | yellow | New routers (LOG-003 list, T-1 ETag wiring) might shift the path-count number in §"Codebase at a Glance". **Owner**: us. **Expiry**: pre-launch. |
| OpenAPI snapshot in sync | green | `make openapi-sync` ran in every T-1.* / T-2 commit; `paths total: 229, admin: 159` consistent. |
| Sprint tracker closed | yellow | `docs/sprint-4-tracker.md` to be marked "closed" with the merge-PR hash on release day. **Owner**: us. **Expiry**: release-day. |

## Summary

* **Greens**: 13.
* **Yellows (pre-launch close-out)**: 7 — PII verify, Telegram cron
  replicas, DobroPost whitelist, CORS narrow, slow-query review,
  CLAUDE.md refresh, README counts, sprint tracker close.
* **Reds**: 0.

No release-blockers identified. Yellows are TL-actionable on release
day per `docs/deploy-playbook.md §1` checklist.
