# Telegram Mini App Authorization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /api/v1/auth/telegram` endpoint that authenticates Telegram Mini App users via initData HMAC-SHA256 validation, auto-provisions new identities, and returns JWT token pairs.

**Architecture:** Extends the existing Identity module with a new `IdentityType.TELEGRAM` and `TelegramCredentials` entity (Shared PK 1:1 with identities). Uses event-driven Customer creation via Transactional Outbox to maintain bounded context isolation. Session eviction (not rejection) when limit reached.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async, aiogram 3.26+ (`safe_parse_webapp_init_data`), PostgreSQL, Redis, Dishka DI, Alembic, pytest + testcontainers

**Spec:** `docs/superpowers/specs/2026-03-20-telegram-auth-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/modules/identity/domain/value_objects.py` | Add `TELEGRAM` to `IdentityType`, add `TelegramUserData` VO |
| Modify | `src/modules/identity/domain/entities.py` | Add `TelegramCredentials` entity |
| Modify | `src/modules/identity/domain/events.py` | Add `TelegramIdentityCreatedEvent` |
| Modify | `src/modules/identity/domain/exceptions.py` | Add 3 initData exception classes |
| Modify | `src/modules/identity/domain/interfaces.py` | Add `ITelegramCredentialsRepository`, `ITelegramInitDataValidator`, extend `ISessionRepository` |
| Modify | `src/modules/identity/infrastructure/models.py` | Add `TelegramCredentialsModel`, extend `IdentityModel` |
| Create | `alembic/versions/2026/03/20_xxxx_add_telegram_credentials.py` | Migration |
| Create | `src/infrastructure/security/telegram.py` | `TelegramInitDataValidator` |
| Create | `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py` | `TelegramCredentialsRepository` |
| Modify | `src/modules/identity/infrastructure/repositories/session_repository.py` | Add `revoke_oldest_active` |
| Create | `src/modules/identity/application/commands/login_telegram.py` | Command, Result, Handler |
| Modify | `src/modules/user/application/consumers/identity_events.py` | Add Telegram consumer |
| Modify | `src/modules/identity/presentation/schemas.py` | Add `TelegramTokenResponse` |
| Modify | `src/modules/identity/presentation/router_auth.py` | Add `/telegram` endpoint |
| Modify | `src/modules/identity/infrastructure/provider.py` | DI wiring |
| Modify | `src/bootstrap/config.py` | 2 new settings |
| Modify | `.env.example` | Document new settings |
| Create | `tests/unit/modules/identity/domain/test_telegram.py` | Domain unit tests |
| Create | `tests/unit/infrastructure/security/test_telegram_validator.py` | Validator unit tests |
| Create | `tests/e2e/api/v1/test_auth_telegram.py` | E2E integration tests |

---

### Task 1: Domain — Value Objects

**Files:**
- Modify: `src/modules/identity/domain/value_objects.py`
- Create: `tests/unit/modules/identity/domain/test_telegram.py`

- [ ] **Step 1: Write failing tests for TelegramUserData and IdentityType.TELEGRAM**

```python
# tests/unit/modules/identity/domain/test_telegram.py
"""Unit tests for Telegram domain objects."""

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.value_objects import IdentityType, TelegramUserData


class TestIdentityTypeTelegram:
    def test_telegram_type_exists(self):
        assert IdentityType.TELEGRAM == "TELEGRAM"

    def test_telegram_type_is_string(self):
        assert isinstance(IdentityType.TELEGRAM, str)


class TestTelegramUserData:
    @pytest.fixture
    def sample_data(self) -> TelegramUserData:
        return TelegramUserData(
            telegram_id=123456789,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=True,
            photo_url="https://t.me/i/userpic/320/photo.jpg",
            allows_write_to_pm=True,
            start_param="ref_ABC123",
        )

    def test_immutable(self, sample_data: TelegramUserData):
        with pytest.raises(FrozenInstanceError):
            sample_data.telegram_id = 999  # type: ignore[misc]

    def test_all_fields_accessible(self, sample_data: TelegramUserData):
        assert sample_data.telegram_id == 123456789
        assert sample_data.first_name == "John"
        assert sample_data.last_name == "Doe"
        assert sample_data.username == "johndoe"
        assert sample_data.language_code == "en"
        assert sample_data.is_premium is True
        assert sample_data.photo_url == "https://t.me/i/userpic/320/photo.jpg"
        assert sample_data.allows_write_to_pm is True
        assert sample_data.start_param == "ref_ABC123"

    def test_optional_fields_none(self):
        data = TelegramUserData(
            telegram_id=1,
            first_name="A",
            last_name=None,
            username=None,
            language_code=None,
            is_premium=False,
            photo_url=None,
            allows_write_to_pm=False,
            start_param=None,
        )
        assert data.last_name is None
        assert data.start_param is None
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/unit/modules/identity/domain/test_telegram.py -v
```

Expected: `ImportError` — `TelegramUserData` and `IdentityType.TELEGRAM` don't exist yet.

- [ ] **Step 3: Implement — extend IdentityType, add TelegramUserData**

In `src/modules/identity/domain/value_objects.py`, add `TELEGRAM = "TELEGRAM"` to `IdentityType` enum. Add `TelegramUserData` frozen dataclass after `PermissionCode` class.

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/unit/modules/identity/domain/test_telegram.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/value_objects.py tests/unit/modules/identity/domain/test_telegram.py
git commit -m "feat(identity): add IdentityType.TELEGRAM and TelegramUserData value object"
```

---

### Task 2: Domain — TelegramCredentials Entity

**Files:**
- Modify: `src/modules/identity/domain/entities.py`
- Modify: `tests/unit/modules/identity/domain/test_telegram.py`

- [ ] **Step 1: Write failing tests for TelegramCredentials**

Append to `tests/unit/modules/identity/domain/test_telegram.py`:

```python
from src.modules.identity.domain.entities import TelegramCredentials
from src.modules.identity.domain.value_objects import AccountType


class TestIdentityRegisterTelegram:
    def test_register_telegram_type(self):
        from src.modules.identity.domain.entities import Identity

        identity = Identity.register(IdentityType.TELEGRAM, AccountType.CUSTOMER)
        assert identity.type == IdentityType.TELEGRAM
        assert identity.account_type == AccountType.CUSTOMER
        assert identity.is_active is True


class TestTelegramCredentials:
    @pytest.fixture
    def credentials(self) -> TelegramCredentials:
        now = datetime.now(UTC)
        return TelegramCredentials(
            identity_id=uuid.uuid4(),
            telegram_id=123456789,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url="https://example.com/photo.jpg",
            allows_write_to_pm=True,
            created_at=now,
            updated_at=now,
        )

    def test_update_profile_detects_changes(self, credentials: TelegramCredentials):
        new_data = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="Jane",  # changed
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=True,  # changed
            photo_url="https://example.com/photo.jpg",
            allows_write_to_pm=True,
            start_param=None,
        )
        assert credentials.update_profile(new_data) is True
        assert credentials.first_name == "Jane"
        assert credentials.is_premium is True

    def test_update_profile_no_changes(self, credentials: TelegramCredentials):
        same_data = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url="https://example.com/photo.jpg",
            allows_write_to_pm=True,
            start_param=None,
        )
        original_updated_at = credentials.updated_at
        assert credentials.update_profile(same_data) is False
        assert credentials.updated_at == original_updated_at

    def test_photo_url_not_erased_by_none(self, credentials: TelegramCredentials):
        data_no_photo = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url=None,  # privacy settings hid it
            allows_write_to_pm=True,
            start_param=None,
        )
        credentials.update_profile(data_no_photo)
        assert credentials.photo_url == "https://example.com/photo.jpg"

    def test_photo_url_updated_when_new_value(self, credentials: TelegramCredentials):
        data_new_photo = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url="https://example.com/new_photo.jpg",
            allows_write_to_pm=True,
            start_param=None,
        )
        assert credentials.update_profile(data_new_photo) is True
        assert credentials.photo_url == "https://example.com/new_photo.jpg"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/unit/modules/identity/domain/test_telegram.py::TestTelegramCredentials -v
```

- [ ] **Step 3: Implement — add TelegramCredentials to entities.py**

Add `TelegramCredentials` class using `from attr import dataclass` (same as `LocalCredentials`). Add after `LinkedAccount` class. Include `update_profile(data: TelegramUserData) -> bool` method as specified in the design doc section 2.2.

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/unit/modules/identity/domain/test_telegram.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/entities.py tests/unit/modules/identity/domain/test_telegram.py
git commit -m "feat(identity): add TelegramCredentials domain entity"
```

---

### Task 3: Domain — Event, Exceptions, Interfaces

**Files:**
- Modify: `src/modules/identity/domain/events.py`
- Modify: `src/modules/identity/domain/exceptions.py`
- Modify: `src/modules/identity/domain/interfaces.py`
- Modify: `tests/unit/modules/identity/domain/test_telegram.py`

- [ ] **Step 1: Write failing tests for event and exceptions**

Append to `tests/unit/modules/identity/domain/test_telegram.py`:

```python
from src.modules.identity.domain.events import TelegramIdentityCreatedEvent
from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)


class TestTelegramIdentityCreatedEvent:
    def test_requires_identity_id(self):
        with pytest.raises(ValueError, match="identity_id is required"):
            TelegramIdentityCreatedEvent(aggregate_id="x")

    def test_sets_aggregate_id_from_identity_id(self):
        uid = uuid.uuid4()
        event = TelegramIdentityCreatedEvent(
            identity_id=uid, telegram_id=123,
        )
        assert event.aggregate_id == str(uid)
        assert event.aggregate_type == "Identity"
        assert event.event_type == "telegram_identity_created"

    def test_start_param_optional(self):
        event = TelegramIdentityCreatedEvent(
            identity_id=uuid.uuid4(), telegram_id=123, start_param="REF123",
        )
        assert event.start_param == "REF123"


class TestTelegramExceptions:
    def test_invalid_init_data_is_401(self):
        exc = InvalidInitDataError()
        assert exc.status_code == 401
        assert exc.error_code == "INVALID_INIT_DATA"

    def test_init_data_expired_has_details(self):
        exc = InitDataExpiredError(age_seconds=600, max_seconds=300)
        assert exc.status_code == 401
        assert exc.details == {"age_seconds": 600, "max_seconds": 300}

    def test_init_data_missing_user_is_401(self):
        exc = InitDataMissingUserError()
        assert exc.status_code == 401
        assert exc.error_code == "INIT_DATA_MISSING_USER"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/unit/modules/identity/domain/test_telegram.py::TestTelegramIdentityCreatedEvent tests/unit/modules/identity/domain/test_telegram.py::TestTelegramExceptions -v
```

- [ ] **Step 3: Implement event, exceptions, interfaces**

1. Add `TelegramIdentityCreatedEvent` to `events.py` — inherits `DomainEvent`, has `aggregate_type="Identity"`, `event_type="telegram_identity_created"`, `__post_init__` validates `identity_id`.

2. Add 3 exceptions to `exceptions.py` — `InvalidInitDataError(UnauthorizedError)`, `InitDataExpiredError(UnauthorizedError)`, `InitDataMissingUserError(UnauthorizedError)`.

3. Add to `interfaces.py`:
   - `ITelegramCredentialsRepository(ABC)` with `add`, `get_by_telegram_id`, `update`
   - `ITelegramInitDataValidator(ABC)` with `validate_and_parse`
   - `revoke_oldest_active` abstract method to existing `ISessionRepository`

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/unit/modules/identity/domain/test_telegram.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/events.py src/modules/identity/domain/exceptions.py src/modules/identity/domain/interfaces.py tests/unit/modules/identity/domain/test_telegram.py
git commit -m "feat(identity): add Telegram domain event, exceptions, and interfaces"
```

---

### Task 4: Infrastructure — ORM Model + Migration

**Files:**
- Modify: `src/modules/identity/infrastructure/models.py`
- Create: `alembic/versions/2026/03/20_xxxx_add_telegram_credentials.py`

- [ ] **Step 1: Add TelegramCredentialsModel to models.py**

Add `TelegramCredentialsModel` after `LinkedAccountModel`. Add `telegram_credentials` relationship to `IdentityModel`. Import `BigInteger` from sqlalchemy. See design doc section 3.1 for exact code.

- [ ] **Step 2: Generate migration**

```bash
uv run alembic revision --autogenerate -m "add_telegram_credentials"
```

- [ ] **Step 3: Review generated migration**

Check the generated file has:
- `op.create_table("telegram_credentials", ...)` with all columns
- Unique index on `telegram_id`
- No accidental changes to existing tables

- [ ] **Step 4: Run migration**

```bash
uv run alembic upgrade head
```

Expected: Migration applies successfully, `telegram_credentials` table created.

- [ ] **Step 5: Verify table exists**

```bash
uv run python -c "
from sqlalchemy import inspect, create_engine
from src.bootstrap.config import settings
engine = create_engine(str(settings.database_url).replace('+asyncpg', '+psycopg2'))
inspector = inspect(engine)
cols = [c['name'] for c in inspector.get_columns('telegram_credentials')]
print('Columns:', cols)
assert 'telegram_id' in cols
print('OK')
"
```

- [ ] **Step 6: Commit**

```bash
git add src/modules/identity/infrastructure/models.py alembic/versions/
git commit -m "feat(identity): add TelegramCredentialsModel and migration"
```

---

### Task 5: Infrastructure — Config + initData Validator

**Files:**
- Modify: `src/bootstrap/config.py`
- Modify: `.env.example`
- Create: `src/infrastructure/security/telegram.py`
- Create: `tests/unit/infrastructure/security/test_telegram_validator.py`

- [ ] **Step 1: Add settings**

In `src/bootstrap/config.py`, add after `THROTTLE_RATE`:

```python
TELEGRAM_INIT_DATA_MAX_AGE: int = 300
TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

In `.env.example`, add:

```bash
# -- Telegram Mini App Auth ---
# TELEGRAM_INIT_DATA_MAX_AGE=300
# TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS=7
```

- [ ] **Step 2: Write failing tests for validator**

```python
# tests/unit/infrastructure/security/test_telegram_validator.py
"""Unit tests for TelegramInitDataValidator."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.security.telegram import TelegramInitDataValidator
from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)
from src.modules.identity.domain.value_objects import TelegramUserData

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


class TestTelegramInitDataValidator:
    @pytest.fixture
    def validator(self) -> TelegramInitDataValidator:
        return TelegramInitDataValidator(bot_token=BOT_TOKEN, max_age=300)

    def _mock_parsed(self, **overrides) -> MagicMock:
        user = MagicMock()
        user.id = 123456789
        user.first_name = "John"
        user.last_name = "Doe"
        user.username = "johndoe"
        user.language_code = "en"
        user.is_premium = True
        user.photo_url = "https://t.me/photo.jpg"
        user.allows_write_to_pm = True

        parsed = MagicMock()
        parsed.user = user
        parsed.auth_date = overrides.get("auth_date", datetime.now(UTC))
        parsed.start_param = overrides.get("start_param", "REF123")

        if "user" in overrides:
            parsed.user = overrides["user"]

        return parsed

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_valid_init_data_returns_telegram_user_data(
        self, mock_parse, validator: TelegramInitDataValidator
    ):
        mock_parse.return_value = self._mock_parsed()
        result = validator.validate_and_parse("valid_init_data")
        assert isinstance(result, TelegramUserData)
        assert result.telegram_id == 123456789
        assert result.first_name == "John"
        assert result.is_premium is True
        assert result.start_param == "REF123"

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_invalid_signature_raises(
        self, mock_parse, validator: TelegramInitDataValidator
    ):
        mock_parse.side_effect = ValueError("Invalid init data signature")
        with pytest.raises(InvalidInitDataError):
            validator.validate_and_parse("bad_data")

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_expired_auth_date_raises(
        self, mock_parse, validator: TelegramInitDataValidator
    ):
        old_date = datetime.now(UTC) - timedelta(seconds=600)
        mock_parse.return_value = self._mock_parsed(auth_date=old_date)
        with pytest.raises(InitDataExpiredError) as exc_info:
            validator.validate_and_parse("old_data")
        assert exc_info.value.details["max_seconds"] == 300

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_future_auth_date_raises(
        self, mock_parse, validator: TelegramInitDataValidator
    ):
        future_date = datetime.now(UTC) + timedelta(seconds=60)
        mock_parse.return_value = self._mock_parsed(auth_date=future_date)
        with pytest.raises(InitDataExpiredError):
            validator.validate_and_parse("future_data")

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_missing_user_raises(
        self, mock_parse, validator: TelegramInitDataValidator
    ):
        mock_parse.return_value = self._mock_parsed(user=None)
        with pytest.raises(InitDataMissingUserError):
            validator.validate_and_parse("no_user_data")

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_optional_fields_default_to_false(
        self, mock_parse, validator: TelegramInitDataValidator
    ):
        user = MagicMock()
        user.id = 1
        user.first_name = "A"
        user.last_name = None
        user.username = None
        user.language_code = None
        user.is_premium = None  # aiogram returns None, not False
        user.photo_url = None
        user.allows_write_to_pm = None
        mock_parse.return_value = self._mock_parsed(user=user)
        mock_parse.return_value.user = user
        result = validator.validate_and_parse("data")
        assert result.is_premium is False
        assert result.allows_write_to_pm is False
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
uv run pytest tests/unit/infrastructure/security/test_telegram_validator.py -v
```

- [ ] **Step 4: Implement TelegramInitDataValidator**

Create `src/infrastructure/security/telegram.py` with the exact code from design doc section 3.2. Also create `__init__.py` files if missing:

```bash
touch tests/unit/infrastructure/security/__init__.py
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
uv run pytest tests/unit/infrastructure/security/test_telegram_validator.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/bootstrap/config.py .env.example src/infrastructure/security/telegram.py tests/unit/infrastructure/security/test_telegram_validator.py
git commit -m "feat(security): add TelegramInitDataValidator with HMAC + freshness checks"
```

---

### Task 6: Infrastructure — Repository + Session Extension

**Files:**
- Create: `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py`
- Modify: `src/modules/identity/infrastructure/repositories/session_repository.py`

- [ ] **Step 1: Implement TelegramCredentialsRepository**

Create `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py` following the Data Mapper pattern from `identity_repository.py`.

**Important:** Use `from sqlalchemy import select, update` (not `sa_update`) — matching the existing import style in `session_repository.py` line 12.

Private mapper methods `_to_identity_domain()` and `_to_credentials_domain()` follow the existing pattern.

- [ ] **Step 2: Add revoke_oldest_active to SessionRepository**

In `src/modules/identity/infrastructure/repositories/session_repository.py`, add:

```python
async def revoke_oldest_active(self, identity_id: uuid.UUID) -> uuid.UUID | None:
    """Revoke the oldest active session to make room for a new one."""
    now = datetime.now(UTC)  # match existing count_active() pattern
    stmt = (
        select(SessionModel.id)
        .where(
            SessionModel.identity_id == identity_id,
            SessionModel.is_revoked.is_(False),
            SessionModel.expires_at > now,
        )
        .order_by(SessionModel.created_at.asc())
        .limit(1)
    )
    session_id = (await self._session.execute(stmt)).scalar_one_or_none()
    if session_id is None:
        return None
    await self._session.execute(
        update(SessionModel)  # `update` already imported on line 12
        .where(SessionModel.id == session_id)
        .values(is_revoked=True)
    )
    return session_id
```

**Note:** Uses `datetime.now(UTC)` (not `func.now()`) for consistency with `count_active()` and `revoke_all_for_identity()`.

- [ ] **Step 3: Commit**

```bash
git add src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py src/modules/identity/infrastructure/repositories/session_repository.py
git commit -m "feat(identity): add TelegramCredentialsRepository and session eviction"
```

---

### Task 7: Application — LoginTelegramHandler

**Files:**
- Create: `src/modules/identity/application/commands/login_telegram.py`

- [ ] **Step 1: Implement command, result, and handler**

Create `src/modules/identity/application/commands/login_telegram.py` with the exact code from design doc section 4.1 and 4.2. This includes:
- `LoginTelegramCommand` (frozen dataclass)
- `LoginTelegramResult` (frozen dataclass)
- `LoginTelegramHandler` class with `handle()` and `_provision_new_identity()`

Follow the import patterns from `login_oidc.py`.

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/application/commands/login_telegram.py
git commit -m "feat(identity): add LoginTelegramHandler with auto-provisioning"
```

---

### Task 8: Application — Event Consumer

**Files:**
- Modify: `src/modules/user/application/consumers/identity_events.py`

- [ ] **Step 1: Add Telegram consumer to identity_events.py**

Add `create_customer_on_telegram_identity_created` function after the existing `anonymize_user_on_identity_deactivated`. Use the exact code from design doc section 4.3. Add `generate_referral_code` to the existing imports from `src.modules.user.domain.services`.

**Note:** `profile_email` is intentionally omitted (defaults to `None`) — Telegram does not provide email addresses. This differs from the email-based `_create_customer` which passes `profile_email=email`.

- [ ] **Step 2: Commit**

```bash
git add src/modules/user/application/consumers/identity_events.py
git commit -m "feat(user): add Telegram customer creation consumer with referral support"
```

---

### Task 9: Presentation — Schema + Router + DI

**Files:**
- Modify: `src/modules/identity/presentation/schemas.py`
- Modify: `src/modules/identity/presentation/router_auth.py`
- Modify: `src/modules/identity/infrastructure/provider.py`

- [ ] **Step 1: Add TelegramTokenResponse schema**

In `schemas.py`, add after `LoginOIDCRequest`:

```python
class TelegramTokenResponse(CamelModel):
    """Response for Telegram Mini App authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool
```

- [ ] **Step 2: Add /telegram endpoint to router_auth.py**

Add the endpoint from design doc section 5.2. Add imports: `LoginTelegramCommand` from commands, `TelegramTokenResponse` from schemas, `UnauthorizedError` from shared exceptions.

- [ ] **Step 3: Add DI wiring to provider.py**

Add the 3 provider entries from design doc section 5.3. Add imports: `TelegramCredentialsRepository`, `TelegramInitDataValidator`, `LoginTelegramHandler`, and their interfaces.

- [ ] **Step 4: Verify app starts**

```bash
uv run python -c "from src.bootstrap.web import create_app; app = create_app(); print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/presentation/schemas.py src/modules/identity/presentation/router_auth.py src/modules/identity/infrastructure/provider.py
git commit -m "feat(identity): add /auth/telegram endpoint with DI wiring"
```

---

### Task 10: E2E Tests

**Files:**
- Create: `tests/e2e/api/v1/test_auth_telegram.py`

- [ ] **Step 1: Write E2E tests**

```python
# tests/e2e/api/v1/test_auth_telegram.py
"""E2E tests for POST /api/v1/auth/telegram."""

import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import settings

pytestmark = pytest.mark.asyncio


def _build_init_data(
    user_id: int = 123456789,
    first_name: str = "Test",
    last_name: str | None = "User",
    username: str | None = "testuser",
    auth_date: int | None = None,
    start_param: str | None = None,
    bot_token: str | None = None,
) -> str:
    """Build a valid Telegram initData string with correct HMAC-SHA256."""
    token = bot_token or settings.BOT_TOKEN.get_secret_value()
    if auth_date is None:
        auth_date = int(time.time())

    user_obj = {"id": user_id, "first_name": first_name}
    if last_name:
        user_obj["last_name"] = last_name
    if username:
        user_obj["username"] = username

    params = {
        "user": json.dumps(user_obj, separators=(",", ":")),
        "auth_date": str(auth_date),
    }
    if start_param:
        params["start_param"] = start_param

    # Build data_check_string (sorted by key, joined by \n)
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    # HMAC: secret_key = HMAC-SHA256(key="WebAppData", msg=bot_token)
    secret_key = hmac.new(
        b"WebAppData", token.encode(), hashlib.sha256
    ).digest()
    hash_value = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    params["hash"] = hash_value
    return urlencode(params)


async def test_login_telegram_new_user_returns_tokens(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900001)
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"
    assert data["isNewUser"] is True


async def test_login_telegram_existing_user_returns_is_new_false(
    async_client: AsyncClient, db_session: AsyncSession
):
    user_id = 900002
    # First login
    init_data = _build_init_data(user_id=user_id)
    await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    # Second login
    init_data2 = _build_init_data(user_id=user_id, first_name="Updated")
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data2}"},
    )
    assert response.status_code == 200
    assert response.json()["isNewUser"] is False


async def test_login_telegram_invalid_signature_returns_401(
    async_client: AsyncClient,
):
    init_data = _build_init_data(bot_token="wrong:token")
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_INIT_DATA"


async def test_login_telegram_expired_returns_401(
    async_client: AsyncClient,
):
    old_time = int(time.time()) - 600  # 10 minutes ago
    init_data = _build_init_data(auth_date=old_time)
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INIT_DATA_EXPIRED"


async def test_login_telegram_missing_tma_header_returns_401(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": "Bearer some_token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTH_SCHEME"


async def test_login_telegram_no_auth_header_returns_401(
    async_client: AsyncClient,
):
    response = await async_client.post("/api/v1/auth/telegram")
    assert response.status_code == 401


async def test_refresh_works_after_telegram_login(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900010)
    login_resp = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    refresh_token = login_resp.json()["refreshToken"]
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refresh_resp.status_code == 200
    assert "accessToken" in refresh_resp.json()


async def test_logout_works_after_telegram_login(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900011)
    login_resp = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    access_token = login_resp.json()["accessToken"]
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200


async def test_login_telegram_deactivated_identity_returns_403(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Deactivated identity should be rejected with 403."""
    user_id = 900020
    # First login — creates identity
    init_data = _build_init_data(user_id=user_id)
    await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    # Deactivate identity directly in DB
    await db_session.execute(
        text("""
            UPDATE identities SET is_active = false,
            deactivated_at = now()
            WHERE id = (
                SELECT identity_id FROM telegram_credentials
                WHERE telegram_id = :tid
            )
        """),
        {"tid": user_id},
    )
    await db_session.commit()
    # Second login — should fail
    init_data2 = _build_init_data(user_id=user_id)
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data2}"},
    )
    assert response.status_code == 403


async def test_login_telegram_session_eviction(
    async_client: AsyncClient, db_session: AsyncSession
):
    """When max sessions reached, oldest should be evicted."""
    user_id = 900030
    # Create MAX_ACTIVE_SESSIONS_PER_IDENTITY sessions (default 5)
    for _ in range(5):
        init_data = _build_init_data(user_id=user_id)
        resp = await async_client.post(
            "/api/v1/auth/telegram",
            headers={"Authorization": f"tma {init_data}"},
        )
        assert resp.status_code == 200

    # 6th login should succeed (eviction, not rejection)
    init_data = _build_init_data(user_id=user_id)
    resp = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert resp.status_code == 200

    # Verify we still have at most 5 active sessions
    result = await db_session.execute(
        text("""
            SELECT count(*) FROM sessions
            WHERE identity_id = (
                SELECT identity_id FROM telegram_credentials
                WHERE telegram_id = :tid
            )
            AND is_revoked = false
            AND expires_at > now()
        """),
        {"tid": user_id},
    )
    active_count = result.scalar()
    assert active_count <= 5


async def test_login_telegram_referral_start_param(
    async_client: AsyncClient, db_session: AsyncSession
):
    """start_param from initData should be included in the event for referral."""
    # This test verifies the login succeeds with start_param —
    # the actual Customer creation is handled by the async consumer
    init_data = _build_init_data(user_id=900040, start_param="TESTREF")
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 200
    assert response.json()["isNewUser"] is True
```

- [ ] **Step 2: Run E2E tests**

```bash
uv run pytest tests/e2e/api/v1/test_auth_telegram.py -v
```

All tests should pass. If any fail, debug and fix the implementation.

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
uv run pytest --tb=short -q
```

Expected: All existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/api/v1/test_auth_telegram.py
git commit -m "test(e2e): add Telegram auth E2E tests"
```

---

### Task 11: Final — Run all tests + cleanup

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest --tb=short -q
```

- [ ] **Step 2: Run architecture tests**

```bash
uv run pytest tests/architecture/ -v
```

Existing `test_domain_layer_is_pure` and `test_domain_has_zero_framework_imports` (parametrized over `["catalog", "storage", "identity", "user"]`) automatically verify that new Telegram domain code has no infrastructure imports. These tests cover the spec's `test_telegram_domain_no_infrastructure_imports` requirement without additional test code.

- [ ] **Step 3: Verify OpenAPI docs show new endpoint**

```bash
uv run python -c "
from src.bootstrap.web import create_app
app = create_app()
routes = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/api/v1/auth/telegram' in routes, f'Missing endpoint. Routes: {routes}'
print('OpenAPI: /auth/telegram endpoint registered')
"
```

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git status
# If clean, skip. Otherwise:
git add -A && git commit -m "chore: cleanup after Telegram auth implementation"
```
