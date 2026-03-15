# IAM RBAC Design Specification

**Date:** 2026-03-16
**Status:** Approved
**Standards:** NIST INCITS 359-2012 (RBAC), GDPR / 152-FZ (PII isolation)

---

## 1. ER-Model

### 1.1 Tables (11 tables, 2 modules)

**Identity module (10 tables):**

| Table | PK | Key Columns | Constraints |
|---|---|---|---|
| `identities` | `id` UUID v7 | `type` (ENUM: LOCAL, OIDC), `is_active`, `created_at`, `updated_at` | — |
| `local_credentials` | `identity_id` UUID (PK + FK → identities) | `email` (UQ), `password_hash` (Argon2id/Bcrypt), `created_at`, `updated_at` | Shared PK 1:1 |
| `linked_accounts` | `id` UUID v7 | `identity_id` FK, `provider`, `provider_sub_id`, `provider_email` (NULL) | UQ(`provider`, `provider_sub_id`) |
| `roles` | `id` UUID v7 | `name` (UQ), `description`, `is_system` (bool), `created_at`, `updated_at` | — |
| `permissions` | `id` UUID v7 | `codename` (UQ), `resource`, `action`, `description`, `created_at` | — |
| `identity_roles` | PK(`identity_id`, `role_id`) | `assigned_at`, `assigned_by` (NULL) | FK → identities, roles |
| `role_permissions` | PK(`role_id`, `permission_id`) | — | FK → roles, permissions |
| `role_hierarchy` | PK(`parent_role_id`, `child_role_id`) | — | FK → roles (self-ref), CHECK (`parent_role_id != child_role_id`) |
| `sessions` | `id` UUID v7 | `identity_id` FK, `refresh_token_hash` (UQ, SHA-256), `ip_address` (INET), `user_agent`, `is_revoked`, `created_at`, `expires_at` | IX(`identity_id`, `is_revoked`) |
| `session_roles` | PK(`session_id`, `role_id`) | — | FK → sessions, roles |

**User module (1 table):**

| Table | PK | Key Columns | Constraints |
|---|---|---|---|
| `users` | `id` UUID (PK + FK → identities) | `profile_email` (NULL), `first_name`, `last_name`, `phone`, `created_at`, `updated_at` | Shared PK 1:1 |

> **Note on timestamps:** Join tables `role_permissions` and `session_roles` intentionally omit timestamps — they are immutable associations (delete + re-insert on change). `identity_roles` has `assigned_at` because audit trail of role assignment time is required.

### 1.2 Domain Entities

All domain entities use `@dataclass` from `attr` and inherit from `AggregateRoot` (matching the existing codebase pattern in `src/modules/catalog/domain/entities.py`). Entities that emit domain events inherit `AggregateRoot` and call `self.add_domain_event(...)`.

**Identity (Aggregate Root):**

```python
@dataclass
class Identity(AggregateRoot):
    id: uuid.UUID           # UUIDv7
    type: IdentityType      # LOCAL | OIDC
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(cls, identity_type: IdentityType) -> "Identity": ...
    def deactivate(self) -> None: ...   # is_active=False, emit IdentityDeactivatedEvent
    def ensure_active(self) -> None: ... # raise IdentityDeactivatedError if not active
```

**LocalCredentials (Entity, owned by Identity):**

```python
@dataclass
class LocalCredentials:
    identity_id: uuid.UUID   # PK + FK → Identity
    email: str
    password_hash: str        # Argon2id (new) or Bcrypt (legacy, transparent rehash)
    created_at: datetime
    updated_at: datetime
```

> `LocalCredentials` is NOT an Aggregate Root — it is created/managed within `RegisterHandler` and `LoginHandler` as part of Identity operations. It is a separate entity (not a value object) because it has its own table and lifecycle.

**Session:**

```python
@dataclass
class Session:
    id: uuid.UUID
    identity_id: uuid.UUID
    refresh_token_hash: str     # SHA-256 of opaque token
    ip_address: str
    user_agent: str
    is_revoked: bool
    created_at: datetime
    expires_at: datetime
    activated_roles: list[uuid.UUID]  # session_roles snapshot

    @classmethod
    def create(cls, identity_id, refresh_token, ip, user_agent, role_ids) -> "Session": ...
    def revoke(self) -> None: ...
    def is_expired(self) -> bool: ...
    def rotate_refresh_token(self, new_token: str) -> str: ...  # returns new hash
    def verify_refresh_token(self, candidate: str) -> None: ... # raise on mismatch
```

**Role, Permission, LinkedAccount:**

```python
@dataclass
class Role:
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool

@dataclass
class Permission:
    id: uuid.UUID
    codename: str       # "brands:create"
    resource: str       # "brands"
    action: str         # "create"

@dataclass
class LinkedAccount:
    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_email: str | None
```

**User (Aggregate Root, user module):**

```python
@dataclass
class User(AggregateRoot):
    id: uuid.UUID           # == identity.id (Shared PK)
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None
    created_at: datetime
    updated_at: datetime

    def update_profile(self, **kwargs) -> None: ...
    def anonymize(self) -> None: ...  # GDPR: PII → "[DELETED]", email → None
```

---

## 2. CQRS Handlers & API Endpoints

### 2.1 Commands (14)

| Command | Module | Handler | Description |
|---|---|---|---|
| `RegisterCommand` | identity | `RegisterHandler` | Create identity + local_credentials, emit `IdentityRegisteredEvent` |
| `LoginCommand` | identity | `LoginHandler` | Verify credentials (with transparent Argon2id rehash), create session with role snapshot, return tokens |
| `LoginOIDCCommand` | identity | `LoginOIDCHandler` | Validate OIDC token via `IOIDCProvider`, create/link identity |
| `RefreshTokenCommand` | identity | `RefreshTokenHandler` | Rotate refresh token, issue new access token |
| `LogoutCommand` | identity | `LogoutHandler` | Revoke session, delete Redis cache key |
| `LogoutAllCommand` | identity | `LogoutAllHandler` | Revoke all sessions for identity |
| `CreateRoleCommand` | identity | `CreateRoleHandler` | Admin: create custom role (non-system), validate name uniqueness |
| `DeleteRoleCommand` | identity | `DeleteRoleHandler` | Admin: delete custom role. Raises `SystemRoleModificationError` if `is_system=True`. Cascades: removes from `identity_roles`, `role_permissions`, `role_hierarchy`, `session_roles` |
| `AssignRoleCommand` | identity | `AssignRoleHandler` | Admin: assign role to identity, update `session_roles` for active sessions, emit `RoleAssignmentChangedEvent` |
| `RevokeRoleCommand` | identity | `RevokeRoleHandler` | Admin: revoke role, update `session_roles` for active sessions, emit `RoleAssignmentChangedEvent` |
| `DeactivateIdentityCommand` | identity | `DeactivateIdentityHandler` | Deactivate identity, revoke all sessions, emit `IdentityDeactivatedEvent` |
| `UpdateProfileCommand` | user | `UpdateProfileHandler` | Update user PII fields (first_name, last_name, phone, profile_email). Validates via `User.update_profile()` |
| `AnonymizeUserCommand` | user | `AnonymizeUserHandler` | GDPR: anonymize PII via `User.anonymize()`. Called by `AnonymizeUserConsumer` on `IdentityDeactivatedEvent` |
| `CreateUserCommand` | user | `CreateUserHandler` | Internal consumer: creates `User` row on `IdentityRegisteredEvent`. Not exposed via API |

### 2.2 Queries (7)

| Query | Module | Handler | Description |
|---|---|---|---|
| `GetSessionPermissionsQuery` | identity | `GetSessionPermissionsHandler` | CTE → effective permissions for session |
| `GetMySessionsQuery` | identity | `GetMySessionsHandler` | List active sessions for current identity |
| `ListRolesQuery` | identity | `ListRolesHandler` | Admin: list all roles with permissions |
| `ListPermissionsQuery` | identity | `ListPermissionsHandler` | Admin: list all permissions |
| `GetIdentityRolesQuery` | identity | `GetIdentityRolesHandler` | Admin: roles assigned to identity |
| `GetMyProfileQuery` | user | `GetMyProfileHandler` | Return current user's PII (first_name, last_name, phone, profile_email) |
| `GetUserByIdentityQuery` | user | `GetUserByIdentityHandler` | Internal: used by `get_current_user_id` backward compat |

### 2.3 API Endpoints (16)

**Auth endpoints (`/auth`):**

| Method | Path | Handler | Auth | Rate Limit |
|---|---|---|---|---|
| POST | `/auth/register` | `RegisterCommand` | Public | 3 req/min per IP |
| POST | `/auth/login` | `LoginCommand` | Public | 5 req/min per IP |
| POST | `/auth/login/oidc` | `LoginOIDCCommand` | Public | 5 req/min per IP |
| POST | `/auth/refresh` | `RefreshTokenCommand` | Refresh Token | 10 req/min per IP |
| POST | `/auth/logout` | `LogoutCommand` | Access Token | — |
| POST | `/auth/logout/all` | `LogoutAllCommand` | Access Token | — |

**User endpoints (`/users`):**

| Method | Path | Handler | Auth |
|---|---|---|---|
| GET | `/users/me` | `GetMyProfileQuery` | `users:read` |
| PATCH | `/users/me` | `UpdateProfileCommand` | `users:update` |
| DELETE | `/users/me` | `DeactivateIdentityCommand` | `users:delete` |
| GET | `/users/me/sessions` | `GetMySessionsQuery` | Access Token |

> **`DELETE /users/me` flow:** The user module router calls `DeactivateIdentityCommand` (identity module) which deactivates the identity and revokes all sessions. This emits `IdentityDeactivatedEvent`, which triggers `AnonymizeUserConsumer` (user module) via Outbox Relay to anonymize PII. This maintains module isolation — the router only calls identity module commands, and PII cleanup happens asynchronously via events.

> **`users:delete` permission scope:** This permission is scoped to self-deletion only (`/users/me`). Admin-level user management (deactivating other users) requires `identities:manage` permission via `/admin/identities/{id}/deactivate`.

**Admin endpoints (`/admin`):**

| Method | Path | Handler | Auth |
|---|---|---|---|
| GET | `/admin/roles` | `ListRolesQuery` | `roles:manage` |
| POST | `/admin/roles` | `CreateRoleCommand` | `roles:manage` |
| DELETE | `/admin/roles/{id}` | `DeleteRoleCommand` | `roles:manage` |
| POST | `/admin/identities/{id}/roles` | `AssignRoleCommand` | `roles:manage` |
| DELETE | `/admin/identities/{id}/roles/{role_id}` | `RevokeRoleCommand` | `roles:manage` |
| GET | `/admin/permissions` | `ListPermissionsQuery` | `roles:manage` |

### 2.4 CTE Query (Role Hierarchy Resolution)

```sql
WITH RECURSIVE role_tree AS (
    SELECT sr.role_id FROM session_roles sr WHERE sr.session_id = :session_id
    UNION
    SELECT rh.child_role_id FROM role_hierarchy rh
    JOIN role_tree rt ON rt.role_id = rh.parent_role_id
)
SELECT DISTINCT p.codename
FROM role_tree rt
JOIN role_permissions rp ON rp.role_id = rt.role_id
JOIN permissions p ON p.id = rp.permission_id;
```

### 2.5 Session-Role Activation Model (NIST Compliance)

**Design decision:** `session_roles` is a NIST-compliant activation snapshot created at login time, BUT it is **dynamically updated** when roles change.

**Flow:**
1. **Login:** `session_roles` populated with all roles from `identity_roles` at login time (NIST Session-Role Activation).
2. **Role assignment/revocation:** `AssignRoleHandler` / `RevokeRoleHandler` update `session_roles` for ALL active (non-revoked, non-expired) sessions of the affected identity, then emit `RoleAssignmentChangedEvent`.
3. **Cache invalidation:** `RoleAssignmentChangedEvent` consumer deletes `perms:{session_id}` keys from Redis for all active sessions.
4. **Next request:** CTE query runs against updated `session_roles` → result cached with TTL 300s.

This approach satisfies NIST (permissions always resolved through `session_roles`, not `identity_roles`) while ensuring admin role changes take effect without requiring re-login.

### 2.6 Cross-Module Register Flow

```
POST /auth/register
  → RegisterHandler (identity module)
    → Identity.register() + LocalCredentials
    → UoW.commit() + OutboxMessage("IdentityRegisteredEvent")
  → Outbox Relay picks up event
    → CreateUserConsumer (user module)
      → User(id=identity_id, profile_email=email)
      → UoW.commit()
```

### 2.7 Cross-Module Delete Flow

```
DELETE /users/me
  → identity module router (dependencies.py: RequirePermission("users:delete"))
    → DeactivateIdentityCommand (identity module)
      → Identity.deactivate() + revoke all sessions
      → UoW.commit() + OutboxMessage("IdentityDeactivatedEvent")
  → Outbox Relay picks up event
    → AnonymizeUserConsumer (user module)
      → User.anonymize() → PII replaced with "[DELETED]"
      → UoW.commit()
```

---

## 3. File Structure & Infrastructure

### 3.1 Module Files (~50 files)

```
src/modules/identity/
├── domain/
│   ├── entities.py          # Identity (AR), LocalCredentials, Session, Role, Permission, LinkedAccount
│   ├── value_objects.py     # RefreshToken, IdentityType, PermissionCode
│   ├── exceptions.py        # InvalidCredentialsError, SessionExpiredError, InsufficientPermissionsError, etc.
│   ├── events.py            # IdentityRegisteredEvent, IdentityDeactivatedEvent, RoleAssignmentChangedEvent
│   └── interfaces.py        # IIdentityRepository, ISessionRepository, IRoleRepository, IPermissionRepository, ILinkedAccountRepository
├── application/
│   ├── commands/
│   │   ├── register.py
│   │   ├── login.py
│   │   ├── login_oidc.py
│   │   ├── refresh_token.py
│   │   ├── logout.py
│   │   ├── logout_all.py
│   │   ├── create_role.py
│   │   ├── delete_role.py
│   │   ├── assign_role.py
│   │   ├── revoke_role.py
│   │   └── deactivate_identity.py
│   └── queries/
│       ├── get_session_permissions.py
│       ├── get_my_sessions.py
│       ├── list_roles.py
│       ├── list_permissions.py
│       └── get_identity_roles.py
├── infrastructure/
│   ├── models.py            # All ORM models (10 tables)
│   ├── repositories/
│   │   ├── identity_repository.py
│   │   ├── session_repository.py
│   │   ├── role_repository.py
│   │   ├── permission_repository.py
│   │   └── linked_account_repository.py
│   └── provider.py          # IdentityProvider (Dishka)
└── presentation/
    ├── router_auth.py       # /auth/* endpoints
    ├── router_admin.py      # /admin/* endpoints
    ├── schemas.py           # Pydantic request/response
    └── dependencies.py      # RequireAuth, RequirePermission, get_auth_context

src/modules/user/
├── domain/
│   ├── entities.py          # User (AR)
│   ├── exceptions.py        # UserNotFoundError
│   └── interfaces.py        # IUserRepository
├── application/
│   ├── commands/
│   │   ├── update_profile.py
│   │   ├── anonymize_user.py
│   │   └── create_user.py   # Consumer for IdentityRegisteredEvent
│   └── queries/
│       ├── get_my_profile.py
│       └── get_user_by_identity.py
├── infrastructure/
│   ├── models.py            # UserModel
│   ├── repositories/
│   │   └── user_repository.py
│   └── provider.py          # UserProvider (Dishka)
└── presentation/
    ├── router.py            # /users/me/* endpoints
    └── schemas.py
```

### 3.2 Shared Interfaces

```
src/shared/interfaces/security.py   — Extended: IPermissionResolver, IOIDCProvider protocols
src/shared/interfaces/auth.py       — NEW: AuthContext dataclass
```

**AuthContext:**

```python
@dataclass(frozen=True, slots=True)
class AuthContext:
    identity_id: uuid.UUID
    session_id: uuid.UUID
```

**IPermissionResolver Protocol:**

```python
class IPermissionResolver(Protocol):
    async def get_permissions(self, session_id: uuid.UUID) -> frozenset[str]: ...
    async def has_permission(self, session_id: uuid.UUID, codename: str) -> bool: ...
    async def invalidate(self, session_id: uuid.UUID) -> None: ...
```

**IOIDCProvider Protocol (abstract, no implementations):**

```python
class IOIDCProvider(Protocol):
    async def validate_token(self, token: str) -> OIDCUserInfo: ...
    async def get_authorization_url(self, state: str) -> str: ...
```

**IPasswordHasher Protocol (extended):**

```python
class IPasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, plain_password: str, hashed_password: str) -> bool: ...
    def needs_rehash(self, hashed_password: str) -> bool: ...
```

**ITokenProvider Protocol (extended):**

```python
class ITokenProvider(Protocol):
    def create_access_token(self, payload_data: dict[str, Any], expires_minutes: int | None = None) -> str: ...
    def decode_access_token(self, token: str) -> dict[str, Any]: ...
    def create_refresh_token(self) -> tuple[str, str]: ...
        """Returns (opaque_token, sha256_hash)."""
```

> **Backward compatibility:** Existing `create_access_token` and `decode_access_token` signatures are preserved. `LoginHandler` constructs the payload dict `{"sub": identity_id, "sid": session_id}` and passes it to `create_access_token`. `create_refresh_token` is a new method. `jti` generation uses `uuid.uuid4()` (matching existing `JwtTokenProvider` behavior).

### 3.3 PermissionResolver (Infrastructure)

Located at `src/infrastructure/security/authorization.py` — cross-cutting concern.

**Cache-Aside pattern:**

```
1. Check Redis SET `perms:{session_id}`
2. Hit  → return frozenset from cache
3. Miss → execute CTE query → cache result with TTL 300s → return
```

**Constructor receives `async_sessionmaker` (not `AsyncSession`):**

```python
class PermissionResolver:
    def __init__(
        self,
        redis: RedisService,
        session_factory: async_sessionmaker[AsyncSession],
        cache_ttl: int = 300,
    ) -> None: ...
```

> **Scope:** Registered at APP scope in Dishka. Uses `async_sessionmaker` to create short-lived sessions per-query (not request-scoped `AsyncSession`). This is the same pattern used by `DLQMiddleware` in `src/bootstrap/worker.py`.

### 3.4 RequirePermission (FastAPI Dependency)

```python
# src/modules/identity/presentation/dependencies.py

class RequirePermission:
    def __init__(self, codename: str): ...

    @inject
    async def __call__(
        self,
        auth_context: AuthContext = Depends(get_auth_context),
        resolver: FromDishka[IPermissionResolver],
    ) -> AuthContext:
        if not await resolver.has_permission(auth_context.session_id, codename):
            raise InsufficientPermissionsError()
        return auth_context
```

**Usage:**

```python
@router.post("/brands", dependencies=[Depends(RequirePermission("brands:create"))])
async def create_brand(...): ...
```

### 3.5 Backward Compatibility

```python
# src/modules/identity/presentation/dependencies.py

async def get_current_user_id(auth: AuthContext = Depends(get_auth_context)) -> uuid.UUID:
    return auth.identity_id
```

Existing endpoints continue using `get_current_user_id` without changes.

### 3.6 Dishka Integration

**IdentityProvider** registers:
- `IIdentityRepository`, `ISessionRepository`, `IRoleRepository`, `IPermissionRepository`, `ILinkedAccountRepository`
- Scoped to REQUEST

**UserProvider** registers:
- `IUserRepository`
- Scoped to REQUEST

**Infrastructure Providers** (in `src/bootstrap/container.py`):
- `IPermissionResolver` → `PermissionResolver` (APP scope, receives `async_sessionmaker` + `RedisService`)
- `IPasswordHasher` → `Argon2PasswordHasher` (APP scope)
- `ITokenProvider` → `JwtTokenProvider` (APP scope, extended with `create_refresh_token`)

> **Container registration:** New providers are added to `create_container()` in `src/bootstrap/container.py` following the existing pattern of `make_async_container(DatabaseProvider(), CacheProvider(), SecurityProvider(), ...)`.

### 3.7 JWT Configuration

**Access Token payload:**

```json
{"sub": "identity_id", "sid": "session_id", "iat": ..., "exp": ..., "jti": "uuid4"}
```

- Lifetime: 15 minutes
- Algorithm: HS256, whitelist `algorithms=["HS256"]` on decode
- `jti`: `uuid.uuid4()` (matching existing `JwtTokenProvider` convention)

**Refresh Token:**

- Opaque: `secrets.token_urlsafe(32)`
- Stored: SHA-256 hash in `sessions.refresh_token_hash`
- Lifetime: 30 days
- Rotation: new token on each `/auth/refresh`

### 3.8 Settings Additions

```python
# src/bootstrap/config.py — Settings class additions:
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 30
SESSION_PERMISSIONS_CACHE_TTL: int = 300
MAX_ACTIVE_SESSIONS_PER_IDENTITY: int = 5
```

> **Breaking change:** Existing `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to `60 * 24 * 7` (7 days). The new default is 15 minutes. This is intentional: the new architecture uses short-lived access tokens + long-lived refresh tokens (30 days) for security. Existing tokens will expire naturally. No migration needed — clients must implement the `/auth/refresh` flow.

---

## 4. Seed Data, Migrations & Domain Events

### 4.1 Password Hashing Migration (Bcrypt → Argon2id)

**Current state:** Codebase uses `BcryptPasswordHasher` via `pwdlib` (`src/infrastructure/security/password.py`).

**Target state:** Argon2id (OWASP recommendation) with transparent rehash.

**Migration strategy (zero-downtime):**

1. New `Argon2PasswordHasher` implements `IPasswordHasher` with `needs_rehash()` method.
2. `needs_rehash()` returns `True` if hash starts with `$2b$` (Bcrypt prefix) instead of `$argon2id$`.
3. `LoginHandler` checks `needs_rehash()` after successful password verification:
   ```python
   if hasher.verify(password, credentials.password_hash):
       if hasher.needs_rehash(credentials.password_hash):
           credentials.password_hash = hasher.hash(password)
           # save updated hash within same UoW
   ```
4. All new registrations use Argon2id immediately.
5. Existing Bcrypt hashes remain valid until user next logs in → transparent rehash.
6. `pwdlib` supports both Bcrypt and Argon2id hashers simultaneously.

**No data migration needed.** Rehash happens organically on login. Inactive accounts retain Bcrypt hashes indefinitely (acceptable).

### 4.2 Alembic Migration (table creation order)

Single migration `2026/03/create_iam_tables.py`, tables created in FK-dependency order:

1. `permissions` — no FK
2. `roles` — no FK
3. `role_permissions` — FK → roles, permissions
4. `role_hierarchy` — FK → roles (self-ref), CHECK (`parent_role_id != child_role_id`)
5. `identities` — no FK
6. `local_credentials` — FK → identities (PK=FK)
7. `linked_accounts` — FK → identities
8. `sessions` — FK → identities
9. `session_roles` — FK → sessions, roles
10. `users` — FK → identities (Shared PK)

### 4.3 Seed Data (data migration)

Separate migration `seed_iam_roles_permissions.py` with idempotent `INSERT ... ON CONFLICT DO NOTHING`.

**Permissions (20):**

| codename | resource | action |
|---|---|---|
| `brands:create` | brands | create |
| `brands:read` | brands | read |
| `brands:update` | brands | update |
| `brands:delete` | brands | delete |
| `categories:create` | categories | create |
| `categories:read` | categories | read |
| `categories:update` | categories | update |
| `categories:delete` | categories | delete |
| `products:create` | products | create |
| `products:read` | products | read |
| `products:update` | products | update |
| `products:delete` | products | delete |
| `orders:create` | orders | create |
| `orders:read` | orders | read |
| `orders:update` | orders | update |
| `users:read` | users | read |
| `users:update` | users | update |
| `users:delete` | users | delete |
| `roles:manage` | roles | manage |
| `identities:manage` | identities | manage |

> **`orders:delete` omitted intentionally.** Orders are immutable audit records in e-commerce — they should never be deleted. Order cancellation is a state transition (`orders:update`), not a deletion.

**Roles (3, `is_system=True`):**

| name | permissions |
|---|---|
| `super_admin` | all 20 permissions |
| `manager` | `brands:*`, `categories:*`, `products:*`, `orders:*`, `users:read` |
| `customer` | `brands:read`, `categories:read`, `products:read`, `orders:create`, `orders:read`, `users:read`, `users:update`, `users:delete` |

**Role Hierarchy:**

```
super_admin → manager → customer
```

`super_admin` inherits all permissions of `manager`; `manager` inherits all permissions of `customer` via recursive CTE.

### 4.4 Domain Events (Transactional Outbox)

| Event | Source | Consumer | Description |
|---|---|---|---|
| `IdentityRegisteredEvent` | `RegisterCommand` | user module → `CreateUserConsumer` | Creates `users` row with Shared PK |
| `IdentityDeactivatedEvent` | `DeactivateIdentityCommand` | user module → `AnonymizeUserConsumer` | GDPR: anonymize PII |
| `RoleAssignmentChangedEvent` | `AssignRoleCommand` / `RevokeRoleCommand` | identity module → cache invalidation | Deletes `perms:{session_id}` keys from Redis |

**Event payloads:**

```python
# IdentityRegisteredEvent
{"identity_id": "uuid", "email": "str", "registered_at": "iso8601"}

# IdentityDeactivatedEvent
{"identity_id": "uuid", "reason": "str", "deactivated_at": "iso8601"}

# RoleAssignmentChangedEvent
{"identity_id": "uuid", "role_id": "uuid", "action": "assigned|revoked"}
```

**Outbox Relay registration** (`src/infrastructure/outbox/tasks.py`):

```python
register_event_handler("IdentityRegisteredEvent", _handle_identity_registered)
register_event_handler("IdentityDeactivatedEvent", _handle_identity_deactivated)
register_event_handler("RoleAssignmentChangedEvent", _handle_role_assignment_changed)
```

### 4.5 Cache Invalidation Strategy

**On `RoleAssignmentChangedEvent`:**
1. Find all active `session_id` for `identity_id` (non-revoked, non-expired)
2. Delete `perms:{session_id}` keys from Redis for each session
3. Next request triggers CTE against updated `session_roles` → result cached with TTL 300s

> **Note:** `AssignRoleHandler` / `RevokeRoleHandler` update `session_roles` rows synchronously (within the same UoW), THEN emit `RoleAssignmentChangedEvent` for cache invalidation. The event only handles cache clearing, not data mutation.

**On logout / revoke_session:**
- Delete `perms:{session_id}` from Redis
- Set `session.is_revoked = True`

---

## 5. Testing Strategy

### 5.1 Unit Tests (domain layer)

Pure tests, no DB or framework dependencies:

| Test | Validates |
|---|---|
| `test_identity_register` | `Identity.register()` → ACTIVE status, UUIDv7 |
| `test_identity_deactivate` | `Identity.deactivate()` → `is_active=False`, emits `IdentityDeactivatedEvent` |
| `test_session_create` | `Session.create()` → SHA-256 hashing, `is_revoked=False` |
| `test_session_revoke` | `Session.revoke()` → `is_revoked=True` |
| `test_session_is_expired` | `Session.is_expired()` → True after 30 days |
| `test_refresh_token_rotate` | `Session.rotate_refresh_token()` → new token, old hash replaced |
| `test_refresh_token_reuse_detection` | Reuse of old token → `RefreshTokenReuseError` |
| `test_role_hierarchy_cycle_prevention` | Cannot create cycle `A → B → A` |
| `test_permission_code_format` | `PermissionCode("brands:create")` — format validation `resource:action` |
| `test_user_anonymize` | `User.anonymize()` → PII replaced with `"[DELETED]"`, email → None |
| `test_local_credentials_entity` | `LocalCredentials` creation with email + password_hash |

### 5.2 Integration Tests (infrastructure layer)

With testcontainers (PostgreSQL + Redis):

| Test | Validates |
|---|---|
| `test_identity_repository_create_and_get` | Write/read Identity + LocalCredentials |
| `test_session_repository_revoke_all` | `revoke_all_for_identity()` marks all sessions |
| `test_role_repository_with_hierarchy` | CTE resolves `super_admin → manager → customer` |
| `test_permission_resolver_cache_hit` | Second call reads from Redis (PostgreSQL not called) |
| `test_permission_resolver_cache_miss` | Redis empty → CTE → result cached |
| `test_permission_resolver_cache_invalidation` | After `RoleAssignmentChangedEvent` → key deleted |
| `test_user_repository_shared_pk` | `User.id == Identity.id` constraint |
| `test_outbox_identity_registered` | `IdentityRegisteredEvent` in `outbox_messages` after commit |
| `test_password_rehash_bcrypt_to_argon2` | Login with Bcrypt hash → transparent rehash to Argon2id |
| `test_session_roles_updated_on_role_change` | `AssignRoleHandler` updates `session_roles` for active sessions |

### 5.3 E2E Tests (presentation layer)

Full HTTP cycle via `httpx.AsyncClient`:

| Test | Scenario |
|---|---|
| `test_register_login_flow` | POST `/auth/register` → POST `/auth/login` → 200 + tokens |
| `test_access_protected_endpoint` | GET `/brands` with valid JWT → 200 |
| `test_expired_token_returns_401` | GET with expired JWT → 401 |
| `test_refresh_token_rotation` | POST `/auth/refresh` → new token pair, old refresh invalid |
| `test_refresh_token_reuse_revokes_all` | Reuse of old refresh → all sessions revoked |
| `test_insufficient_permissions_403` | Customer attempts POST `/admin/roles` → 403 |
| `test_logout_invalidates_session` | POST `/auth/logout` → session revoked, subsequent request → 401 |
| `test_gdpr_anonymize_user` | DELETE `/users/me` → PII deleted, identity deactivated |
| `test_create_and_delete_role` | POST `/admin/roles` → DELETE `/admin/roles/{id}` → 200 |
| `test_delete_system_role_returns_403` | DELETE `/admin/roles/{system_role_id}` → 403 |

### 5.4 Architecture Tests (pytest-archon)

```python
# identity module does not import from user module
assert_not_imported("src.modules.user", by="src.modules.identity")

# user module does not import from identity module
assert_not_imported("src.modules.identity", by="src.modules.user")

# domain layer does not import from infrastructure
assert_not_imported("src.modules.identity.infrastructure", by="src.modules.identity.domain")
assert_not_imported("src.modules.user.infrastructure", by="src.modules.user.domain")
```

---

## 6. Error Handling & Security

### 6.1 Domain Exceptions

```python
# src/modules/identity/domain/exceptions.py

class IdentityError(Exception): ...
class InvalidCredentialsError(IdentityError): ...        # Unified: wrong email OR password (user enumeration protection)
class IdentityAlreadyExistsError(IdentityError): ...     # Email already registered
class IdentityDeactivatedError(IdentityError): ...       # Account is deactivated
class SessionExpiredError(IdentityError): ...             # Refresh token expired (> 30 days)
class SessionRevokedError(IdentityError): ...             # Session revoked (logout/reuse)
class RefreshTokenReuseError(IdentityError): ...          # Reuse detected → defensive revocation
class MaxSessionsExceededError(IdentityError): ...        # > 5 active sessions
class RoleHierarchyCycleError(IdentityError): ...         # Cycle in role hierarchy
class SystemRoleModificationError(IdentityError): ...     # Cannot modify/delete is_system=True roles
class InsufficientPermissionsError(IdentityError): ...    # RequirePermission check failed
```

### 6.2 Exception → HTTP Mapping

| Exception | HTTP | Response |
|---|---|---|
| `InvalidCredentialsError` | 401 | `{"detail": "Invalid email or password"}` |
| `IdentityAlreadyExistsError` | 409 | `{"detail": "Email already registered"}` |
| `IdentityDeactivatedError` | 403 | `{"detail": "Account is deactivated"}` |
| `SessionExpiredError` | 401 | `{"detail": "Session expired"}` |
| `SessionRevokedError` | 401 | `{"detail": "Session revoked"}` |
| `RefreshTokenReuseError` | 401 | `{"detail": "Token reuse detected, all sessions revoked"}` |
| `MaxSessionsExceededError` | 429 | `{"detail": "Maximum active sessions limit reached"}` |
| `RoleHierarchyCycleError` | 422 | `{"detail": "Role hierarchy cycle detected"}` |
| `SystemRoleModificationError` | 403 | `{"detail": "System roles cannot be modified"}` |
| `InsufficientPermissionsError` | 403 | `{"detail": "Insufficient permissions"}` |

### 6.3 Security Hardening

| Measure | Implementation |
|---|---|
| Timing-safe comparison | `hmac.compare_digest()` for refresh token hash verification |
| Argon2id parameters | `time_cost=3, memory_cost=65536 (64MB), parallelism=4` (OWASP recommendation) |
| Transparent rehash | Bcrypt → Argon2id on next login via `needs_rehash()` (see Section 4.1) |
| JWT algorithm | HS256, whitelist `algorithms=["HS256"]` on decode |
| Refresh token | `secrets.token_urlsafe(32)`, SHA-256 hash stored, never plain text |
| Rate limiting | `/auth/register` 3 req/min, `/auth/login` 5 req/min, `/auth/refresh` 10 req/min per IP |
| Session limit | Max 5 active sessions per identity, 429 on exceed (no auto-eviction) |
| CORS | From existing `Settings.cors_origins`, `credentials=True` |
| User enumeration protection | `InvalidCredentialsError` does not distinguish email-not-found vs wrong-password |

### 6.4 Security Logging (Structlog)

```python
# Success
logger.info("identity.registered", identity_id=..., email=...)
logger.info("identity.login.success", identity_id=..., ip=..., user_agent=...)
logger.info("session.refreshed", session_id=..., identity_id=...)
logger.info("session.revoked", session_id=..., reason="logout|reuse_detection")
logger.info("password.rehashed", identity_id=..., from_algo="bcrypt", to_algo="argon2id")

# Security events (warning/error)
logger.warning("identity.login.failed", email=..., ip=..., reason="invalid_credentials")
logger.warning("refresh_token.reuse_detected", session_id=..., identity_id=..., ip=...)
logger.warning("max_sessions.exceeded", identity_id=..., ip=...)
logger.error("identity.deactivated", identity_id=..., reason=...)
```
