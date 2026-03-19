# Deep Analysis: Текущее состояние системы Users/Staff — Backend

## Содержание

1. [Обзор архитектуры](#1-обзор-архитектуры)
2. [Identity Module — Полный разбор](#2-identity-module--полный-разбор)
3. [User Module — Полный разбор](#3-user-module--полный-разбор)
4. [Shared Infrastructure](#4-shared-infrastructure)
5. [Database Schema](#5-database-schema)
6. [API Contract](#6-api-contract)
7. [Event-Driven Integration](#7-event-driven-integration)
8. [RBAC Model](#8-rbac-model)
9. [Frontend Current State](#9-frontend-current-state)
10. [Тесты](#10-тесты)
11. [Проблемы и Gap Analysis](#11-проблемы-и-gap-analysis)
12. [Зависимости и Impact Map](#12-зависимости-и-impact-map)

---

## 1. Обзор архитектуры

### 1.1 Диаграмма модулей и их связей

```
                        ┌──────────────────────────────────────┐
                        │           src/bootstrap/             │
                        │  container.py  config.py  web.py     │
                        └──────┬───────────────┬───────────────┘
                               │               │
                    ┌──────────▼──────────┐    │
                    │     src/api/        │    │
                    │  router.py          │    │
                    │  dependencies/auth  │    │
                    │  exceptions/        │    │
                    │  middlewares/       │    │
                    └──────────┬──────────┘    │
                               │               │
        ┌──────────────────────┼───────────────┼───────────────────┐
        │                      │               │                   │
   ┌────▼────┐          ┌──────▼──────┐  ┌─────▼─────┐    ┌───────▼──────┐
   │ catalog │          │  identity   │  │   user    │    │   storage    │
   │ module  │          │   module    │  │  module   │    │   module     │
   └─────────┘          └──────┬──────┘  └─────┬─────┘    └──────────────┘
                               │               │
                               │  SharedPK 1:1  │
                               │  (user.id =    │
                               │  identity.id)  │
                               │               │
                               ▼               │
                        IdentityRegistered ────▶ CreateUser (via Outbox)
                        IdentityDeactivated ───▶ AnonymizeUser (via Outbox)
                        RoleAssignmentChanged ─▶ InvalidatePermCache (via Outbox)
```

### 1.2 Связь Identity и User через Shared PK

Identity и User — два отдельных bounded context, связанных через **shared primary key**:
- `identities.id` = `users.id` (FK `users.id -> identities.id ON DELETE CASCADE`)
- Связь 1:1, создается через domain event `IdentityRegisteredEvent`
- Коммуникация исключительно через Transactional Outbox + TaskIQ consumers

### 1.3 Поток данных: регистрация -> аутентификация -> авторизация

```
1. POST /auth/register
   → RegisterHandler: create Identity + LocalCredentials + assign "customer" role
   → emit IdentityRegisteredEvent (Outbox)
   → Outbox Relay → TaskIQ → create_user_on_identity_registered → User.create_from_identity()

2. POST /auth/login
   → LoginHandler: verify credentials → ensure_active() → check session limit
   → create Session + add session_roles → generate JWT (sub=identity_id, sid=session_id)
   → return access_token + refresh_token

3. GET /admin/identities (protected)
   → get_auth_context: decode JWT → AuthContext(identity_id, session_id)
   → RequirePermission("identities:manage"): PermissionResolver.has_permission()
     → Redis cache "perms:{session_id}" → hit: return frozenset
     → miss: recursive CTE (session_roles → role_hierarchy → role_permissions → permissions)
     → cache result with TTL=300s
```

---

## 2. Identity Module — Полный разбор

**Путь:** `src/modules/identity/`

### 2.1 Domain Layer

**Путь:** `src/modules/identity/domain/`

#### Entities

**`Identity`** (Aggregate Root) — `entities.py:30`
```python
@dataclass
class Identity(AggregateRoot):
    id: uuid.UUID
    type: IdentityType           # LOCAL | OIDC
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None
    deactivated_by: uuid.UUID | None = None
```

Методы:
- `register(cls, identity_type) -> Identity` — фабрика, создает активную identity с UUIDv7
- `deactivate(reason, deactivated_by=None) -> None` — выставляет `is_active=False`, эмитит `IdentityDeactivatedEvent`
- `reactivate() -> None` — восстанавливает активность, эмитит `IdentityReactivatedEvent`
- `ensure_active() -> None` — проверяет `is_active`, бросает `IdentityDeactivatedError`

**`LocalCredentials`** — `entities.py:117`
```python
@dataclass
class LocalCredentials:
    identity_id: uuid.UUID
    email: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
```

**`Session`** — `entities.py:136`
```python
@dataclass
class Session:
    id: uuid.UUID
    identity_id: uuid.UUID
    refresh_token_hash: str       # SHA-256
    ip_address: str
    user_agent: str
    is_revoked: bool
    created_at: datetime
    expires_at: datetime
    activated_roles: list[uuid.UUID]   # NIST RBAC session-role activation
```

Методы:
- `create(cls, ..., role_ids, expires_days=30) -> Session` — фабрика с хешированием токена
- `revoke() -> None` — устанавливает `is_revoked = True`
- `is_expired() -> bool` — проверяет `datetime.now(UTC) >= self.expires_at`
- `rotate_refresh_token(new_token) -> str` — обновляет хеш
- `verify_refresh_token(candidate) -> None` — HMAC constant-time сравнение, бросает `RefreshTokenReuseError`
- `ensure_valid() -> None` — проверяет expiry + revoked

**`Role`** — `entities.py:256`
```python
@dataclass
class Role:
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
```

**`Permission`** — `entities.py:273`
```python
@dataclass
class Permission:
    id: uuid.UUID
    codename: str        # e.g. "orders:read"
    resource: str
    action: str
    description: str | None = None
```

**`LinkedAccount`** — `entities.py:291`
```python
@dataclass
class LinkedAccount:
    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str               # "google", "github"
    provider_sub_id: str
    provider_email: str | None
```

#### Value Objects — `value_objects.py`

- **`IdentityType(str, Enum)`** — `LOCAL`, `OIDC`
- **`PermissionCode`** — frozen dataclass, validates `resource:action` format, properties: `resource`, `action`

#### Domain Events — `events.py`

| Event | Поля | Когда публикуется |
|-------|------|-------------------|
| `IdentityRegisteredEvent` | `identity_id`, `email`, `registered_at` | При регистрации (local/OIDC) |
| `IdentityDeactivatedEvent` | `identity_id`, `reason`, `deactivated_by`, `deactivated_at` | При деактивации identity |
| `RoleAssignmentChangedEvent` | `identity_id`, `role_id`, `action` ("assigned"/"revoked") | При назначении/отзыве роли |
| `IdentityReactivatedEvent` | `identity_id`, `reactivated_at` | При реактивации identity |

Все события наследуют `DomainEvent` (shared kernel), имеют `aggregate_type="Identity"`.

#### Exceptions — `exceptions.py`

| Exception | HTTP Code | Error Code | Когда |
|-----------|-----------|------------|-------|
| `InvalidCredentialsError` | 401 | `INVALID_CREDENTIALS` | Неверный email/пароль |
| `IdentityAlreadyExistsError` | 409 | `IDENTITY_ALREADY_EXISTS` | Дубликат email |
| `IdentityDeactivatedError` | 403 | `IDENTITY_DEACTIVATED` | Деактивированный аккаунт |
| `SessionExpiredError` | 401 | `SESSION_EXPIRED` | Истекший refresh token |
| `SessionRevokedError` | 401 | `SESSION_REVOKED` | Отозванная сессия |
| `RefreshTokenReuseError` | 401 | `REFRESH_TOKEN_REUSE` | Повторное использование токена |
| `MaxSessionsExceededError` | 429 | `MAX_SESSIONS_EXCEEDED` | Лимит сессий (по умолчанию 5) |
| `RoleHierarchyCycleError` | 422 | `ROLE_HIERARCHY_CYCLE` | Цикл в иерархии ролей |
| `SystemRoleModificationError` | 403 | `SYSTEM_ROLE_MODIFICATION` | Попытка изменить системную роль |
| `InsufficientPermissionsError` | 403 | `INSUFFICIENT_PERMISSIONS` | Нет нужного permission |
| `IdentityAlreadyDeactivatedError` | 409 | `IDENTITY_ALREADY_DEACTIVATED` | Повторная деактивация |
| `IdentityAlreadyActiveError` | 409 | `IDENTITY_ALREADY_ACTIVE` | Повторная реактивация |
| `SelfDeactivationError` | 403 | `SELF_DEACTIVATION_FORBIDDEN` | Админ пытается деактивировать себя |
| `LastAdminProtectionError` | 403 | `LAST_ADMIN_PROTECTION` | Удаление последнего super_admin |
| `PrivilegeEscalationError` | 403 | `PRIVILEGE_ESCALATION` | Назначение прав, которых нет у админа |

#### Repository Interfaces — `interfaces.py`

**`IIdentityRepository`** — методы:
- `add(identity) -> Identity`
- `get(identity_id) -> Identity | None`
- `get_by_email(email) -> tuple[Identity, LocalCredentials] | None`
- `add_credentials(credentials) -> LocalCredentials`
- `update_credentials(credentials) -> None`
- `email_exists(email) -> bool`
- `update(identity) -> None`

**`ISessionRepository`** — методы:
- `add(session) -> Session`
- `get(session_id) -> Session | None`
- `get_by_refresh_token_hash(token_hash) -> Session | None`
- `update(session) -> None`
- `revoke_all_for_identity(identity_id) -> list[uuid.UUID]`
- `count_active(identity_id) -> int`
- `get_active_session_ids(identity_id) -> list[uuid.UUID]`
- `add_session_roles(session_id, role_ids) -> None`
- `remove_session_role(session_id, role_id) -> None`

**`IRoleRepository`** — методы:
- `add(role) -> Role`
- `get(role_id) -> Role | None`
- `get_by_name(name) -> Role | None`
- `delete(role_id) -> None`
- `get_all() -> list[Role]`
- `get_identity_role_ids(identity_id) -> list[uuid.UUID]`
- `assign_to_identity(identity_id, role_id, assigned_by=None) -> None`
- `revoke_from_identity(identity_id, role_id) -> None`
- `update(role) -> None`
- `count_identities_with_role(role_name) -> int`
- `get_identity_ids_with_role(role_id) -> list[uuid.UUID]`
- `set_permissions(role_id, permission_ids) -> None`

**`IPermissionRepository`** — методы:
- `get_all() -> list[Permission]`
- `get_by_codename(codename) -> Permission | None`
- `get_by_ids(permission_ids) -> list[Permission]`

**`ILinkedAccountRepository`** — методы:
- `add(account) -> LinkedAccount`
- `get_by_provider(provider, provider_sub_id) -> LinkedAccount | None`
- `get_all_for_identity(identity_id) -> list[LinkedAccount]`

### 2.2 Application Layer

#### Commands

| Handler | Command Input | Action | Output | Side Effects |
|---------|--------------|--------|--------|-------------|
| `RegisterHandler` | `email`, `password` | Create Identity + LocalCredentials, assign "customer" role | `RegisterResult(identity_id)` | Emit `IdentityRegisteredEvent` |
| `LoginHandler` | `email`, `password`, `ip`, `user_agent` | Verify creds, check active, rehash if needed, create Session | `LoginResult(access_token, refresh_token, identity_id)` | Session creation, session_roles |
| `LoginOIDCHandler` | `provider_token`, `ip`, `user_agent` | Validate OIDC, create or link identity, create Session | `LoginOIDCResult(access_token, refresh_token, identity_id, is_new)` | May emit `IdentityRegisteredEvent` |
| `LogoutHandler` | `session_id` | Revoke session | None | Invalidate `perms:{session_id}` cache |
| `LogoutAllHandler` | `identity_id` | Revoke all sessions | None | Invalidate all session caches |
| `RefreshTokenHandler` | `refresh_token`, `ip`, `user_agent` | Verify + rotate token, check identity active | `RefreshTokenResult(access_token, refresh_token)` | Update session hash |
| `AssignRoleHandler` | `identity_id`, `role_id`, `assigned_by` | Assign role to identity + all active sessions | None | Emit `RoleAssignmentChangedEvent` |
| `RevokeRoleHandler` | `identity_id`, `role_id` | Remove role from identity + sessions | None | Emit `RoleAssignmentChangedEvent` |
| `CreateRoleHandler` | `name`, `description` | Create non-system role | `CreateRoleResult(role_id)` | None |
| `DeleteRoleHandler` | `role_id` | Delete non-system role | None | None |
| `UpdateRoleHandler` | `role_id`, `name?`, `description?` | Update role name/description | `UpdateRoleResult(role_id)` | None |
| `SetRolePermissionsHandler` | `role_id`, `permission_ids`, `session_id` | Full-replace permissions, check privilege escalation | None | Invalidate all affected session caches |
| `DeactivateIdentityHandler` | `identity_id`, `reason` | Self-deactivation (GDPR) | None | Emit `IdentityDeactivatedEvent`, revoke sessions |
| `AdminDeactivateIdentityHandler` | `identity_id`, `reason`, `deactivated_by` | Admin deactivation with guards | None | Emit `IdentityDeactivatedEvent`, revoke sessions |
| `ReactivateIdentityHandler` | `identity_id`, `reactivated_by` | Reactivate deactivated identity | None | Emit `IdentityReactivatedEvent` |

Ключевые бизнес-правила в command handlers:
- **LoginHandler**: max_sessions=5 (config), rehash bcrypt->argon2id
- **AdminDeactivateIdentityHandler**: self-deactivation protection, last super_admin protection
- **SetRolePermissionsHandler**: privilege escalation prevention (admin can't grant perms they don't have)

#### Queries

| Handler | Input | SQL Strategy | Output |
|---------|-------|-------------|--------|
| `ListIdentitiesHandler` | offset, limit, search, role_id, is_active, sort_by, sort_order | Raw SQL: LEFT JOIN identities + local_credentials + users, 2nd query for role names | `AdminIdentityListResult` (paginated) |
| `GetIdentityDetailHandler` | `identity_id` | Raw SQL: LEFT JOIN identities + local_credentials + users + roles | `AdminIdentityDetail` |
| `GetIdentityRolesHandler` | `identity_id` | Raw SQL: JOIN roles + identity_roles | `list[IdentityRoleInfo]` |
| `GetSessionPermissionsHandler` | `session_id` | Delegates to `IPermissionResolver` (cache-aside) | `frozenset[str]` |
| `GetMySessionsHandler` | `identity_id`, `current_session_id` | Raw SQL: sessions WHERE identity_id, not revoked | `list[SessionInfo]` |
| `ListRolesHandler` | None | Raw SQL: roles + role_permissions + permissions | `list[RoleWithPermissions]` |
| `ListPermissionsHandler` | None | Raw SQL: permissions ORDER BY codename | `list[PermissionGroup]` (grouped by resource) |
| `GetRoleDetailHandler` | `role_id` | Raw SQL: role + role_permissions + permissions | `RoleDetail` |

**Важно:** Query handlers используют raw SQL через `sqlalchemy.text()` и `AsyncSession` напрямую, минуя domain entities (CQRS read side). ListIdentitiesHandler делает JOIN `identities + local_credentials + users` — cross-module join на уровне SQL.

### 2.3 Infrastructure Layer

#### ORM Models — `infrastructure/models.py`

| Model | Table | PK | Notable Columns |
|-------|-------|----|-----------------|
| `IdentityModel` | `identities` | `id` (UUID) | `type` (Enum), `is_active`, `deactivated_at`, `deactivated_by` |
| `LocalCredentialsModel` | `local_credentials` | `identity_id` (FK→identities, shared PK 1:1) | `email` (unique), `password_hash` |
| `LinkedAccountModel` | `linked_accounts` | `id` | `identity_id` (FK), `provider`, `provider_sub_id`, UQ(provider, provider_sub_id) |
| `RoleModel` | `roles` | `id` | `name` (unique), `is_system`, `description` |
| `PermissionModel` | `permissions` | `id` | `codename` (unique), `resource`, `action`, `description` |
| `RolePermissionModel` | `role_permissions` | (`role_id`, `permission_id`) | M:M junction |
| `RoleHierarchyModel` | `role_hierarchy` | (`parent_role_id`, `child_role_id`) | CHECK parent != child |
| `IdentityRoleModel` | `identity_roles` | (`identity_id`, `role_id`) | `assigned_at`, `assigned_by` |
| `SessionModel` | `sessions` | `id` | `refresh_token_hash` (unique), `ip_address` (INET), `expires_at` |
| `SessionRoleModel` | `session_roles` | (`session_id`, `role_id`) | NIST session-role activation |

#### DI Provider — `infrastructure/provider.py`

`IdentityProvider` регистрирует все зависимости в `Scope.REQUEST`:
- 5 repositories: IdentityRepository, SessionRepository, RoleRepository, PermissionRepository, LinkedAccountRepository
- 14 command handlers (LoginHandler с custom factory для config injection)
- 8 query handlers

### 2.4 Presentation Layer

#### Routers

**`router_auth.py`** — prefix `/auth`, tags ["Authentication"]
| Method | Path | Permission | Handler |
|--------|------|-----------|---------|
| POST | `/auth/register` | Public | RegisterHandler |
| POST | `/auth/login` | Public | LoginHandler |
| POST | `/auth/refresh` | Public | RefreshTokenHandler |
| POST | `/auth/logout` | Authenticated | LogoutHandler |
| POST | `/auth/logout/all` | Authenticated | LogoutAllHandler |

**`router_admin.py`** — prefix `/admin`, tags ["Admin -- IAM"]
| Method | Path | Permission | Handler |
|--------|------|-----------|---------|
| GET | `/admin/identities` | `identities:manage` | ListIdentitiesHandler |
| GET | `/admin/identities/{id}` | `identities:manage` | GetIdentityDetailHandler |
| POST | `/admin/identities/{id}/deactivate` | `identities:manage` | AdminDeactivateIdentityHandler |
| POST | `/admin/identities/{id}/reactivate` | `identities:manage` | ReactivateIdentityHandler |
| GET | `/admin/roles` | `roles:manage` | ListRolesHandler |
| POST | `/admin/roles` | `roles:manage` | CreateRoleHandler |
| GET | `/admin/roles/{id}` | `roles:manage` | GetRoleDetailHandler |
| PATCH | `/admin/roles/{id}` | `roles:manage` | UpdateRoleHandler |
| DELETE | `/admin/roles/{id}` | `roles:manage` | DeleteRoleHandler |
| PUT | `/admin/roles/{id}/permissions` | `roles:manage` | SetRolePermissionsHandler |
| GET | `/admin/permissions` | `roles:manage` | ListPermissionsHandler |
| POST | `/admin/identities/{id}/roles` | `roles:manage` | AssignRoleHandler |
| DELETE | `/admin/identities/{id}/roles/{role_id}` | `roles:manage` | RevokeRoleHandler |

**`router_account.py`** — prefix `/users`, tags ["Account Management"]
| Method | Path | Permission | Handler |
|--------|------|-----------|---------|
| DELETE | `/users/me` | `users:delete` | DeactivateIdentityHandler |
| GET | `/users/me/sessions` | Authenticated | GetMySessionsHandler |

#### Schemas — `presentation/schemas.py`

Все наследуют `CamelModel` (snake_case -> camelCase).

Request schemas:
- `RegisterRequest`: `email: EmailStr`, `password: str (8-128 chars)`
- `LoginRequest`: `email: EmailStr`, `password: str (max 128)`
- `RefreshTokenRequest`: `refresh_token: str`
- `LoginOIDCRequest`: `provider_token: str`
- `CreateRoleRequest`: `name: str (pattern ^[a-z_]+$, 2-100)`, `description: str? (max 500)`
- `AssignRoleRequest`: `role_id: uuid.UUID`
- `AdminDeactivateRequest`: `reason: str (1-200)`
- `UpdateRoleRequest`: `name?: str`, `description?: str` (at-least-one validator)
- `SetRolePermissionsRequest`: `permission_ids: list[uuid.UUID]`

Response schemas:
- `RegisterResponse`: `identity_id`, `message`
- `TokenResponse`: `access_token`, `refresh_token`, `token_type="bearer"`
- `MessageResponse`: `message`
- `AdminIdentityResponse`: `identity_id`, `email?`, `auth_type`, `is_active`, `first_name?`, `last_name?`, `phone?`, `roles: list[str]`, `created_at`
- `AdminIdentityListResponse`: `items`, `total`, `offset`, `limit`
- `AdminIdentityDetailResponse`: extends AdminIdentityResponse + `roles: list[RoleInfoResponse]`, `deactivated_at?`, `deactivated_by?`
- `RoleDetailResponse`: `id`, `name`, `description?`, `is_system`, `permissions: list[PermissionDetailResponse]`
- `PermissionGroupResponse`: `resource`, `permissions: list[PermissionInfoResponse]`

#### Dependencies — `presentation/dependencies.py`

- **`get_auth_context`**: Decodes JWT Bearer token, extracts `sub` (identity_id) and `sid` (session_id), returns `AuthContext`
- **`RequirePermission(codename)`**: Callable class, checks `IPermissionResolver.has_permission(session_id, codename)`, raises `InsufficientPermissionsError`
- **`get_current_user_id`**: Backward-compatible wrapper, returns `auth.identity_id` as `uuid.UUID`

---

## 3. User Module — Полный разбор

**Путь:** `src/modules/user/`

### 3.1 Domain Layer

**`User`** (Aggregate Root) — `domain/entities.py`
```python
@dataclass
class User(AggregateRoot):
    id: uuid.UUID                 # == identity.id (shared PK)
    profile_email: str | None     # может отличаться от login email
    first_name: str
    last_name: str
    phone: str | None
    created_at: datetime
    updated_at: datetime
```

Методы:
- `create_from_identity(cls, identity_id, profile_email=None) -> User` — фабрика, создает с пустыми полями
- `update_profile(**kwargs) -> None` — обновляет только поля из `_UPDATABLE_FIELDS` = `{profile_email, first_name, last_name, phone}`
- `anonymize() -> None` — GDPR: first_name="[DELETED]", last_name="[DELETED]", phone=None, profile_email=None

**`UserNotFoundError`** — 404, `USER_NOT_FOUND`

**`IUserRepository`** — методы: `add(user)`, `get(user_id)`, `update(user)`

### 3.2 Application Layer

#### Commands

| Handler | Input | Output | Action |
|---------|-------|--------|--------|
| `CreateUserHandler` | `identity_id`, `profile_email?` | None | Idempotent create from IdentityRegisteredEvent |
| `UpdateProfileHandler` | `user_id`, `first_name?`, `last_name?`, `phone?`, `profile_email?` | None | Partial update |
| `AnonymizeUserHandler` | `user_id` | None | GDPR anonymization (idempotent) |

#### Queries

| Handler | Input | SQL | Output |
|---------|-------|-----|--------|
| `GetMyProfileHandler` | `user_id` | `SELECT id, profile_email, first_name, last_name, phone FROM users WHERE id = :user_id` | `UserProfile` |
| `GetUserByIdentityHandler` | `identity_id` | `SELECT id FROM users WHERE id = :identity_id` | `uuid.UUID | None` |

#### Consumers — `application/consumers/identity_events.py`

TaskIQ consumers, queue `iam_events`:
- **`create_user_on_identity_registered`**: routing_key `user.identity_registered`, creates User row
- **`anonymize_user_on_identity_deactivated`**: routing_key `user.identity_deactivated`, anonymizes PII

### 3.3 Infrastructure Layer

**`UserModel`** — table `users`
```
id               UUID    PK + FK→identities.id (ON DELETE CASCADE)
profile_email    String(320)  nullable
first_name       String(100)  default=""
last_name        String(100)  default=""
phone            String(20)   nullable
created_at       TIMESTAMP(tz)
updated_at       TIMESTAMP(tz)
```

**`UserRepository`** — Data Mapper pattern, explicit UPDATE via `sqlalchemy.update()`.

**`UserProvider`** — registers: UserRepository→IUserRepository, 3 command handlers, 2 query handlers.

### 3.4 Presentation Layer

**`router.py`** — prefix `/users`, tags ["User Profile"]
| Method | Path | Permission | Handler |
|--------|------|-----------|---------|
| GET | `/users/me` | `users:read` | GetMyProfileHandler |
| PATCH | `/users/me` | `users:update` | UpdateProfileHandler |

**Schemas:**
- `UserProfileResponse`: `id`, `profile_email?`, `first_name`, `last_name`, `phone?`
- `UpdateProfileRequest`: `first_name?`, `last_name?`, `phone?`, `profile_email?` (at-least-one validator)

**Важно:** User router импортирует `get_auth_context` и `RequirePermission` из `identity.presentation.dependencies` — разрешенное cross-module исключение (enforced в architecture tests).

---

## 4. Shared Infrastructure

### 4.1 AuthContext и JWT

**`AuthContext`** — `src/shared/interfaces/auth.py`
```python
@dataclass(frozen=True, slots=True)
class AuthContext:
    identity_id: uuid.UUID
    session_id: uuid.UUID
```

JWT payload claims: `sub` (identity_id), `sid` (session_id), `exp`, `iat`, `jti`

**`JwtTokenProvider`** — `src/infrastructure/security/jwt.py`:
- `create_access_token(payload_data, expires_minutes?)` — PyJWT encode, HS256, key from `SECRET_KEY`
- `decode_access_token(token)` — PyJWT decode, raises `UnauthorizedError` on expiry/invalid
- `create_refresh_token()` — `secrets.token_urlsafe(32)`, returns `(raw, sha256_hash)`

Config values (from `Settings`):
- `ACCESS_TOKEN_EXPIRE_MINUTES`: 15 (default)
- `REFRESH_TOKEN_EXPIRE_DAYS`: 30
- `MAX_ACTIVE_SESSIONS_PER_IDENTITY`: 5
- `SESSION_PERMISSIONS_CACHE_TTL`: 300

### 4.2 Permission Resolution (cache-aside Redis)

**`PermissionResolver`** — `src/infrastructure/security/authorization.py`

Cache key: `perms:{session_id}` (Redis), TTL=300s.

Recursive CTE for resolving effective permissions:
```sql
WITH RECURSIVE role_tree AS (
    SELECT sr.role_id
    FROM session_roles sr
    WHERE sr.session_id = :session_id
    UNION
    SELECT rh.child_role_id
    FROM role_hierarchy rh
    JOIN role_tree rt ON rt.role_id = rh.parent_role_id
)
SELECT DISTINCT p.codename
FROM role_tree rt
JOIN role_permissions rp ON rp.role_id = rt.role_id
JOIN permissions p ON p.id = rp.permission_id
```

Это означает: session_roles -> traverse role_hierarchy (children inherit up) -> role_permissions -> permissions.

### 4.3 Unit of Work

**`UnitOfWork`** — `src/infrastructure/database/uow.py`
- Tracks aggregates via `register_aggregate()`
- On `commit()`: collects domain events from all registered aggregates, serializes them to `OutboxMessage` rows, commits atomically
- Outbox Relay (TaskIQ task) picks up messages and dispatches to consumers

### 4.4 Base classes

**`DomainEvent`** — `src/shared/interfaces/entities.py`:
- `event_id`, `occurred_at`, `aggregate_type`, `aggregate_id`, `event_type`
- `__init_subclass__` validation: must override `aggregate_type` and `event_type`

**`AggregateRoot`** — mixin for attrs dataclasses:
- `_domain_events: list[DomainEvent]`
- `add_domain_event()`, `clear_domain_events()`, `domain_events` property

**Exception hierarchy** — `src/shared/exceptions.py`:
- `AppException(message, status_code, error_code, details)`
- Subclasses: `NotFoundError(404)`, `BadRequestError(400)`, `UnauthorizedError(401)`, `ForbiddenError(403)`, `ConflictError(409)`, `ValidationError(400)`, `UnprocessableEntityError(422)`, `ServiceUnavailableError(503)`

---

## 5. Database Schema

### 5.1 ER-диаграмма

```
identities (PK: id)
  ├── 1:1 ── local_credentials (PK: identity_id FK→identities)
  ├── 1:N ── sessions (FK: identity_id)
  │              └── M:M ── session_roles ── roles
  ├── 1:N ── linked_accounts (FK: identity_id)
  ├── M:M ── identity_roles ── roles
  └── 1:1 ── users (PK: id FK→identities)

roles (PK: id)
  ├── M:M ── role_permissions ── permissions
  └── M:M ── role_hierarchy (parent_role_id, child_role_id)
```

### 5.2 Все таблицы

**`identities`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| type | VARCHAR(10) Enum(LOCAL, OIDC) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default=true |
| created_at | TIMESTAMP(tz) | NOT NULL, default=now() |
| updated_at | TIMESTAMP(tz) | NOT NULL, default=now() |
| deactivated_at | TIMESTAMP(tz) | nullable |
| deactivated_by | UUID | nullable |

**`local_credentials`**
| Column | Type | Constraints |
|--------|------|-------------|
| identity_id | UUID | PK, FK→identities(CASCADE) |
| email | VARCHAR(320) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| created_at | TIMESTAMP(tz) | NOT NULL |
| updated_at | TIMESTAMP(tz) | NOT NULL |

**`users`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, FK→identities(CASCADE) |
| profile_email | VARCHAR(320) | nullable |
| first_name | VARCHAR(100) | NOT NULL, default="" |
| last_name | VARCHAR(100) | NOT NULL, default="" |
| phone | VARCHAR(20) | nullable |
| created_at | TIMESTAMP(tz) | NOT NULL |
| updated_at | TIMESTAMP(tz) | NOT NULL |

**`sessions`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| identity_id | UUID | FK→identities(CASCADE), NOT NULL |
| refresh_token_hash | VARCHAR(64) | NOT NULL, UNIQUE |
| ip_address | INET | nullable |
| user_agent | VARCHAR(500) | nullable |
| is_revoked | BOOLEAN | NOT NULL, default=false |
| created_at | TIMESTAMP(tz) | NOT NULL |
| expires_at | TIMESTAMP(tz) | NOT NULL |

**`roles`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | VARCHAR(100) | NOT NULL, UNIQUE |
| description | VARCHAR(500) | nullable |
| is_system | BOOLEAN | NOT NULL, default=false |
| created_at | TIMESTAMP(tz) | NOT NULL |
| updated_at | TIMESTAMP(tz) | NOT NULL |

**`permissions`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| codename | VARCHAR(100) | NOT NULL, UNIQUE |
| resource | VARCHAR(50) | NOT NULL |
| action | VARCHAR(50) | NOT NULL |
| description | VARCHAR(500) | nullable |
| created_at | TIMESTAMP(tz) | NOT NULL |

### 5.3 Junction Tables (M:M)

**`identity_roles`** — PK: (identity_id, role_id), `assigned_at`, `assigned_by`
**`role_permissions`** — PK: (role_id, permission_id)
**`role_hierarchy`** — PK: (parent_role_id, child_role_id), CHECK parent != child
**`session_roles`** — PK: (session_id, role_id)

### 5.4 Индексы

- `ix_sessions_identity_revoked` — composite index on `(identity_id, is_revoked)`
- `ix_linked_accounts_identity_id` — index on `identity_id`
- `uq_local_credentials_email` — unique on `email`
- `uq_sessions_refresh_token_hash` — unique on `refresh_token_hash`
- `uq_roles_name` — unique on `name`
- `uq_permissions_codename` — unique on `codename`
- `uq_linked_accounts_provider_sub` — unique on `(provider, provider_sub_id)`

### 5.5 Seed Data

**Файл:** `scripts/seed_dev.sql`

Идемпотентный скрипт: DELETE + INSERT для IAM данных.

**Dev admin:** `admin@loyality.dev` / `Admin123!` (Argon2id hash), identity_id=`00000000-...-000000000099`, role=admin

---

## 6. API Contract

### 6.1 Все эндпоинты

API prefix: `/api/v1` (from `Settings.API_V1_STR`)

#### Public (no auth)
| Method | Full Path | Request | Response |
|--------|-----------|---------|----------|
| POST | `/api/v1/auth/register` | `{email, password}` | `{identityId, message}` (201) |
| POST | `/api/v1/auth/login` | `{email, password}` | `{accessToken, refreshToken, tokenType}` |
| POST | `/api/v1/auth/refresh` | `{refreshToken}` | `{accessToken, refreshToken, tokenType}` |

#### Authenticated (Bearer JWT)
| Method | Full Path | Permission | Request | Response |
|--------|-----------|-----------|---------|----------|
| POST | `/api/v1/auth/logout` | auth | - | `{message}` |
| POST | `/api/v1/auth/logout/all` | auth | - | `{message}` |
| GET | `/api/v1/users/me` | `users:read` | - | `{id, profileEmail, firstName, lastName, phone}` |
| PATCH | `/api/v1/users/me` | `users:update` | `{firstName?, lastName?, phone?, profileEmail?}` | `{message}` |
| DELETE | `/api/v1/users/me` | `users:delete` | - | `{message}` |
| GET | `/api/v1/users/me/sessions` | auth | - | `[{id, ipAddress, userAgent, isRevoked, createdAt, expiresAt, isCurrent}]` |

#### Admin (requires specific permissions)
| Method | Full Path | Permission | Request | Response |
|--------|-----------|-----------|---------|----------|
| GET | `/api/v1/admin/identities` | `identities:manage` | query: offset, limit, search, roleId, isActive, sortBy, sortOrder | `{items, total, offset, limit}` |
| GET | `/api/v1/admin/identities/{id}` | `identities:manage` | - | `{identityId, email, authType, isActive, firstName, lastName, phone, roles, createdAt, deactivatedAt, deactivatedBy}` |
| POST | `/api/v1/admin/identities/{id}/deactivate` | `identities:manage` | `{reason}` | `{message}` |
| POST | `/api/v1/admin/identities/{id}/reactivate` | `identities:manage` | - | `{message}` |
| POST | `/api/v1/admin/identities/{id}/roles` | `roles:manage` | `{roleId}` | `{message}` |
| DELETE | `/api/v1/admin/identities/{id}/roles/{roleId}` | `roles:manage` | - | `{message}` |
| GET | `/api/v1/admin/roles` | `roles:manage` | - | `[{id, name, description, isSystem, permissions}]` |
| POST | `/api/v1/admin/roles` | `roles:manage` | `{name, description?}` | `{roleId, message}` (201) |
| GET | `/api/v1/admin/roles/{id}` | `roles:manage` | - | `{id, name, description, isSystem, permissions}` |
| PATCH | `/api/v1/admin/roles/{id}` | `roles:manage` | `{name?, description?}` | `{id, name, description, isSystem, permissions}` |
| DELETE | `/api/v1/admin/roles/{id}` | `roles:manage` | - | `{message}` |
| PUT | `/api/v1/admin/roles/{id}/permissions` | `roles:manage` | `{permissionIds}` | `{id, name, description, isSystem, permissions}` |
| GET | `/api/v1/admin/permissions` | `roles:manage` | - | `[{resource, permissions: [{id, codename, resource, action, description}]}]` |

### 6.2 Конфликт путей

**Проблема:** `router_account.py` и `router.py` оба используют prefix `/users`:
- `identity_account_router`: `/users/me` (DELETE) и `/users/me/sessions` (GET)
- `user_router`: `/users/me` (GET, PATCH)

Оба подключены в `api/router.py` без prefix — конфликт разрешается FastAPI: разные HTTP methods на одном пути работают, но это архитектурный запах (два модуля владеют одним путем).

### 6.3 Error Responses

Все ошибки возвращают JSON:
```json
{
  "message": "Human-readable description",
  "error_code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

---

## 7. Event-Driven Integration

### 7.1 Domain Events

| Event | Publisher | Consumer | Action |
|-------|----------|----------|--------|
| `IdentityRegisteredEvent` | `RegisterHandler`, `LoginOIDCHandler` | `create_user_on_identity_registered` (User module) | Creates User row with shared PK |
| `IdentityDeactivatedEvent` | `DeactivateIdentityHandler`, `AdminDeactivateIdentityHandler` | `anonymize_user_on_identity_deactivated` (User module) | Anonymizes user PII |
| `RoleAssignmentChangedEvent` | `AssignRoleHandler`, `RevokeRoleHandler` | `invalidate_permissions_cache_on_role_change` (Identity module) | Deletes Redis `perms:{sid}` entries |
| `IdentityReactivatedEvent` | `ReactivateIdentityHandler` | **НЕТ CONSUMER** | Event emitted but not consumed |

### 7.2 TaskIQ Consumers

Все consumers в queue `iam_events`, exchange `taskiq_rpc_exchange`:

| Consumer Function | Routing Key | Module | Retry |
|------------------|-------------|--------|-------|
| `create_user_on_identity_registered` | `user.identity_registered` | `user.application.consumers` | 3x, timeout=30s |
| `anonymize_user_on_identity_deactivated` | `user.identity_deactivated` | `user.application.consumers` | 3x, timeout=30s |
| `invalidate_permissions_cache_on_role_change` | `identity.role_assignment_changed` | `identity.application.consumers` | 3x, timeout=30s |

### 7.3 Transactional Outbox

UoW собирает domain events из зарегистрированных aggregates и записывает их в таблицу `outbox_messages` атомарно с бизнес-данными. Outbox Relay (`src/infrastructure/outbox/relay.py`) извлекает и отправляет через TaskIQ broker.

---

## 8. RBAC Model

### 8.1 Роли (seed)

| ID | Name | Description | is_system |
|----|------|-------------|-----------|
| `...001` | `admin` | Администратор -- полный доступ | true |
| `...002` | `customer` | Клиент -- каталог, заказы, профиль | true |
| `...003` | `content_manager` | Контент-менеджер -- каталог и карточки | true |
| `...004` | `order_manager` | Менеджер по заказам | true |
| `...005` | `support_specialist` | Специалист поддержки | true |
| `...006` | `review_moderator` | Модератор отзывов | true |

**Нет роли `super_admin`** в seed data, но код `AdminDeactivateIdentityHandler` проверяет `role.name == "super_admin"` и `count_identities_with_role("super_admin")`. Это **GAP** — роль `super_admin` не создана, protection не работает.

### 8.2 Пермиссии (13 total)

| Codename | Resource | Action | Description |
|----------|----------|--------|-------------|
| `catalog:read` | catalog | read | Просмотр каталога |
| `catalog:manage` | catalog | manage | CRUD каталога |
| `orders:read` | orders | read | Просмотр заказов |
| `orders:manage` | orders | manage | Управление заказами |
| `reviews:read` | reviews | read | Просмотр отзывов |
| `reviews:moderate` | reviews | moderate | Модерация отзывов |
| `returns:read` | returns | read | Просмотр возвратов |
| `returns:manage` | returns | manage | Обработка возвратов |
| `users:read` | users | read | Просмотр профиля |
| `users:update` | users | update | Редактирование профиля |
| `users:delete` | users | delete | Удаление аккаунта (GDPR) |
| `roles:manage` | roles | manage | Управление ролями |
| `identities:manage` | identities | manage | Управление пользователями |

### 8.3 Role-Permission Assignments (seed)

| Role | Permissions |
|------|-------------|
| admin | ALL 13 |
| customer | catalog:read, orders:read, reviews:read, users:read, users:update, users:delete |
| content_manager | catalog:read, catalog:manage, reviews:read, users:read |
| order_manager | orders:read, orders:manage, returns:read, returns:manage, catalog:read, users:read |
| support_specialist | users:read, users:update, orders:read, returns:read, catalog:read |
| review_moderator | reviews:read, reviews:moderate, catalog:read, users:read |

### 8.4 Role Hierarchy (seed)

```
admin
  ├── content_manager → customer
  ├── order_manager → customer
  ├── support_specialist → customer
  └── review_moderator → customer
```

Через recursive CTE: admin получает все пермиссии всех дочерних ролей.

### 8.5 Session-Role Activation (NIST)

При login: `role_ids = get_identity_role_ids(identity.id)`, затем `add_session_roles(session_id, role_ids)`.
При assign_role: пропагируется в `session_roles` для всех активных сессий.
При revoke_role: удаляется из `session_roles` для всех активных сессий.

PermissionResolver работает от `session_roles`, не от `identity_roles` — это NIST RBAC compliance (пермиссии привязаны к сессии, а не к identity напрямую).

---

## 9. Frontend Current State

### 9.1 Users Page

**Данные:** `src/data/users.js` — mock-генератор 57 пользователей с полями:
- `id`, `handle`, `userId`, `avatar`, `createdAt`, `source`, `followers`, `orders`

**Service:** `src/services/users.js` — `getUsers()`, `getUserById(id)` — возвращает mock data.

**Проблема:** Frontend users data model не совпадает с backend. Frontend ожидает `handle`, `userId`, `source`, `followers`, `orders` — ничего из этого нет в backend User entity.

### 9.2 Staff Page

**Путь:** `src/app/admin/settings/staff/page.jsx`

**Данные:** `src/data/staff.js` — hardcoded массив из 3 сотрудников:
```js
[
  { id: 'staff-evgeny', name: 'Evgeny', email: 'evgeny@example.com', role: 'Администратор' },
  { id: 'staff-nikita', name: 'Никита', email: 'nikita@example.com', role: 'Администратор' },
  { id: 'staff-ivan', name: 'Иван', email: 'ivan@example.com', role: 'Контент-менеджер' },
]
```

**Service:** `src/services/staff.js` — `getStaff()` — возвращает копию mock data.

**UI функциональность:**
- Список сотрудников (из mock)
- Модал "Добавление сотрудника" с полями: Имя, Эл. почта, Роль (dropdown: Администратор / Контент-менеджер)
- Генерация invite link: `https://invite.admin.loyaltymarket.ru/{random_token}`
- Копирование invite link
- **Полностью на моках, нет API вызовов к backend**

### 9.3 Roles Page

Frontend BFF routes для ролей не найдены (`src/app/api/admin/roles/` не существует). Управление ролями доступно только через прямые API вызовы к backend.

### 9.4 Frontend Data Models vs Backend

| Frontend Field | Backend Equivalent | Status |
|---------------|-------------------|--------|
| `staff.name` | `user.first_name + user.last_name` | Разная структура |
| `staff.email` | `local_credentials.email` | Совпадает по смыслу |
| `staff.role` | `identity_roles -> roles.name` | Совпадает по смыслу |
| `users.handle` | **НЕТ** | Отсутствует в backend |
| `users.source` | **НЕТ** | Отсутствует в backend |
| `users.followers` | **НЕТ** | Отсутствует в backend |
| `users.orders` | **НЕТ** | Отсутствует в backend (другой bounded context) |

---

## 10. Тесты

### 10.1 Unit Tests

**Identity commands** — `tests/unit/modules/identity/application/commands/test_commands.py`:
- `TestLogoutHandler`: 3 теста (revoke + cache, skip revoked, missing session)
- `TestLogoutAllHandler`: 2 теста (revoke all + cache, no sessions)
- `TestRefreshTokenHandler`: 4 теста (success, reuse detection, expired session, deactivated identity)
- `TestAssignRoleHandler`: 3 теста (success + event, identity not found, role not found)
- `TestCreateRoleHandler`: 2 теста (success, duplicate name)
- `TestDeleteRoleHandler`: 3 теста (success, not found, system role protection)
- `TestRevokeRoleHandler`: 2 теста (success + event, identity not found)
- `TestDeactivateIdentityHandler`: 2 теста (success + session revoke + cache, not found)
- `TestLoginOIDCHandler`: 4 теста (existing identity, new identity, deactivated, orphan linked account)

**User commands** — `tests/unit/modules/user/application/commands/test_commands.py`:
- `TestCreateUserHandler`: 2 теста (success, idempotent skip)
- `TestAnonymizeUserHandler`: 2 теста (success, not found)
- `TestUpdateProfileHandler`: 4 теста (success, not found, no updates, partial fields)

**Что НЕ покрыто unit тестами:**
- `RegisterHandler` (нет unit тестов, есть integration)
- `LoginHandler` (нет unit тестов, есть integration)
- `AdminDeactivateIdentityHandler` (нет тестов)
- `ReactivateIdentityHandler` (нет тестов)
- `UpdateRoleHandler` (нет тестов)
- `SetRolePermissionsHandler` (нет тестов)
- Все query handlers (тестируются через integration)

### 10.2 Architecture Boundary Tests

**`tests/architecture/test_boundaries.py`** — 7 rules:
1. Domain layer purity (no outer layer imports)
2. Domain has zero framework imports (per module)
3. Application layer boundaries (excluding queries and consumers)
4. Infrastructure does not import presentation
5. Cross-module isolation (allowed: user.presentation→identity.presentation, catalog.presentation→identity.presentation)
6. Shared kernel independence
7. No reverse layer dependencies

### 10.3 Integration Tests

Identity:
- `test_register.py`, `test_login.py` — full flow with real DB
- `test_identity_repo.py`, `test_identity_repo_extended.py` — repository tests
- `test_session_repo.py` — session repository
- `test_role_repo.py`, `test_permission_repo.py` — role/permission repos
- `test_get_identity_roles.py`, `test_get_my_sessions.py`, `test_list_roles.py` — query tests

User:
- `test_create_user.py` — CreateUserHandler with real DB
- `test_get_my_profile.py`, `test_get_user_by_identity.py` — query tests
- `test_user_repo.py` — UserRepository

### 10.4 Gaps (что НЕ покрыто)

- **AdminDeactivateIdentityHandler** — нет тестов для self-deactivation guard, last admin protection
- **ReactivateIdentityHandler** — нет тестов
- **UpdateRoleHandler** — нет тестов для system role name protection
- **SetRolePermissionsHandler** — нет тестов для privilege escalation prevention
- **E2E тесты** — `test_auth.py` и `test_users.py` существуют, но содержимое не проверено
- **Consumer tests** — нет unit тестов для TaskIQ consumers
- **PermissionResolver** — нет unit тестов для cache-aside logic

---

## 11. Проблемы и Gap Analysis

### 11.1 Отсутствие разделения Customer/Staff

**Критическая проблема:** В domain model нет различия между клиентами и сотрудниками. Все являются Identity + User.

- `Identity` entity не имеет поля `account_type` или аналога
- Единственное различие — через роли (`customer` vs `admin`/`content_manager`/etc.)
- При регистрации ВСЕМ присваивается роль `customer`
- Нет отдельного флоу создания сотрудника

### 11.2 Нет инвайт-флоу для сотрудников

Frontend staff page генерирует invite links чисто на клиенте (`crypto.getRandomValues`), без backend API:
- Нет entity `Invitation` в domain
- Нет таблицы `invitations` в schema
- Нет endpoint `/admin/staff/invite`
- Нет валидации invite token при регистрации
- Роли в UI hardcoded: "Администратор", "Контент-менеджер" (не из backend)

### 11.3 Единый endpoint для всех типов

`GET /admin/identities` возвращает ALL identities (customers + staff) без фильтрации по типу. SQL делает LEFT JOIN identities + users:
- Нет способа отфильтровать только staff
- Frontend staff page не использует этот endpoint (работает на моках)
- Frontend users page тоже не использует backend API

### 11.4 Staff страница полностью на моках

`src/services/staff.js` возвращает hardcoded данные из `src/data/staff.js`. Нет:
- API вызовов к backend
- BFF route handlers
- Реального CRUD для сотрудников

### 11.5 Отсутствие реферальной системы

Frontend имеет mock data (`src/data/referrals.js`), но в backend нет bounded context для рефералов. `users` data model на frontend ожидает `source` (откуда пришел пользователь) — этого поля нет в backend.

### 11.6 Другие найденные проблемы

1. **super_admin роль не существует в seed** — код `AdminDeactivateIdentityHandler` проверяет `role.name == "super_admin"`, но в seed data такой роли нет. Protection от удаления последнего super_admin не работает.

2. **IdentityReactivatedEvent не имеет consumer** — событие эмитится, но никто его не обрабатывает. Если user был anonymized, реактивация identity не восстанавливает PII.

3. **Cross-module SQL join в queries** — `ListIdentitiesHandler` и `GetIdentityDetailHandler` делают `LEFT JOIN users u ON u.id = i.id` — прямой join через bounded context boundary. Это нарушение модулярности, хотя допустимо для CQRS read side.

4. **Duplicate auth dependency** — `src/api/dependencies/auth.py` содержит legacy `get_current_user_id` (returns string), а `src/modules/identity/presentation/dependencies.py` содержит новый `get_current_user_id` (returns uuid.UUID). Два разных dependency с одним именем.

5. **Нет password reset flow** — нет endpoint для сброса/смены пароля.

6. **Нет email verification** — регистрация не требует подтверждения email.

7. **User model слишком простой** — только name + phone + email. Нет: аватар, адреса, дата рождения, предпочтения, etc.

---

## 12. Зависимости и Impact Map

### 12.1 Что затронет добавление AccountType

Если добавить `AccountType` (CUSTOMER/STAFF) в Identity domain:

**Domain changes:**
- `Identity` entity: добавить поле `account_type: AccountType`
- `IdentityType` → не подходит (это auth method), нужен новый enum `AccountType`
- `Identity.register()` → принимать `account_type`
- Domain events: `IdentityRegisteredEvent` — добавить `account_type`

**Application changes:**
- `RegisterHandler` → default `account_type=CUSTOMER`
- Новый command: `InviteStaffHandler` → `account_type=STAFF`
- `ListIdentitiesHandler` → фильтр по `account_type`
- Возможно: отдельные query handlers для staff vs customers

**Infrastructure changes:**
- `IdentityModel` → новая колонка `account_type`
- Alembic migration: ADD COLUMN + data migration
- Seed data: указать account_type для dev admin

**Presentation changes:**
- Новые admin endpoints: `/admin/staff`, `/admin/staff/invite`
- Фильтр `account_type` в `/admin/identities`
- Schema changes: response models с account_type

### 12.2 Файлы, которые нужно изменить (полный список)

**Identity domain:**
- `src/modules/identity/domain/value_objects.py` — добавить `AccountType` enum
- `src/modules/identity/domain/entities.py` — поле `account_type` в Identity
- `src/modules/identity/domain/events.py` — `account_type` в IdentityRegisteredEvent
- `src/modules/identity/domain/interfaces.py` — возможно новые методы в IIdentityRepository

**Identity application:**
- `src/modules/identity/application/commands/register.py` — default CUSTOMER
- Новые файлы для staff invite flow
- `src/modules/identity/application/queries/list_identities.py` — фильтр account_type в SQL
- `src/modules/identity/application/queries/get_identity_detail.py` — account_type в read model

**Identity infrastructure:**
- `src/modules/identity/infrastructure/models.py` — колонка account_type
- `src/modules/identity/infrastructure/repositories/identity_repository.py` — маппинг
- `src/modules/identity/infrastructure/provider.py` — новые handlers

**Identity presentation:**
- `src/modules/identity/presentation/schemas.py` — account_type в response models
- `src/modules/identity/presentation/router_admin.py` — фильтр + новые endpoints

**User module:**
- `src/modules/user/application/consumers/identity_events.py` — обработка account_type

**Shared:**
- `src/shared/interfaces/auth.py` — возможно `account_type` в AuthContext

### 12.3 Миграции, которые нужно создать

1. `ADD COLUMN account_type VARCHAR(10) NOT NULL DEFAULT 'CUSTOMER'` к таблице `identities`
2. `UPDATE identities SET account_type = 'STAFF' WHERE id IN (SELECT identity_id FROM identity_roles ir JOIN roles r ON r.id = ir.role_id WHERE r.name IN ('admin', 'content_manager', 'order_manager', 'support_specialist', 'review_moderator'))` — data migration
3. Возможно: таблица `staff_invitations` для invite flow

### 12.4 Тесты, которые нужно обновить

**Unit tests:**
- `tests/unit/modules/identity/domain/test_value_objects.py` — тесты для AccountType
- `tests/unit/modules/identity/application/commands/test_commands.py` — обновить все тесты, где создается Identity
- `tests/unit/modules/user/application/commands/test_commands.py` — consumer tests с account_type
- Новые тесты для invite flow

**Integration tests:**
- `tests/integration/modules/identity/application/commands/test_register.py`
- `tests/integration/modules/identity/application/commands/test_login.py`
- `tests/integration/modules/identity/infrastructure/repositories/test_identity_repo.py`
- Все query integration tests

**Architecture tests:**
- `tests/architecture/test_boundaries.py` — без изменений, если новый код соблюдает boundaries

**E2E tests:**
- `tests/e2e/api/v1/test_auth.py` — register flow с account_type
- `tests/e2e/api/v1/test_users.py` — staff endpoints
