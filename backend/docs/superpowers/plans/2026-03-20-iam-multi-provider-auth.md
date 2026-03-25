# IAM Multi-Provider Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify Telegram credentials into the generic LinkedAccount model, add token versioning for instant JWT invalidation, and implement OWASP/NIST dual session timeouts.

**Architecture:** The Identity aggregate root gains a `token_version` integer field included in JWT `tv` claim; the Session entity gains `last_active_at` + `idle_expires_at` for sliding idle timeout. `TelegramCredentials` (entity, model, repo, event) is fully deleted — Telegram becomes a row in `linked_accounts` with profile data in JSONB `provider_metadata`. All existing tests and E2E flows must continue to pass.

**Tech Stack:** Python 3.12, attrs dataclasses, SQLAlchemy 2.0 async, Alembic, FastAPI, Dishka DI, TaskIQ, pytest, PostgreSQL, Redis

**Spec:** `docs/superpowers/specs/2026-03-20-iam-multi-provider-auth-design.md`

---

## Scope Check

This is a single subsystem (IAM Identity module refactor). The spec's "Future" items (LinkProviderHandler, LoginOIDCHandler, UnlinkProviderHandler, WebAuthn) are explicitly out of scope — they are separate specs.

---

## File Structure

### Files to CREATE

| File                                                            | Responsibility                                |
| --------------------------------------------------------------- | --------------------------------------------- |
| `alembic/versions/2026/03/20_0002_iam_multi_provider.py`        | Migration A: extend schema, migrate data      |
| `alembic/versions/2026/03/20_0003_drop_telegram_credentials.py` | Migration B: drop old table (after deploy)    |
| `tests/unit/modules/identity/domain/test_session_timeouts.py`   | Session idle/absolute timeout + touch() tests |
| `tests/unit/modules/identity/domain/test_token_version.py`      | Identity.bump_token_version() tests           |

### Files to MODIFY

| File                                                                            | What Changes                                                                                                                                                                                           |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/modules/identity/domain/value_objects.py`                                  | Rename `IdentityType` → `PrimaryAuthMethod`; add `AuthProvider`, `TRUSTED_EMAIL_PROVIDERS`; keep `IdentityType = PrimaryAuthMethod` alias                                                              |
| `src/modules/identity/domain/entities.py`                                       | Identity: add `token_version` + `bump_token_version()`; Session: add idle timeout fields + `touch()`; LinkedAccount: expand fields + `update_metadata()`; delete `TelegramCredentials`                 |
| `src/modules/identity/domain/events.py`                                         | Delete `TelegramIdentityCreatedEvent`; add `LinkedAccountCreatedEvent`, `LinkedAccountRemovedEvent`, `IdentityTokenVersionBumpedEvent`                                                                 |
| `src/modules/identity/domain/interfaces.py`                                     | Delete `ITelegramCredentialsRepository`; expand `ILinkedAccountRepository` (6 new methods)                                                                                                             |
| `src/modules/identity/infrastructure/models.py`                                 | IdentityModel: add `token_version`, rename `type`→`primary_auth_method`; SessionModel: add idle timeout columns; LinkedAccountModel: add new columns; delete `TelegramCredentialsModel` + relationship |
| `src/modules/identity/infrastructure/repositories/linked_account_repository.py` | Implement expanded interface; update `_to_domain`/`add` for new fields; change `get_by_provider` return                                                                                                |
| `src/modules/identity/infrastructure/repositories/identity_repository.py`       | Update `_identity_to_domain`: `orm.type` → `orm.primary_auth_method`; `IdentityType` → `PrimaryAuthMethod`; `identity.type` → `identity.primary_auth_method`; add `token_version` field mapping        |
| `src/modules/identity/infrastructure/repositories/session_repository.py`        | Update `_to_domain` + `add()`: map `last_active_at`, `idle_expires_at` new Session fields                                                                                                              |
| `src/modules/identity/infrastructure/provider.py`                               | Remove `ITelegramCredentialsRepository` binding; rewire `login_telegram_handler`; add session timeout config params                                                                                    |
| `src/modules/identity/application/commands/login_telegram.py`                   | Replace `ITelegramCredentialsRepository` → `ILinkedAccountRepository`; emit `LinkedAccountCreatedEvent`; pass idle timeout config                                                                      |
| `src/modules/identity/application/commands/login.py`                            | Include `tv` claim; pass `idle_timeout_minutes` to `Session.create()`                                                                                                                                  |
| `src/modules/identity/application/commands/login_oidc.py`                       | Update `IdentityType.OIDC` → `PrimaryAuthMethod.OIDC`                                                                                                                                                  |
| `src/modules/identity/application/commands/register.py`                         | Rename `IdentityType.LOCAL` → `PrimaryAuthMethod.LOCAL`                                                                                                                                                |
| `src/modules/identity/application/commands/refresh_token.py`                    | Add `session.touch()`; include `tv` claim in new JWT; persist session updates                                                                                                                          |
| `src/modules/identity/application/commands/assign_role.py`                      | Call `identity.bump_token_version()` after role assignment                                                                                                                                             |
| `src/modules/identity/application/commands/revoke_role.py`                      | Call `identity.bump_token_version()` after role revocation                                                                                                                                             |
| `src/modules/identity/application/commands/logout_all.py`                       | Add `IIdentityRepository` dep; call `identity.bump_token_version()`                                                                                                                                    |
| `src/modules/identity/presentation/dependencies.py`                             | Add token version validation in `get_auth_context()` (Option A: DB check per request)                                                                                                                  |
| `src/modules/identity/presentation/schemas.py`                                  | Add `auth_methods: list[str]` and `username: str \| None` to `CustomerListItemResponse` and `CustomerDetailResponse`                                                                                   |
| `src/modules/identity/application/queries/list_customers.py`                    | Add batch query for `linked_accounts`; add `auth_methods` + `username` to CustomerListItem                                                                                                             |
| `src/modules/identity/application/queries/get_customer_detail.py`               | Add `auth_methods` + `username` to CustomerDetail                                                                                                                                                      |
| `src/modules/identity/presentation/router_customers.py`                         | Pass `auth_methods`, `username` through to response schemas                                                                                                                                            |
| `src/infrastructure/database/registry.py`                                       | Remove `TelegramCredentialsModel` import and `__all__` entry                                                                                                                                           |
| `src/bootstrap/config.py`                                                       | Add 4 new settings: `SESSION_IDLE_TIMEOUT_MINUTES`, `SESSION_ABSOLUTE_LIFETIME_HOURS`, `TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES`, `TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS`                             |
| `src/modules/user/domain/entities.py`                                           | Customer: add `username` field; update `create_from_identity()`; add to `_CUSTOMER_UPDATABLE_FIELDS`                                                                                                   |
| `src/modules/user/infrastructure/models.py`                                     | CustomerModel: add `username` column                                                                                                                                                                   |
| `src/modules/user/application/consumers/identity_events.py`                     | Delete `create_customer_on_telegram_identity_created`; add `on_linked_account_created`                                                                                                                 |
| `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py` | **DELETE FILE**                                                                                                                                                                                        |
| `tests/factories/identity_mothers.py`                                           | Update `LinkedAccountMothers` for new fields; update `IdentityType` → `PrimaryAuthMethod`; add `IdentityMothers.active_telegram()`                                                                     |
| `tests/unit/modules/identity/domain/test_telegram.py`                           | Delete `TestTelegramCredentials`, `TestTelegramIdentityCreatedEvent`; add `TestLinkedAccount`, `TestLinkedAccountCreatedEvent`                                                                         |
| `tests/unit/modules/user/domain/test_customer.py`                               | Add `username` field tests                                                                                                                                                                             |
| `tests/e2e/api/v1/test_auth_telegram.py`                                        | Update SQL queries: `telegram_credentials` → `linked_accounts WHERE provider = 'telegram'`                                                                                                             |

### Files with `IdentityType` imports (backward-compat alias handles these — update opportunistically)

These files import `IdentityType` which continues to work via the `IdentityType = PrimaryAuthMethod` alias. No urgent changes needed, but should be updated to `PrimaryAuthMethod` when touched for other reasons:

- `tests/unit/modules/identity/domain/test_value_objects.py`
- `tests/unit/modules/identity/domain/test_entities.py`
- `tests/unit/modules/identity/application/commands/test_commands.py`
- `tests/unit/modules/identity/application/commands/test_admin_commands.py`
- `tests/integration/modules/identity/infrastructure/repositories/test_*.py` (6 files)
- `tests/integration/modules/user/infrastructure/repositories/test_user_repo.py`
- `tests/integration/modules/user/application/commands/test_create_user.py`

---

## Important: Migration Ordering

The Alembic migration (Task 24) creates DB columns referenced by code changes in Tasks 1-23. During development:

- **Unit tests** (domain layer, no DB) work immediately after code changes
- **Integration/E2E tests** require running `alembic upgrade head` first (Task 24)
- **Recommended workflow:** Apply Migration A (Task 24) to dev/test DB early, then work through code tasks 1-23. The migration is safe to run before code deployment because all new columns have defaults.

---

## Task Breakdown

### Task 1: Domain Value Objects — Rename IdentityType → PrimaryAuthMethod + New Enums

**Files:**

- Modify: `src/modules/identity/domain/value_objects.py:11-22`

- [ ] **Step 1: Write the failing test**

In `tests/unit/modules/identity/domain/test_telegram.py`, the existing `TestIdentityTypeTelegram` (line 13) tests `IdentityType.TELEGRAM`. We'll update these tests first to use `PrimaryAuthMethod`.

```python
# tests/unit/modules/identity/domain/test_telegram.py — replace TestIdentityTypeTelegram
from src.modules.identity.domain.value_objects import PrimaryAuthMethod, AuthProvider, TRUSTED_EMAIL_PROVIDERS

class TestPrimaryAuthMethod:
    def test_telegram_value(self):
        assert PrimaryAuthMethod.TELEGRAM == "TELEGRAM"
        assert PrimaryAuthMethod.TELEGRAM.value == "TELEGRAM"

    def test_all_methods(self):
        assert set(PrimaryAuthMethod) == {PrimaryAuthMethod.LOCAL, PrimaryAuthMethod.OIDC, PrimaryAuthMethod.TELEGRAM}

class TestAuthProvider:
    def test_values(self):
        assert AuthProvider.TELEGRAM == "telegram"
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.APPLE == "apple"

    def test_trusted_email_providers(self):
        assert AuthProvider.GOOGLE in TRUSTED_EMAIL_PROVIDERS
        assert AuthProvider.APPLE in TRUSTED_EMAIL_PROVIDERS
        assert AuthProvider.TELEGRAM not in TRUSTED_EMAIL_PROVIDERS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modules/identity/domain/test_telegram.py::TestPrimaryAuthMethod -v`
Expected: FAIL — `PrimaryAuthMethod` not found in imports

- [ ] **Step 3: Implement value_objects.py changes**

In `src/modules/identity/domain/value_objects.py`:

1. Rename class `IdentityType` → `PrimaryAuthMethod` (keep same values: LOCAL, OIDC, TELEGRAM)
2. Add backward-compat alias: `IdentityType = PrimaryAuthMethod`
3. Add `AuthProvider` enum and `TRUSTED_EMAIL_PROVIDERS` frozenset:

```python
class PrimaryAuthMethod(enum.StrEnum):
    """Authentication method used by an identity."""
    LOCAL = "LOCAL"
    OIDC = "OIDC"
    TELEGRAM = "TELEGRAM"

# Backward compatibility alias (remove after full migration)
IdentityType = PrimaryAuthMethod

class AuthProvider(enum.StrEnum):
    """External authentication provider identifiers."""
    TELEGRAM = "telegram"
    GOOGLE = "google"
    APPLE = "apple"

TRUSTED_EMAIL_PROVIDERS: frozenset[str] = frozenset({
    AuthProvider.GOOGLE,
    AuthProvider.APPLE,
})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/modules/identity/domain/test_telegram.py::TestPrimaryAuthMethod tests/unit/modules/identity/domain/test_telegram.py::TestAuthProvider -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/value_objects.py tests/unit/modules/identity/domain/test_telegram.py
git commit -m "refactor(identity): rename IdentityType → PrimaryAuthMethod, add AuthProvider enum"
```

---

### Task 2: Domain — Identity token_version + bump_token_version()

**Files:**

- Modify: `src/modules/identity/domain/entities.py:37-60` (Identity class)
- Create: `tests/unit/modules/identity/domain/test_token_version.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/modules/identity/domain/test_token_version.py
from src.modules.identity.domain.value_objects import PrimaryAuthMethod
from src.modules.identity.domain.entities import Identity


class TestTokenVersion:
    def test_default_token_version_is_one(self):
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        assert identity.token_version == 1

    def test_bump_increments_version(self):
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        old_updated = identity.updated_at
        identity.bump_token_version()
        assert identity.token_version == 2
        assert identity.updated_at >= old_updated

    def test_multiple_bumps(self):
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        identity.bump_token_version()
        identity.bump_token_version()
        identity.bump_token_version()
        assert identity.token_version == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modules/identity/domain/test_token_version.py -v`
Expected: FAIL — `Identity` has no attribute `token_version`

- [ ] **Step 3: Add token_version to Identity**

In `src/modules/identity/domain/entities.py`, modify the `Identity` class:

1. Add field after `deactivated_by` (line 60): `token_version: int = 1`
2. Add method after `ensure_active()` (after line 151):

```python
    def bump_token_version(self) -> None:
        """Increment token version to invalidate all outstanding JWTs."""
        self.token_version += 1
        self.updated_at = datetime.now(UTC)
```

3. Update `register()` factory (line 78) to include `token_version=1` in the constructor call.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/modules/identity/domain/test_token_version.py -v`
Expected: PASS

- [ ] **Step 5: Run existing identity tests to check no regressions**

Run: `pytest tests/unit/modules/identity/domain/ -v`
Expected: All PASS (existing tests don't reference `token_version`)

- [ ] **Step 6: Commit**

```bash
git add src/modules/identity/domain/entities.py tests/unit/modules/identity/domain/test_token_version.py
git commit -m "feat(identity): add token_version field for instant JWT invalidation"
```

---

### Task 3: Domain — Session idle timeout (last_active_at, idle_expires_at, touch)

**Files:**

- Modify: `src/modules/identity/domain/entities.py:173-291` (Session class)
- Create: `tests/unit/modules/identity/domain/test_session_timeouts.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/modules/identity/domain/test_session_timeouts.py
import uuid
from datetime import UTC, datetime, timedelta

from src.modules.identity.domain.entities import Session
from src.modules.identity.domain.exceptions import SessionExpiredError


class TestSessionIdleTimeout:
    def test_create_sets_idle_expires_at(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=30,
        )
        # idle_expires_at should be ~30 min from now
        assert session.idle_expires_at > session.created_at
        assert session.idle_expires_at <= session.created_at + timedelta(minutes=31)
        assert session.last_active_at == session.created_at

    def test_touch_extends_idle_timeout(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=15,
        )
        old_idle = session.idle_expires_at
        session.touch(idle_timeout_minutes=15)
        assert session.idle_expires_at >= old_idle
        assert session.last_active_at >= session.created_at

    def test_ensure_valid_raises_on_idle_expiry(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=30,
        )
        # Force idle expiry in the past
        session.idle_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        try:
            session.ensure_valid()
            assert False, "Should have raised SessionExpiredError"
        except SessionExpiredError:
            pass

    def test_ensure_valid_passes_when_both_valid(self):
        session = Session.create(
            identity_id=uuid.uuid4(),
            refresh_token="test-token",
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            role_ids=[],
            expires_days=30,
            idle_timeout_minutes=30,
        )
        # Should not raise
        session.ensure_valid()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modules/identity/domain/test_session_timeouts.py -v`
Expected: FAIL — `Session.create()` doesn't accept `idle_timeout_minutes`

- [ ] **Step 3: Add idle timeout fields to Session**

In `src/modules/identity/domain/entities.py`, modify the `Session` class:

1. Add fields after `activated_roles` (line 201):

```python
    last_active_at: datetime
    idle_expires_at: datetime
```

2. Update `create()` factory (lines 203-238) — add `idle_timeout_minutes: int = 30` param, set both fields:

```python
    @classmethod
    def create(
        cls,
        identity_id: uuid.UUID,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        role_ids: list[uuid.UUID],
        expires_days: int = 30,
        idle_timeout_minutes: int = 30,
    ) -> Session:
        now = datetime.now(UTC)
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            identity_id=identity_id,
            refresh_token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            is_revoked=False,
            created_at=now,
            expires_at=now + timedelta(days=expires_days),
            activated_roles=tuple(role_ids),
            last_active_at=now,
            idle_expires_at=now + timedelta(minutes=idle_timeout_minutes),
        )
```

3. Add `touch()` method after `ensure_valid()`:

```python
    def touch(self, idle_timeout_minutes: int) -> None:
        """Extend idle timeout on activity (refresh token use)."""
        now = datetime.now(UTC)
        self.last_active_at = now
        self.idle_expires_at = now + timedelta(minutes=idle_timeout_minutes)
```

4. Update `ensure_valid()` to also check `idle_expires_at`:

```python
    def ensure_valid(self) -> None:
        if self.is_expired():
            raise SessionExpiredError()
        if datetime.now(UTC) >= self.idle_expires_at:
            raise SessionExpiredError()
        if self.is_revoked:
            raise SessionRevokedError()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/modules/identity/domain/test_session_timeouts.py -v`
Expected: PASS

- [ ] **Step 5: Fix existing Session tests that call Session.create() without idle fields**

The `tests/factories/identity_mothers.py` `SessionMothers` and `IdentityMothers.with_session()` both call `Session.create()` — the new `idle_timeout_minutes` parameter has a default, so they should still work. Verify:

Run: `pytest tests/unit/modules/identity/domain/ tests/factories/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/modules/identity/domain/entities.py tests/unit/modules/identity/domain/test_session_timeouts.py
git commit -m "feat(identity): add Session idle/absolute dual timeout model (OWASP/NIST)"
```

---

### Task 4: Domain — Expand LinkedAccount entity + delete TelegramCredentials

**Files:**

- Modify: `src/modules/identity/domain/entities.py:332-389` (LinkedAccount + TelegramCredentials)

- [ ] **Step 1: Write test for expanded LinkedAccount**

Update `tests/unit/modules/identity/domain/test_telegram.py` — delete `TestTelegramCredentials` class (lines 81-160) and add:

```python
from datetime import UTC, datetime
from src.modules.identity.domain.entities import LinkedAccount

class TestLinkedAccount:
    def test_update_metadata_returns_true_on_change(self):
        now = datetime.now(UTC)
        account = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            provider="telegram",
            provider_sub_id="123456",
            provider_email=None,
            email_verified=False,
            provider_metadata={"username": "old"},
            created_at=now,
            updated_at=now,
        )
        old_updated = account.updated_at
        changed = account.update_metadata({"username": "new"})
        assert changed is True
        assert account.provider_metadata == {"username": "new"}
        assert account.updated_at >= old_updated

    def test_update_metadata_returns_false_no_change(self):
        now = datetime.now(UTC)
        meta = {"username": "same"}
        account = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            provider="telegram",
            provider_sub_id="123456",
            provider_email=None,
            email_verified=False,
            provider_metadata=meta,
            created_at=now,
            updated_at=now,
        )
        old_updated = account.updated_at
        changed = account.update_metadata({"username": "same"})
        assert changed is False
        assert account.updated_at == old_updated
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modules/identity/domain/test_telegram.py::TestLinkedAccount -v`
Expected: FAIL — `LinkedAccount` doesn't accept `email_verified`, `provider_metadata`, etc.

- [ ] **Step 3: Expand LinkedAccount, delete TelegramCredentials**

In `src/modules/identity/domain/entities.py`:

1. **Expand LinkedAccount** (lines 332-349) to:

```python
@dataclass
class LinkedAccount:
    """External provider account linked to an Identity."""
    id: uuid.UUID
    identity_id: uuid.UUID
    provider: str
    provider_sub_id: str
    provider_email: str | None
    email_verified: bool
    provider_metadata: dict
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

2. **Delete entire `TelegramCredentials` class** (lines 351-389)

3. **Remove imports**: Remove `TelegramIdentityCreatedEvent` from the imports at line 12 (will be deleted in Task 5). Remove `TelegramUserData` from imports at line 33 (no longer needed by this file after TelegramCredentials removal).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/modules/identity/domain/test_telegram.py::TestLinkedAccount -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/entities.py tests/unit/modules/identity/domain/test_telegram.py
git commit -m "feat(identity): expand LinkedAccount fields, delete TelegramCredentials entity"
```

---

### Task 5: Domain Events — Replace TelegramIdentityCreatedEvent with LinkedAccount events

**Files:**

- Modify: `src/modules/identity/domain/events.py:165-184`

- [ ] **Step 1: Write test for new events**

Replace `TestTelegramIdentityCreatedEvent` in `tests/unit/modules/identity/domain/test_telegram.py`:

```python
from src.modules.identity.domain.events import (
    LinkedAccountCreatedEvent,
    LinkedAccountRemovedEvent,
    IdentityTokenVersionBumpedEvent,
)

class TestLinkedAccountCreatedEvent:
    def test_creation(self):
        identity_id = uuid.uuid4()
        event = LinkedAccountCreatedEvent(
            identity_id=identity_id,
            provider="telegram",
            provider_sub_id="123456",
            provider_metadata={"username": "test"},
            start_param="ref123",
            is_new_identity=True,
            aggregate_id=str(identity_id),
        )
        assert event.provider == "telegram"
        assert event.is_new_identity is True
        assert event.event_type == "linked_account_created"

    def test_requires_identity_id(self):
        import pytest
        with pytest.raises(ValueError):
            LinkedAccountCreatedEvent(
                identity_id=None,
                provider="telegram",
                provider_sub_id="123",
                provider_metadata={},
                start_param=None,
                is_new_identity=True,
            )

class TestLinkedAccountRemovedEvent:
    def test_creation(self):
        identity_id = uuid.uuid4()
        event = LinkedAccountRemovedEvent(
            identity_id=identity_id,
            provider="telegram",
            provider_sub_id="123456",
            aggregate_id=str(identity_id),
        )
        assert event.event_type == "linked_account_removed"

class TestIdentityTokenVersionBumpedEvent:
    def test_creation(self):
        identity_id = uuid.uuid4()
        event = IdentityTokenVersionBumpedEvent(
            identity_id=identity_id,
            new_version=2,
            reason="password_change",
            aggregate_id=str(identity_id),
        )
        assert event.new_version == 2
        assert event.reason == "password_change"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modules/identity/domain/test_telegram.py::TestLinkedAccountCreatedEvent -v`
Expected: FAIL — `LinkedAccountCreatedEvent` not importable

- [ ] **Step 3: Replace events in events.py**

In `src/modules/identity/domain/events.py`:

1. **Delete** `TelegramIdentityCreatedEvent` class (lines 165-184)
2. **Add** three new event classes at the end of the file:

```python
@dataclass
class LinkedAccountCreatedEvent(DomainEvent):
    """Emitted when a new provider is linked to an Identity."""
    identity_id: uuid.UUID | None = None
    provider: str = ""
    provider_sub_id: str = ""
    provider_metadata: dict | None = None
    start_param: str | None = None
    is_new_identity: bool = False
    aggregate_type: str = "Identity"
    event_type: str = "linked_account_created"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
        if self.provider_metadata is None:
            self.provider_metadata = {}


@dataclass
class LinkedAccountRemovedEvent(DomainEvent):
    """Emitted when a provider is unlinked from an Identity."""
    identity_id: uuid.UUID | None = None
    provider: str = ""
    provider_sub_id: str = ""
    aggregate_type: str = "Identity"
    event_type: str = "linked_account_removed"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)


@dataclass
class IdentityTokenVersionBumpedEvent(DomainEvent):
    """Emitted when token_version is incremented (all JWTs invalidated)."""
    identity_id: uuid.UUID | None = None
    new_version: int = 0
    reason: str = ""
    aggregate_type: str = "Identity"
    event_type: str = "token_version_bumped"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/modules/identity/domain/test_telegram.py::TestLinkedAccountCreatedEvent tests/unit/modules/identity/domain/test_telegram.py::TestLinkedAccountRemovedEvent tests/unit/modules/identity/domain/test_telegram.py::TestIdentityTokenVersionBumpedEvent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/events.py tests/unit/modules/identity/domain/test_telegram.py
git commit -m "feat(identity): replace TelegramIdentityCreatedEvent with LinkedAccount domain events"
```

---

### Task 6: Domain Interfaces — Expand ILinkedAccountRepository, delete ITelegramCredentialsRepository

**Files:**

- Modify: `src/modules/identity/domain/interfaces.py:437-493`

- [ ] **Step 1: Expand ILinkedAccountRepository**

In `src/modules/identity/domain/interfaces.py`:

1. Change `get_by_provider()` return type (line 457) from `LinkedAccount | None` to `tuple[Identity, LinkedAccount] | None`
2. Add 5 new abstract methods to `ILinkedAccountRepository`:

```python
    @abstractmethod
    async def update(self, account: LinkedAccount) -> None: ...

    @abstractmethod
    async def get_by_identity_and_provider(self, identity_id: uuid.UUID, provider: str) -> LinkedAccount | None: ...

    @abstractmethod
    async def find_by_verified_email(self, email: str) -> tuple[Identity, LinkedAccount] | None: ...

    @abstractmethod
    async def count_for_identity(self, identity_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def delete(self, account_id: uuid.UUID) -> None: ...
```

3. **Delete** `ITelegramCredentialsRepository` class (lines 482-493)

4. Remove `TelegramCredentials` from the imports at the top of the file (it was imported for the type hint in `ITelegramCredentialsRepository`)

- [ ] **Step 2: Verify no import errors**

Run: `python -c "from src.modules.identity.domain.interfaces import ILinkedAccountRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/modules/identity/domain/interfaces.py
git commit -m "refactor(identity): expand ILinkedAccountRepository, delete ITelegramCredentialsRepository"
```

---

### Task 7: Infrastructure — Update IdentityRepository (column rename + token_version mapping)

**Files:**

- Modify: `src/modules/identity/infrastructure/repositories/identity_repository.py:28-46,65-82`

- [ ] **Step 1: Update \_identity_to_domain mapper**

At line 39, change `type=IdentityType(orm.type)` → `type=PrimaryAuthMethod(orm.primary_auth_method)`.
At line 45, after `deactivated_by=orm.deactivated_by`, add: `token_version=orm.token_version,`.

Update import: `IdentityType` → `PrimaryAuthMethod`.

- [ ] **Step 2: Update add() method**

At line 76, change `type=identity.type.value` → `primary_auth_method=identity.type.value`.
At line 79, after `is_active=identity.is_active`, add: `token_version=identity.token_version,`.

- [ ] **Step 3: Check for update() method**

If there's an `update()` method that writes `orm.type`, update it to `orm.primary_auth_method`. Also ensure `orm.token_version = identity.token_version` is set.

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/infrastructure/repositories/identity_repository.py
git commit -m "refactor(identity): update IdentityRepository for column rename + token_version"
```

---

### Task 8: Infrastructure — Update SessionRepository (idle timeout field mapping)

**Files:**

- Modify: `src/modules/identity/infrastructure/repositories/session_repository.py:27-69`

- [ ] **Step 1: Update \_to_domain mapper**

At line 46, after `activated_roles=role_ids`, add:

```python
            last_active_at=orm.last_active_at,
            idle_expires_at=orm.idle_expires_at,
```

- [ ] **Step 2: Update add() method**

At line 65, after `expires_at=session.expires_at`, add:

```python
            last_active_at=session.last_active_at,
            idle_expires_at=session.idle_expires_at,
```

- [ ] **Step 3: Check update() method**

Ensure the `update()` method persists `last_active_at` and `idle_expires_at` when `session.touch()` is called. If the update method copies individual fields, add these.

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/infrastructure/repositories/session_repository.py
git commit -m "feat(identity): map Session idle timeout fields in SessionRepository"
```

---

### Task 9: Infrastructure — Update ORM models (IdentityModel, SessionModel, LinkedAccountModel, delete TelegramCredentialsModel)

**Files:**

- Modify: `src/modules/identity/infrastructure/models.py`

- [ ] **Step 1: Add token_version to IdentityModel**

In `src/modules/identity/infrastructure/models.py`:

After `deactivated_by` (line 83), add:

```python
    token_version: Mapped[int] = mapped_column(
        Integer,
        server_default=text("1"),
        nullable=False,
        comment="Incrementing version for instant JWT invalidation",
    )
```

Add `Integer` to the imports from sqlalchemy (line 11).

- [ ] **Step 2: Rename IdentityModel.type → primary_auth_method**

Change line 43-47:

```python
    primary_auth_method: Mapped[str] = mapped_column(
        Enum(PrimaryAuthMethod, native_enum=False, length=10),
        nullable=False,
        comment="Authentication method: LOCAL, OIDC, or TELEGRAM",
    )
```

Update import at line 28: `from src.modules.identity.domain.value_objects import PrimaryAuthMethod`

- [ ] **Step 3: Add idle timeout columns to SessionModel**

In `SessionModel` (after `expires_at` at line 440), add:

```python
    last_active_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Last token refresh timestamp",
    )
    idle_expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="Sliding idle timeout (extends on refresh)",
    )
```

- [ ] **Step 4: Expand LinkedAccountModel**

In `LinkedAccountModel` (after `provider_email` at line 167), add:

```python
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
        comment="Whether provider verified this email",
    )
    provider_metadata: Mapped[dict] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
        comment="Provider-specific profile data",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Add `JSONB` to the postgresql dialect imports: `from sqlalchemy.dialects.postgresql import INET, JSONB, UUID`

- [ ] **Step 5: Delete TelegramCredentialsModel**

Delete the entire `TelegramCredentialsModel` class (lines 172-241).

Delete the `telegram_credentials` relationship from `IdentityModel` (lines 98-102):

```python
    telegram_credentials: Mapped[TelegramCredentialsModel | None] = relationship(
        back_populates="identity",
        uselist=False,
        cascade="all, delete-orphan",
    )
```

- [ ] **Step 6: Verify module imports**

Run: `python -c "from src.modules.identity.infrastructure.models import IdentityModel, SessionModel, LinkedAccountModel; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Update database registry**

In `src/infrastructure/database/registry.py`:

- Remove `TelegramCredentialsModel` from the import (line 33)
- Remove `"TelegramCredentialsModel"` from `__all__` (line 62)

- [ ] **Step 8: Verify imports**

Run: `python -c "from src.modules.identity.infrastructure.models import IdentityModel, SessionModel, LinkedAccountModel; print('OK')"`
Expected: `OK`

Run: `python -c "from src.infrastructure.database.registry import Base; print('OK')"`
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add src/modules/identity/infrastructure/models.py src/infrastructure/database/registry.py
git commit -m "refactor(identity): update ORM models — token_version, idle timeout, expand LinkedAccount, delete TelegramCredentialsModel"
```

---

### Task 10: Infrastructure — Update LinkedAccountRepository

**Files:**

- Modify: `src/modules/identity/infrastructure/repositories/linked_account_repository.py`

- [ ] **Step 1: Update `_to_domain()` and `add()` for new fields**

Update `_to_domain()` to map all new fields. Update `add()` to persist them.

- [ ] **Step 2: Change `get_by_provider()` to return `tuple[Identity, LinkedAccount] | None`**

Join with `IdentityModel` and return both. Import `IdentityModel` and add `_to_identity_domain()` helper (similar to how `telegram_credentials_repo.py` does it).

- [ ] **Step 3: Implement new methods**

```python
    async def update(self, account: LinkedAccount) -> None:
        stmt = select(LinkedAccountModel).where(LinkedAccountModel.id == account.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        orm.provider_email = account.provider_email
        orm.email_verified = account.email_verified
        orm.provider_metadata = account.provider_metadata
        orm.updated_at = account.updated_at
        await self._session.flush()

    async def get_by_identity_and_provider(
        self, identity_id: uuid.UUID, provider: str,
    ) -> LinkedAccount | None:
        stmt = select(LinkedAccountModel).where(
            LinkedAccountModel.identity_id == identity_id,
            LinkedAccountModel.provider == provider,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_verified_email(self, email: str) -> tuple[Identity, LinkedAccount] | None:
        stmt = (
            select(LinkedAccountModel, IdentityModel)
            .join(IdentityModel, LinkedAccountModel.identity_id == IdentityModel.id)
            .where(
                LinkedAccountModel.provider_email == email,
                LinkedAccountModel.email_verified == True,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return self._to_identity_domain(row[1]), self._to_domain(row[0])

    async def count_for_identity(self, identity_id: uuid.UUID) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(LinkedAccountModel).where(
            LinkedAccountModel.identity_id == identity_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete(self, account_id: uuid.UUID) -> None:
        from sqlalchemy import delete
        stmt = delete(LinkedAccountModel).where(LinkedAccountModel.id == account_id)
        await self._session.execute(stmt)
        await self._session.flush()
```

- [ ] **Step 4: Delete telegram_credentials_repo.py**

Delete file: `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py`

- [ ] **Step 5: Verify imports**

Run: `python -c "from src.modules.identity.infrastructure.repositories.linked_account_repository import LinkedAccountRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/modules/identity/infrastructure/repositories/linked_account_repository.py
git rm src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py
git commit -m "refactor(identity): expand LinkedAccountRepository, delete TelegramCredentialsRepository"
```

---

### Task 11: Config — Add session timeout settings

**Files:**

- Modify: `src/bootstrap/config.py:60-63`

- [ ] **Step 1: Add new settings**

After `MAX_ACTIVE_SESSIONS_PER_IDENTITY` (line 63), add:

```python
    SESSION_IDLE_TIMEOUT_MINUTES: int = 30
    SESSION_ABSOLUTE_LIFETIME_HOURS: int = 24
    TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES: int = 1440
    TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS: int = 168
```

- [ ] **Step 2: Commit**

```bash
git add src/bootstrap/config.py
git commit -m "feat(config): add session idle/absolute timeout settings (OWASP/NIST)"
```

---

### Task 12: Infrastructure — Update DI provider.py

**Files:**

- Modify: `src/modules/identity/infrastructure/provider.py:140-178`

- [ ] **Step 1: Remove TelegramCredentialsRepository binding**

Delete lines 141-144 (the `telegram_creds_repo` provide).

Remove imports:

- `TelegramCredentialsRepository`
- `ITelegramCredentialsRepository`

- [ ] **Step 2: Rewire LoginTelegramHandler factory**

Change `login_telegram_handler` factory (lines 153-178):

- Remove `telegram_creds_repo: ITelegramCredentialsRepository` parameter
- Add `linked_account_repo: ILinkedAccountRepository` parameter
- Pass `linked_account_repo` instead of `telegram_creds_repo`
- Add `idle_timeout_minutes=settings.TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES`
- Change `refresh_token_days` calculation: `int(settings.TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS / 24)` or keep `settings.TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS`

- [ ] **Step 3: Update LoginHandler factory**

Add `idle_timeout_minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES` parameter.

- [ ] **Step 4: Update LogoutAllHandler factory**

LogoutAllHandler now needs `IIdentityRepository` — add it. Check if it's already auto-wired by Dishka. Since it's `provide(LogoutAllHandler, scope=Scope.REQUEST)`, Dishka auto-injects constructor params. We'll update the handler constructor in Task 14.

- [ ] **Step 5: Verify module loads**

Run: `python -c "from src.modules.identity.infrastructure.provider import IdentityProvider; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/modules/identity/infrastructure/provider.py
git commit -m "refactor(identity): rewire DI — remove TelegramCredentialsRepo, add session timeout config"
```

---

### Task 13: Application — Refactor LoginTelegramHandler

**Files:**

- Modify: `src/modules/identity/application/commands/login_telegram.py`

- [ ] **Step 1: Replace all Telegram credential references**

Full rewrite of `login_telegram.py`:

1. **Imports**: Replace `ITelegramCredentialsRepository` → `ILinkedAccountRepository`, `TelegramCredentials` → `LinkedAccount`, `TelegramIdentityCreatedEvent` → `LinkedAccountCreatedEvent`, `IdentityType` → `PrimaryAuthMethod`

2. **Constructor**: Replace `telegram_creds_repo` param with `linked_account_repo: ILinkedAccountRepository`. Add `idle_timeout_minutes: int = 1440`.

3. **handle()** method:
   - Lookup: `self._linked_account_repo.get_by_provider("telegram", str(telegram_user.telegram_id))`
   - Return type changes to `tuple[Identity, LinkedAccount] | None`
   - Existing user: call `linked_account.update_metadata(new_metadata)` + `self._linked_account_repo.update(linked_account)`
   - Session.create(): pass `idle_timeout_minutes=self._idle_timeout_minutes`
   - JWT payload: add `"tv": identity.token_version`

4. **\_provision_new_identity()** method:
   - Create `LinkedAccount` instead of `TelegramCredentials`
   - Build `provider_metadata` dict from `TelegramUserData` fields
   - Emit `LinkedAccountCreatedEvent` instead of `TelegramIdentityCreatedEvent`
   - Use `PrimaryAuthMethod.TELEGRAM` instead of `IdentityType.TELEGRAM`

- [ ] **Step 2: Run existing E2E tests**

Run: `pytest tests/e2e/api/v1/test_auth_telegram.py -v`
Expected: Some tests may fail if DB schema hasn't been updated yet — this is expected, we'll fix with migration later. The code should at least compile.

- [ ] **Step 3: Verify handler imports**

Run: `python -c "from src.modules.identity.application.commands.login_telegram import LoginTelegramHandler; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/application/commands/login_telegram.py
git commit -m "refactor(identity): LoginTelegramHandler uses LinkedAccount instead of TelegramCredentials"
```

---

### Task 14: Application — Update LoginHandler (tv claim + idle timeout)

**Files:**

- Modify: `src/modules/identity/application/commands/login.py:141-164`

- [ ] **Step 1: Add tv claim and idle timeout**

1. Add `idle_timeout_minutes: int = 30` to `LoginHandler.__init__()`
2. In `handle()`, change `Session.create()` call to pass `idle_timeout_minutes=self._idle_timeout_minutes`
3. In `handle()`, change JWT payload to include `"tv": identity.token_version`:

```python
            access_token = self._token_provider.create_access_token(
                payload_data={
                    "sub": str(identity.id),
                    "sid": str(session.id),
                    "tv": identity.token_version,
                },
            )
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/application/commands/login.py
git commit -m "feat(identity): add tv claim and idle timeout to LoginHandler"
```

---

### Task 15: Application — Update RefreshTokenHandler (touch + token version check)

**Files:**

- Modify: `src/modules/identity/application/commands/refresh_token.py:77-147`

- [ ] **Step 1: Add idle timeout and token version check**

1. Add `idle_timeout_minutes: int = 30` to `RefreshTokenHandler.__init__()`
2. After `identity.ensure_active()` (line 111), add token version check:

```python
            # Token version check — reject if JWT was issued before a security event
            # (Backward compat: tokens without tv claim get tv=1)
            # Note: We don't have the original JWT here, so we check on the session-level
            # Token version is enforced in get_auth_context dependency
```

3. After `session.ensure_valid()` (line 105), add `session.touch(self._idle_timeout_minutes)`
4. In JWT payload creation (line 122-127), add `"tv": identity.token_version`
5. The `session_repo.update(session)` at line 119 will now also persist `last_active_at` and `idle_expires_at`

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/application/commands/refresh_token.py
git commit -m "feat(identity): add session.touch() and tv claim to RefreshTokenHandler"
```

---

### Task 16: Application — Update AssignRole, RevokeRole, LogoutAll (bump token_version)

**Files:**

- Modify: `src/modules/identity/application/commands/assign_role.py:103-127`
- Modify: `src/modules/identity/application/commands/revoke_role.py:72-97`
- Modify: `src/modules/identity/application/commands/logout_all.py:42-64`

- [ ] **Step 1: AssignRoleHandler — bump token version**

After role assignment (line 108) and before emitting the event (line 118), add:

```python
            identity.bump_token_version()
```

The `identity` variable is already loaded at lines 77-82.

- [ ] **Step 2: RevokeRoleHandler — bump token version**

Need to load identity first. Add after line 72:

```python
            identity = await self._identity_repo.get(command.identity_id)
            if identity:
                identity.bump_token_version()
                await self._identity_repo.update(identity)
```

Add `IIdentityRepository` to constructor if not already there. Check the imports.

- [ ] **Step 3: LogoutAllHandler — bump token version**

Add `IIdentityRepository` to constructor and `__init__()`. After revoking sessions, bump:

```python
        async with self._uow:
            revoked_ids = await self._session_repo.revoke_all_for_identity(command.identity_id)
            identity = await self._identity_repo.get(command.identity_id)
            if identity:
                identity.bump_token_version()
                await self._identity_repo.update(identity)
            await self._uow.commit()
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/application/commands/assign_role.py src/modules/identity/application/commands/revoke_role.py src/modules/identity/application/commands/logout_all.py
git commit -m "feat(identity): bump token_version on role change and logout-all"
```

---

### Task 17: Application — Update RegisterHandler (PrimaryAuthMethod)

**Files:**

- Modify: `src/modules/identity/application/commands/register.py`

- [ ] **Step 1: Update import**

Change `from src.modules.identity.domain.value_objects import IdentityType` to `PrimaryAuthMethod`.

Update usage: `Identity.register(PrimaryAuthMethod.LOCAL)` → already works because of the `IdentityType = PrimaryAuthMethod` alias but we should use the new name.

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/application/commands/register.py
git commit -m "refactor(identity): use PrimaryAuthMethod in RegisterHandler"
```

---

### Task 18: Presentation — Token version validation in get_auth_context

**Files:**

- Modify: `src/modules/identity/presentation/dependencies.py:24-84`

- [ ] **Step 1: Add identity lookup and token version check**

Add `IIdentityRepository` to `get_auth_context()` parameters:

```python
@inject
async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_provider: FromDishka[ITokenProvider] = ...,
    identity_repo: FromDishka[IIdentityRepository] = ...,
) -> AuthContext:
```

After extracting `identity_id` and `session_id` (line 69), add:

```python
    # Token version validation (Option A: DB check per request, ~1ms)
    # Enables instant JWT invalidation on password change, role change, force logout
    identity = await identity_repo.get(identity_id)
    if identity is None or not identity.is_active:
        raise UnauthorizedError(
            message="Identity not found or deactivated",
            error_code="IDENTITY_INVALID",
        )
    tv = payload.get("tv", 1)  # Backward compat: old tokens without tv get version 1
    if tv < identity.token_version:
        raise UnauthorizedError(
            message="Token has been invalidated",
            error_code="TOKEN_VERSION_STALE",
        )
```

Add import: `from src.modules.identity.domain.interfaces import IIdentityRepository`

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/presentation/dependencies.py
git commit -m "feat(identity): add token version validation to get_auth_context (Option A)"
```

---

### Task 19: User Module — Customer username field

**Files:**

- Modify: `src/modules/user/domain/entities.py:105-110,131-176`
- Modify: `src/modules/user/infrastructure/models.py:40-65`
- Test: `tests/unit/modules/user/domain/test_customer.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/modules/user/domain/test_customer.py`:

```python
class TestCustomerUsername:
    def test_create_with_username(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            referral_code="USR12345",
            username="johndoe",
        )
        assert customer.username == "johndoe"

    def test_create_without_username(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            referral_code="USR12345",
        )
        assert customer.username is None

    def test_update_profile_username(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            referral_code="USR12345",
        )
        customer.update_profile(username="newname")
        assert customer.username == "newname"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modules/user/domain/test_customer.py::TestCustomerUsername -v`
Expected: FAIL — `Customer` has no `username`

- [ ] **Step 3: Add username to Customer entity**

In `src/modules/user/domain/entities.py`:

1. Add field after `last_name` (line 135): `username: str | None`
2. Add `username: str | None = None` to `create_from_identity()` params (after line 148)
3. In `create_from_identity()` return (line 166-176), add `username=username`
4. Add `"username"` to `_CUSTOMER_UPDATABLE_FIELDS` (line 105-110)
5. In `anonymize()`, add `self.username = None`

- [ ] **Step 4: Add username to CustomerModel**

In `src/modules/user/infrastructure/models.py`, after `last_name` (line 53), add:

```python
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/modules/user/domain/test_customer.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/modules/user/domain/entities.py src/modules/user/infrastructure/models.py tests/unit/modules/user/domain/test_customer.py
git commit -m "feat(user): add username field to Customer entity and model"
```

---

### Task 20: Application — Update login_oidc.py (PrimaryAuthMethod)

**Files:**

- Modify: `src/modules/identity/application/commands/login_oidc.py`

- [ ] **Step 1: Update import**

Change `from src.modules.identity.domain.value_objects import IdentityType` → `PrimaryAuthMethod`.
Update usage: `Identity.register(PrimaryAuthMethod.OIDC)`.

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/application/commands/login_oidc.py
git commit -m "refactor(identity): use PrimaryAuthMethod in LoginOIDCHandler"
```

---

### Task 21: User Module — Replace Telegram consumer with LinkedAccount consumer

**Files:**

- Modify: `src/modules/user/application/consumers/identity_events.py:214-267`

- [ ] **Step 1: Delete `create_customer_on_telegram_identity_created`**

Delete the entire function (lines 204-267, including the decorator).

- [ ] **Step 2: Add `on_linked_account_created` consumer**

```python
@broker.task(
    queue_name="user.linked_account_created",
    retry_on_error=True,
    timeout=30,
)
@inject
async def on_linked_account_created(
    identity_id: str,
    provider: str,
    customer_repo: FromDishka[ICustomerRepository],
    uow: FromDishka[IUnitOfWork],
    provider_metadata: dict | None = None,
    start_param: str | None = None,
    is_new_identity: bool = True,
    provider_sub_id: str = "",
) -> dict:
    """Handle LinkedAccountCreatedEvent — create or enrich Customer."""
    identity_uuid = uuid.UUID(identity_id)
    provider_metadata = provider_metadata or {}

    if is_new_identity:
        # New identity → create Customer
        existing = await customer_repo.get(identity_uuid)
        if existing:
            logger.info("customer.already_exists", identity_id=identity_id)
            return {"status": "skipped", "reason": "already_exists"}

        referred_by: uuid.UUID | None = None
        if start_param:
            referrer = await customer_repo.get_by_referral_code(start_param)
            referred_by = referrer.id if referrer else None

        customer = Customer.create_from_identity(
            identity_id=identity_uuid,
            first_name=provider_metadata.get("first_name", ""),
            last_name=provider_metadata.get("last_name", ""),
            username=provider_metadata.get("username"),
            referral_code=generate_referral_code(),
            referred_by=referred_by,
        )

        async with uow:
            await customer_repo.add(customer)
            uow.register_aggregate(customer)
            await uow.commit()

        logger.info(
            "customer.created_from_provider",
            identity_id=identity_id,
            provider=provider,
            referred_by=str(referred_by) if referred_by else None,
        )
        return {"status": "success", "type": "customer"}
    else:
        # Linking to existing identity — optionally enrich profile
        customer = await customer_repo.get(identity_uuid)
        if customer and not customer.username:
            username = provider_metadata.get("username")
            if username:
                async with uow:
                    customer.update_profile(username=username)
                    await customer_repo.update(customer)
                    await uow.commit()
                logger.info("customer.username_enriched", identity_id=identity_id, provider=provider)
        return {"status": "success", "type": "enriched"}
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/user/application/consumers/identity_events.py
git commit -m "refactor(user): replace Telegram consumer with generic LinkedAccount consumer"
```

---

### Task 22: Presentation — Response schemas (auth_methods + username)

**Files:**

- Modify: `src/modules/identity/presentation/schemas.py`

- [ ] **Step 1: Add fields to CustomerListItemResponse**

Add to the `CustomerListItemResponse` class:

```python
    username: str | None = None
    auth_methods: list[str] = []
```

- [ ] **Step 2: Add fields to CustomerDetailResponse**

Add to `CustomerDetailResponse`:

```python
    username: str | None = None
    auth_methods: list[str] = []
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/identity/presentation/schemas.py
git commit -m "feat(identity): add auth_methods and username to customer response schemas"
```

---

### Task 23: Query — ListCustomersHandler (auth_methods + username)

**Files:**

- Modify: `src/modules/identity/application/queries/list_customers.py`

- [ ] **Step 1: Add auth_methods and username to CustomerListItem**

Add fields to the `CustomerListItem` dataclass:

```python
    username: str | None = None
    auth_methods: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Add batch query for linked_accounts**

After fetching the main customer rows (around line 154), add:

```python
    # Batch query: auth methods per customer
    identity_ids = [row.identity_id for row in rows]
    if identity_ids:
        la_stmt = text("SELECT identity_id, provider FROM linked_accounts WHERE identity_id = ANY(:ids)")
        la_result = await self._session.execute(la_stmt, {"ids": identity_ids})
        providers_by_identity: dict[uuid.UUID, list[str]] = {}
        for la_row in la_result:
            providers_by_identity.setdefault(la_row.identity_id, []).append(la_row.provider)
```

- [ ] **Step 3: Build auth_methods per customer**

When constructing `CustomerListItem`, add:

```python
    auth_methods = []
    if row.email:  # has local_credentials
        auth_methods.append("local")
    auth_methods.extend(providers_by_identity.get(row.identity_id, []))
```

Pass `auth_methods=auth_methods` and `username=row.username` to `CustomerListItem`.

- [ ] **Step 4: Update SQL query to include username**

Add `c.username` to the main SELECT query for customers.

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/application/queries/list_customers.py
git commit -m "feat(identity): add auth_methods + username to ListCustomersHandler"
```

---

### Task 24: Query — GetCustomerDetailHandler (auth_methods + username)

**Files:**

- Modify: `src/modules/identity/application/queries/get_customer_detail.py`

- [ ] **Step 1: Add auth_methods and username to CustomerDetail**

Add to the `CustomerDetail` dataclass:

```python
    username: str | None = None
    auth_methods: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Add linked_accounts query**

After fetching the main customer detail, query linked_accounts for auth methods:

```python
    la_stmt = text("SELECT provider FROM linked_accounts WHERE identity_id = :id")
    la_result = await self._session.execute(la_stmt, {"id": identity_id})
    providers = [row.provider for row in la_result]

    auth_methods = []
    if customer_row.email:
        auth_methods.append("local")
    auth_methods.extend(providers)
```

- [ ] **Step 3: Update router_customers.py**

In `src/modules/identity/presentation/router_customers.py`, ensure the new `auth_methods` and `username` fields are passed through to the response schemas. Since Pydantic models auto-map by field name, this should work if the query handler returns the fields.

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/application/queries/get_customer_detail.py src/modules/identity/presentation/router_customers.py
git commit -m "feat(identity): add auth_methods + username to GetCustomerDetailHandler"
```

---

### Task 25: Test Factories — Update identity_mothers.py

**Files:**

- Modify: `tests/factories/identity_mothers.py`

- [ ] **Step 1: Update imports and factories**

1. Change `IdentityType` import to `PrimaryAuthMethod` (or use both via alias)
2. Update `IdentityMothers` methods to use `PrimaryAuthMethod`
3. Add `IdentityMothers.active_telegram()`:

```python
    @staticmethod
    def active_telegram() -> Identity:
        """Standard active identity via Telegram."""
        return Identity.register(PrimaryAuthMethod.TELEGRAM)
```

4. Update `LinkedAccountMothers.google()` and `github()` to include new fields:

```python
    @staticmethod
    def google(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        now = datetime.now(UTC)
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="google",
            provider_sub_id=f"google-{uuid.uuid4().hex[:8]}",
            provider_email="user@gmail.com",
            email_verified=True,
            provider_metadata={"name": "Test User", "picture": ""},
            created_at=now,
            updated_at=now,
        )
```

5. Add `LinkedAccountMothers.telegram()`:

```python
    @staticmethod
    def telegram(identity_id: uuid.UUID | None = None) -> LinkedAccount:
        now = datetime.now(UTC)
        return LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id or uuid.uuid4(),
            provider="telegram",
            provider_sub_id=f"{uuid.uuid4().int % 1000000000}",
            provider_email=None,
            email_verified=False,
            provider_metadata={
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en",
                "is_premium": False,
                "photo_url": None,
                "allows_write_to_pm": True,
            },
            created_at=now,
            updated_at=now,
        )
```

- [ ] **Step 2: Run all unit tests to check no regressions**

Run: `pytest tests/unit/ -v --tb=short`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/factories/identity_mothers.py
git commit -m "test: update identity test mothers for multi-provider auth"
```

---

### Task 26: Alembic Migration A — Schema changes + data migration

**Files:**

- Create: `alembic/versions/2026/03/20_0002_iam_multi_provider.py`

- [ ] **Step 1: Create migration**

```python
"""IAM multi-provider auth: extend schema, migrate telegram_credentials data.

Revision ID: 20260320_0002
Revises: 20_0001_add_telegram_credentials
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260320_0002"
down_revision = "20_0001_add_telegram_credentials"


def upgrade() -> None:
    # 1. Identity: add token_version
    op.add_column("identities", sa.Column("token_version", sa.Integer(), server_default="1", nullable=False))

    # 2. LinkedAccount: add new columns
    op.add_column("linked_accounts", sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("linked_accounts", sa.Column("provider_metadata", JSONB(), server_default="'{}'::jsonb", nullable=False))
    op.add_column("linked_accounts", sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("linked_accounts", sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))

    # 3. Session: idle timeout columns
    # Note: idle_expires_at defaults to expires_at for existing sessions to avoid
    # premature session invalidation (especially for long-lived Telegram sessions)
    op.add_column("sessions", sa.Column("last_active_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("sessions", sa.Column("idle_expires_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))
    # Backfill existing sessions: set idle_expires_at = expires_at (preserve existing lifetimes)
    op.execute("UPDATE sessions SET idle_expires_at = expires_at WHERE NOT is_revoked")

    # 4. Customer: username
    op.add_column("customers", sa.Column("username", sa.String(100), nullable=True))

    # 5. Rename identities.type → primary_auth_method
    op.alter_column("identities", "type", new_column_name="primary_auth_method")

    # 6. Migrate telegram_credentials → linked_accounts
    op.execute("""
        INSERT INTO linked_accounts (id, identity_id, provider, provider_sub_id, provider_email, email_verified, provider_metadata, created_at, updated_at)
        SELECT gen_random_uuid(), identity_id, 'telegram', telegram_id::text,
               NULL, false,
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
        ON CONFLICT (provider, provider_sub_id) DO NOTHING
    """)

    # 7. Backfill customer usernames from migrated linked_accounts
    op.execute("""
        UPDATE customers c
        SET username = (la.provider_metadata->>'username')
        FROM linked_accounts la
        WHERE la.identity_id = c.id
          AND la.provider = 'telegram'
          AND la.provider_metadata->>'username' IS NOT NULL
    """)


def downgrade() -> None:
    op.alter_column("identities", "primary_auth_method", new_column_name="type")
    op.drop_column("customers", "username")
    op.drop_column("sessions", "idle_expires_at")
    op.drop_column("sessions", "last_active_at")
    op.drop_column("linked_accounts", "updated_at")
    op.drop_column("linked_accounts", "created_at")
    op.drop_column("linked_accounts", "provider_metadata")
    op.drop_column("linked_accounts", "email_verified")
    op.drop_column("identities", "token_version")
    # Note: migrated data in linked_accounts is NOT removed on downgrade
```

- [ ] **Step 2: Verify migration revision chain**

Run: `alembic heads`
Expected: Shows the new revision as head

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/2026/03/20_0002_iam_multi_provider.py
git commit -m "migration: IAM multi-provider schema changes + telegram_credentials data migration"
```

---

### Task 27: E2E Tests — Update test_auth_telegram.py

**Files:**

- Modify: `tests/e2e/api/v1/test_auth_telegram.py`

- [ ] **Step 1: Update SQL queries**

Find all references to `telegram_credentials` table in the test file and replace with `linked_accounts WHERE provider = 'telegram'`.

For example, if there's a query like:

```sql
SELECT * FROM telegram_credentials WHERE identity_id = :id
```

Replace with:

```sql
SELECT * FROM linked_accounts WHERE identity_id = :id AND provider = 'telegram'
```

The `telegram_id` column becomes `provider_sub_id` (as text).

- [ ] **Step 2: Run E2E tests**

Run: `pytest tests/e2e/api/v1/test_auth_telegram.py -v`
Expected: All PASS (requires running migration against test DB first)

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/api/v1/test_auth_telegram.py
git commit -m "test(e2e): update Telegram auth tests for linked_accounts table"
```

---

### Task 28: Alembic Migration B — Drop telegram_credentials (post-deploy)

**Files:**

- Create: `alembic/versions/2026/03/20_0003_drop_telegram_credentials.py`

- [ ] **Step 1: Create migration**

```python
"""Drop telegram_credentials table after multi-provider migration verified.

Revision ID: 20260320_0003
Revises: 20260320_0002
"""
from alembic import op

revision = "20260320_0003"
down_revision = "20260320_0002"


def upgrade() -> None:
    op.drop_table("telegram_credentials")


def downgrade() -> None:
    # Recreating telegram_credentials from scratch is not practical.
    # Restore from backup if needed.
    raise NotImplementedError("Cannot reverse telegram_credentials drop. Restore from backup.")
```

- [ ] **Step 2: Commit**

```bash
git add alembic/versions/2026/03/20_0003_drop_telegram_credentials.py
git commit -m "migration: drop telegram_credentials table (post-deploy verification)"
```

---

### Task 29: Final Integration — Run all tests

- [ ] **Step 1: Run full unit test suite**

Run: `pytest tests/unit/ -v --tb=short`
Expected: All PASS

- [ ] **Step 2: Run full E2E test suite**

Run: `pytest tests/e2e/ -v --tb=short`
Expected: All PASS (requires DB with migrations applied)

- [ ] **Step 3: Run import check on all modified modules**

```bash
python -c "
from src.modules.identity.domain.entities import Identity, Session, LinkedAccount
from src.modules.identity.domain.events import LinkedAccountCreatedEvent, LinkedAccountRemovedEvent, IdentityTokenVersionBumpedEvent
from src.modules.identity.domain.value_objects import PrimaryAuthMethod, AuthProvider, TRUSTED_EMAIL_PROVIDERS
from src.modules.identity.domain.interfaces import ILinkedAccountRepository
from src.modules.identity.infrastructure.models import IdentityModel, SessionModel, LinkedAccountModel
from src.modules.identity.infrastructure.repositories.linked_account_repository import LinkedAccountRepository
from src.modules.identity.infrastructure.provider import IdentityProvider
from src.modules.identity.application.commands.login_telegram import LoginTelegramHandler
from src.modules.identity.application.commands.login import LoginHandler
from src.modules.identity.application.commands.refresh_token import RefreshTokenHandler
from src.modules.identity.presentation.dependencies import get_auth_context
from src.modules.user.domain.entities import Customer
from src.modules.user.infrastructure.models import CustomerModel
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 4: Final commit tag**

```bash
git tag iam-multi-provider-v1
```
