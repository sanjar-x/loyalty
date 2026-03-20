# Users/Staff Separation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Разделить единый User aggregate на Customer и StaffMember с явным AccountType в Identity, Staff invitation flow и раздельными API endpoints.

**Architecture:** Identity BC получает AccountType discriminator + StaffInvitation aggregate. User BC разделяется на Customer (referral-enabled) и StaffMember aggregates с раздельными таблицами. Cross-module communication через domain events с routing по account_type. Separate Tables pattern (Shopify/Medusa/Azure AD).

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2.1 async, Alembic, Dishka DI, TaskIQ, attrs, Pydantic v2, pytest

**Source documents:**

- SPEC: `docs/specs/2026-03-19-users-staff-separation-spec.md`
- Gap Analysis: `docs/research/2026-03-19-gap-analysis-users-staff-separation.md`
- Backend Analysis: `docs/research/2026-03-19-backend-users-staff-current-state-analysis.md`
- Deep Research: `docs/research/2026-03-19-users-staff-separation-deep-research.md`

---

## File Structure

### New Files

```
src/modules/identity/domain/
  value_objects.py                    ← MODIFY: add AccountType, InvitationStatus enums

src/modules/identity/domain/
  entities.py                        ← MODIFY: add account_type field to Identity, add StaffInvitation entity

src/modules/identity/domain/
  events.py                          ← MODIFY: add account_type to IdentityRegisteredEvent, add StaffInvitedEvent, StaffInvitationAcceptedEvent

src/modules/identity/domain/
  exceptions.py                      ← MODIFY: add 6 invitation exceptions + AccountTypeMismatchError

src/modules/identity/domain/
  interfaces.py                      ← MODIFY: add IStaffInvitationRepository

src/modules/identity/infrastructure/
  models.py                          ← MODIFY: add account_type to IdentityModel, add StaffInvitationModel, StaffInvitationRoleModel

src/modules/identity/infrastructure/
  repositories/
    staff_invitation_repository.py   ← CREATE: StaffInvitationRepository implementation

src/modules/identity/infrastructure/
  provider.py                        ← MODIFY: register new handlers + repos

src/modules/identity/application/commands/
  invite_staff.py                    ← CREATE: InviteStaffCommand + Handler
  accept_staff_invitation.py         ← CREATE: AcceptStaffInvitationCommand + Handler
  revoke_staff_invitation.py         ← CREATE: RevokeStaffInvitationCommand + Handler
  assign_role.py                     ← MODIFY: add SoD check
  deactivate_identity.py             ← MODIFY: fix super_admin → admin

src/modules/identity/application/queries/
  list_staff.py                      ← CREATE: ListStaffQuery + Handler
  list_customers.py                  ← CREATE: ListCustomersQuery + Handler
  list_staff_invitations.py          ← CREATE: ListStaffInvitationsQuery + Handler
  validate_invitation.py             ← CREATE: ValidateInvitationTokenQuery + Handler
  get_staff_detail.py                ← CREATE: GetStaffDetailQuery + Handler
  get_customer_detail.py             ← CREATE: GetCustomerDetailQuery + Handler

src/modules/identity/presentation/
  schemas.py                         ← MODIFY: add Staff, Customer, Invitation schemas
  router_staff.py                    ← CREATE: /admin/staff endpoints
  router_customers.py                ← CREATE: /admin/customers endpoints
  router_invitation.py               ← CREATE: /invitations/{token} public endpoints

src/modules/user/domain/
  entities.py                        ← REWRITE: User → Customer + StaffMember
  interfaces.py                      ← REWRITE: IUserRepository → ICustomerRepository + IStaffMemberRepository
  exceptions.py                      ← MODIFY: add CustomerNotFoundError, StaffMemberNotFoundError
  services.py                        ← CREATE: generate_referral_code()

src/modules/user/infrastructure/
  models.py                          ← REWRITE: UserModel → CustomerModel + StaffMemberModel
  repositories/
    customer_repository.py           ← CREATE: CustomerRepository
    staff_member_repository.py       ← CREATE: StaffMemberRepository
  provider.py                        ← REWRITE: register new repos + handlers

src/modules/user/application/
  commands/
    create_customer.py               ← CREATE: replaces create_user
    create_staff_member.py           ← CREATE: new
    update_profile.py                ← MODIFY: use ICustomerRepository
    anonymize_customer.py            ← CREATE: replaces anonymize_user
  queries/
    get_my_profile.py                ← MODIFY: query customers table
  consumers/
    identity_events.py               ← REWRITE: route by account_type

src/modules/user/presentation/
  router.py                          ← MODIFY: use ICustomerRepository
  schemas.py                         ← MODIFY: referral_code in response

src/api/router.py                    ← MODIFY: mount new routers
src/bootstrap/container.py           ← MODIFY: no changes (providers auto-register)
scripts/seed_dev.sql                 ← MODIFY: account_type + staff_members + new permissions

alembic/versions/2026/03/           ← CREATE: 5 migration files

tests/unit/modules/identity/domain/
  test_staff_invitation.py           ← CREATE
tests/unit/modules/identity/application/commands/
  test_invite_staff.py               ← CREATE
  test_accept_invitation.py          ← CREATE
  test_assign_role_sod.py            ← CREATE
tests/unit/modules/user/domain/
  test_customer.py                   ← CREATE
  test_staff_member.py               ← CREATE
tests/unit/modules/user/application/commands/
  test_commands.py                   ← REWRITE: Customer/StaffMember
```

---

## Task 1: Hotfix — `super_admin` → `admin` + unit tests

**Files:**

- Modify: `src/modules/identity/application/commands/admin_deactivate_identity.py`
- Modify: `src/modules/identity/domain/exceptions.py`
- Create: `tests/unit/modules/identity/application/commands/test_admin_deactivate.py`

> **Почему первым:** GAP-4.1 — Last Admin Protection не работает. Handler проверяет роль `"super_admin"`, но в seed data её нет (есть только `"admin"`). Это баг, и нужен safety net (тесты) ДО рефакторинга.

- [ ] **Step 1: Read the admin deactivate handler**

Read `src/modules/identity/application/commands/admin_deactivate_identity.py`. Lines 92-105 contain the `super_admin` check:

- Line 98: `if role is not None and role.name == "super_admin"` — iterates through target's role IDs, fetches each via `role_repo.get(role_id)`
- Line 103: `count = await self._role_repo.count_identities_with_role("super_admin")`

Both must change to `"admin"`.

- [ ] **Step 2: Write failing test for last-admin protection**

```python
# tests/unit/modules/identity/application/commands/test_admin_deactivate.py
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityCommand,
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.exceptions import (
    LastAdminProtectionError,
    SelfDeactivationError,
)
from src.modules.identity.domain.value_objects import IdentityType


@pytest.fixture
def identity_repo():
    return AsyncMock()


@pytest.fixture
def role_repo():
    return AsyncMock()


@pytest.fixture
def session_repo():
    return AsyncMock()


@pytest.fixture
def uow():
    mock = AsyncMock()
    mock.register_aggregate = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def permission_resolver():
    return AsyncMock()


@pytest.fixture
def logger():
    mock = MagicMock()
    mock.bind.return_value = mock
    return mock


class TestAdminDeactivateIdentityHandler:
    async def test_self_deactivation_raises(
        self, identity_repo, role_repo, session_repo, uow, permission_resolver, logger
    ):
        """Admin cannot deactivate themselves."""
        admin_id = uuid.uuid4()
        identity = Identity.register(IdentityType.LOCAL)
        object.__setattr__(identity, "id", admin_id)
        identity_repo.get.return_value = identity

        handler = AdminDeactivateIdentityHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )
        cmd = AdminDeactivateIdentityCommand(
            identity_id=admin_id,
            reason="test",
            deactivated_by=admin_id,  # same as target → SelfDeactivationError
        )
        with pytest.raises(SelfDeactivationError):
            await handler.handle(cmd)

    async def test_last_admin_protection_raises(
        self, identity_repo, role_repo, session_repo, uow, permission_resolver, logger
    ):
        """Cannot deactivate the last admin."""
        target_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        admin_role_id = uuid.uuid4()

        # Target identity is active
        identity = Identity.register(IdentityType.LOCAL)
        object.__setattr__(identity, "id", target_id)
        identity_repo.get.return_value = identity

        # Target has admin role — handler calls get_identity_role_ids then get(role_id)
        admin_role = MagicMock()
        admin_role.id = admin_role_id
        admin_role.name = "admin"
        role_repo.get_identity_role_ids.return_value = [admin_role_id]
        role_repo.get.return_value = admin_role

        # Only 1 identity has admin role → last admin
        role_repo.count_identities_with_role.return_value = 1

        handler = AdminDeactivateIdentityHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )
        cmd = AdminDeactivateIdentityCommand(
            identity_id=target_id,
            reason="test",
            deactivated_by=admin_id,
        )
        with pytest.raises(LastAdminProtectionError):
            await handler.handle(cmd)
```

- [ ] **Step 4: Fix handler — change `super_admin` to `admin`**

In `src/modules/identity/application/commands/admin_deactivate_identity.py`:

```python
# Line 94: rename variable for clarity
target_has_admin = False

# Line 98: BEFORE:
if role is not None and role.name == "super_admin":
    target_has_super_admin = True
# AFTER:
if role is not None and role.name == "admin":
    target_has_admin = True

# Line 102: BEFORE:
if target_has_super_admin:
    count = await self._role_repo.count_identities_with_role("super_admin")
# AFTER:
if target_has_admin:
    count = await self._role_repo.count_identities_with_role("admin")
```

Also update `LastAdminProtectionError` message in `src/modules/identity/domain/exceptions.py`:

```python
# BEFORE:
message="Cannot remove the last super_admin"
# AFTER:
message="Cannot remove the last admin"
```

- [ ] **Step 7: Commit**

```bash
git add src/modules/identity/application/commands/admin_deactivate_identity.py src/modules/identity/domain/exceptions.py tests/unit/modules/identity/application/commands/test_admin_deactivate.py
git commit -m "fix(identity): change last-admin protection from super_admin to admin role"
```

---

## Task 2: Domain Value Objects — AccountType + InvitationStatus

**Files:**

- Modify: `src/modules/identity/domain/value_objects.py`
- Create: `tests/unit/modules/identity/domain/test_value_objects.py`

- [ ] **Step 1: Write tests for new enums**

```python
# tests/unit/modules/identity/domain/test_value_objects.py
from src.modules.identity.domain.value_objects import AccountType, InvitationStatus


class TestAccountType:
    def test_customer_value(self):
        assert AccountType.CUSTOMER == "CUSTOMER"
        assert AccountType.CUSTOMER.value == "CUSTOMER"

    def test_staff_value(self):
        assert AccountType.STAFF == "STAFF"
        assert AccountType.STAFF.value == "STAFF"

    def test_is_string_enum(self):
        assert isinstance(AccountType.CUSTOMER, str)


class TestInvitationStatus:
    def test_all_statuses_exist(self):
        assert InvitationStatus.PENDING == "PENDING"
        assert InvitationStatus.ACCEPTED == "ACCEPTED"
        assert InvitationStatus.EXPIRED == "EXPIRED"
        assert InvitationStatus.REVOKED == "REVOKED"
```

- [ ] **Step 3: Add enums to value_objects.py**

Add to `src/modules/identity/domain/value_objects.py` after `IdentityType`:

```python
class AccountType(str, enum.Enum):
    """Type of account — determines lifecycle and available roles.

    Immutable after Identity creation.

    Attributes:
        CUSTOMER: Platform buyer. Self-registration.
        STAFF: Internal employee. Invitation-based registration.
    """

    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"


class InvitationStatus(str, enum.Enum):
    """Staff invitation lifecycle status.

    Attributes:
        PENDING: Awaiting acceptance.
        ACCEPTED: Accepted by invitee.
        EXPIRED: TTL exceeded without acceptance.
        REVOKED: Cancelled by admin before acceptance.
    """

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
```

- [ ] **Step 5: commit**

```bash
git add src/modules/identity/domain/value_objects.py tests/unit/modules/identity/domain/test_value_objects.py
git commit -m "feat(identity): add AccountType and InvitationStatus value objects"
```

---

## Task 3: Identity Entity — add `account_type` field

**Files:**

- Modify: `src/modules/identity/domain/entities.py`
- Modify: `src/modules/identity/domain/events.py`
- Create: `tests/unit/modules/identity/domain/test_identity_account_type.py`

- [ ] **Step 1: Write tests for account_type in Identity**

```python
# tests/unit/modules/identity/domain/test_identity_account_type.py
from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.value_objects import AccountType, IdentityType


class TestIdentityAccountType:
    def test_register_defaults_to_customer(self):
        identity = Identity.register(IdentityType.LOCAL)
        assert identity.account_type == AccountType.CUSTOMER

    def test_register_with_explicit_customer(self):
        identity = Identity.register(IdentityType.LOCAL, AccountType.CUSTOMER)
        assert identity.account_type == AccountType.CUSTOMER

    def test_register_with_staff(self):
        identity = Identity.register(IdentityType.LOCAL, AccountType.STAFF)
        assert identity.account_type == AccountType.STAFF

    def test_register_staff_factory(self):
        identity = Identity.register_staff()
        assert identity.account_type == AccountType.STAFF
        assert identity.type == IdentityType.LOCAL
        assert identity.is_active is True
```

- [ ] **Step 3: Add `account_type` to Identity entity**

In `src/modules/identity/domain/entities.py`:

1. Add import: `from src.modules.identity.domain.value_objects import AccountType` (alongside existing IdentityType import)

2. Add field to Identity dataclass (after `type` field):

```python
account_type: AccountType = AccountType.CUSTOMER
```

3. Modify `register()` classmethod:

```python
@classmethod
def register(
    cls,
    identity_type: IdentityType,
    account_type: AccountType = AccountType.CUSTOMER,
) -> Identity:
    """Create a new active identity with the given authentication type.

    Args:
        identity_type: The authentication method for this identity.
        account_type: The type of account (CUSTOMER or STAFF). Defaults to CUSTOMER.

    Returns:
        A new Identity instance in active state.
    """
    now = datetime.now(UTC)
    return cls(
        id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
        type=identity_type,
        account_type=account_type,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
```

4. Add `register_staff()` classmethod:

```python
@classmethod
def register_staff(cls, identity_type: IdentityType = IdentityType.LOCAL) -> Identity:
    """Create a new active staff identity.

    Args:
        identity_type: The authentication method. Defaults to LOCAL.

    Returns:
        A new Identity instance with account_type=STAFF.
    """
    return cls.register(identity_type, AccountType.STAFF)
```

- [ ] **Step 4: Add `account_type` to IdentityRegisteredEvent**

In `src/modules/identity/domain/events.py`, add field to `IdentityRegisteredEvent`:

```python
account_type: str = "CUSTOMER"
```

- [ ] **Step 7: commit**

```bash
git add src/modules/identity/domain/entities.py src/modules/identity/domain/events.py tests/unit/modules/identity/domain/test_identity_account_type.py
git commit -m "feat(identity): add account_type field to Identity entity"
```

---

## Task 4: Domain Exceptions — Invitation errors + AccountTypeMismatchError

**Files:**

- Modify: `src/modules/identity/domain/exceptions.py`

- [ ] **Step 1: Add all new exceptions**

Append to `src/modules/identity/domain/exceptions.py`:

```python
class InvitationNotFoundError(NotFoundError):
    """Raised when a staff invitation is not found."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation not found",
            error_code="INVITATION_NOT_FOUND",
        )


class InvitationExpiredError(AppException):
    """Raised when a staff invitation has expired (TTL exceeded)."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation has expired",
            status_code=410,
            error_code="INVITATION_EXPIRED",
        )


class InvitationAlreadyAcceptedError(ConflictError):
    """Raised when attempting to accept an already-accepted invitation."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation already accepted",
            error_code="INVITATION_ALREADY_ACCEPTED",
        )


class InvitationRevokedError(ForbiddenError):
    """Raised when attempting to use a revoked invitation."""

    def __init__(self) -> None:
        super().__init__(
            message="Staff invitation has been revoked",
            error_code="INVITATION_REVOKED",
        )


class InvitationNotPendingError(ConflictError):
    """Raised when an operation requires PENDING status but invitation is not."""

    def __init__(self) -> None:
        super().__init__(
            message="Invitation is not in pending status",
            error_code="INVITATION_NOT_PENDING",
        )


class ActiveInvitationExistsError(ConflictError):
    """Raised when a pending invitation already exists for the given email."""

    def __init__(self) -> None:
        super().__init__(
            message="Active invitation for this email already exists",
            error_code="ACTIVE_INVITATION_EXISTS",
        )


class AccountTypeMismatchError(ForbiddenError):
    """Raised when a role is incompatible with the identity's account type."""

    def __init__(self) -> None:
        super().__init__(
            message="Role is not compatible with account type",
            error_code="ACCOUNT_TYPE_MISMATCH",
        )
```

Add `NotFoundError` to the imports at the top if not present:

```python
from src.shared.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableEntityError,
)
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/identity/domain/exceptions.py
git commit -m "feat(identity): add invitation and account-type exceptions"
```

---

## Task 5: StaffInvitation Entity

**Files:**

- Modify: `src/modules/identity/domain/entities.py`
- Modify: `src/modules/identity/domain/events.py`
- Create: `tests/unit/modules/identity/domain/test_staff_invitation.py`

- [ ] **Step 1: Write tests for StaffInvitation**

```python
# tests/unit/modules/identity/domain/test_staff_invitation.py
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.identity.domain.entities import StaffInvitation
from src.modules.identity.domain.exceptions import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotPendingError,
    InvitationRevokedError,
)
from src.modules.identity.domain.value_objects import InvitationStatus


class TestStaffInvitationCreate:
    def test_create_sets_pending_status(self):
        invitation = StaffInvitation.create(
            email="new@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="test-token-abc",
            ttl_hours=72,
        )
        assert invitation.status == InvitationStatus.PENDING
        assert invitation.email == "new@example.com"
        assert invitation.accepted_at is None
        assert invitation.accepted_identity_id is None

    def test_create_hashes_token(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="my-secret-token",
        )
        assert invitation.token_hash != "my-secret-token"
        assert len(invitation.token_hash) == 64  # SHA-256 hex

    def test_create_sets_expiry(self):
        before = datetime.now(UTC)
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
            ttl_hours=24,
        )
        assert invitation.expires_at > before
        assert invitation.expires_at <= before + timedelta(hours=24, seconds=5)

    def test_create_emits_staff_invited_event(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
        )
        events = invitation.domain_events
        assert len(events) == 1
        assert events[0].event_type == "staff_invited"


class TestStaffInvitationAccept:
    def test_accept_success(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
        )
        invitation.clear_domain_events()
        identity_id = uuid.uuid4()
        invitation.accept(identity_id)
        assert invitation.status == InvitationStatus.ACCEPTED
        assert invitation.accepted_identity_id == identity_id
        assert invitation.accepted_at is not None
        events = invitation.domain_events
        assert len(events) == 1
        assert events[0].event_type == "staff_invitation_accepted"

    def test_accept_already_accepted_raises(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
        )
        invitation.accept(uuid.uuid4())
        with pytest.raises(InvitationAlreadyAcceptedError):
            invitation.accept(uuid.uuid4())

    def test_accept_revoked_raises(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
        )
        invitation.revoke()
        with pytest.raises(InvitationRevokedError):
            invitation.accept(uuid.uuid4())

    def test_accept_expired_raises(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
            ttl_hours=0,  # expires immediately
        )
        with pytest.raises(InvitationExpiredError):
            invitation.accept(uuid.uuid4())


class TestStaffInvitationRevoke:
    def test_revoke_success(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
        )
        invitation.revoke()
        assert invitation.status == InvitationStatus.REVOKED

    def test_revoke_already_accepted_raises(self):
        invitation = StaffInvitation.create(
            email="test@example.com",
            invited_by=uuid.uuid4(),
            role_ids=[uuid.uuid4()],
            raw_token="token",
        )
        invitation.accept(uuid.uuid4())
        with pytest.raises(InvitationNotPendingError):
            invitation.revoke()


class TestHashToken:
    def test_hash_produces_consistent_result(self):
        hash1 = StaffInvitation.hash_token("same-token")
        hash2 = StaffInvitation.hash_token("same-token")
        assert hash1 == hash2

    def test_hash_differs_for_different_tokens(self):
        hash1 = StaffInvitation.hash_token("token-a")
        hash2 = StaffInvitation.hash_token("token-b")
        assert hash1 != hash2
```

- [ ] **Step 3: Add StaffInvitedEvent and StaffInvitationAcceptedEvent to events.py**

**IMPORTANT:** Add `from dataclasses import field` to imports at top of `events.py` (needed for `default_factory`).

Append to `src/modules/identity/domain/events.py`:

```python
@dataclass
class StaffInvitedEvent(DomainEvent):
    """Emitted when a staff member is invited."""

    aggregate_type: str = "StaffInvitation"
    event_type: str = "staff_invited"

    invitation_id: uuid.UUID | None = None
    email: str = ""
    invited_by: uuid.UUID | None = None
    role_ids: list[uuid.UUID] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate required fields and set aggregate_id."""
        if not self.email:
            raise ValueError("email is required for StaffInvitedEvent")
        if not self.aggregate_id and self.invitation_id:
            self.aggregate_id = str(self.invitation_id)


@dataclass
class StaffInvitationAcceptedEvent(DomainEvent):
    """Emitted when a staff invitation is accepted."""

    aggregate_type: str = "StaffInvitation"
    event_type: str = "staff_invitation_accepted"

    invitation_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    email: str = ""

    def __post_init__(self) -> None:
        """Validate required fields and set aggregate_id."""
        if not self.email:
            raise ValueError("email is required for StaffInvitationAcceptedEvent")
        if not self.aggregate_id and self.invitation_id:
            self.aggregate_id = str(self.invitation_id)
```

> **Pattern note:** All existing events in this file auto-populate `aggregate_id` in `__post_init__`. The new events must follow the same pattern, otherwise outbox persistence will have empty `aggregate_id`.

- [ ] **Step 4: Add StaffInvitation entity to entities.py**

**IMPORTANT:** The existing entities use `from attr import dataclass` (attrs library), NOT `from dataclasses import dataclass`. The StaffInvitation entity MUST use the same attrs `@dataclass` decorator to match `Identity`, `Session`, and other entities in this file.

Update imports at top of `src/modules/identity/domain/entities.py`:

```python
from src.modules.identity.domain.events import (
    IdentityDeactivatedEvent,
    IdentityReactivatedEvent,
    StaffInvitationAcceptedEvent,
    StaffInvitedEvent,
)
from src.modules.identity.domain.exceptions import (
    IdentityDeactivatedError,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotPendingError,
    InvitationRevokedError,
    RefreshTokenReuseError,
    SessionExpiredError,
    SessionRevokedError,
)
from src.modules.identity.domain.value_objects import AccountType, IdentityType, InvitationStatus
```

Then append the `StaffInvitation` entity class as specified in the SPEC (Section 2.1.3). Use attrs `@dataclass` decorator (already imported). Use `hashlib`, `uuid`, `datetime`, `timedelta` — all already imported.

- [ ] **Step 7: commit**

```bash
git add src/modules/identity/domain/entities.py src/modules/identity/domain/events.py tests/unit/modules/identity/domain/test_staff_invitation.py
git commit -m "feat(identity): add StaffInvitation entity with lifecycle management"
```

---

## Task 6: Customer + StaffMember Entities (User BC)

**Files:**

- Rewrite: `src/modules/user/domain/entities.py`
- Rewrite: `src/modules/user/domain/interfaces.py`
- Modify: `src/modules/user/domain/exceptions.py`
- Create: `src/modules/user/domain/services.py`
- Create: `tests/unit/modules/user/domain/test_customer.py`
- Create: `tests/unit/modules/user/domain/test_staff_member.py`
- Create: `tests/unit/modules/user/domain/test_referral_code.py`

- [ ] **Step 1: Write Customer entity tests**

```python
# tests/unit/modules/user/domain/test_customer.py
import uuid

from src.modules.user.domain.entities import Customer


class TestCustomerCreate:
    def test_create_from_identity(self):
        identity_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            profile_email="test@example.com",
            referral_code="ABC12345",
        )
        assert customer.id == identity_id
        assert customer.profile_email == "test@example.com"
        assert customer.referral_code == "ABC12345"
        assert customer.referred_by is None
        assert customer.first_name == ""
        assert customer.last_name == ""

    def test_create_with_referrer(self):
        referrer_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            referral_code="XYZ99999",
            referred_by=referrer_id,
        )
        assert customer.referred_by == referrer_id


class TestCustomerUpdate:
    def test_update_profile_partial(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(), referral_code="AAA11111"
        )
        old_updated = customer.updated_at
        customer.update_profile(first_name="John")
        assert customer.first_name == "John"
        assert customer.last_name == ""
        assert customer.updated_at >= old_updated


class TestCustomerAnonymize:
    def test_anonymize_clears_pii_keeps_referral(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            profile_email="test@example.com",
            referral_code="KEEP1234",
        )
        customer.update_profile(first_name="John", last_name="Doe", phone="+123")
        customer.anonymize()
        assert customer.first_name == "[DELETED]"
        assert customer.last_name == "[DELETED]"
        assert customer.phone is None
        assert customer.profile_email is None
        assert customer.referral_code == "KEEP1234"  # NOT PII
```

- [ ] **Step 2: Write StaffMember entity tests**

```python
# tests/unit/modules/user/domain/test_staff_member.py
import uuid

from src.modules.user.domain.entities import StaffMember


class TestStaffMemberCreate:
    def test_create_from_invitation(self):
        identity_id = uuid.uuid4()
        invited_by = uuid.uuid4()
        staff = StaffMember.create_from_invitation(
            identity_id=identity_id,
            profile_email="staff@company.com",
            invited_by=invited_by,
            first_name="Jane",
            last_name="Doe",
        )
        assert staff.id == identity_id
        assert staff.first_name == "Jane"
        assert staff.invited_by == invited_by
        assert staff.position is None
        assert staff.department is None


class TestStaffMemberUpdate:
    def test_update_position_and_department(self):
        staff = StaffMember.create_from_invitation(
            identity_id=uuid.uuid4(),
            profile_email="s@c.com",
            invited_by=uuid.uuid4(),
        )
        staff.update_profile(position="CTO", department="Engineering")
        assert staff.position == "CTO"
        assert staff.department == "Engineering"
```

- [ ] **Step 3: Write referral code tests**

```python
# tests/unit/modules/user/domain/test_referral_code.py
from src.modules.user.domain.services import generate_referral_code


class TestReferralCodeGeneration:
    def test_default_length_is_8(self):
        code = generate_referral_code()
        assert len(code) == 8

    def test_custom_length(self):
        code = generate_referral_code(length=12)
        assert len(code) == 12

    def test_excludes_ambiguous_chars(self):
        for _ in range(100):
            code = generate_referral_code()
            assert "O" not in code
            assert "0" not in code
            assert "I" not in code
            assert "1" not in code
            assert "L" not in code

    def test_unique_codes(self):
        codes = {generate_referral_code() for _ in range(1000)}
        assert len(codes) == 1000  # no collisions in 1000 generations
```

- [ ] **Step 5: Implement entities, interfaces, services, exceptions**

Implement as specified in SPEC Section 2.2. Key files:

- `src/modules/user/domain/entities.py` — replace `User` with `Customer` + `StaffMember`
- `src/modules/user/domain/interfaces.py` — replace `IUserRepository` with `ICustomerRepository` + `IStaffMemberRepository`
- `src/modules/user/domain/services.py` — `generate_referral_code()`
- `src/modules/user/domain/exceptions.py` — add `CustomerNotFoundError`, `StaffMemberNotFoundError`

**IMPORTANT:** Keep the old `User` class temporarily with `# deprecated` comment. Other modules still reference it. We'll remove it in Task 8 when consumers are updated.

- [ ] **Step 7: commit**

```bash
git add src/modules/user/domain/ tests/unit/modules/user/domain/
git commit -m "feat(user): add Customer and StaffMember aggregates with referral code generation"
```

---

## Task 7: IStaffInvitationRepository Interface

**Files:**

- Modify: `src/modules/identity/domain/interfaces.py`

- [ ] **Step 1: Add IStaffInvitationRepository interface**

Append to `src/modules/identity/domain/interfaces.py`:

```python
class IStaffInvitationRepository(Protocol):
    """Repository interface for StaffInvitation aggregate."""

    async def add(self, invitation: StaffInvitation) -> StaffInvitation:
        """Persist a new staff invitation."""
        ...

    async def get(self, invitation_id: uuid.UUID) -> StaffInvitation | None:
        """Get invitation by ID."""
        ...

    async def get_by_token_hash(self, token_hash: str) -> StaffInvitation | None:
        """Get invitation by SHA-256 token hash."""
        ...

    async def get_pending_by_email(self, email: str) -> StaffInvitation | None:
        """Get active (PENDING) invitation for the given email."""
        ...

    async def update(self, invitation: StaffInvitation) -> None:
        """Update an existing invitation."""
        ...

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 20,
        status: InvitationStatus | None = None,
    ) -> tuple[list[StaffInvitation], int]:
        """List invitations with optional status filter. Returns (items, total)."""
        ...
```

Add necessary imports: `StaffInvitation`, `InvitationStatus`.

- [ ] **Step 2: commit**

```bash
git add src/modules/identity/domain/interfaces.py
git commit -m "feat(identity): add IStaffInvitationRepository interface"
```

---

## Task 8: Alembic Migrations

**Files:**

- Create: 5 migration files in `alembic/versions/2026/03/`

> **IMPORTANT:** These migrations must be created using `uv run alembic revision --autogenerate` AFTER updating ORM models. This task and Task 9 (ORM models) are done together.

- [ ] **Step 1: Update IdentityModel — add `account_type` column**

In `src/modules/identity/infrastructure/models.py`, add to `IdentityModel`:

```python
account_type = Column(String(10), nullable=False, server_default="CUSTOMER", index=True)
```

- [ ] **Step 2: Create StaffInvitationModel + StaffInvitationRoleModel**

In `src/modules/identity/infrastructure/models.py`, add new ORM models:

```python
class StaffInvitationModel(Base):
    __tablename__ = "staff_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(320), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("identities.id"), nullable=False)
    status = Column(String(10), nullable=False, server_default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_identity_id = Column(UUID(as_uuid=True), ForeignKey("identities.id"), nullable=True)


class StaffInvitationRoleModel(Base):
    __tablename__ = "staff_invitation_roles"

    invitation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("staff_invitations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id"),
        primary_key=True,
    )
```

- [ ] **Step 3: Create CustomerModel + StaffMemberModel (User BC)**

In `src/modules/user/infrastructure/models.py`:

Rename `UserModel` to `CustomerModel`, add referral columns:

```python
class CustomerModel(Base):
    __tablename__ = "customers"
    # ... existing columns (id, profile_email, first_name, last_name, phone, timestamps)
    referral_code = Column(String(12), unique=True, nullable=True)
    referred_by = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
```

Add new `StaffMemberModel`:

```python
class StaffMemberModel(Base):
    __tablename__ = "staff_members"

    id = Column(UUID(as_uuid=True), ForeignKey("identities.id", ondelete="CASCADE"), primary_key=True)
    first_name = Column(String(100), nullable=False, server_default="")
    last_name = Column(String(100), nullable=False, server_default="")
    profile_email = Column(String(320), nullable=True)
    position = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("identities.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Step 4: Generate migrations**

Run: `uv run alembic revision --autogenerate -m "add account_type to identities and create staff tables"`

Review generated migration — verify it:

1. Adds `account_type` column to `identities` with DEFAULT
2. Creates `staff_invitations` + `staff_invitation_roles` tables
3. Renames `users` → `customers` + adds referral columns
4. Creates `staff_members` table

- [ ] **Step 5: Add data migration for backfill**

Create a separate data migration:

Run: `uv run alembic revision -m "backfill account_type and migrate staff data"`

Edit the generated file to add backfill SQL (from SPEC Section 3.1-3.3).

- [ ] **Step 6: Add new permissions migration**

Run: `uv run alembic revision -m "add staff and customer permissions"`

Add the SQL from SPEC Section 3.5.

- [ ] **Step 7: Test migrations (if Docker is running)**

Run: `uv run alembic upgrade head`
Expected: No errors

Run: `uv run alembic downgrade -1` (test rollback)

- [ ] **Step 8: Commit**

```bash
git add src/modules/identity/infrastructure/models.py src/modules/user/infrastructure/models.py alembic/
git commit -m "feat: add database schema for users/staff separation with migrations"
```

---

## Task 9: Repository Implementations

**Files:**

- Create: `src/modules/identity/infrastructure/repositories/staff_invitation_repository.py`
- Create: `src/modules/user/infrastructure/repositories/customer_repository.py`
- Create: `src/modules/user/infrastructure/repositories/staff_member_repository.py`

> Each repository follows the existing Data Mapper pattern (see `UserRepository` for reference).

- [ ] **Step 1: Implement StaffInvitationRepository**

Data Mapper: `StaffInvitation` entity ↔ `StaffInvitationModel` + `StaffInvitationRoleModel`

Key methods: `add()`, `get()`, `get_by_token_hash()`, `get_pending_by_email()`, `update()`, `list_all()`

- [ ] **Step 2: Implement CustomerRepository**

Based on existing `UserRepository`, rename + add `get_by_referral_code()`.

- [ ] **Step 3: Implement StaffMemberRepository**

Similar pattern to CustomerRepository but for `staff_members` table.

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/infrastructure/repositories/ src/modules/user/infrastructure/repositories/
git commit -m "feat: add repository implementations for StaffInvitation, Customer, StaffMember"
```

---

## Task 10: AssignRoleHandler — Static SoD

**Files:**

- Modify: `src/modules/identity/application/commands/assign_role.py`
- Create: `tests/unit/modules/identity/application/commands/test_assign_role_sod.py`

- [ ] **Step 1: Write SoD test**

```python
# tests/unit/modules/identity/application/commands/test_assign_role_sod.py
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.identity.application.commands.assign_role import (
    AssignRoleCommand,
    AssignRoleHandler,
)
from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.exceptions import AccountTypeMismatchError
from src.modules.identity.domain.value_objects import AccountType, IdentityType


class TestAssignRoleSoD:
    async def test_customer_cannot_get_admin_role(self):
        identity = Identity.register(IdentityType.LOCAL, AccountType.CUSTOMER)
        role = MagicMock()
        role.name = "admin"

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get.return_value = role

        handler = AssignRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=AsyncMock(),
            uow=AsyncMock(),
            logger=MagicMock(),
        )
        cmd = AssignRoleCommand(
            identity_id=identity.id, role_id=uuid.uuid4()
        )
        with pytest.raises(AccountTypeMismatchError):
            await handler.handle(cmd)

    async def test_staff_cannot_get_customer_role(self):
        identity = Identity.register(IdentityType.LOCAL, AccountType.STAFF)
        role = MagicMock()
        role.name = "customer"

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get.return_value = role

        handler = AssignRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=AsyncMock(),
            uow=AsyncMock(),
            logger=MagicMock(),
        )
        cmd = AssignRoleCommand(
            identity_id=identity.id, role_id=uuid.uuid4()
        )
        with pytest.raises(AccountTypeMismatchError):
            await handler.handle(cmd)
```

- [ ] **Step 3: Add SoD check to AssignRoleHandler**

In `src/modules/identity/application/commands/assign_role.py`, after fetching identity and role, add:

```python
from src.modules.identity.domain.exceptions import AccountTypeMismatchError
from src.modules.identity.domain.value_objects import AccountType

_STAFF_ROLE_NAMES = frozenset({
    "admin", "content_manager", "order_manager",
    "support_specialist", "review_moderator",
})

# In handle() method, after identity and role are fetched:
if identity.account_type == AccountType.CUSTOMER and role.name in _STAFF_ROLE_NAMES:
    raise AccountTypeMismatchError()
if identity.account_type == AccountType.STAFF and role.name == "customer":
    raise AccountTypeMismatchError()
```

- [ ] **Step 6: Commit**

```bash
git add src/modules/identity/application/commands/assign_role.py tests/unit/modules/identity/application/commands/test_assign_role_sod.py
git commit -m "feat(identity): add Static Separation of Duties to AssignRoleHandler"
```

---

## Task 11: RegisterHandler — explicit CUSTOMER

**Files:**

- Modify: `src/modules/identity/application/commands/register.py`

- [ ] **Step 1: Update RegisterHandler**

In `register.py`, where `Identity.register(IdentityType.LOCAL)` is called, add explicit `AccountType.CUSTOMER`:

```python
from src.modules.identity.domain.value_objects import AccountType

# In handle():
identity = Identity.register(IdentityType.LOCAL, AccountType.CUSTOMER)
```

Where `IdentityRegisteredEvent` is created, add `account_type`:

```python
IdentityRegisteredEvent(
    identity_id=identity.id,
    email=command.email,
    registered_at=identity.created_at,
    account_type=AccountType.CUSTOMER.value,
    aggregate_id=str(identity.id),
)
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/identity/application/commands/register.py
git commit -m "feat(identity): explicit CUSTOMER account_type in RegisterHandler"
```

---

## Task 12: Command Handlers — InviteStaff, AcceptInvitation, RevokeInvitation

**Files:**

- Create: `src/modules/identity/application/commands/invite_staff.py`
- Create: `src/modules/identity/application/commands/accept_staff_invitation.py`
- Create: `src/modules/identity/application/commands/revoke_staff_invitation.py`
- Create: `tests/unit/modules/identity/application/commands/test_invite_staff.py`
- Create: `tests/unit/modules/identity/application/commands/test_accept_invitation.py`

> These handlers follow the exact patterns from SPEC Section 5. Each handler uses constructor injection with Dishka, follows CQRS command pattern, and commits through UoW.

- [ ] **Step 1: Write InviteStaff test**

Test happy path + edge cases (email already registered, pending invitation exists, roles not found).

- [ ] **Step 2: Implement InviteStaffHandler**

Follow SPEC Section 5.1 flow exactly.

- [ ] **Step 3: Run test — expect PASS**

- [ ] **Step 4: Write AcceptStaffInvitation test**

Test happy path + expired token + already accepted + creates Identity(STAFF).

- [ ] **Step 5: Implement AcceptStaffInvitationHandler**

Follow SPEC Section 5.2 flow. This is the most complex handler — it creates Identity, credentials, assigns roles, marks invitation accepted, creates session, returns tokens.

- [ ] **Step 6: Run test — expect PASS**

- [ ] **Step 7: Implement RevokeStaffInvitationHandler**

Simple handler — get invitation, call `revoke()`, update, commit.

- [ ] **Step 9: commit**

```bash

git add src/modules/identity/application/commands/invite_staff.py src/modules/identity/application/commands/accept_staff_invitation.py src/modules/identity/application/commands/revoke_staff_invitation.py tests/unit/modules/identity/application/commands/
git commit -m "feat(identity): add InviteStaff, AcceptInvitation, RevokeInvitation command handlers"
```

---

## Task 13: Query Handlers — ListStaff, ListCustomers, ListInvitations, ValidateToken

**Files:**

- Create: `src/modules/identity/application/queries/list_staff.py`
- Create: `src/modules/identity/application/queries/list_customers.py`
- Create: `src/modules/identity/application/queries/list_staff_invitations.py`
- Create: `src/modules/identity/application/queries/validate_invitation.py`
- Create: `src/modules/identity/application/queries/get_staff_detail.py`
- Create: `src/modules/identity/application/queries/get_customer_detail.py`

> Follow the existing `ListIdentitiesHandler` pattern — raw SQL via `sqlalchemy.text()`, direct `AsyncSession`, return Pydantic read models.

- [ ] **Step 1: Implement ListStaffHandler with SQL from SPEC Section 6.1**

- [ ] **Step 2: Implement ListCustomersHandler with SQL from SPEC Section 6.2**

- [ ] **Step 3: Implement ListStaffInvitationsHandler with SQL from SPEC Section 6.3**

- [ ] **Step 4: Implement ValidateInvitationTokenHandler with SQL from SPEC Section 6.4**

- [ ] **Step 5: Implement GetStaffDetailHandler and GetCustomerDetailHandler**

Similar to existing `GetIdentityDetailHandler` but scoped to account_type.

- [ ] **Step 6: commit**

```bash
git add src/modules/identity/application/queries/
git commit -m "feat(identity): add ListStaff, ListCustomers, ListInvitations, ValidateToken query handlers"
```

---

## Task 14: Event Consumers — Route by account_type

**Files:**

- Rewrite: `src/modules/user/application/consumers/identity_events.py`
- Modify: `src/modules/user/application/commands/` — add CreateCustomerHandler, CreateStaffMemberHandler, AnonymizeCustomerHandler

> Follow SPEC Section 7. The consumer becomes a dispatcher routing by `account_type`.

- [ ] **Step 1: Create CreateCustomerHandler (replaces CreateUserHandler)**

Add `referral_code` generation via `generate_referral_code()`.

- [ ] **Step 2: Create CreateStaffMemberHandler**

Creates StaffMember with `invited_by` from event data.

- [ ] **Step 3: Create AnonymizeCustomerHandler (replaces AnonymizeUserHandler)**

Customer: full anonymization. Staff: skip (GDPR legitimate interest).

- [ ] **Step 3b: Update `get_user_by_identity.py` query**

This query references the `users` table which is being renamed to `customers`. Update it to query `customers` table instead, or replace with separate `get_customer_by_identity` / `get_staff_by_identity` helpers.

- [ ] **Step 4: Rewrite consumer to route by account_type**

The consumer function reads `account_type` from event payload and dispatches to the appropriate handler.

- [ ] **Step 5: Update tests**

- [ ] **Step 6: Commit**

```bash
git add src/modules/user/application/
git commit -m "feat(user): split event consumers to route Customer/Staff by account_type"
```

---

## Task 15: Pydantic Schemas + Routers

**Files:**

- Modify: `src/modules/identity/presentation/schemas.py`
- Create: `src/modules/identity/presentation/router_staff.py`
- Create: `src/modules/identity/presentation/router_customers.py`
- Create: `src/modules/identity/presentation/router_invitation.py`
- Modify: `src/api/router.py`

> Follow SPEC Section 4 for exact schema definitions and endpoint contracts.

- [ ] **Step 1: Add all new schemas to schemas.py**

Staff schemas, Customer schemas, Invitation schemas as specified in SPEC Section 4.4.

- [ ] **Step 2: Create router_staff.py**

Mount at `/admin/staff` with `RequirePermission("staff:manage")`.

- [ ] **Step 3: Create router_customers.py**

Mount at `/admin/customers` with `RequirePermission("customers:read")`.

- [ ] **Step 4: Create router_invitation.py**

Mount at `/invitations` — public endpoints (no auth).

- [ ] **Step 5: Add `account_type` filter + deprecation to existing `/admin/identities`**

In `src/modules/identity/presentation/router_admin.py`, update `list_identities()`:

- Add optional query param: `account_type: str | None = None`
- Pass to `ListIdentitiesQuery` (add field there too)
- Add `deprecated=True` to the `@router.get` decorator

In `src/modules/identity/application/queries/list_identities.py`:

- Add `account_type` field to `ListIdentitiesQuery`
- Add WHERE clause: `if query.account_type: where_clauses.append("i.account_type = :account_type")`

- [ ] **Step 6: Mount routers in api/router.py**

```python
router.include_router(staff_admin_router)       # /admin/staff
router.include_router(customers_admin_router)    # /admin/customers
router.include_router(invitation_router)         # /invitations
```

- [ ] **Step 7: Commit**

```bash
git add src/modules/identity/presentation/ src/api/router.py
git commit -m "feat(identity): add Staff, Customer, Invitation admin routers and schemas"
```

---

## Task 16: DI Registration + Seed Update

**Files:**

- Modify: `src/modules/identity/infrastructure/provider.py`
- Modify: `src/modules/user/infrastructure/provider.py`
- Modify: `scripts/seed_dev.sql`

- [ ] **Step 1: Register new handlers in IdentityProvider**

Add to `IdentityProvider`:

- `staff_invitation_repo: IStaffInvitationRepository = StaffInvitationRepository`
- `invite_staff_handler: InviteStaffHandler`
- `accept_invitation_handler: AcceptStaffInvitationHandler`
- `revoke_invitation_handler: RevokeStaffInvitationHandler`
- All new query handlers (list_staff, list_customers, list_invitations, validate_invitation, get_staff_detail, get_customer_detail)

- [ ] **Step 2: Update UserProvider**

Replace `IUserRepository → ICustomerRepository + IStaffMemberRepository`.
Replace old handlers with new ones.

- [ ] **Step 3: Update seed_dev.sql**

- Add `account_type = 'STAFF'` for dev admin
- Create `staff_members` row for dev admin
- Add new permissions (`staff:manage`, `staff:invite`, `customers:read`, `customers:manage`)
- Update role-permission assignments

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/infrastructure/provider.py src/modules/user/infrastructure/provider.py scripts/seed_dev.sql
git commit -m "feat: register new DI providers and update seed data for users/staff separation"
```

---

## Task 17: User Profile Router + Schema Update

**Files:**

- Modify: `src/modules/user/presentation/router.py`
- Modify: `src/modules/user/presentation/schemas.py`

- [ ] **Step 1: Update router to use ICustomerRepository**

Change from `IUserRepository` to `ICustomerRepository` in the profile endpoints.

- [ ] **Step 2: Add `referral_code` to UserProfileResponse**
- [ ] **Step 4: Commit**

```bash
git add src/modules/user/presentation/
git commit -m "feat(user): update profile router to use CustomerRepository"
```

---

## Task 18: Final Quality Gates + Architecture Test Update

**Files:**

- Modify: `tests/architecture/test_boundaries.py` (if needed)

- [ ] **Step 2: Fix any architecture boundary violations**

New modules must follow existing boundary rules:

- Domain layer: zero framework imports
- No cross-module imports (except allowed exceptions)
- Application layer: no infrastructure imports

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete users/staff separation — all quality gates pass"
```
