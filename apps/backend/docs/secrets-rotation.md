# Secrets Rotation Playbook (T-4 / Sprint 4)

Operational runbook for the credentials Loyality backend depends on.
Covers (a) one-time generation prior to the production launch, and
(b) routine rotation procedures for post-launch incidents.

> [!warning]
> Production credentials are managed in **Railway** (per-service env
> vars on `backend`, `worker`, `scheduler`, `image_ml`). Never commit
> a real value into the repo — `.env.example` is the only blessed
> place for placeholders, and even there we don't paste real tokens
> (incl. test-mode tokens — they leak the account that owns them).

## 1. Inventory — every secret the backend reads

Pulled from `src/bootstrap/config.py` (single source of truth — fields
typed `SecretStr`). Adding a new secret? Add it to `Settings` first,
then update this list.

| Env var | Purpose | Owner |
| --- | --- | --- |
| `SECRET_KEY` | JWT HS256 signing key (access + refresh) | Loyality core |
| `PGPASSWORD` | PostgreSQL password | Railway Postgres add-on (auto) |
| `REDISPASSWORD` | Redis AUTH password | Railway Redis add-on (auto) |
| `RABBITMQ_PRIVATE_URL` | TaskIQ broker URL with embedded creds | Railway RabbitMQ add-on (auto) |
| `BOT_TOKEN` | Aiogram bot token (Telegram FSM + Mini App auth + T-2 push) | @BotFather (production bot) |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Object storage (image module / Bria worker) | Tigris / MinIO |
| `CDEK_ACCOUNT` / `CDEK_SECURE_PASSWORD` | CDEK production API | CDEK partner cabinet |
| `CDEK_TEST_ACCOUNT` / `CDEK_TEST_SECURE_PASSWORD` | CDEK test sandbox | CDEK |
| `YANDEX_DELIVERY_OAUTH_TOKEN` | Yandex Delivery OAuth (production) | Yandex Delivery cabinet |
| `YANDEX_DELIVERY_TEST_OAUTH_TOKEN` | Yandex Delivery sandbox | Yandex Delivery cabinet |
| `DOBROPOST_EMAIL` / `DOBROPOST_PASSWORD` | DobroPost sign-in (12h-token) | DobroPost partner |
| `DOBROPOST_WEBHOOK_TOKEN` | URL-path token for inbound webhooks | Loyality core (we generate) |

`PROVIDER_ACCOUNTS` table-stored credentials (CDEK/Yandex per
customer) — managed via the admin API; **not** an env-level concern.

## 2. Pre-launch one-time generation runbook

Run before flipping `ENVIRONMENT=prod` on Railway. Each step yields a
value that you paste into the Railway service env vars (NOT into the
local `.env`).

### 2.1 `SECRET_KEY` (CRITICAL)

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

86-char URL-safe string. Loyality JWT today is HS256 — single shared
secret. Rotate post-launch invalidates ALL access + refresh tokens
because their HMAC seeds change; plan the cutover during a low-traffic
window. (RS256 migration is a Sprint 5 backlog item.)

### 2.2 `PGPASSWORD`, `REDISPASSWORD`, `RABBITMQ_PRIVATE_URL`

Railway-managed. Provision the add-ons; Railway injects them into
every linked service automatically. Do NOT override them by hand.

### 2.3 `BOT_TOKEN`

* Open `@BotFather` in Telegram.
* `/newbot` → choose a production bot name (e.g. `LoyalityBot`,
  separate from any dev bot).
* Copy the issued `123456:ABC...` token onto Railway env. The
  same token powers (a) Telegram Mini App `initData` HMAC validation,
  (b) FSM storage, (c) T-2 outbound push.
* Configure bot privacy via `/setprivacy` → `Disable` so it can read
  `/start` deep-link payloads.

### 2.4 `S3_*`

* **Tigris (recommended)** — Railway → Tigris add-on. Copy
  `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_ENDPOINT_URL` /
  `S3_BUCKET_NAME` from the dashboard. Set `S3_REGION=auto`.
* **MinIO (self-hosted)** — generate keys via the MinIO console and
  paste them into Railway. Beware: MinIO does not auto-rotate.

### 2.5 CDEK / Yandex Delivery / DobroPost

* CDEK: log into the partner cabinet → `Settings → API` → generate
  `client_id` (becomes `CDEK_ACCOUNT`) and `client_secret`
  (`CDEK_SECURE_PASSWORD`). Sandbox vs prod creds are separate keys
  — keep both wired so smoke testing on staging works.
* Yandex Delivery: cabinet → `Интеграция → OAuth` → "Создать токен".
  Use a dedicated bot name so the token is distinguishable in audit.
* DobroPost: account `email` + `password` from the partner; flip
  `DOBROPOST_USE_STUB=False` only after both creds AND
  `DOBROPOST_WEBHOOK_TOKEN` are populated (the config validator
  `_validate_dobropost_invariants` aborts startup otherwise).

`DOBROPOST_WEBHOOK_TOKEN` is generated locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then registered on the DobroPost side in the webhook URL:
`https://api.loyality.example.com/api/v1/webhooks/dobropost/{TOKEN}`.

## 3. Routine rotation procedure

Triggered when (a) a credential leaks, (b) annual policy review, (c)
team member offboarding.

### 3.1 `SECRET_KEY` rotation

1. Pre-flight: confirm no in-flight legitimate refresh-token flows
   you can't afford to invalidate.
2. Generate the new key locally (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
3. Set `SECRET_KEY` on the Railway `backend` service. Trigger a deploy.
4. Worker / scheduler don't sign JWTs — no env update needed there.
5. Customers will see a single forced re-login on their next request
   (existing tokens fail HMAC verification → 401).

### 3.2 Provider-API key rotation (CDEK / Yandex / DobroPost)

* Provision the NEW key in the provider cabinet WITHOUT revoking the
  old one yet.
* Set the new env vars on Railway, deploy.
* Smoke-test (rate-quote / shipment booking) on staging.
* Revoke the old key in the provider cabinet.

(Avoid the naive "set new, revoke old simultaneously" — Railway
deploys take ~30s during which the old key would already be invalid.)

### 3.3 `BOT_TOKEN` rotation

* `@BotFather → /token → /revoke` issues a fresh token for the same
  bot — username and ID are preserved, so deep-links keep working.
* Update on Railway → backend + bot worker services.
* In-flight Telegram updates with the old token return 401 — Aiogram
  middleware logs and retries on the next poll cycle.

### 3.4 `S3_*` rotation

Tigris / MinIO supports multiple active key pairs on the same bucket.
Generate the new pair, deploy, then revoke the old pair after smoke.
Pre-existing object URLs are unaffected (presigned only on upload).

## 4. What MUST NOT live in `.env.example`

* Real tokens (even test-mode ones — they leak the account).
* Placeholder values shaped like real tokens (e.g. `BOT_TOKEN=123456:...`).
  Use `BOT_TOKEN=<from-@BotFather>` so a `grep` doesn't paste-match.
* Email addresses tied to people (`alice@company.example`) — use
  `ops@example.com` placeholders.
* `DOBROPOST_USE_STUB=false` — the example MUST keep `true` so
  fresh clones boot without crashing on the cross-field validator.

## 5. Validation matrix

| Check | Tool | When |
| --- | --- | --- |
| `SECRET_KEY` length ≥ 64 | manual smoke | pre-launch |
| `DOBROPOST_USE_STUB=false` ⇒ all 3 DP creds set | `Settings._validate_dobropost_invariants` (boot) | every deploy |
| `BOT_TOKEN` matches `^[0-9]+:[A-Za-z0-9_-]{35,}$` | manual | rotation events |
| Railway env diff between staging ↔ prod | `railway variables list` per service | release readiness |

## 6. Incident response

* **Suspected leak** — rotate the affected secret per §3 immediately,
  revoke the old key.
* **Provider 401 storm in logs** — first check whether a recent
  rotation forgot a service; fall back to revoke-and-rotate if the
  count crosses `_DLQ_GROWTH_THRESHOLD` (10/15min, OBS-002 alert).
* **Repo accidentally pushed real value** — `git filter-repo` is too
  late; treat the secret as compromised and rotate. Force-push
  rewrite NEVER replaces a rotation.
