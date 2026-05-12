# SPEC: Разделение Users / Staff — Техническая спецификация

> **Дата:** 2026-03-19
> **Статус:** Ready for Implementation
> **Входные документы:**
>
> - Backend Current State Analysis (1073 строки)
> - Deep Research: 15+ платформ, 50+ источников
> - Gap Analysis: 42 аспекта, 7 critical / 9 major / 6 minor / 20 OK
>
> **Architectural Decision:** Separate Tables + AccountType discriminator в Identity
> (Score 4/5: Shopify ✅, Medusa ✅, Azure AD ✅, Sylius ✅, Saleor ❌)

---

## 1. Архитектурное решение

### 1.1 Целевая архитектура

```
Identity BC (аутентификация)                 User BC (профили)
┌─────────────────────────────┐    ┌──────────────────────────────────┐
│ Identity (aggregate root)   │    │ Customer (aggregate root) ← NEW  │
│   + account_type: AccountType│    │   shared PK → identities.id     │
│   type: IdentityType        │    │   referral_code, referred_by     │
│   is_active, deactivated_*  │    │   first_name, last_name, phone   │
│                             │    │                                  │
│ LocalCredentials            │    │ StaffMember (aggregate root) ← NEW│
│ Session + activated_roles   │    │   shared PK → identities.id     │
│ Role + Permission           │    │   first_name, last_name          │
│ LinkedAccount               │    │   position, department           │
│                             │    │   invited_by                     │
│ StaffInvitation ← NEW       │    │                                  │
│   token_hash, role_ids      │    └──────────────────────────────────┘
│   status lifecycle          │
└─────────────────────────────┘

Events:
  IdentityRegisteredEvent (+ account_type)
    → if CUSTOMER → CreateCustomerHandler → auto-gen referral_code
    → if STAFF    → CreateStaffMemberHandler
  IdentityDeactivatedEvent
    → if CUSTOMER → AnonymizeCustomerHandler
    → if STAFF    → DeactivateStaffMemberHandler
  StaffInvitedEvent ← NEW
  StaffInvitationAcceptedEvent ← NEW
```

### 1.2 Что НЕ меняется

- Identity BC auth flow (register, login, logout, refresh, OIDC)
- Session-Role Activation (NIST Dynamic RBAC)
- Recursive CTE permission resolution + Redis cache-aside
- Transactional Outbox + TaskIQ consumers
- Architecture boundary tests (7 rules)
- JWT structure (sub, sid, exp, iat, jti)

---

## 2. Domain Model — Exact Specifications

### 2.1 Identity BC — Изменения

#### 2.1.1 Value Object: `AccountType`

**Файл:** `src/modules/identity/domain/value_objects.py`

```python
class AccountType(enum.StrEnum):
    """Тип аккаунта — определяет жизненный цикл и доступные роли.

    Immutable после создания Identity (как Okta User Types).

    Attributes:
        CUSTOMER: Покупатель платформы. Самостоятельная регистрация.
        STAFF: Внутренний сотрудник. Регистрация по приглашению.
    """

    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
```

#### 2.1.2 Entity: `Identity` — новое поле

**Файл:** `src/modules/identity/domain/entities.py`

```python
@dataclass
class Identity(AggregateRoot):
    id: uuid.UUID
    type: IdentityType              # LOCAL | OIDC (auth method)
    account_type: AccountType       # ← NEW: CUSTOMER | STAFF
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None
    deactivated_by: uuid.UUID | None = None
```

**Изменения в методах:**

```python
@classmethod
def register(cls, identity_type: IdentityType, account_type: AccountType = AccountType.CUSTOMER) -> Identity:
    """Фабрика. account_type по умолчанию CUSTOMER для обратной совместимости."""
    now = datetime.now(UTC)
    return cls(
        id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
        type=identity_type,
        account_type=account_type,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

@classmethod
def register_staff(cls, identity_type: IdentityType = IdentityType.LOCAL) -> Identity:
    """Фабрика для staff. Вызывается из AcceptStaffInvitationHandler."""
    return cls.register(identity_type, AccountType.STAFF)
```

**Инвариант:** `account_type` не может быть изменён после создания. Нет setter/method для изменения.

#### 2.1.3 Entity: `StaffInvitation` — НОВЫЙ aggregate

**Файл:** `src/modules/identity/domain/entities.py` (добавить в конец)

```python
@dataclass
class StaffInvitation(AggregateRoot):
    """Приглашение сотрудника.

    Lifecycle: PENDING → ACCEPTED | EXPIRED | REVOKED
    Token: CSPRNG 256 бит → SHA-256 hash в БД.
    TTL: 72 часа (конфигурируемо).

    Attributes:
        id: Unique invitation identifier.
        email: Email приглашённого.
        token_hash: SHA-256 hash invite-токена.
        role_ids: Роли, назначаемые при принятии.
        invited_by: identity_id пригласившего.
        status: Текущий статус приглашения.
        created_at: Когда создано.
        expires_at: Когда истекает.
        accepted_at: Когда принято (None если не принято).
        accepted_identity_id: identity_id принявшего (None если не принято).
    """

    id: uuid.UUID
    email: str
    token_hash: str
    role_ids: list[uuid.UUID]
    invited_by: uuid.UUID
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_identity_id: uuid.UUID | None = None

    @classmethod
    def create(
        cls,
        email: str,
        invited_by: uuid.UUID,
        role_ids: list[uuid.UUID],
        raw_token: str,
        ttl_hours: int = 72,
    ) -> StaffInvitation:
        """Фабрика. raw_token генерируется в command handler через secrets.token_urlsafe(32)."""
        now = datetime.now(UTC)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        invitation = cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            email=email,
            token_hash=token_hash,
            role_ids=list(role_ids),
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        )
        invitation.add_domain_event(
            StaffInvitedEvent(
                invitation_id=invitation.id,
                email=email,
                invited_by=invited_by,
                role_ids=role_ids,
                aggregate_id=str(invitation.id),
            )
        )
        return invitation

    def accept(self, identity_id: uuid.UUID) -> None:
        """Принять приглашение. Вызывается после создания Identity + StaffMember."""
        if self.status != InvitationStatus.PENDING:
            if self.status == InvitationStatus.ACCEPTED:
                raise InvitationAlreadyAcceptedError()
            if self.status == InvitationStatus.REVOKED:
                raise InvitationRevokedError()
            raise InvitationExpiredError()
        if datetime.now(UTC) > self.expires_at:
            self.status = InvitationStatus.EXPIRED
            raise InvitationExpiredError()
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = datetime.now(UTC)
        self.accepted_identity_id = identity_id
        self.add_domain_event(
            StaffInvitationAcceptedEvent(
                invitation_id=self.id,
                identity_id=identity_id,
                email=self.email,
                aggregate_id=str(self.id),
            )
        )

    def revoke(self) -> None:
        """Отозвать приглашение. Только PENDING → REVOKED."""
        if self.status != InvitationStatus.PENDING:
            raise InvitationNotPendingError()
        self.status = InvitationStatus.REVOKED

    def is_expired(self) -> bool:
        """Проверить истечение срока."""
        return datetime.now(UTC) > self.expires_at

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """SHA-256 hash для lookup по токену."""
        return hashlib.sha256(raw_token.encode()).hexdigest()
```

#### 2.1.4 Value Object: `InvitationStatus`

**Файл:** `src/modules/identity/domain/value_objects.py`

```python
class InvitationStatus(enum.StrEnum):
    """Статус приглашения сотрудника."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
```

#### 2.1.5 Domain Events — НОВЫЕ

**Файл:** `src/modules/identity/domain/events.py`

```python
@dataclass(frozen=True)
class StaffInvitedEvent(DomainEvent):
    """Сотрудник приглашён."""

    aggregate_type: str = "StaffInvitation"
    event_type: str = "staff_invited"

    invitation_id: uuid.UUID
    email: str
    invited_by: uuid.UUID
    role_ids: list[uuid.UUID]


@dataclass(frozen=True)
class StaffInvitationAcceptedEvent(DomainEvent):
    """Приглашение принято, Identity + StaffMember созданы."""

    aggregate_type: str = "StaffInvitation"
    event_type: str = "staff_invitation_accepted"

    invitation_id: uuid.UUID
    identity_id: uuid.UUID
    email: str
```

**Изменение в `IdentityRegisteredEvent`:**

```python
@dataclass(frozen=True)
class IdentityRegisteredEvent(DomainEvent):
    aggregate_type: str = "Identity"
    event_type: str = "identity_registered"

    identity_id: uuid.UUID
    email: str
    registered_at: datetime
    account_type: str  # ← NEW: "CUSTOMER" | "STAFF"
```

#### 2.1.6 Exceptions — НОВЫЕ

**Файл:** `src/modules/identity/domain/exceptions.py`

```python
class InvitationNotFoundError(NotFoundError):
    """Приглашение не найдено."""
    def __init__(self) -> None:
        super().__init__(message="Staff invitation not found", error_code="INVITATION_NOT_FOUND")

class InvitationExpiredError(AppException):
    """Приглашение истекло."""
    def __init__(self) -> None:
        super().__init__(message="Staff invitation has expired", status_code=410, error_code="INVITATION_EXPIRED")

class InvitationAlreadyAcceptedError(ConflictError):
    """Приглашение уже принято."""
    def __init__(self) -> None:
        super().__init__(message="Staff invitation already accepted", error_code="INVITATION_ALREADY_ACCEPTED")

class InvitationRevokedError(ForbiddenError):
    """Приглашение отозвано."""
    def __init__(self) -> None:
        super().__init__(message="Staff invitation has been revoked", error_code="INVITATION_REVOKED")

class InvitationNotPendingError(ConflictError):
    """Приглашение не в статусе PENDING."""
    def __init__(self) -> None:
        super().__init__(message="Invitation is not in pending status", error_code="INVITATION_NOT_PENDING")

class ActiveInvitationExistsError(ConflictError):
    """Активное приглашение для этого email уже существует."""
    def __init__(self) -> None:
        super().__init__(message="Active invitation for this email already exists", error_code="ACTIVE_INVITATION_EXISTS")

class AccountTypeMismatchError(ForbiddenError):
    """Роль несовместима с типом аккаунта."""
    def __init__(self) -> None:
        super().__init__(message="Role is not compatible with account type", error_code="ACCOUNT_TYPE_MISMATCH")
```

#### 2.1.7 Repository Interface: `IStaffInvitationRepository`

**Файл:** `src/modules/identity/domain/interfaces.py`

```python
class IStaffInvitationRepository(Protocol):
    """Repository interface for StaffInvitation aggregate."""

    async def add(self, invitation: StaffInvitation) -> StaffInvitation: ...
    async def get(self, invitation_id: uuid.UUID) -> StaffInvitation | None: ...
    async def get_by_token_hash(self, token_hash: str) -> StaffInvitation | None: ...
    async def get_pending_by_email(self, email: str) -> StaffInvitation | None: ...
    async def update(self, invitation: StaffInvitation) -> None: ...
    async def list_all(
        self, offset: int = 0, limit: int = 20, status: InvitationStatus | None = None
    ) -> tuple[list[StaffInvitation], int]: ...
```

### 2.2 User BC — Разделение на Customer / StaffMember

#### 2.2.1 Entity: `Customer` (заменяет `User`)

**Файл:** `src/modules/user/domain/entities.py`

```python
_CUSTOMER_UPDATABLE_FIELDS = frozenset({"profile_email", "first_name", "last_name", "phone"})


@dataclass
class Customer(AggregateRoot):
    """Aggregate root — профиль клиента (покупателя).

    Shared PK с Identity (customer.id == identity.id).
    Referral code генерируется автоматически при создании.

    Attributes:
        id: UUID = identity.id (shared PK).
        profile_email: Отображаемый email (может отличаться от login email).
        first_name: Имя.
        last_name: Фамилия.
        phone: Телефон.
        referral_code: Уникальный реферальный код (8 символов, auto-generated).
        referred_by: customer_id того, кто привёл (None если пришёл сам).
        created_at: Дата создания.
        updated_at: Дата последнего обновления.
    """

    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str
    referred_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_from_identity(
        cls,
        identity_id: uuid.UUID,
        profile_email: str | None = None,
        referral_code: str | None = None,
        referred_by: uuid.UUID | None = None,
    ) -> Customer:
        """Фабрика. referral_code генерируется в handler если не передан."""
        now = datetime.now(UTC)
        return cls(
            id=identity_id,
            profile_email=profile_email,
            first_name="",
            last_name="",
            phone=None,
            referral_code=referral_code or "",
            referred_by=referred_by,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, **kwargs: str | None) -> None:
        """Partial update — только поля из _CUSTOMER_UPDATABLE_FIELDS."""
        for field, value in kwargs.items():
            if field in _CUSTOMER_UPDATABLE_FIELDS:
                setattr(self, field, value)
        self.updated_at = datetime.now(UTC)

    def anonymize(self) -> None:
        """GDPR anonymization. Referral code сохраняется (не PII)."""
        self.first_name = "[DELETED]"
        self.last_name = "[DELETED]"
        self.phone = None
        self.profile_email = None
        self.updated_at = datetime.now(UTC)
```

#### 2.2.2 Entity: `StaffMember`

**Файл:** `src/modules/user/domain/entities.py`

```python
_STAFF_UPDATABLE_FIELDS = frozenset({"first_name", "last_name", "position", "department"})


@dataclass
class StaffMember(AggregateRoot):
    """Aggregate root — профиль сотрудника.

    Shared PK с Identity (staff_member.id == identity.id).
    Создаётся при принятии StaffInvitation.

    Attributes:
        id: UUID = identity.id (shared PK).
        first_name: Имя.
        last_name: Фамилия.
        profile_email: Отображаемый email.
        position: Должность.
        department: Отдел.
        invited_by: identity_id пригласившего.
        created_at: Дата создания.
        updated_at: Дата последнего обновления.
    """

    id: uuid.UUID
    first_name: str
    last_name: str
    profile_email: str | None
    position: str | None
    department: str | None
    invited_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_from_invitation(
        cls,
        identity_id: uuid.UUID,
        profile_email: str | None,
        invited_by: uuid.UUID,
        first_name: str = "",
        last_name: str = "",
    ) -> StaffMember:
        """Фабрика. Вызывается из AcceptStaffInvitationHandler."""
        now = datetime.now(UTC)
        return cls(
            id=identity_id,
            first_name=first_name,
            last_name=last_name,
            profile_email=profile_email,
            position=None,
            department=None,
            invited_by=invited_by,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, **kwargs: str | None) -> None:
        """Partial update — только поля из _STAFF_UPDATABLE_FIELDS."""
        for field, value in kwargs.items():
            if field in _STAFF_UPDATABLE_FIELDS:
                setattr(self, field, value)
        self.updated_at = datetime.now(UTC)
```

#### 2.2.3 Repository Interfaces

**Файл:** `src/modules/user/domain/interfaces.py`

```python
class ICustomerRepository(Protocol):
    async def add(self, customer: Customer) -> Customer: ...
    async def get(self, customer_id: uuid.UUID) -> Customer | None: ...
    async def update(self, customer: Customer) -> None: ...
    async def get_by_referral_code(self, code: str) -> Customer | None: ...

class IStaffMemberRepository(Protocol):
    async def add(self, staff: StaffMember) -> StaffMember: ...
    async def get(self, staff_id: uuid.UUID) -> StaffMember | None: ...
    async def update(self, staff: StaffMember) -> None: ...
```

#### 2.2.4 Referral Code Generation

**Файл:** `src/modules/user/domain/services.py`

```python
import secrets

_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 30 chars, no O/0/I/1/L


def generate_referral_code(length: int = 8) -> str:
    """Генерация уникального реферального кода.

    30^8 ≈ 6.5×10¹¹ комбинаций. Collision probability < 0.0001% при 1M users.
    Uniqueness enforced by UNIQUE constraint в БД; retry при collision.
    """
    return "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(length))
```

---

## 3. Database Schema

### 3.1 Migration 1: `account_type` в `identities`

```sql
-- Non-blocking: ADD COLUMN with DEFAULT
ALTER TABLE identities
    ADD COLUMN account_type VARCHAR(10) NOT NULL DEFAULT 'CUSTOMER';

-- Backfill: staff-роли → STAFF
UPDATE identities SET account_type = 'STAFF'
WHERE id IN (
    SELECT DISTINCT ir.identity_id
    FROM identity_roles ir
    JOIN roles r ON r.id = ir.role_id
    WHERE r.name IN ('admin', 'content_manager', 'order_manager',
                     'support_specialist', 'review_moderator')
);

CREATE INDEX ix_identities_account_type ON identities (account_type);
```

### 3.2 Migration 2: `customers` table (replaces `users`)

```sql
-- Переименовать users → customers, добавить referral-поля
ALTER TABLE users RENAME TO customers;

ALTER TABLE customers
    ADD COLUMN referral_code VARCHAR(12) UNIQUE,
    ADD COLUMN referred_by UUID REFERENCES customers(id);

-- Backfill referral codes для существующих customers
-- (выполняется в Python через domain service, не в SQL)

CREATE INDEX ix_customers_referral_code ON customers (referral_code);
CREATE INDEX ix_customers_referred_by ON customers (referred_by);
```

### 3.3 Migration 3: `staff_members` table

```sql
CREATE TABLE staff_members (
    id UUID PRIMARY KEY REFERENCES identities(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL DEFAULT '',
    last_name VARCHAR(100) NOT NULL DEFAULT '',
    profile_email VARCHAR(320),
    position VARCHAR(100),
    department VARCHAR(100),
    invited_by UUID NOT NULL REFERENCES identities(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Migrate existing staff from customers → staff_members
INSERT INTO staff_members (id, first_name, last_name, profile_email, invited_by, created_at, updated_at)
SELECT c.id, c.first_name, c.last_name, c.profile_email,
       '00000000-0000-0000-0000-000000000099',  -- dev admin as inviter
       c.created_at, c.updated_at
FROM customers c
JOIN identities i ON i.id = c.id
WHERE i.account_type = 'STAFF';

-- Remove migrated staff from customers
DELETE FROM customers
WHERE id IN (SELECT id FROM identities WHERE account_type = 'STAFF');
```

### 3.4 Migration 4: `staff_invitations` table

```sql
CREATE TABLE staff_invitations (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    invited_by UUID NOT NULL REFERENCES identities(id),
    status VARCHAR(10) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    accepted_identity_id UUID REFERENCES identities(id),

    CONSTRAINT chk_invitation_status
        CHECK (status IN ('PENDING', 'ACCEPTED', 'EXPIRED', 'REVOKED'))
);

-- M:M для pre-assigned roles
CREATE TABLE staff_invitation_roles (
    invitation_id UUID NOT NULL REFERENCES staff_invitations(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id),
    PRIMARY KEY (invitation_id, role_id)
);

CREATE INDEX ix_staff_invitations_email ON staff_invitations (email);
CREATE INDEX ix_staff_invitations_status ON staff_invitations (status);
```

### 3.5 Migration 5: Новые permissions

```sql
INSERT INTO permissions (id, codename, resource, action, description) VALUES
    ('b1000000-0000-0000-0000-000000000001', 'staff:manage',     'staff',     'manage',  'Управление сотрудниками'),
    ('b1000000-0000-0000-0000-000000000002', 'staff:invite',     'staff',     'invite',  'Приглашение сотрудников'),
    ('b1000000-0000-0000-0000-000000000003', 'customers:read',   'customers', 'read',    'Просмотр клиентов'),
    ('b1000000-0000-0000-0000-000000000004', 'customers:manage', 'customers', 'manage',  'Управление клиентами');

-- admin gets all new permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000001', id
FROM permissions WHERE codename IN ('staff:manage', 'staff:invite', 'customers:read', 'customers:manage');

-- staff roles get customers:read
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name IN ('content_manager', 'order_manager', 'support_specialist', 'review_moderator')
  AND p.codename = 'customers:read';
```

### 3.6 Целевая ER-диаграмма

```
identities (PK: id)
  + account_type (CUSTOMER | STAFF)     ← NEW
  ├── 1:1 ── local_credentials
  ├── 1:N ── sessions
  │              └── M:M ── session_roles ── roles
  ├── 1:N ── linked_accounts
  ├── M:M ── identity_roles ── roles
  ├── 1:1 ── customers ← RENAMED from users  (if account_type=CUSTOMER)
  │              + referral_code ← NEW
  │              + referred_by   ← NEW
  └── 1:1 ── staff_members ← NEW             (if account_type=STAFF)
                 + position, department ← NEW
                 + invited_by          ← NEW

staff_invitations ← NEW
  ├── M:M ── staff_invitation_roles ── roles
  └── FK ── invited_by → identities.id
```

---

## 4. API Contract

### 4.1 Staff Management — НОВЫЕ endpoints

**Router:** `src/modules/identity/presentation/router_staff.py`
**Prefix:** `/admin/staff`
**Tag:** `Admin — Staff Management`

| Method | Path                            | Permission     | Handler                          | Request                                                               | Response                 | Status |
| ------ | ------------------------------- | -------------- | -------------------------------- | --------------------------------------------------------------------- | ------------------------ | ------ |
| GET    | `/admin/staff`                  | `staff:manage` | `ListStaffHandler`               | query: offset, limit, search, role_id, is_active, sort_by, sort_order | `StaffListResponse`      | 200    |
| GET    | `/admin/staff/{id}`             | `staff:manage` | `GetStaffDetailHandler`          | -                                                                     | `StaffDetailResponse`    | 200    |
| POST   | `/admin/staff/{id}/deactivate`  | `staff:manage` | `AdminDeactivateIdentityHandler` | `{reason}`                                                            | `{message}`              | 200    |
| POST   | `/admin/staff/{id}/reactivate`  | `staff:manage` | `ReactivateIdentityHandler`      | -                                                                     | `{message}`              | 200    |
| POST   | `/admin/staff/invitations`      | `staff:invite` | `InviteStaffHandler`             | `InviteStaffRequest`                                                  | `InviteStaffResponse`    | 201    |
| GET    | `/admin/staff/invitations`      | `staff:manage` | `ListInvitationsHandler`         | query: offset, limit, status                                          | `InvitationListResponse` | 200    |
| DELETE | `/admin/staff/invitations/{id}` | `staff:manage` | `RevokeInvitationHandler`        | -                                                                     | `{message}`              | 200    |

### 4.2 Customer Management — НОВЫЕ endpoints

**Router:** `src/modules/identity/presentation/router_customers.py`
**Prefix:** `/admin/customers`
**Tag:** `Admin — Customer Management`

| Method | Path                               | Permission         | Handler                          | Request                                                      | Response                 | Status |
| ------ | ---------------------------------- | ------------------ | -------------------------------- | ------------------------------------------------------------ | ------------------------ | ------ |
| GET    | `/admin/customers`                 | `customers:read`   | `ListCustomersHandler`           | query: offset, limit, search, is_active, sort_by, sort_order | `CustomerListResponse`   | 200    |
| GET    | `/admin/customers/{id}`            | `customers:read`   | `GetCustomerDetailHandler`       | -                                                            | `CustomerDetailResponse` | 200    |
| POST   | `/admin/customers/{id}/deactivate` | `customers:manage` | `AdminDeactivateIdentityHandler` | `{reason}`                                                   | `{message}`              | 200    |
| POST   | `/admin/customers/{id}/reactivate` | `customers:manage` | `ReactivateIdentityHandler`      | -                                                            | `{message}`              | 200    |

### 4.3 Invitation Acceptance — PUBLIC endpoints

**Router:** `src/modules/identity/presentation/router_invitation.py`
**Prefix:** `/invitations`
**Tag:** `Staff Invitation`

| Method | Path                            | Permission | Handler                        | Request                   | Response                 | Status |
| ------ | ------------------------------- | ---------- | ------------------------------ | ------------------------- | ------------------------ | ------ |
| GET    | `/invitations/{token}/validate` | Public     | `ValidateInvitationHandler`    | -                         | `InvitationInfoResponse` | 200    |
| POST   | `/invitations/{token}/accept`   | Public     | `AcceptStaffInvitationHandler` | `AcceptInvitationRequest` | `TokenResponse`          | 201    |

### 4.4 Pydantic Schemas

```python
# --- Staff ---

class StaffListItemResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    first_name: str
    last_name: str
    position: str | None
    department: str | None
    roles: list[str]
    is_active: bool
    created_at: datetime

class StaffListResponse(CamelModel):
    items: list[StaffListItemResponse]
    total: int
    offset: int
    limit: int

class StaffDetailResponse(StaffListItemResponse):
    phone: str | None  # нет у StaffMember, но есть через identity joins
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None
    invited_by: uuid.UUID

# --- Invitations ---

class InviteStaffRequest(CamelModel):
    email: EmailStr
    role_ids: list[uuid.UUID]  # min 1

    @field_validator("role_ids")
    @classmethod
    def at_least_one_role(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if not v:
            raise ValueError("At least one role is required")
        return v

class InviteStaffResponse(CamelModel):
    invitation_id: uuid.UUID
    invite_url: str  # полная URL для копирования

class InvitationListItemResponse(CamelModel):
    id: uuid.UUID
    email: str
    status: str
    invited_by_email: str | None
    roles: list[str]
    created_at: datetime
    expires_at: datetime

class InvitationListResponse(CamelModel):
    items: list[InvitationListItemResponse]
    total: int
    offset: int
    limit: int

class InvitationInfoResponse(CamelModel):
    email: str
    roles: list[str]
    expires_at: datetime

class AcceptInvitationRequest(CamelModel):
    password: str  # 8-128 chars
    first_name: str = ""
    last_name: str = ""

# --- Customers ---

class CustomerListItemResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str
    roles: list[str]
    is_active: bool
    created_at: datetime

class CustomerListResponse(CamelModel):
    items: list[CustomerListItemResponse]
    total: int
    offset: int
    limit: int

class CustomerDetailResponse(CustomerListItemResponse):
    referred_by: uuid.UUID | None
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None
```

### 4.5 Deprecated endpoints

`GET /admin/identities` — добавить query param `account_type` (optional), пометить `@deprecated`.

---

## 5. Command Handlers — НОВЫЕ

### 5.1 `InviteStaffCommand`

```
Input: email, role_ids, invited_by (identity_id)
Pre-conditions:
  1. email не зарегистрирован (IIdentityRepository.email_exists)
  2. нет PENDING invitation для этого email (IStaffInvitationRepository.get_pending_by_email)
  3. все role_ids существуют (IRoleRepository.get)
  4. invited_by имеет permission staff:invite (проверяется на уровне router)
Action:
  1. raw_token = secrets.token_urlsafe(32)
  2. invitation = StaffInvitation.create(email, invited_by, role_ids, raw_token, ttl_hours=72)
  3. repo.add(invitation)
  4. uow.commit()  # persists invitation + StaffInvitedEvent
Output: InviteStaffResult(invitation_id, raw_token)
  → router формирует invite_url: f"{settings.FRONTEND_URL}/invite/{raw_token}"
```

### 5.2 `AcceptStaffInvitationCommand`

```
Input: raw_token, password, first_name, last_name
Pre-conditions:
  1. invitation = repo.get_by_token_hash(hash(raw_token)) — exists
  2. invitation.status == PENDING и не expired
  3. email не зарегистрирован (double-check)
Action:
  1. identity = Identity.register_staff()
  2. credentials = LocalCredentials(identity.id, invitation.email, hash(password))
  3. identity_repo.add(identity) + add_credentials(credentials)
  4. Assign each role_id from invitation to identity
  5. invitation.accept(identity.id)
  6. invitation_repo.update(invitation)
  7. Create Session + JWT (как в LoginHandler)
  8. uow.commit()  # persists identity + credentials + roles + invitation update + events
Output: AcceptInvitationResult(access_token, refresh_token, identity_id)
Side effects:
  - IdentityRegisteredEvent (account_type=STAFF) → CreateStaffMemberHandler (consumer)
  - StaffInvitationAcceptedEvent
```

### 5.3 `RevokeStaffInvitationCommand`

```
Input: invitation_id, revoked_by (identity_id)
Pre-conditions:
  1. invitation exists
  2. invitation.status == PENDING
Action:
  1. invitation.revoke()
  2. repo.update(invitation)
  3. uow.commit()
Output: None
```

---

## 6. Query Handlers — НОВЫЕ

### 6.1 `ListStaffQuery`

```sql
SELECT i.id AS identity_id, lc.email, i.is_active,
       sm.first_name, sm.last_name, sm.position, sm.department,
       i.created_at
FROM identities i
LEFT JOIN local_credentials lc ON lc.identity_id = i.id
JOIN staff_members sm ON sm.id = i.id
WHERE i.account_type = 'STAFF'
  [AND (lc.email ILIKE :search OR sm.first_name ILIKE :search OR sm.last_name ILIKE :search)]
  [AND i.is_active = :is_active]
  [AND EXISTS (SELECT 1 FROM identity_roles ir WHERE ir.identity_id = i.id AND ir.role_id = :role_id)]
ORDER BY {sort_col} {sort_dir}
LIMIT :limit OFFSET :offset
```

### 6.2 `ListCustomersQuery`

```sql
SELECT i.id AS identity_id, lc.email, i.is_active,
       c.first_name, c.last_name, c.phone, c.referral_code,
       i.created_at
FROM identities i
LEFT JOIN local_credentials lc ON lc.identity_id = i.id
JOIN customers c ON c.id = i.id
WHERE i.account_type = 'CUSTOMER'
  [AND (lc.email ILIKE :search OR c.first_name ILIKE :search OR c.last_name ILIKE :search)]
  [AND i.is_active = :is_active]
ORDER BY {sort_col} {sort_dir}
LIMIT :limit OFFSET :offset
```

### 6.3 `ListStaffInvitationsQuery`

```sql
SELECT si.id, si.email, si.status, si.created_at, si.expires_at,
       lc.email AS invited_by_email
FROM staff_invitations si
LEFT JOIN local_credentials lc ON lc.identity_id = si.invited_by
[WHERE si.status = :status]
ORDER BY si.created_at DESC
LIMIT :limit OFFSET :offset
```

### 6.4 `ValidateInvitationTokenQuery`

```sql
SELECT si.id, si.email, si.status, si.expires_at,
       r.name AS role_name
FROM staff_invitations si
JOIN staff_invitation_roles sir ON sir.invitation_id = si.id
JOIN roles r ON r.id = sir.role_id
WHERE si.token_hash = :token_hash
  AND si.status = 'PENDING'
  AND si.expires_at > now()
```

---

## 7. Event Consumer Changes

### 7.1 Текущий consumer → split по account_type

**Файл:** `src/modules/user/application/consumers/identity_events.py`

```python
# BEFORE (single consumer):
# create_user_on_identity_registered → creates User

# AFTER (split):

@broker.task(queue="iam_events", routing_key="user.identity_registered")
async def handle_identity_registered(event_data: dict) -> dict:
    """Route by account_type to Customer or StaffMember creation."""
    account_type = event_data.get("account_type", "CUSTOMER")
    if account_type == "CUSTOMER":
        return await create_customer_on_identity_registered(event_data)
    elif account_type == "STAFF":
        return await create_staff_member_on_identity_registered(event_data)
    return {"status": "skipped", "reason": f"Unknown account_type: {account_type}"}


async def create_customer_on_identity_registered(event_data: dict) -> dict:
    """Creates Customer with auto-generated referral code."""
    identity_id = uuid.UUID(event_data["identity_id"])
    # Idempotent check
    existing = await customer_repo.get(identity_id)
    if existing:
        return {"status": "skipped", "reason": "Customer already exists"}

    referral_code = generate_referral_code()
    customer = Customer.create_from_identity(
        identity_id=identity_id,
        profile_email=event_data.get("email"),
        referral_code=referral_code,
    )
    await customer_repo.add(customer)
    await uow.commit()
    return {"status": "success", "customer_id": str(identity_id)}


async def create_staff_member_on_identity_registered(event_data: dict) -> dict:
    """Creates StaffMember. Invitation data passed through event or looked up."""
    identity_id = uuid.UUID(event_data["identity_id"])
    existing = await staff_repo.get(identity_id)
    if existing:
        return {"status": "skipped", "reason": "StaffMember already exists"}

    # invited_by извлекается из StaffInvitation (accepted_identity_id → invitation → invited_by)
    staff = StaffMember.create_from_invitation(
        identity_id=identity_id,
        profile_email=event_data.get("email"),
        invited_by=event_data.get("invited_by", identity_id),
    )
    await staff_repo.add(staff)
    await uow.commit()
    return {"status": "success", "staff_id": str(identity_id)}
```

### 7.2 Anonymization consumer → split

```python
# BEFORE: anonymize_user_on_identity_deactivated → User.anonymize()
# AFTER:  route by account_type

async def handle_identity_deactivated(event_data: dict) -> dict:
    identity_id = uuid.UUID(event_data["identity_id"])
    # Try customer first, then staff
    customer = await customer_repo.get(identity_id)
    if customer:
        customer.anonymize()
        await customer_repo.update(customer)
        await uow.commit()
        return {"status": "success", "type": "customer"}

    staff = await staff_repo.get(identity_id)
    if staff:
        # Staff: не анонимизируем полностью (GDPR legitimate interest)
        # Только помечаем как деактивированного
        return {"status": "success", "type": "staff", "action": "deactivated_only"}

    return {"status": "skipped", "reason": "Profile not found"}
```

---

## 8. Hotfix: `super_admin` → `admin`

**Файл:** `src/modules/identity/application/commands/deactivate_identity.py`

```python
# BEFORE:
role = await self._role_repo.get_by_name("super_admin")
count = await self._role_repo.count_identities_with_role("super_admin")

# AFTER:
role = await self._role_repo.get_by_name("admin")
count = await self._role_repo.count_identities_with_role("admin")
```

---

## 9. Static SoD в AssignRoleHandler

**Файл:** `src/modules/identity/application/commands/assign_role.py`

```python
# Добавить проверку после получения identity и role:

STAFF_ROLE_NAMES = frozenset({"admin", "content_manager", "order_manager",
                              "support_specialist", "review_moderator"})

if identity.account_type == AccountType.CUSTOMER and role.name in STAFF_ROLE_NAMES:
    raise AccountTypeMismatchError()
if identity.account_type == AccountType.STAFF and role.name == "customer":
    raise AccountTypeMismatchError()
```

---

## 10. Seed Data Update

**Файл:** `scripts/seed_dev.sql`

```sql
-- Dev admin: account_type = STAFF
DO $$
DECLARE
    v_admin_id UUID := '00000000-0000-0000-0000-000000000099';
BEGIN
    DELETE FROM staff_members WHERE id = v_admin_id;
    DELETE FROM customers WHERE id = v_admin_id;
    DELETE FROM identities WHERE id = v_admin_id;

    INSERT INTO identities (id, type, account_type, is_active)
    VALUES (v_admin_id, 'LOCAL', 'STAFF', true);

    INSERT INTO local_credentials (identity_id, email, password_hash)
    VALUES (v_admin_id, 'admin@loyality.dev', '$argon2id$...');

    INSERT INTO staff_members (id, first_name, last_name, profile_email, invited_by)
    VALUES (v_admin_id, 'Admin', 'Dev', 'admin@loyality.dev', v_admin_id);

    INSERT INTO identity_roles (identity_id, role_id, assigned_by)
    VALUES (v_admin_id, '00000000-0000-0000-0000-000000000001', null);
END $$;
```

---

## 11. Micro-Tasks — Ordered Implementation

### Overview

| MT    | Название                                                           | Layer         | Type    | Dependencies | Opus Calls |
| ----- | ------------------------------------------------------------------ | ------------- | ------- | ------------ | ---------- |
| MT-1  | AccountType + InvitationStatus VOs                                 | Domain        | simple  | —            | 2          |
| MT-2  | Identity entity changes + StaffInvitation entity + exceptions      | Domain        | simple  | MT-1         | 2          |
| MT-3  | Customer + StaffMember entities + repo interfaces                  | Domain        | simple  | MT-1         | 2          |
| MT-4  | Migrations (5 scripts)                                             | Infra         | complex | MT-1,2,3     | 3          |
| MT-5  | ORM models + repositories (Customer, StaffMember, StaffInvitation) | Infra         | complex | MT-4         | 3          |
| MT-6  | InviteStaff + AcceptInvitation + RevokeInvitation commands         | App           | simple  | MT-2,5       | 2          |
| MT-7  | ListStaff + ListCustomers + ListInvitations queries                | App           | simple  | MT-5         | 2          |
| MT-8  | Event consumer split (Customer/Staff routing)                      | App           | simple  | MT-3,5       | 2          |
| MT-9  | Schemas + Routers (staff, customers, invitations)                  | Presentation  | complex | MT-6,7       | 3          |
| MT-10 | DI registration + bootstrap + seed update                          | Cross-cutting | complex | MT-5,6,7,8,9 | 3          |
| MT-11 | Hotfix: super_admin → admin + SoD in AssignRole                    | App           | simple  | MT-1         | 2          |

### Waves (parallelizable groups)

```
Wave 1: MT-1 (VOs), MT-11 (hotfix)                          ← 2 MTs parallel
Wave 2: MT-2 (Identity + Invitation entities), MT-3 (Customer + Staff entities)  ← 2 MTs parallel
Wave 3: MT-4 (migrations)                                     ← 1 MT
Wave 4: MT-5 (ORM + repos)                                    ← 1 MT
Wave 5: MT-6 (invitation commands), MT-7 (queries), MT-8 (consumers)  ← 3 MTs parallel
Wave 6: MT-9 (schemas + routers)                               ← 1 MT
Wave 7: MT-10 (DI + bootstrap + seed)                          ← 1 MT

Total: 7 waves, 11 MTs, ~26 Opus calls
```

### Acceptance Criteria per MT

**MT-1:** `AccountType` и `InvitationStatus` enums exist, pass unit tests, `ruff + mypy` clean.

**MT-2:** `Identity.register()` accepts `account_type`, `StaffInvitation` entity with `create/accept/revoke` methods, all domain exceptions defined, unit tests for each method.

**MT-3:** `Customer` and `StaffMember` aggregates with factory methods, `anonymize()` on Customer, repo interfaces defined, unit tests.

**MT-4:** 5 Alembic migrations pass `upgrade head` + `downgrade` on clean DB. `account_type` backfill works. `customers` table has referral columns. `staff_members` and `staff_invitations` tables created.

**MT-5:** All 3 ORM models mapped, all 3 repository implementations pass integration tests with real DB.

**MT-6:** `InviteStaffHandler` creates invitation + returns token. `AcceptStaffInvitationHandler` creates Identity(STAFF) + credentials + assigns roles + creates session. `RevokeStaffInvitationHandler` sets status REVOKED. Unit tests for each.

**MT-7:** `ListStaffHandler` returns only STAFF identities with staff_member profile. `ListCustomersHandler` returns only CUSTOMER identities with customer profile. `ListInvitationsHandler` returns paginated invitations. Integration tests.

**MT-8:** `IdentityRegisteredEvent` routes to Customer or StaffMember creation based on `account_type`. `IdentityDeactivatedEvent` anonymizes Customer, logs Staff. Unit tests.

**MT-9:** All Pydantic schemas defined, all routers mounted, `ruff + mypy` clean, OpenAPI spec generates correctly.

**MT-10:** Dishka providers register all new handlers/repos. App starts without errors. Seed creates dev admin as STAFF. Architecture tests pass.

**MT-11:** `AdminDeactivateIdentityHandler` checks `admin` not `super_admin`. `AssignRoleHandler` enforces SoD. Unit tests added.

---

## 12. Quality Gates

After ALL MTs complete:

```bash
uv run ruff check --fix .                          # lint
uv run ruff format .                               # format
uv run mypy .                                      # strict type check
uv run pytest tests/unit/ -v                       # unit tests
uv run pytest tests/architecture/ -v               # boundary tests
uv run pytest tests/integration/ -v                # integration (needs Docker)
uv run pytest tests/e2e/ -v                        # e2e (needs Docker)
```

All must pass with 0 failures.
