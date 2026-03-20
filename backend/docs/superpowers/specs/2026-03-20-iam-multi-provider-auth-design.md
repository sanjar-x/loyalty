# IAM Multi-Provider Auth Design

**Date:** 2026-03-20
**Status:** Approved

## Problem

Customer может авторизоваться через Telegram, email+password, Google, Apple — но текущая архитектура создаёт отдельный Identity (и отдельный Customer) для каждого способа входа. `telegram_credentials` выделена в отдельную таблицу с Shared PK, хотя Telegram — такой же внешний провайдер как Google и Apple.

## Decisions

| Вопрос | Решение |
|--------|---------|
| Модель | Один Identity — несколько credentials |
| Credentials | `local_credentials` (0..1) + `linked_accounts` (0..N) |
| Telegram | Обычный провайдер в `linked_accounts`, не отдельная таблица |
| Linking | Ручное (из приложения) + auto-link по email |
| Auto-link безопасность | Trusted providers (Google/Apple) auto-link сразу, остальные — через email verification |
| Provider-specific данные | JSONB `provider_metadata` в `linked_accounts` |
| Customer profile | `username` — общее поле Customer, заполняется из любого провайдера |

## Target Architecture

### DB Schema

```
identities
  ├── id                    UUID PK
  ├── primary_auth_method   "LOCAL" | "TELEGRAM" | "OIDC"
  ├── account_type          "CUSTOMER" | "STAFF"
  ├── is_active             bool
  ├── created_at / updated_at / deactivated_at / deactivated_by
  │
  ├── local_credentials     (0..1, Shared PK)
  │     ├── identity_id     PK+FK
  │     ├── email           UNIQUE
  │     └── password_hash
  │
  ├── linked_accounts       (0..N)
  │     ├── id              UUID PK
  │     ├── identity_id     FK → identities
  │     ├── provider        "telegram" | "google" | "apple"
  │     ├── provider_sub_id VARCHAR
  │     ├── provider_metadata  JSONB DEFAULT '{}'
  │     ├── created_at / updated_at
  │     └── UNIQUE(provider, provider_sub_id)
  │
  ├── sessions              (0..N)  — без изменений
  └── identity_roles        (N..M)  — без изменений

customers
  ├── id                    FK → identities.id (Shared PK)
  ├── profile_email         VARCHAR nullable
  ├── first_name            VARCHAR
  ├── last_name             VARCHAR
  ├── username              VARCHAR nullable    ← НОВОЕ
  ├── phone                 VARCHAR nullable
  ├── referral_code         VARCHAR UNIQUE
  ├── referred_by           FK → customers.id
  └── created_at / updated_at
```

### Two Categories of Credentials

- **`local_credentials`** (0..1) — email + password_hash. Единственный тип с паролем.
- **`linked_accounts`** (0..N) — ВСЕ внешние провайдеры: Telegram, Google, Apple. Provider-specific данные в JSONB `provider_metadata`.

### Telegram provider_metadata Example

```json
{
  "username": "johndoe",
  "language_code": "en",
  "is_premium": true,
  "photo_url": "https://t.me/i/userpic/320/photo.jpg",
  "allows_write_to_pm": true
}
```

## Domain Layer Changes

### Renames

- `IdentityType` → `PrimaryAuthMethod` (values: LOCAL, OIDC, TELEGRAM)
- `Identity.type` → `Identity.primary_auth_method`

### New Value Object

```python
class AuthProvider(str, Enum):
    TELEGRAM = "telegram"
    GOOGLE = "google"
    APPLE = "apple"

TRUSTED_EMAIL_PROVIDERS: frozenset[str] = frozenset({"google", "apple"})
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
    provider_metadata: dict    # provider-specific JSONB
    created_at: datetime
    updated_at: datetime
```

### ILinkedAccountRepository (expanded)

```python
class ILinkedAccountRepository:
    async def add(self, account: LinkedAccount) -> LinkedAccount: ...
    async def get_by_provider(self, provider: str, provider_sub_id: str) -> tuple[Identity, LinkedAccount] | None: ...
    async def get_all_for_identity(self, identity_id: uuid.UUID) -> list[LinkedAccount]: ...
    async def update(self, account: LinkedAccount) -> None: ...
    async def get_by_identity_and_provider(self, identity_id: uuid.UUID, provider: str) -> LinkedAccount | None: ...
```

### New Domain Event

```python
@dataclass
class LinkedAccountCreatedEvent(DomainEvent):
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_metadata: dict
    start_param: str | None    # Telegram referral (null for others)
    is_new_identity: bool      # True = registration, False = linking
    aggregate_type: str = "Identity"
    event_type: str = "linked_account_created"
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

## Application Layer Changes

### Modified: LoginTelegramHandler

- Replace `ITelegramCredentialsRepository` → `ILinkedAccountRepository`
- Lookup: `linked_account_repo.get_by_provider("telegram", str(telegram_id))`
- Provision: create `LinkedAccount` instead of `TelegramCredentials`
- Profile sync: compare `provider_metadata` dict, update if changed
- Event: emit `LinkedAccountCreatedEvent` instead of `TelegramIdentityCreatedEvent`

### Modified: RegisterHandler

- Rename `IdentityType.LOCAL` → `PrimaryAuthMethod.LOCAL`
- No other changes (local_credentials flow unchanged)

### New: LinkLocalCredentialsHandler

```
POST /auth/link/local  (authenticated)
Body: { email, password }

1. identity_id from token
2. Check: no existing local_credentials for this Identity
3. Check: email not taken
4. Create LocalCredentials(identity_id, email, hash(password))
5. Commit
```

### New: LinkProviderHandler

```
POST /auth/link/telegram  (authenticated)
POST /auth/link/google    (authenticated)
POST /auth/link/apple     (authenticated)

1. identity_id from token
2. Validate provider token/initData → extract provider_sub_id
3. Check: provider_sub_id not linked to another Identity
4. Check: no existing linked_account with this provider for this Identity
5. Create LinkedAccount(identity_id, provider, provider_sub_id, metadata)
6. Emit LinkedAccountCreatedEvent(is_new_identity=False)
7. Commit
```

### Future: LoginOIDCHandler (Google/Apple)

```
POST /auth/google   { id_token }
POST /auth/apple    { authorization_code }

1. Validate token → extract provider, provider_sub_id, email
2. linked_account_repo.get_by_provider(provider, sub_id)
3. Found → login (create session)
4. Not found:
   a. provider ∈ TRUSTED_EMAIL_PROVIDERS and email matches existing local_credentials.email
      → AUTO-LINK: create LinkedAccount to same Identity, create session
   b. Email not found
      → create new Identity + LinkedAccount, emit event
   c. Provider NOT trusted + email matches
      → return error "needs_verification"
```

### Consumer: Unified handler

```python
# REPLACES: create_user_on_identity_registered (for linked accounts)
#           create_customer_on_telegram_identity_created

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
        # resolve referral from start_param
    else:
        customer = await customer_repo.get(identity_id)
        if customer and not customer.first_name:
            customer.update_profile(
                first_name=provider_metadata.get("first_name", ""),
            )
```

`IdentityRegisteredEvent` + `create_user_on_identity_registered` remain for LOCAL registration (no linked account involved).

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

## Migration Plan

### Alembic Migration

**Step 1:** Extend `linked_accounts`
```sql
ALTER TABLE linked_accounts ADD COLUMN provider_metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE linked_accounts ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE linked_accounts ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
```

**Step 2:** Migrate `telegram_credentials` → `linked_accounts`
```sql
INSERT INTO linked_accounts (id, identity_id, provider, provider_sub_id, provider_metadata, created_at, updated_at)
SELECT gen_random_uuid(), identity_id, 'telegram', telegram_id::text,
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
FROM telegram_credentials;
```

**Step 3:** Add `username` to `customers`
```sql
ALTER TABLE customers ADD COLUMN username VARCHAR(100);

UPDATE customers c
SET username = tc.username
FROM telegram_credentials tc
WHERE tc.identity_id = c.id AND tc.username IS NOT NULL;
```

**Step 4:** Rename `identities.type` → `identities.primary_auth_method`
```sql
ALTER TABLE identities RENAME COLUMN type TO primary_auth_method;
```

**Step 5:** Drop `telegram_credentials`
```sql
DROP TABLE telegram_credentials;
```

**Step 6:** Remove unused columns from `linked_accounts`
```sql
ALTER TABLE linked_accounts DROP COLUMN IF EXISTS provider_email;
```

### Code Deletions and Modifications

#### Identity Module — Deletions

| File | Action |
|------|--------|
| `identity/domain/entities.py` → `TelegramCredentials` class | Delete |
| `identity/domain/interfaces.py` → `ITelegramCredentialsRepository` | Delete |
| `identity/domain/events.py` → `TelegramIdentityCreatedEvent` | Delete; add `LinkedAccountCreatedEvent` in same file |
| `identity/domain/value_objects.py` → `IdentityType` | Rename to `PrimaryAuthMethod` |
| `identity/infrastructure/models.py` → `TelegramCredentialsModel` | Delete model |
| `identity/infrastructure/models.py` → `IdentityModel.telegram_credentials` relationship | Delete |
| `identity/infrastructure/models.py` → `IdentityModel.type` column | Rename to `primary_auth_method`, update `Enum(PrimaryAuthMethod, ...)` |
| `identity/infrastructure/repositories/telegram_credentials_repository.py` | Delete file |

#### Identity Module — Modifications

| File | Action |
|------|--------|
| `identity/domain/entities.py` → `LinkedAccount` | Add `provider_metadata`, `created_at`, `updated_at` fields |
| `identity/domain/interfaces.py` → `ILinkedAccountRepository` | Add `update()`, `get_by_identity_and_provider()`; change `get_by_provider()` return to `tuple[Identity, LinkedAccount] \| None` |
| `identity/infrastructure/models.py` → `LinkedAccountModel` | Add `provider_metadata` (JSONB), `created_at`, `updated_at` columns; remove `provider_email` |
| `identity/infrastructure/repositories/linked_account_repository.py` | Implement `update()`, `get_by_identity_and_provider()`; update `get_by_provider()` to join Identity; update `_to_domain()` / `add()` for new fields |
| `identity/infrastructure/provider.py` | Remove `ITelegramCredentialsRepository` registration; update `login_telegram_handler` factory to inject `ILinkedAccountRepository` instead of `ITelegramCredentialsRepository` |
| `identity/application/commands/login_telegram.py` | Replace `ITelegramCredentialsRepository` → `ILinkedAccountRepository`; emit `LinkedAccountCreatedEvent` |
| `identity/application/commands/register.py` | Rename `IdentityType.LOCAL` → `PrimaryAuthMethod.LOCAL` |
| `identity/application/queries/get_customer_detail.py` | Add `auth_methods` to response |
| `identity/application/queries/list_customers.py` | Add batch query for `linked_accounts`; add `auth_methods` + `username` |
| `identity/presentation/schemas.py` | Add `auth_methods`, `username` to `CustomerListItemResponse` / `CustomerDetailResponse` |
| `identity/presentation/router_customers.py` | Pass `auth_methods`, `username` through |

#### User Module — Modifications

| File | Action |
|------|--------|
| `user/domain/entities.py` → `Customer` | Add `username: str \| None` field; update `create_from_identity()` to accept `username`; add `username` to `_CUSTOMER_UPDATABLE_FIELDS` |
| `user/infrastructure/models.py` → `CustomerModel` | Add `username` column `VARCHAR(100)` |
| `user/application/consumers/identity_events.py` | Delete `create_customer_on_telegram_identity_created`; add `on_linked_account_created` consumer |
| `user/infrastructure/provider.py` | Update consumer/broker registrations if needed |

#### Tests — Required Updates

| File | Action |
|------|--------|
| `tests/unit/modules/identity/domain/test_telegram.py` | Rewrite: delete `TestTelegramCredentials` and `TestTelegramIdentityCreatedEvent`; update `IdentityType` → `PrimaryAuthMethod`; add `TestLinkedAccountCreatedEvent` |
| `tests/e2e/api/v1/test_auth_telegram.py` | Update raw SQL: replace `telegram_credentials` table queries with `linked_accounts WHERE provider = 'telegram'` |
| `tests/unit/modules/identity/application/commands/test_commands.py` | Update `IdentityType` imports → `PrimaryAuthMethod` |
| `tests/factories/identity_mothers.py` | Update `LinkedAccountMothers` to include `provider_metadata`, `created_at`, `updated_at` |
| `tests/unit/modules/user/domain/test_customer.py` | Add tests for `username` field in `Customer.create_from_identity()` |

### Migration Safety

- Step 2 INSERT uses `ON CONFLICT (provider, provider_sub_id) DO NOTHING` for idempotency
- Steps 1–4 run in a single Alembic migration (atomic)
- Step 5 (DROP TABLE) runs in a separate migration after code deployment is verified

### Updated Migration Step 2

```sql
INSERT INTO linked_accounts (id, identity_id, provider, provider_sub_id, provider_metadata, created_at, updated_at)
SELECT gen_random_uuid(), identity_id, 'telegram', telegram_id::text,
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

### Implementation Order

```
1. Migration A: extend linked_accounts, migrate data, add username to customers, rename type column
2. Domain: rename IdentityType → PrimaryAuthMethod, delete TelegramCredentials, expand LinkedAccount entity, add LinkedAccountCreatedEvent
3. Infrastructure: update LinkedAccountModel, LinkedAccountRepository, IdentityModel; delete TelegramCredentialsModel, TelegramCredentialsRepository
4. DI: update provider.py (remove telegram repo, rewire login handler)
5. LoginTelegramHandler: refactor to use ILinkedAccountRepository
6. Consumer: delete create_customer_on_telegram_identity_created, add on_linked_account_created
7. Customer entity + model: add username field
8. Query handlers: add auth_methods + username
9. Response schemas: add authMethods + username
10. Tests: update all affected test files
11. Migration B (after deploy verified): DROP TABLE telegram_credentials
12. Future: LinkLocalCredentialsHandler, LinkProviderHandler, LoginOIDCHandler + auto-link
```
