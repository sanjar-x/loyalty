# Production Deploy Playbook (T-5 / Sprint 4)

Deterministic procedure for shipping the Loyality backend to Railway.
Use this on every production release — no improvising.

> [!info]
> Three Railway services share the same image: `web`, `worker`,
> `scheduler` (and `image_ml` when the heavy bg-removal model is
> needed). They are distinguished by `SERVICE_MODE` env var.
> `railway.toml` `preDeployCommand` runs `alembic upgrade head` only
> on `web` to avoid concurrent migration locks (HARD-1 / REC-005).

## 1. Pre-deploy checklist

Run before clicking the deploy button. Each unchecked item is a
release-blocker.

- [ ] Branch is `main` and the local working tree is clean
      (`git status` empty).
- [ ] `make test` — passes locally on `main`. Includes
      `production-smoke + tests-unit + tests-architecture`. (Hooks
      run automatically on every `git push`, but a deliberate sweep
      before deploy catches anything that landed via merge but didn't
      trip a hook.)
- [ ] OpenAPI snapshot is current: `make openapi-sync` then
      `git status` reports no diff in `backend/openapi.json`. The
      frontend admin app pulls types from the snapshot — out-of-sync
      backend ↔ frontend produces silent type drift.
- [ ] Frontend admin Sprint 3 part 2 PR merged on `main`. The
      backend change set includes router renames (LOG-003 hotfix)
      and the ETag/If-Match contract on Brand/Category/Variant/SKU
      that the frontend interceptor expects.
- [ ] Smoke testing pass on staging (CEO session) — see
      `docs/sprint-{n}-smoke-results.md`. Smoke MUST exercise the
      golden-path flows changed in this release, plus auth, cart,
      checkout, payment authorize.
- [ ] Secrets rotated per `docs/secrets-rotation.md` if a key is
      due for rotation OR a team member offboarded since the last
      release.
- [ ] `DOBROPOST_USE_STUB=false` on Railway `backend` service AND
      `DOBROPOST_EMAIL` / `DOBROPOST_PASSWORD` /
      `DOBROPOST_WEBHOOK_TOKEN` are set. The boot-time validator
      (`Settings._validate_dobropost_invariants`) aborts startup if
      missing — verify NOW, not at deploy time.
- [ ] `BOT_TOKEN` points at the production bot (NOT a dev bot —
      `@BotFather → /token` for the production bot ID). Verify by
      checking the bot's username in Telegram.
- [ ] `CORS_ORIGINS` on the `backend` service contains ONLY the
      production frontend URLs (no `http://localhost:*`,
      no `*.netlify.app` preview branches).
- [ ] `ENVIRONMENT=prod` and `DEBUG=False` on every service.

## 2. Deploy procedure

### 2.1 Trigger the deploy

Railway pushes are tied to GitHub. Once the PR merges into `main`:

1. Railway autodetects the push and starts a build.
2. The build runs `Dockerfile` (image used by all four services).
3. **Per service**, Railway then runs `preDeployCommand` BEFORE
   shifting traffic:
   - `web` → `alembic upgrade head` (canonical migration, HARD-1).
   - `worker` / `scheduler` / `image_ml` → echo skip.
4. On success, Railway swaps traffic to the new revision.
   On failure, the deploy aborts and the previous revision continues
   serving.

If you DON'T see Railway pick up the push within 2 min, check the
Railway dashboard `Activity` tab — sometimes the GitHub webhook needs
a re-trigger from `Settings → Service → Deploy`.

### 2.2 Monitor the deploy

Railway dashboard → service `web` → `Deployments` tab:

* `preDeploy` log shows `alembic upgrade head` output. Look for
  `Running upgrade {prev} -> {head}, ...`. Empty output (already at
  head) is also success.
* `Build` log finishes with `Build successful`.
* `Deploy` log: first lines are `Initialising Dishka IoC container`
  (from `src.bootstrap.web`). The container then logs
  `Starting Enterprise API` with `version=...`.
* `Health` switches to green within ~30s of deploy start.

Repeat for `worker` and `scheduler` services. Their `Deploy` logs
should show `TaskIQ Worker started and ready to process tasks` and
`TaskiqScheduler initialised` respectively.

### 2.3 Verify the new revision serves

Run from your laptop. `$BACKEND` is the production URL.

```bash
# 1. Health
curl -s "$BACKEND/health" | jq .  # {"status": "ok", "environment": "prod"}

# 2. OpenAPI version present (proves the new code shipped)
curl -s "$BACKEND/health" -i | grep -i x-process-time-ms

# 3. Outbox relay is firing (gives a few seconds for the first tick)
sleep 60
# Look in Railway logs for `Outbox Relay: batch processed`.

# 4. Scheduler picked up the cron labels — check
# `TaskiqScheduler initialised, schedule_count=N` in scheduler logs.
```

## 3. Post-deploy smoke

Run AS A REAL CUSTOMER through the live UI. Does NOT test cancellation
flows — only golden path:

1. **Auth** — register a fresh email at `/auth/register` (admin panel
   has its own login but customer flows live in main app).
2. **Catalog** — open the storefront, list products, drill into one
   PDP. Storefront should return cached responses fast (<300 ms).
3. **Order** — add a SKU to cart, choose a pickup point, freeze
   checkout, confirm. Verify a `PaymentIntent` is `AUTHORIZED`
   (DB query OR `GET /payments/intents/{id}`).
4. **Telegram push (if account is Telegram-linked)** — manager
   procures the order via admin panel; confirm a "Ваш заказ выкуплен"
   message lands in the bot chat (T-2).

DO NOT test:
- Cancellation flows in production until pricing/inventory verified.
- DobroPost passport-fail scenarios — needs intentionally bad data.

## 4. Rollback procedure

When a deploy fails or post-deploy smoke surfaces a regression, you
have three rollback paths in increasing severity:

### 4.1 Fast — Railway auto-rollback (preDeployCommand failure)

If `alembic upgrade head` fails, Railway aborts the deploy
automatically — the previous revision continues serving. No action
needed; investigate the migration in the deploy log.

### 4.2 Manual — redeploy a prior revision

When the build/deploy succeeded but post-deploy smoke caught a bug:

```bash
# Either via the dashboard:
#   Deployments → previous green deploy → "Redeploy"
# Or via CLI:
railway redeploy --service backend --deployment-id <ID-from-dashboard>
```

This re-runs `preDeployCommand` on the **previous** image — usually
no-op because the migration is already at head.

### 4.3 DB-state rollback (rare, dangerous)

ONLY when the regression includes a non-backward-compatible migration:

```bash
# 1. Take a manual Railway Postgres backup (dashboard → Backups → Take).
# 2. Connect a one-shot container with the migration tooling.
railway run -s backend uv run alembic downgrade -1
# 3. Verify production is healthy on the previous schema, then redeploy
#    the previous image (§4.2).
```

DO NOT downgrade across multiple migrations cascade-style — each
backward step is a discrete decision. Plan an expand-deploy-contract
forward fix instead (REC-022 backlog).

## 5. Incident playbook

| Symptom | First action |
| --- | --- |
| `Outbox lag > 10 min` (OBS-001 WARN line in logs) | Check `failed_tasks` table for stuck consumer; investigate per-event log line for the trapped event_type. |
| `DLQ growth > 10 / 15 min` (OBS-002 ERROR `dlq_growth_alert`) | Page TL. ``by_task`` breakdown identifies the task; correlate with structlog `request_id` + `correlation_id` for root cause. |
| 500 spike on a single endpoint | `request_id` is in every error envelope — grep production logs for the matching ID; the structured log line carries the stack frame. |
| `IDENTITY_INVALID` 401 surge | Likely `SECRET_KEY` rotation hit a stale token cache — wait one access-token TTL (15 min) for natural expiry. If it persists, `bump_token_version` per identity invalidates outstanding JWTs. |
| Telegram push storm in `failed_tasks` | T-2 adapter swallows known-permanent failures. A storm of `TelegramRetryAfter` indicates we're blowing the bot's rate limit — reduce push fan-out or batch. |

## 6. Cross-team signals

After every successful production deploy:

* Update `docs/sprint-{n}-tracker.md` → mark the release as shipped.
* Notify Frontend so they can deploy their own Sprint matching this
  backend revision.
* Tag the merge commit on GitHub (`v{semver}`) once the post-deploy
  smoke is green — the tag is the canonical "good revision" anchor
  for §4.2 rollbacks.
