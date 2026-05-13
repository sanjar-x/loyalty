# Observability Runbook

> Single page for the on-call. What to look at, what each alert means,
> what to do when one fires. Updated each time a new metric / alert
> lands in Sprint N.

## Where signals live

There is no dedicated metrics backend yet (no Prometheus / Grafana
in the stack). Every observability signal is a **structured log
line** consumed by whatever log aggregator the deploy uses (Railway
log explorer in dev, future Grafana Loki / CloudWatch in prod). Each
alert is built from one `logger.warning` / `logger.error` event name
plus a JSON payload — search the aggregator on the event name.

## Alerts at a glance

| Event name | Source | Cadence | Trigger |
| --- | --- | --- | --- |
| `outbox_lag_high` | `outbox_lag_metric_task` | every 1 min | oldest unprocessed `outbox_messages.created_at` is older than 5 minutes (300 s) |
| `dlq_growth_alert` | `failed_tasks_alert_task` | every 15 min | more than 10 failed_tasks rows in the last 15 minutes |

Below threshold the same tasks emit `outbox_lag` / `dlq_growth_ok`
INFO lines for routine observability — useful for dashboards but not
alerts.

## Runbook entries

### `outbox_lag_high`

**Payload**:
```json
{
  "lag_seconds": 612,
  "pending_count": 88,
  "threshold_seconds": 300
}
```

**What it means**: the outbox relay isn't keeping up with the
inflow. Either the relay is dead, the relay's queue has backed up
(broker issue), or a single consumer is stuck on a slow
event_type and starving the rest.

**First five minutes**:

1. Check the TaskIQ scheduler is alive — `outbox_relay_task`
   should fire every minute. If the schedule line went silent →
   scheduler container crashed → restart.
2. Inspect `pending_count`. If it's bounded (under 1000) — the
   relay is just lagging temporarily; wait one more cycle.
3. If `pending_count` keeps climbing — query the offenders:
   ```sql
   SELECT event_type, COUNT(*)
   FROM outbox_messages
   WHERE processed_at IS NULL
   GROUP BY event_type
   ORDER BY 2 DESC LIMIT 10;
   ```
   Top row = the consumer to triage.

### `dlq_growth_alert`

**Payload**:
```json
{
  "window_minutes": 15,
  "threshold": 10,
  "total_failures": 27,
  "by_task": {
    "order.OrderProcured": 15,
    "catalog.cleanup_storage_after_detached": 12
  }
}
```

**What it means**: TaskIQ tasks are exhausting their retry budget
faster than usual. Either the dependency is down (S3, DobroPost,
payment provider), or a recent deploy introduced a bug in the task
body.

**First five minutes**:

1. Read `by_task` to identify the offender.
2. Pull a sample failure:
   ```sql
   SELECT task_name, error_message, retry_count, failed_at
   FROM failed_tasks
   WHERE task_name = 'order.OrderProcured'
   ORDER BY failed_at DESC LIMIT 5;
   ```
3. If the error points at an external dependency — check that
   provider's status. ORD-006 design covers this case for
   DobroPost: failed bookings auto-pivot to
   `Order.ON_HOLD(BOOKING_FAILED)`, so the customer-side surface
   is graceful — but confirm by spot-checking an affected order.
4. If the error is a stack trace from the task body — check
   recent commits for that task's module, consider rolling back
   the deploy.

## PII safety in structured logs (SEC-001 / D2.3)

`src/infrastructure/logging/pii_redactor.py` masks customs PII
before any payload reaches `logger.info(payload=...)` / `.warning`
/ `.error`. Currently wired:

* Outbox `_structured_log_handler` (every event observed by the
  relay's audit trail handler).

When adding a new `logger.exception(..., payload=raw_event_payload)`
call, wrap the payload in `redact_pii(...)` first. The function is
idempotent so it's safe to apply twice if a peer site already did
the wrap.

Sensitive fields recognised by name (snake_case + camelCase
aliases): `passport_serial`, `passport_number`, `inn`, `phone`,
`email`, `incoming_declaration`, `dp_track_number`.

## Why no Prometheus yet

Sprint 3 spec called for Prometheus as **optional** alongside the
logging hooks. The current stack doesn't include `prometheus_client`
in the runtime image, and adding it is a deploy-side change (extra
Railway service for the scrape target) that the team agreed to defer
until a single grafana instance is in place. The log-line alerts are
sufficient pre-MVP — every paid log aggregator can grep them. When
Prometheus lands, add a gauge alongside each `logger.warning` /
`logger.error` site and update this runbook with the metric names.
