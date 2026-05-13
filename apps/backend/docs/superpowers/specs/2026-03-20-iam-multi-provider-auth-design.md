# IAM Multi-Provider Auth Design

**Date:** 2026-03-20
**Status:** Draft (pending review)
**Standards:** OWASP Authentication/Session Cheat Sheets, NIST SP 800-63B-4, RFC 9700 (OAuth 2.0 Security BCP), WebAuthn Level 2
**References:** Auth0, Supabase Auth, Firebase Auth, FusionAuth, Keycloak, Clerk

---

## Problem

Customer может авторизоваться через Telegram, email+password, Google, Apple — но текущая архитектура создаёт отдельный Identity (и отдельный Customer) для каждого способа входа. `telegram_credentials` выделена в отдельную таблицу с Shared PK, хотя Telegram — такой же внешний провайдер как Google и Apple.

Дополнительные проблемы:
- Нет возможности привязать несколько провайдеров к одному аккаунту
- Нет email verification guard при auto-linking (риск pre-account takeover — OWASP)
- Session entity не имеет idle timeout (только absolute expiry) — нарушение OWASP/NIST
- Нет механизма мгновенной инвалидации токенов (token versioning)
- LinkedAccount не хранит `email_verified` от провайдера

---

## Decisions

| Вопрос | Решение | Обоснование (стандарт) |
|--------|---------|----------------------|
| Модель | Один Identity — несколько credentials | Auth0/Supabase/Firebase/Keycloak universal pattern |
| Credentials | `local_credentials` (0..1) + `linked_accounts` (0..N) | FusionAuth IdentityProviderLink pattern |
| Telegram | Обычный провайдер в `linked_accounts`, не отдельная таблица | Единообразие, упрощение кода |
| Auto-link | **Только по verified email** от trusted провайдеров | Supabase/OWASP: предотвращение pre-account takeover |
| Untrusted email | Возврат `needs_email_verification` — пользователь верифицирует | FusionAuth Pending Link strategy |
| Telegram (без email) | Explicit linking only (из приложения) | Telegram не даёт email — auto-link невозможен |
| Provider metadata | JSONB `provider_metadata` в `linked_accounts` | Auth0 normalized profile + provider-specific data |
| Token versioning | `token_version` integer на Identity для мгновенной инвалидации | SkyCloak pattern — проще Redis blacklist для монолита |
| Session timeouts | Dual model: idle (sliding) + absolute (fixed) | OWASP Session Cheat Sheet, NIST SP 800-63B-4 |
| OIDC flows | PKCE mandatory для всех OAuth code flows | RFC 9700 (2025), OAuth 2.1 |
| Customer profile | `username` — общее поле Customer, заполняется из любого провайдера | — |

---

## Target Architecture

### DB Schema

```
identities
  ├── id                      UUID PK
  ├── primary_auth_method     "LOCAL" | "TELEGRAM" | "OIDC"
  ├── account_type            "CUSTOMER" | "STAFF"
  ├── is_active               bool
  ├── token_version           INTEGER NOT NULL DEFAULT 1    ← NEW: мгновенная инвалидация
  ├── created_at / updated_at / deactivated_at / deactivated_by
  │
  ├── local_credentials       (0..1, Shared PK)
  │     ├── identity_id       PK+FK
  │     ├── email             UNIQUE
  │     └── password_hash
  │
  ├── linked_accounts         (0..N)
  │     ├── id                UUID PK
  │     ├── identity_id       FK → identities
  │     ├── provider          "telegram" | "google" | "apple"
  │     ├── provider_sub_id   VARCHAR
  │     ├── provider_email    VARCHAR nullable              ← KEPT: email от провайдера
  │     ├── email_verified    BOOLEAN NOT NULL DEFAULT false ← NEW: верифицирован ли email провайдером
  │     ├── provider_metadata JSONB DEFAULT '{}'
  │     ├── created_at / updated_at
  │     └── UNIQUE(provider, provider_sub_id)
  │
  ├── sessions                (0..N)
  │     ├── id                UUID PK
  │     ├── identity_id       FK → identities
  │     ├── refresh_token_hash VARCHAR UNIQUE
  │     ├── ip_address         INET
  │     ├── user_agent         VARCHAR
  │     ├── is_revoked         BOOLEAN
  │     ├── created_at         TIMESTAMPTZ                  — absolute start
  │     ├── expires_at         TIMESTAMPTZ                  — absolute max lifetime
  │     ├── last_active_at     TIMESTAMPTZ NOT NULL         ← NEW: последнее использование
  │     ├── idle_expires_at    TIMESTAMPTZ NOT NULL         ← NEW: sliding idle timeout
  │     └── activated_roles    (session_roles junction)
  │
  └── identity_roles          (N..M)  — без изменений

customers
  ├── id                      FK → identities.id (Shared PK)
  ├── profile_email           VARCHAR nullable
  ├── first_name              VARCHAR
  ├── last_name               VARCHAR
  ├── username                VARCHAR nullable              ← NEW
  ├── phone                   VARCHAR nullable
  ├── referral_code           VARCHAR UNIQUE
  ├── referred_by             FK → customers.id
  └── created_at / updated_at
```

### Two Categories of Credentials

- **`local_credentials`** (0..1) — email + password_hash. Единственный тип с паролем. Argon2id (OWASP: m=19MiB, t=2, p=1 minimum).
- **`linked_accounts`** (0..N) — ВСЕ внешние провайдеры: Telegram, Google, Apple. Provider-specific данные в JSONB `provider_metadata`. Поле `email_verified` определяет, можно ли использовать email для auto-link.

### Token Versioning (мгновенная инвалидация)

```
Identity.token_version (int, default=1)
  ↓ включается в JWT payload: {"sub": "...", "sid": "...", "tv": 1}
  ↓ при проверке JWT: если jwt.tv < identity.token_version → reject
  ↓ increment on: password change, role change, force logout, security event
```

**Зачем:** Текущая архитектура не проверяет валидность сессии при каждом запросе (stateless JWT). Token versioning даёт мгновенную инвалидацию всех токенов за O(1) — одно поле INTEGER вместо Redis blacklist. Для монолита это оптимальный подход (Auth0/Clerk pattern).

**Когда инкрементировать:**
- Смена пароля
- Изменение ролей (RoleAssignmentChangedEvent)
- Force logout all sessions
- Деактивация аккаунта
- Подозрительная активность (reuse detection)

### Session Dual Timeout Model (OWASP/NIST)

```
Session.created_at        — фиксированный момент создания
Session.expires_at        — absolute max lifetime (never extends)
Session.last_active_at    — обновляется при каждом refresh
Session.idle_expires_at   — sliding timeout (extends on refresh)
```

**Конфигурация:**

| Параметр | Default | Стандарт |
|----------|---------|----------|
| `SESSION_ABSOLUTE_LIFETIME_HOURS` | 24 | NIST AAL1: 30 days, AAL2: 12 hours |
| `SESSION_IDLE_TIMEOUT_MINUTES` | 30 | OWASP: 15-30 min (general), 2-5 min (high-value) |
| `TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS` | 168 (7 дней) | Mobile/Mini App: более длинные сессии |
| `TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES` | 1440 (24 часа) | Mini App: менее частое использование |

**Проверка при refresh:**
```python
def ensure_valid(self) -> None:
    if datetime.now(UTC) >= self.expires_at:
        raise SessionExpiredError("absolute timeout exceeded")
    if datetime.now(UTC) >= self.idle_expires_at:
        raise SessionExpiredError("idle timeout exceeded")
    if self.is_revoked:
        raise SessionRevokedError()

def touch(self, idle_timeout_minutes: int) -> None:
    """Extend idle timeout on activity (refresh token use)."""
    now = datetime.now(UTC)
    self.last_active_at = now
    self.idle_expires_at = now + timedelta(minutes=idle_timeout_minutes)
```

### Telegram provider_metadata Example

```json
{
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "language_code": "en",
  "is_premium": true,
  "photo_url": "https://t.me/i/userpic/320/photo.jpg",
  "allows_write_to_pm": true
}
```

### Google/Apple provider_metadata Example

```json
{
  "email": "john@gmail.com",
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/...",
  "locale": "en"
}
```

---

## Domain Layer Changes

### Renames

- `IdentityType` → `PrimaryAuthMethod` (values: LOCAL, OIDC, TELEGRAM)
- `Identity.type` → `Identity.primary_auth_method`

### New Fields on Identity

```python
@dataclass
class Identity(AggregateRoot):
    # ... existing fields ...
    token_version: int = 1  # NEW: increment to invalidate all JWTs instantly

    def bump_token_version(self) -> None:
        """Increment token version to invalidate all outstanding JWTs."""
        self.token_version += 1
        self.updated_at = datetime.now(UTC)
```

### New Value Objects

```python
class AuthProvider(str, Enum):
    TELEGRAM = "telegram"
    GOOGLE = "google"
    APPLE = "apple"

# Providers whose email claims are verified at the IdP level
# Google/Apple verify email ownership — safe for auto-link
# Telegram does NOT provide email — never auto-link
TRUSTED_EMAIL_PROVIDERS: frozenset[str] = frozenset({
    AuthProvider.GOOGLE,
    AuthProvider.APPLE,
})
```

### New Fields on Session

```python
@dataclass
class Session:
    # ... existing fields ...
    last_active_at: datetime      # NEW: updated on each token refresh
    idle_expires_at: datetime     # NEW: sliding idle timeout

    @classmethod
    def create(cls, ..., idle_timeout_minutes: int = 30) -> Session:
        now = datetime.now(UTC)
        return cls(
            ...,
            last_active_at=now,
            idle_expires_at=now + timedelta(minutes=idle_timeout_minutes),
        )

    def touch(self, idle_timeout_minutes: int) -> None:
        """Extend idle timeout on token refresh."""
        now = datetime.now(UTC)
        self.last_active_at = now
        self.idle_expires_at = now + timedelta(minutes=idle_timeout_minutes)

    def ensure_valid(self) -> None:
        now = datetime.now(UTC)
        if now >= self.expires_at:
            raise SessionExpiredError("absolute timeout exceeded")
        if now >= self.idle_expires_at:
            raise SessionExpiredError("idle timeout exceeded")
        if self.is_revoked:
            raise SessionRevokedError()
```

### Deleted

- `TelegramCredentials` entity
- `ITelegramCredentialsRepository` interface
- `TelegramCredentialsModel` ORM model
- `TelegramCredentialsRepository` implementation
- `TelegramIdentityCreatedEvent` domain event
- `IdentityModel.telegram_credentials` relationship

### Kept

- `ITelegramInitDataValidator` — валидация initData по-прежнему нужна

### LinkedAccount Entity (expanded)

```python
@dataclass
class LinkedAccount:
    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str              # "telegram" | "google" | "apple"
    provider_sub_id: str       # unique ID at provider
    provider_email: str | None # email from provider (if available)
    email_verified: bool       # NEW: whether provider verified this email
    provider_metadata: dict    # provider-specific JSONB
    created_at: datetime
    updated_at: datetime

    def update_metadata(self, new_metadata: dict) -> bool:
        """Update provider_metadata if changed. Returns True if updated."""
        if self.provider_metadata != new_metadata:
            self.provider_metadata = new_metadata
            self.updated_at = datetime.now(UTC)
            return True
        return False
```

### ILinkedAccountRepository (expanded)

```python
class ILinkedAccountRepository(Protocol):
    async def add(self, account: LinkedAccount) -> LinkedAccount: ...
    async def get_by_provider(self, provider: str, provider_sub_id: str) -> tuple[Identity, LinkedAccount] | None: ...
    async def get_all_for_identity(self, identity_id: uuid.UUID) -> list[LinkedAccount]: ...
    async def update(self, account: LinkedAccount) -> None: ...
    async def get_by_identity_and_provider(self, identity_id: uuid.UUID, provider: str) -> LinkedAccount | None: ...
    async def find_by_verified_email(self, email: str) -> tuple[Identity, LinkedAccount] | None: ...  # NEW: для auto-link
    async def count_for_identity(self, identity_id: uuid.UUID) -> int: ...  # NEW: для unlink guard
    async def delete(self, account_id: uuid.UUID) -> None: ...  # NEW: для unlink
```

### New Domain Events

```python
@dataclass
class LinkedAccountCreatedEvent(DomainEvent):
    """Emitted when a new provider is linked to an Identity."""
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_metadata: dict
    start_param: str | None    # Telegram referral (null for others)
    is_new_identity: bool      # True = registration, False = linking
    aggregate_type: str = "Identity"
    event_type: str = "linked_account_created"

@dataclass
class LinkedAccountRemovedEvent(DomainEvent):
    """Emitted when a provider is unlinked from an Identity."""
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    aggregate_type: str = "Identity"
    event_type: str = "linked_account_removed"

@dataclass
class IdentityTokenVersionBumpedEvent(DomainEvent):
    """Emitted when token_version is incremented (all JWTs invalidated)."""
    identity_id: uuid.UUID
    new_version: int
    reason: str  # "password_change" | "role_change" | "force_logout" | "security_event"
    aggregate_type: str = "Identity"
    event_type: str = "token_version_bumped"
```

### Customer Entity (expanded)

```python
@dataclass
class Customer(AggregateRoot):
    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    username: str | None        # NEW — public handle from any provider
    phone: str | None
    referral_code: str
    referred_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
```

---

## Application Layer Changes

### Modified: LoginTelegramHandler

- Replace `ITelegramCredentialsRepository` → `ILinkedAccountRepository`
- Lookup: `linked_account_repo.get_by_provider("telegram", str(telegram_id))`
- Provision: create `LinkedAccount` instead of `TelegramCredentials`
- Profile sync: compare `provider_metadata` dict, update if changed via `update_metadata()`
- Event: emit `LinkedAccountCreatedEvent` instead of `TelegramIdentityCreatedEvent`
- Session: pass `idle_timeout_minutes` config to `Session.create()`
- Session: call `session.touch()` on refresh
- JWT: include `tv` (token_version) claim

### Modified: LoginHandler

- Include `tv` (token_version) claim in JWT
- Session: pass `idle_timeout_minutes` config to `Session.create()`

### Modified: RegisterHandler

- Rename `IdentityType.LOCAL` → `PrimaryAuthMethod.LOCAL`
- No other changes (local_credentials flow unchanged)

### Modified: RefreshTokenHandler

- Call `session.touch(idle_timeout_minutes)` after successful refresh
- Validate `session.idle_expires_at` in `ensure_valid()`
- **Token version check:** Load identity, compare JWT `tv` claim with `identity.token_version`
  - If `tv < token_version`: reject immediately (revoke session, return 401)
- Persist `last_active_at` and `idle_expires_at` updates

### Modified: JwtTokenProvider

```python
def create_access_token(
    self,
    identity_id: uuid.UUID,
    session_id: uuid.UUID,
    token_version: int,  # NEW
) -> str:
    payload = {
        "sub": str(identity_id),
        "sid": str(session_id),
        "tv": token_version,      # NEW: token version for instant invalidation
        "exp": datetime.now(UTC) + timedelta(minutes=self.access_token_ttl),
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, self.secret_key, algorithm="HS256")
```

### Modified: get_auth_context (dependency)

**Option A (рекомендуется для монолита):** Добавить проверку `token_version` на каждый запрос. Один SELECT по PK — O(1) lookup, ~1ms.

```python
async def get_auth_context(token: str, identity_repo: IIdentityRepository) -> AuthContext:
    payload = decode_jwt(token)
    identity = await identity_repo.get(payload["sub"])
    if not identity or not identity.is_active:
        raise UnauthorizedError()
    if payload.get("tv", 0) < identity.token_version:
        raise UnauthorizedError("token invalidated")
    return AuthContext(identity_id=identity.id, session_id=payload["sid"])
```

**Option B (если нужна полная stateless):** Проверять `tv` только при refresh. Окно уязвимости = ACCESS_TOKEN_EXPIRE_MINUTES (15 мин).

**Рекомендация:** Option A. Для монолита один SELECT по PK — negligible cost. Даёт мгновенную инвалидацию без Redis blacklist.

### New: LinkLocalCredentialsHandler

```
POST /auth/link/local  (authenticated)
Body: { email, password }

1. identity_id from token
2. Check: no existing local_credentials for this Identity
3. Check: email not taken (identity_repo.email_exists)
4. Hash password (Argon2id, outside UoW)
5. Create LocalCredentials(identity_id, email, hash(password))
6. Commit
```

### New: LinkProviderHandler

```
POST /auth/link/telegram  (authenticated)
POST /auth/link/google    (authenticated)
POST /auth/link/apple     (authenticated)

1. identity_id from token
2. Validate provider token/initData → extract provider_sub_id, email, email_verified
3. Check: provider_sub_id not linked to another Identity
   → If linked to DIFFERENT identity: return ConflictError("provider_already_linked")
4. Check: no existing linked_account with this provider for this Identity
   → If exists: return ConflictError("provider_already_linked_to_self")
5. Create LinkedAccount(identity_id, provider, provider_sub_id, email, email_verified, metadata)
6. Emit LinkedAccountCreatedEvent(is_new_identity=False)
7. Commit
```

### New: UnlinkProviderHandler

```
POST /auth/unlink/{provider}  (authenticated)

1. identity_id from token
2. Count total auth methods (local_credentials + linked_accounts)
   → If total <= 1: return error "cannot_remove_last_auth_method"
3. Find linked_account for (identity_id, provider)
   → If not found: return NotFoundError
4. Delete linked_account
5. Emit LinkedAccountRemovedEvent
6. Commit
```

**Защита:** Пользователь не может остаться без способов входа (Auth0/Supabase pattern).

### Future: LoginOIDCHandler (Google/Apple)

```
POST /auth/google   { id_token }
POST /auth/apple    { authorization_code, code_verifier }   ← PKCE mandatory (RFC 9700)

1. Validate token:
   - Google: verify id_token signature via JWKS endpoint (RS256)
   - Apple: exchange authorization_code + code_verifier for id_token, verify via JWKS
   - Extract: provider, provider_sub_id, email, email_verified, name, picture
2. linked_account_repo.get_by_provider(provider, sub_id)
3. Found → login (create session, include token_version in JWT)
4. Not found:
   a. email_verified=true AND provider ∈ TRUSTED_EMAIL_PROVIDERS:
      - Check identity_repo.get_by_email(email) for existing local_credentials
      - Check linked_account_repo.find_by_verified_email(email) for existing linked account
      - Found existing identity → AUTO-LINK: create LinkedAccount to same Identity, create session
   b. email_verified=false OR provider ∉ TRUSTED_EMAIL_PROVIDERS:
      - Check if email matches existing identity
      - If matches → return NeedsEmailVerificationError("needs_verification")
      - If no match → proceed to create new identity
   c. No email match anywhere:
      → Create new Identity(primary_auth_method=OIDC) + LinkedAccount, emit LinkedAccountCreatedEvent
5. Profile sync: update provider_metadata if changed
```

**Важно:**
- **PKCE обязателен** для Apple (authorization code flow). Google id_token flow не использует PKCE (implicit-like), но рекомендуется миграция на code flow + PKCE.
- **JWKS caching:** Кешировать ключи Google/Apple с TTL 24h, с forced refresh при kid mismatch.
- **Nonce:** Для Google id_token flow — включать `nonce` в запрос, проверять в response (anti-replay).

### Consumer: Unified handler

```python
# REPLACES: create_customer_on_telegram_identity_created
# (create_user_on_identity_registered remains for LOCAL registration)

@broker.task(routing_key="user.linked_account_created")
async def on_linked_account_created(
    identity_id, provider, provider_metadata,
    start_param, is_new_identity, ...
):
    if is_new_identity:
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            first_name=provider_metadata.get("first_name", ""),
            last_name=provider_metadata.get("last_name", ""),
            username=provider_metadata.get("username"),
        )
        # resolve referral from start_param (Telegram only)
    else:
        # Linking to existing identity — optionally enrich profile
        customer = await customer_repo.get(identity_id)
        if customer and not customer.username:
            username = provider_metadata.get("username")
            if username:
                customer.update_profile(username=username)
```

`IdentityRegisteredEvent` + `create_user_on_identity_registered` remain for LOCAL registration (no linked account involved).

---

## Security Considerations

### Rate Limiting

| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| `POST /auth/login` | 5/min per IP, 10/min per email | OWASP: prevent brute force |
| `POST /auth/telegram` | 10/min per IP | Lower risk (HMAC-signed) |
| `POST /auth/google`, `/apple` | 10/min per IP | Token validation is external |
| `POST /auth/refresh` | 30/min per session | Normal refresh pattern |
| `POST /auth/link/*` | 5/min per identity | Prevent linking spam |
| `POST /auth/register` | 3/min per IP | Prevent mass registration |

**Реализация:** Middleware с Redis sliding window counter. Не в scope этого spec — отдельная задача.

### User Enumeration Prevention (OWASP)

- `/auth/login`: Generic error "Invalid credentials" for both unknown email and wrong password
- `/auth/register`: На дублирующий email — 200 OK с generic message (не 409) или delay-based equalization
- `/auth/link/local`: Generic error if email taken (не раскрываем существование аккаунта)
- Timing: Constant-time comparison для password (уже реализовано), hash dummy password для unknown email path

### Auto-Link Security Matrix

| Provider | Email Verified? | Existing Identity Found? | Action |
|----------|----------------|--------------------------|--------|
| Google/Apple | true (always) | Yes, by email | AUTO-LINK |
| Google/Apple | true | No | Create new Identity |
| Telegram | N/A (no email) | — | Create new Identity or explicit link |
| Unknown/Custom | false | Yes | Return `needs_verification` |
| Unknown/Custom | false | No | Create new Identity (email unlinked) |

### Audit Events (для будущего audit log)

Текущие events покрывают основные flows. Рекомендуемые дополнения для compliance:

| Event | When | Priority |
|-------|------|----------|
| `IdentityAuthenticatedEvent` | Each successful login | Medium (audit trail) |
| `AuthenticationFailedEvent` | Each failed attempt | Medium (security monitoring) |
| `SessionCreatedEvent` | Each new session | Low (covered by login) |

**Решение:** Не добавляем сейчас. Текущие events (`LinkedAccountCreatedEvent`, `IdentityRegisteredEvent`) покрывают main flows. Audit events — отдельная задача при внедрении audit log.

---

## Query Layer Changes

### ListCustomersHandler

Additional batch query for auth methods:
```sql
SELECT identity_id, provider FROM linked_accounts WHERE identity_id = ANY(:identity_ids)
```

Build auth_methods per customer:
```python
auth_methods = []
if row["email"]:
    auth_methods.append("local")
auth_methods.extend(providers_by_identity.get(row["identity_id"], []))
```

### Response Schemas

```python
class CustomerListItemResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    username: str | None        # NEW
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str | None
    roles: list[str]
    auth_methods: list[str]     # NEW: ["local", "telegram", "google"]
    is_active: bool
    created_at: datetime
```

### Example Response

```json
{
  "items": [
    {
      "identityId": "550e8400-...",
      "email": "john@gmail.com",
      "username": "johndoe",
      "firstName": "John",
      "lastName": "Doe",
      "phone": "+998901234567",
      "referralCode": "A1B2C3D4",
      "roles": ["customer"],
      "authMethods": ["local", "telegram", "google"],
      "isActive": true,
      "createdAt": "2026-03-20T12:00:00Z"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 20
}
```

---

## Migration Plan

### Alembic Migration A (atomic, before code deployment)

**Step 1:** Add `token_version` to identities, extend `linked_accounts`, add session fields
```sql
-- Identity: token versioning
ALTER TABLE identities ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1;

-- LinkedAccount: provider_metadata, email_verified, timestamps
ALTER TABLE linked_accounts ADD COLUMN provider_metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE linked_accounts ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE linked_accounts ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE linked_accounts ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Session: idle timeout support
ALTER TABLE sessions ADD COLUMN last_active_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE sessions ADD COLUMN idle_expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 minutes');
```

**Step 2:** Migrate `telegram_credentials` → `linked_accounts`
```sql
INSERT INTO linked_accounts (id, identity_id, provider, provider_sub_id, provider_email, email_verified, provider_metadata, created_at, updated_at)
SELECT gen_random_uuid(), identity_id, 'telegram', telegram_id::text,
       NULL,  -- Telegram doesn't provide email
       false, -- email not verified (no email)
       jsonb_build_object(
         'first_name', first_name,
         'last_name', last_name,
         'username', username,
         'language_code', language_code,
         'is_premium', is_premium,
         'photo_url', photo_url,
         'allows_write_to_pm', allows_write_to_pm
       ),
       created_at, updated_at
FROM telegram_credentials
ON CONFLICT (provider, provider_sub_id) DO NOTHING;
```

**Step 3:** Add `username` to `customers`
```sql
ALTER TABLE customers ADD COLUMN username VARCHAR(100);

UPDATE customers c
SET username = (la.provider_metadata->>'username')
FROM linked_accounts la
WHERE la.identity_id = c.id
  AND la.provider = 'telegram'
  AND la.provider_metadata->>'username' IS NOT NULL;
```

**Step 4:** Rename `identities.type` → `identities.primary_auth_method`
```sql
ALTER TABLE identities RENAME COLUMN type TO primary_auth_method;
```

### Alembic Migration B (after code deployment verified)

**Step 5:** Drop `telegram_credentials`
```sql
DROP TABLE telegram_credentials;
```

**Step 6:** Remove unused columns from `linked_accounts`
```sql
-- provider_email kept (used for auto-link queries)
-- Remove only truly unused columns if any
```

### Migration Safety

- Step 2 INSERT uses `ON CONFLICT (provider, provider_sub_id) DO NOTHING` for idempotency
- Steps 1–4 run in a single Alembic migration (atomic)
- Step 5 (DROP TABLE) runs in a separate migration after code deployment is verified
- `last_active_at` and `idle_expires_at` defaults ensure existing sessions work immediately
- `token_version` default=1 ensures existing JWTs (without `tv` claim) are treated as valid (backward compat: `payload.get("tv", 1)`)

---

## Code Deletions and Modifications

### Identity Module — Deletions

| File | Action |
|------|--------|
| `identity/domain/entities.py` → `TelegramCredentials` class | Delete |
| `identity/domain/interfaces.py` → `ITelegramCredentialsRepository` | Delete |
| `identity/domain/events.py` → `TelegramIdentityCreatedEvent` | Delete; add `LinkedAccountCreatedEvent`, `LinkedAccountRemovedEvent`, `IdentityTokenVersionBumpedEvent` |
| `identity/domain/value_objects.py` → `IdentityType` | Rename to `PrimaryAuthMethod`; add `AuthProvider` enum and `TRUSTED_EMAIL_PROVIDERS` |
| `identity/infrastructure/models.py` → `TelegramCredentialsModel` | Delete model |
| `identity/infrastructure/models.py` → `IdentityModel.telegram_credentials` relationship | Delete |
| `identity/infrastructure/models.py` → `IdentityModel.type` column | Rename to `primary_auth_method`, update Enum |
| `identity/infrastructure/repositories/telegram_credentials_repository.py` | Delete file |

### Identity Module — Modifications

| File | Action |
|------|--------|
| `identity/domain/entities.py` → `Identity` | Add `token_version: int` field, `bump_token_version()` method |
| `identity/domain/entities.py` → `Session` | Add `last_active_at`, `idle_expires_at` fields; add `touch()` method; update `ensure_valid()` and `create()` |
| `identity/domain/entities.py` → `LinkedAccount` | Add `provider_email`, `email_verified`, `provider_metadata`, `created_at`, `updated_at` fields; add `update_metadata()` method |
| `identity/domain/interfaces.py` → `ILinkedAccountRepository` | Add `update()`, `get_by_identity_and_provider()`, `find_by_verified_email()`, `count_for_identity()`, `delete()`; change `get_by_provider()` return to `tuple[Identity, LinkedAccount] \| None` |
| `identity/infrastructure/models.py` → `IdentityModel` | Add `token_version` column (INTEGER, default=1) |
| `identity/infrastructure/models.py` → `SessionModel` | Add `last_active_at`, `idle_expires_at` columns |
| `identity/infrastructure/models.py` → `LinkedAccountModel` | Add `email_verified` (BOOLEAN), `provider_metadata` (JSONB), `created_at`, `updated_at` columns |
| `identity/infrastructure/repositories/linked_account_repository.py` | Implement new methods; update `_to_domain()` / `add()` for new fields |
| `identity/infrastructure/provider.py` | Remove `ITelegramCredentialsRepository` registration; update `login_telegram_handler` factory; add session timeout configs |
| `identity/application/commands/login_telegram.py` | Replace `ITelegramCredentialsRepository` → `ILinkedAccountRepository`; emit `LinkedAccountCreatedEvent`; pass `idle_timeout_minutes` |
| `identity/application/commands/login.py` | Include `tv` claim in JWT; pass `idle_timeout_minutes` to Session.create() |
| `identity/application/commands/register.py` | Rename `IdentityType.LOCAL` → `PrimaryAuthMethod.LOCAL` |
| `identity/application/commands/refresh_token.py` | Add `session.touch()`; add token version check; persist idle timeout update |
| `identity/application/commands/assign_role.py` | Call `identity.bump_token_version()` after role assignment |
| `identity/application/commands/revoke_role.py` | Call `identity.bump_token_version()` after role revocation |
| `identity/application/commands/logout_all.py` | Call `identity.bump_token_version()` |
| `identity/presentation/dependencies.py` | Add token version validation in `get_auth_context()` (Option A) |
| `identity/presentation/schemas.py` | Add `auth_methods`, `username` to response schemas |
| `identity/presentation/router_customers.py` | Pass `auth_methods`, `username` through |
| `identity/application/queries/list_customers.py` | Add batch query for `linked_accounts`; add `auth_methods` + `username` |
| `src/infrastructure/security/jwt.py` | Add `token_version` param to `create_access_token()`; include `tv` claim |

### User Module — Modifications

| File | Action |
|------|--------|
| `user/domain/entities.py` → `Customer` | Add `username: str \| None` field; update `create_from_identity()` to accept `username`; add `username` to `_CUSTOMER_UPDATABLE_FIELDS` |
| `user/infrastructure/models.py` → `CustomerModel` | Add `username` column `VARCHAR(100)` |
| `user/application/consumers/identity_events.py` | Delete `create_customer_on_telegram_identity_created`; add `on_linked_account_created` consumer |
| `user/infrastructure/provider.py` | Update consumer/broker registrations if needed |

### Tests — Required Updates

| File | Action |
|------|--------|
| `tests/unit/modules/identity/domain/test_telegram.py` | Rewrite: delete `TestTelegramCredentials` and `TestTelegramIdentityCreatedEvent`; update `IdentityType` → `PrimaryAuthMethod`; add `TestLinkedAccountCreatedEvent` |
| `tests/e2e/api/v1/test_auth_telegram.py` | Update raw SQL: replace `telegram_credentials` table queries with `linked_accounts WHERE provider = 'telegram'` |
| `tests/unit/modules/identity/application/commands/test_commands.py` | Update `IdentityType` imports → `PrimaryAuthMethod` |
| `tests/factories/identity_mothers.py` | Update `LinkedAccountMothers` to include new fields |
| `tests/unit/modules/user/domain/test_customer.py` | Add tests for `username` field in `Customer.create_from_identity()` |
| NEW: `tests/unit/modules/identity/domain/test_session_timeouts.py` | Test idle timeout, absolute timeout, touch() |
| NEW: `tests/unit/modules/identity/domain/test_token_version.py` | Test bump_token_version(), JWT rejection on stale tv |

---

## Configuration (new settings)

```python
# config.py additions
SESSION_IDLE_TIMEOUT_MINUTES: int = 30                    # OWASP: 15-30 min
SESSION_ABSOLUTE_LIFETIME_HOURS: int = 24                 # NIST AAL1
TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES: int = 1440         # 24 hours (Mini App)
TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS: int = 168       # 7 days (Mini App)
```

---

## Implementation Order

```
1. Migration A: add token_version, extend linked_accounts, add session fields,
                migrate telegram_credentials data, add username to customers,
                rename type column
2. Domain:
   a. Rename IdentityType → PrimaryAuthMethod
   b. Add AuthProvider enum, TRUSTED_EMAIL_PROVIDERS
   c. Add token_version to Identity + bump_token_version()
   d. Add last_active_at, idle_expires_at to Session + touch() + updated ensure_valid()
   e. Expand LinkedAccount (email_verified, provider_metadata, timestamps, update_metadata())
   f. Delete TelegramCredentials entity
   g. Add LinkedAccountCreatedEvent, LinkedAccountRemovedEvent, IdentityTokenVersionBumpedEvent
   h. Delete TelegramIdentityCreatedEvent
3. Infrastructure:
   a. Update IdentityModel (token_version), SessionModel (new fields), LinkedAccountModel (new fields)
   b. Update LinkedAccountRepository (new methods)
   c. Delete TelegramCredentialsModel, TelegramCredentialsRepository
   d. Update JwtTokenProvider (tv claim)
4. DI: update provider.py (remove telegram repo, rewire login handler, add session timeout configs)
5. LoginTelegramHandler: refactor to use ILinkedAccountRepository
6. LoginHandler + RefreshTokenHandler: add token version, idle timeout
7. get_auth_context: add token version validation (Option A)
8. assign_role/revoke_role/logout_all: bump token_version
9. Consumer: delete create_customer_on_telegram_identity_created, add on_linked_account_created
10. Customer entity + model: add username field
11. Query handlers: add auth_methods + username
12. Response schemas: add authMethods + username
13. Tests: update all affected test files + new timeout/token_version tests
14. Migration B (after deploy verified): DROP TABLE telegram_credentials
15. Future (separate specs):
    a. LinkLocalCredentialsHandler + LinkProviderHandler + UnlinkProviderHandler
    b. LoginOIDCHandler (Google/Apple) + PKCE + JWKS caching
    c. Rate limiting middleware
    d. WebAuthn/Passkey support (data model: webauthn_credentials table)
    e. Audit log (IdentityAuthenticatedEvent, AuthenticationFailedEvent)
```

---

## Future: WebAuthn/Passkey Data Model (placeholder)

Для будущей поддержки passkeys (NIST SP 800-63B-4 AAL2/AAL3) — предусмотренная структура:

```
webauthn_credentials  (future table)
  ├── id                  UUID PK
  ├── identity_id         FK → identities
  ├── credential_id       BYTEA UNIQUE       — WebAuthn credential ID
  ├── public_key          BYTEA              — COSE public key
  ├── sign_count          INTEGER            — replay detection counter
  ├── transports          VARCHAR[]           — ["usb", "nfc", "ble", "internal"]
  ├── aaguid              UUID               — authenticator attestation GUID
  ├── is_discoverable     BOOLEAN            — resident key / passkey
  ├── backed_up           BOOLEAN            — synced passkey indicator
  ├── created_at          TIMESTAMPTZ
  └── last_used_at        TIMESTAMPTZ
```

**Не реализуется сейчас.** Документируется для архитектурного планирования.
