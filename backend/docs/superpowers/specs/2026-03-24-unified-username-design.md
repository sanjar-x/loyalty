# Unified Username Design

## Problem

`username` is duplicated across two bounded contexts:

- `local_credentials.username` (Identity module) — login identifier, UNIQUE
- `customers.username` (User module) — display name from Telegram, NOT unique
- `staff_members` has no username at all

This creates data inconsistency: Telegram users have username only in `customers`, LOCAL users have it only in `local_credentials`, and staff members cannot have one.

## Decision

Single `username` field lives in the **User module** (`customers` and `staff_members` tables). Identity module resolves username-based login via a raw SQL JOIN (read-path cross-module query, acceptable in CQRS).

### Rationale

- `username` is profile data (PII), not a credential like password
- `identities` table is intentionally minimal — auth method, is_active, token_version
- Telegram users already have `customers.username` populated via events
- Both account types (CUSTOMER and STAFF) need username support

### Cross-Module JOIN Justification

`IdentityRepository.get_by_login()` will JOIN `identities` with `customers` and `staff_members` tables using **raw SQL text()** — not ORM model imports. This is a read-path query, which is an acceptable cross-context boundary in CQRS. The Identity repository does NOT import User module ORM models. This pattern already exists in the codebase: `list_customers.py` and `get_customer_detail.py` in the Identity module already JOIN across `identities`, `local_credentials`, and `customers` via raw SQL.

## Architecture

```
Identity module (login)          User module (profile)
local_credentials                customers
  email (UNIQUE)                   username (UNIQUE) <- source of truth
  password_hash                    first_name, last_name
                                 staff_members
get_by_login("john")               username (UNIQUE) <- adding
  @ in login -> email lookup       first_name, last_name
  no @ -> raw SQL JOIN
```

## Changes

### Remove

- `local_credentials.username` column, ORM field, entity field. Specifically:
  - `LocalCredentialsModel.username` mapped column in `infrastructure/models.py`
  - `LocalCredentials.username` field in `domain/entities.py`
  - `orm.username` mapping in `IdentityRepository._credentials_to_domain()`
  - `credentials.username` in `IdentityRepository.add_credentials()`
  - Old ORM-based username lookup in `IdentityRepository.get_by_login()` — replaced entirely by raw SQL JOIN
- Migration `2026_03_23_add_username_to_local_credentials.py`

### Keep (already added, still needed)

- `RegisterRequest.username` — API still accepts username at registration
- `RegisterCommand.username` — command still carries username to handler
- `LoginRequest.login` — unified login field (email or username)
- `LoginCommand.login` — command carries login identifier

### Add

- `staff_members.username` — `String(64)`, nullable, UNIQUE
- `StaffMember.username` in domain entity and ORM model
- `StaffMember.create_from_invitation()` — add `username: str | None = None` parameter
- `_STAFF_UPDATABLE_FIELDS` — add `"username"` to the frozenset
- `IdentityRegisteredEvent.username: str | None = None` — new optional field
- `IUsernameUniquenessChecker` — domain service interface in User module
- `UsernameUniquenessChecker` — application-level implementation that queries both `customers` and `staff_members`

### Rewrite

- `IIdentityRepository.get_by_login()` — raw SQL JOIN with `customers` and `staff_members`
- `IdentityRepository.get_by_login()` — implementation using `sqlalchemy.text()`
- `RegisterHandler` — pass `command.username` into `IdentityRegisteredEvent`
- `create_admin.py` — add `INSERT INTO staff_members` with username (currently only creates `identities`, `local_credentials`, `identity_roles`)
- Event consumer `create_profile_on_identity_registered` — add `username: str | None = None` parameter, pass to `Customer.create_from_identity()`

### Unchanged

- Telegram login flow (username already written to `customers` via `on_linked_account_created`)
- OIDC login flow
- Health check, RBAC, sessions, token management

## Login Flow

```
POST /auth/login { "login": "john", "password": "..." }

1. Does login contain '@'?
   YES -> SELECT ... FROM local_credentials WHERE email = :login
   NO  -> SELECT ... FROM local_credentials lc
            JOIN identities i ON i.id = lc.identity_id
            LEFT JOIN customers c ON c.id = i.id
            LEFT JOIN staff_members s ON s.id = i.id
            WHERE LOWER(c.username) = LOWER(:login)
               OR LOWER(s.username) = LOWER(:login)
2. Verify password against local_credentials.password_hash
3. Continue normal login flow (session, tokens, RBAC)
```

Note: username login only works for identities that have `local_credentials` (LOCAL auth method). Telegram-only users cannot login by username through this endpoint — they use the Telegram auth flow.

### Edge Cases

- `john@` (trailing @) — treated as email lookup, fails with InvalidCredentialsError (same as any wrong email). No special handling needed.
- Case sensitivity — username lookup is **case-insensitive** via `LOWER()` in SQL. UNIQUE constraint enforced via `UNIQUE(LOWER(username))` functional index. Telegram usernames are also case-insensitive.
- Username contains only dots/dashes (e.g. `...`) — rejected by min_length=3 and regex pattern.

## Username Validation

- Regex: `^[a-zA-Z0-9_.-]+$` (no `@` allowed — prevents ambiguity with email)
- Length: 3-64 characters
- Column size: `String(64)` on both `customers` and `staff_members` (align `customers.username` from current `String(100)` to `String(64)`)
- Storage: case-preserving (store as-is), lookup: case-insensitive (via `LOWER()`)
- UNIQUE constraint per table via functional index: `CREATE UNIQUE INDEX ... ON customers (LOWER(username)) WHERE username IS NOT NULL`
- Cross-table uniqueness check at application level before insert/update via `IUsernameUniquenessChecker`
- Race condition on cross-table check is acceptable — low-frequency operation, user gets a clear error

### Username Uniqueness Service

```python
# Interface: src/modules/user/domain/interfaces.py
class IUsernameUniquenessChecker(ABC):
    async def is_available(self, username: str, exclude_identity_id: uuid.UUID | None = None) -> bool:
        """Check both customers and staff_members tables. Case-insensitive."""

# Implementation: src/modules/user/infrastructure/services/username_checker.py
# Uses raw SQL: SELECT 1 FROM customers WHERE LOWER(username) = LOWER(:u) AND id != :exclude
#          UNION SELECT 1 FROM staff_members WHERE LOWER(username) = LOWER(:u) AND id != :exclude
```

Called from:

- `create_profile_on_identity_registered` consumer (on registration)
- `on_linked_account_created` consumer (on Telegram signup)
- Customer profile update handler
- Staff profile update handler (future)

Error handling by context:

- **Synchronous API** (profile update): raise `ConflictError(message="Username already taken", error_code="USERNAME_TAKEN")`
- **Async event consumers** (registration, Telegram signup): log warning, create/update profile without username. The user can set username later via profile update. This prevents async event processing failures from blocking account creation.
- **DB constraint fallback**: if a race condition bypasses the application check, catch `IntegrityError` on the UNIQUE index, log warning, and proceed without username (same graceful degradation).

## Registration Flow with Username

```
POST /auth/register { "email": "...", "password": "...", "username": "john" }

1. RegisterHandler validates email uniqueness
2. Creates Identity + LocalCredentials (no username in local_credentials)
3. Emits IdentityRegisteredEvent(identity_id=..., email=..., username="john")
4. User module consumer receives event with username parameter
5. Consumer calls IUsernameUniquenessChecker.is_available("john")
6. Consumer creates Customer(username="john") if available
7. If username taken: log warning, create Customer without username (no failure)
```

Note: username uniqueness failure during async event processing should NOT fail the registration. The customer is created without username, and the user can set it later via profile update.

## create_admin.py Changes

Current script inserts into 3 tables: `identities`, `local_credentials`, `identity_roles`.
New script inserts into 4 tables: `identities`, `local_credentials`, `identity_roles`, **`staff_members`**.

```python
_INSERT_STAFF_MEMBER = text("""
    INSERT INTO staff_members (id, first_name, last_name, username, invited_by)
    VALUES (:id, 'Admin', '', :username, :id)
""")
```

The `--username` CLI argument writes to `staff_members.username`, not `local_credentials`.

## Migration

Single migration replacing `2026_03_23_add_username_to_local_credentials.py`:

1. Drop `username` from `local_credentials` (if column exists)
2. Alter `customers.username` from `String(100)` to `String(64)` (no existing data exceeds 32 chars — Telegram limit)
3. Deduplicate any existing `customers.username` values (SET username = NULL for duplicates, keeping the most recent)
4. Add case-insensitive UNIQUE index: `CREATE UNIQUE INDEX ix_customers_username_lower ON customers (LOWER(username)) WHERE username IS NOT NULL`
5. Add `staff_members.username` column: `String(64)`, nullable
6. Add case-insensitive UNIQUE index: `CREATE UNIQUE INDEX ix_staff_members_username_lower ON staff_members (LOWER(username)) WHERE username IS NOT NULL`

### Data Migration for Existing Duplicates

Before adding the UNIQUE index on `customers.username`, run:

```sql
UPDATE customers SET username = NULL
WHERE id NOT IN (
    SELECT DISTINCT ON (LOWER(username)) id
    FROM customers
    WHERE username IS NOT NULL
    ORDER BY LOWER(username), updated_at DESC
)
AND username IS NOT NULL;
```

This keeps the most recently updated row's username and NULLs the rest.
