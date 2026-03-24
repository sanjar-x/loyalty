# Unified Username Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `username` into User module (`customers` + `staff_members`), remove from `local_credentials`, enable login by email or username.

**Architecture:** Username lives in profile tables (`customers`, `staff_members`) with case-insensitive UNIQUE indexes. Identity module resolves username login via raw SQL JOIN. Cross-table uniqueness enforced at application level via `IUsernameUniquenessChecker`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Dishka DI, attrs dataclasses, TaskIQ

**Spec:** `docs/superpowers/specs/2026-03-24-unified-username-design.md`

---

## Task Order

Dependencies require this execution order:

1. **Task 1** — Add username to StaffMember (User module, no deps)
2. **Task 2** — Create IUsernameUniquenessChecker (User module, no deps)
3. **Task 3** — Update event + consumer + RegisterHandler (Identity+User, uses Task 2)
4. **Task 4** — Remove username from local_credentials (Identity, after Task 3 removes usage)
5. **Task 5** — Rewrite get_by_login with raw SQL JOIN (Identity, after Task 4)
6. **Task 6** — Update create_admin.py (Identity, after Task 1+4)
7. **Task 7** — Migration (DB, after all code changes)
8. **Task 8** — Tests
9. **Task 9** — Final verification

---

### Task 1: Add `username` to StaffMember domain entity and ORM model

**Files:**
- Modify: `src/modules/user/domain/entities.py:120-206`
- Modify: `src/modules/user/infrastructure/models.py:44-71`
- Modify: `src/modules/user/infrastructure/repositories/staff_member_repository.py`

- [ ] **Step 1: Add `username` to `_STAFF_UPDATABLE_FIELDS`**

In `src/modules/user/domain/entities.py`, add `"username"` to the frozenset at line 120:

```python
_STAFF_UPDATABLE_FIELDS = frozenset(
    {
        "first_name",
        "last_name",
        "position",
        "department",
        "username",
    }
)
```

- [ ] **Step 2: Add `username` field to `StaffMember` dataclass**

In `src/modules/user/domain/entities.py`, add `username: str | None` after `last_name` in the `StaffMember` class. Also add `username` parameter to `create_from_invitation()` and pass it through:

```python
@dataclass
class StaffMember(AggregateRoot):
    id: uuid.UUID
    first_name: str
    last_name: str
    username: str | None  # ADD
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
        username: str | None = None,  # ADD
    ) -> StaffMember:
        now = datetime.now(UTC)
        return cls(
            id=identity_id,
            first_name=first_name,
            last_name=last_name,
            username=username,  # ADD
            profile_email=profile_email,
            position=None,
            department=None,
            invited_by=invited_by,
            created_at=now,
            updated_at=now,
        )
```

- [ ] **Step 3: Add `username` column to `StaffMemberModel`**

In `src/modules/user/infrastructure/models.py`, add after `last_name` and change existing `customers.username` from `String(100)` to `String(64)`:

```python
# StaffMemberModel:
username: Mapped[str | None] = mapped_column(String(64), nullable=True)

# CustomerModel (change existing):
username: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

- [ ] **Step 4: Update `StaffMemberRepository` mapper and persistence**

In `src/modules/user/infrastructure/repositories/staff_member_repository.py`:

`_to_domain()` — add `username=orm.username`
`add()` — add `username=staff.username` in `StaffMemberModel()`
`update()` — add `username=staff.username` in `.values()`

- [ ] **Step 5: Commit**

```bash
git add src/modules/user/
git commit -m "feat(user): add username to StaffMember entity and ORM"
```

---

### Task 2: Create `IUsernameUniquenessChecker` and implementation

**Files:**
- Modify: `src/modules/user/domain/interfaces.py`
- Create: `src/modules/user/infrastructure/services/__init__.py`
- Create: `src/modules/user/infrastructure/services/username_checker.py`
- Modify: `src/modules/user/infrastructure/provider.py`

- [ ] **Step 1: Add interface to User domain**

In `src/modules/user/domain/interfaces.py`, add at the end:

```python
class IUsernameUniquenessChecker(ABC):
    """Check username availability across customers and staff_members."""

    @abstractmethod
    async def is_available(
        self, username: str, exclude_identity_id: uuid.UUID | None = None,
    ) -> bool:
        """Return True if username is not taken (case-insensitive)."""
```

- [ ] **Step 2: Create implementation**

Create `src/modules/user/infrastructure/services/__init__.py` (empty) and `src/modules/user/infrastructure/services/username_checker.py`:

```python
"""Cross-table username uniqueness checker."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.interfaces import IUsernameUniquenessChecker

_CHECK_SQL = text("""
    SELECT 1 FROM (
        SELECT id FROM customers
        WHERE LOWER(username) = LOWER(:username) AND (:exclude_id IS NULL OR id != :exclude_id)
        UNION ALL
        SELECT id FROM staff_members
        WHERE LOWER(username) = LOWER(:username) AND (:exclude_id IS NULL OR id != :exclude_id)
    ) t
    LIMIT 1
""")


class UsernameUniquenessChecker(IUsernameUniquenessChecker):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_available(
        self, username: str, exclude_identity_id: uuid.UUID | None = None,
    ) -> bool:
        result = await self._session.execute(
            _CHECK_SQL,
            {"username": username, "exclude_id": exclude_identity_id},
        )
        return result.scalar() is None
```

- [ ] **Step 3: Register in DI provider**

In `src/modules/user/infrastructure/provider.py`, add import and binding:

```python
from src.modules.user.domain.interfaces import (
    ICustomerRepository,
    IStaffMemberRepository,
    IUsernameUniquenessChecker,
)
from src.modules.user.infrastructure.services.username_checker import (
    UsernameUniquenessChecker,
)

# Inside ProfileProvider class, add:
username_checker: CompositeDependencySource = provide(
    UsernameUniquenessChecker, scope=Scope.REQUEST, provides=IUsernameUniquenessChecker
)
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/user/
git commit -m "feat(user): add IUsernameUniquenessChecker service"
```

---

### Task 3: Update event, RegisterHandler, and event consumers

This task does three things atomically: adds `username` to the event, passes it from RegisterHandler, and updates both consumers to use the uniqueness checker.

**Files:**
- Modify: `src/modules/identity/domain/events.py:14-42`
- Modify: `src/modules/identity/application/commands/register.py`
- Modify: `src/modules/user/application/consumers/identity_events.py`

- [ ] **Step 1: Add `username` field to `IdentityRegisteredEvent`**

In `src/modules/identity/domain/events.py`, add after `account_type` (line 32):

```python
username: str | None = None
```

- [ ] **Step 2: Update RegisterHandler — pass username to event, remove from LocalCredentials**

In `src/modules/identity/application/commands/register.py`:

First, remove `username=command.username` from the `LocalCredentials()` construction:

```python
credentials = LocalCredentials(
    identity_id=identity.id,
    email=command.email,
    password_hash=password_hash,
    created_at=now,
    updated_at=now,
)
```

Then update the event emission to include username:

```python
identity.add_domain_event(
    IdentityRegisteredEvent(
        identity_id=identity.id,
        email=command.email,
        account_type=AccountType.CUSTOMER.value,
        username=command.username,
        aggregate_id=str(identity.id),
    )
)
```

- [ ] **Step 3: Update `create_profile_on_identity_registered` consumer**

In `src/modules/user/application/consumers/identity_events.py`:

Add `username: str | None = None` parameter to `create_profile_on_identity_registered()` (after `last_name`). Pass to `_create_customer()`:

```python
return await _create_customer(identity_uuid, email, customer_repo, uow, username=username)
```

Update `_create_customer()` to accept username and use it:

```python
async def _create_customer(
    identity_id: uuid.UUID,
    email: str,
    customer_repo: ICustomerRepository,
    uow: IUnitOfWork,
    username: str | None = None,
) -> dict:
    """Create a Customer profile with auto-generated referral code."""
    existing = await customer_repo.get(identity_id)
    if existing:
        logger.info("customer.already_exists", identity_id=str(identity_id))
        return {"status": "skipped", "reason": "already_exists"}

    referral_code = generate_referral_code()
    customer = Customer.create_from_identity(
        identity_id=identity_id,
        profile_email=email,
        referral_code=referral_code,
        username=username,
    )
    async with uow:
        await customer_repo.add(customer)
        uow.register_aggregate(customer)
        await uow.commit()

    logger.info("customer.created_from_event", identity_id=str(identity_id))
    return {"status": "success", "type": "customer"}
```

- [ ] **Step 4: Add uniqueness check to `on_linked_account_created` consumer**

In the same file, update `on_linked_account_created()`. Where it creates a customer with username (around line 210-214), add graceful uniqueness handling. The consumer does NOT inject `IUsernameUniquenessChecker` via Dishka — instead, rely on the DB UNIQUE index and catch `IntegrityError`:

In the `is_new_identity` branch where `Customer.create_from_identity()` is called with `username=provider_metadata.get("username")`, wrap the `customer_repo.add()` + `uow.commit()` block to catch integrity errors on username:

```python
from sqlalchemy.exc import IntegrityError

# In the is_new_identity branch, after creating the customer:
try:
    async with uow:
        await customer_repo.add(customer)
        uow.register_aggregate(customer)
        await uow.commit()
except IntegrityError:
    # Username taken — retry without username
    logger.warning(
        "customer.username_conflict",
        identity_id=identity_id,
        username=provider_metadata.get("username"),
    )
    customer = Customer.create_from_identity(
        identity_id=identity_uuid,
        first_name=provider_metadata.get("first_name", ""),
        last_name=provider_metadata.get("last_name", ""),
        username=None,
        referral_code=generate_referral_code(),
        referred_by=referred_by,
    )
    async with uow:
        await customer_repo.add(customer)
        uow.register_aggregate(customer)
        await uow.commit()
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/identity/domain/events.py src/modules/identity/application/commands/register.py src/modules/user/application/consumers/identity_events.py
git commit -m "feat: propagate username through events with uniqueness handling"
```

---

### Task 4: Remove `username` from `local_credentials` (Identity module)

**Files:**
- Modify: `src/modules/identity/domain/entities.py:161-177`
- Modify: `src/modules/identity/infrastructure/models.py:106-145`
- Modify: `src/modules/identity/infrastructure/repositories/identity_repository.py`
- Delete: `alembic/versions/2026_03_23_add_username_to_local_credentials.py`

- [ ] **Step 1: Remove `username` from `LocalCredentials` entity**

In `src/modules/identity/domain/entities.py`, remove `username: str | None = None` from the `LocalCredentials` dataclass.

- [ ] **Step 2: Remove `username` column from `LocalCredentialsModel`**

In `src/modules/identity/infrastructure/models.py`, remove the entire `username` mapped_column block (5 lines).

- [ ] **Step 3: Remove `username` from repository mapper and persistence**

In `src/modules/identity/infrastructure/repositories/identity_repository.py`:
- `_credentials_to_domain()`: remove `username=orm.username`
- `add_credentials()`: remove `username=credentials.username`

- [ ] **Step 4: Delete the old migration**

```bash
rm alembic/versions/2026_03_23_add_username_to_local_credentials.py
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(identity): remove username from local_credentials"
```

---

### Task 5: Rewrite `get_by_login()` with raw SQL JOIN

**Files:**
- Modify: `src/modules/identity/domain/interfaces.py`
- Modify: `src/modules/identity/infrastructure/repositories/identity_repository.py`

- [ ] **Step 1: Update interface docstring**

In `src/modules/identity/domain/interfaces.py`, update `get_by_login()` docstring to say it JOINs with `customers` and `staff_members` via raw SQL.

- [ ] **Step 2: Rewrite `get_by_login()` implementation**

In `src/modules/identity/infrastructure/repositories/identity_repository.py`, replace the existing `get_by_login()` method entirely. Import `text` from sqlalchemy if not already imported:

```python
from sqlalchemy import exists, select, text, update
```

New method:

```python
async def get_by_login(
    self,
    login: str,
) -> tuple[Identity, LocalCredentials] | None:
    """Retrieve an identity by email or username.

    If login contains '@', look up by email. Otherwise look up by
    username across customers and staff_members via raw SQL JOIN.
    """
    if "@" in login:
        return await self.get_by_email(login)

    stmt = text("""
        SELECT i.id, i.primary_auth_method, i.account_type, i.is_active,
               i.created_at, i.updated_at, i.deactivated_at, i.deactivated_by,
               i.token_version,
               lc.identity_id AS lc_identity_id, lc.email, lc.password_hash,
               lc.created_at AS lc_created_at, lc.updated_at AS lc_updated_at
        FROM identities i
        JOIN local_credentials lc ON lc.identity_id = i.id
        LEFT JOIN customers c ON c.id = i.id
        LEFT JOIN staff_members s ON s.id = i.id
        WHERE LOWER(c.username) = LOWER(:login)
           OR LOWER(s.username) = LOWER(:login)
        LIMIT 1
    """)
    result = await self._session.execute(stmt, {"login": login})
    row = result.mappings().first()
    if row is None:
        return None

    identity = Identity(
        id=row["id"],
        type=PrimaryAuthMethod(row["primary_auth_method"]),
        account_type=AccountType(row["account_type"]),
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deactivated_at=row["deactivated_at"],
        deactivated_by=row["deactivated_by"],
        token_version=row["token_version"],
    )
    credentials = LocalCredentials(
        identity_id=row["lc_identity_id"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row["lc_created_at"],
        updated_at=row["lc_updated_at"],
    )
    return identity, credentials
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/identity/
git commit -m "feat(identity): rewrite get_by_login with raw SQL JOIN"
```

---

### Task 6: Update `create_admin.py` to create staff_members row

**Files:**
- Modify: `src/modules/identity/management/create_admin.py`

- [ ] **Step 1: Update SQL and function**

Remove `username` from `_INSERT_CREDENTIALS` SQL and its parameter dict. Add `_INSERT_STAFF_MEMBER` SQL. Add the insert call in the function.

New `_INSERT_CREDENTIALS`:
```python
_INSERT_CREDENTIALS = text("""
    INSERT INTO local_credentials (identity_id, email, password_hash)
    VALUES (:identity_id, :email, :password_hash)
""")
```

New SQL constant:
```python
_INSERT_STAFF_MEMBER = text("""
    INSERT INTO staff_members (id, first_name, last_name, username, invited_by)
    VALUES (:id, 'Admin', '', :username, :id)
""")
```

Update `_INSERT_CREDENTIALS` execute call — remove `"username": username` from the params dict:
```python
await session.execute(
    _INSERT_CREDENTIALS,
    {
        "identity_id": identity_id,
        "email": email,
        "password_hash": password_hash,
    },
)
```

Add after `_INSERT_IDENTITY_ROLE` execute:
```python
await session.execute(
    _INSERT_STAFF_MEMBER,
    {"id": identity_id, "username": username},
)
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/management/create_admin.py
git commit -m "feat(management): create_admin now inserts staff_members row"
```

---

### Task 7: Write Alembic migration

**Files:**
- Create: `alembic/versions/2026_03_24_unified_username.py`

- [ ] **Step 1: Determine current head revision**

```bash
cd C:\Users\Sanjar\Desktop\loyality\backend && alembic heads
```

Use the output as `down_revision` value. If no heads exist (empty versions), use `None`.

- [ ] **Step 2: Write migration**

Create `alembic/versions/2026_03_24_unified_username.py`:

```python
"""Unified username: move to User module, add to staff_members.

Revision ID: b1c2d3e4f5a6
Revises: <HEAD from step 1, or None>
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = None  # SET FROM STEP 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop username from local_credentials (may not exist)
    op.execute("ALTER TABLE local_credentials DROP COLUMN IF EXISTS username")

    # 2. Alter customers.username from String(100) to String(64)
    op.alter_column(
        "customers", "username",
        type_=sa.String(64),
        existing_type=sa.String(100),
        existing_nullable=True,
    )

    # 3. Deduplicate existing usernames (keep most recently updated)
    op.execute("""
        UPDATE customers SET username = NULL
        WHERE id NOT IN (
            SELECT DISTINCT ON (LOWER(username)) id
            FROM customers
            WHERE username IS NOT NULL
            ORDER BY LOWER(username), updated_at DESC
        )
        AND username IS NOT NULL
    """)

    # 4. Add case-insensitive UNIQUE index on customers.username
    op.create_index(
        "ix_customers_username_lower",
        "customers",
        [sa.text("LOWER(username)")],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )

    # 5. Add username column to staff_members
    op.add_column(
        "staff_members",
        sa.Column("username", sa.String(64), nullable=True),
    )

    # 6. Add case-insensitive UNIQUE index on staff_members.username
    op.create_index(
        "ix_staff_members_username_lower",
        "staff_members",
        [sa.text("LOWER(username)")],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_staff_members_username_lower", table_name="staff_members")
    op.drop_column("staff_members", "username")
    op.drop_index("ix_customers_username_lower", table_name="customers")
    op.alter_column(
        "customers", "username",
        type_=sa.String(100),
        existing_type=sa.String(64),
        existing_nullable=True,
    )
```

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/
git commit -m "feat(migration): unified username indexes and staff_members.username"
```

---

### Task 8: Tests

**Files:**
- Modify: `tests/unit/modules/identity/presentation/test_schemas.py`
- Modify: `tests/integration/modules/identity/application/commands/test_login.py`
- Create: `tests/unit/modules/user/infrastructure/services/test_username_checker.py`

- [ ] **Step 1: Verify existing schema tests pass**

```bash
pytest tests/unit/modules/identity/presentation/test_schemas.py -v
```

- [ ] **Step 2: Verify existing login integration tests pass**

```bash
pytest tests/integration/modules/identity/application/commands/test_login.py -v
```

- [ ] **Step 3: Fix any test failures**

If tests reference `LocalCredentials(... username=...)`, remove the `username` kwarg.

- [ ] **Step 4: Commit if fixes needed**

```bash
git add tests/
git commit -m "test: fix tests for unified username"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full test suite**

```bash
pytest --tb=short
```

- [ ] **Step 2: Verify app starts**

```bash
uvicorn src.bootstrap.web:create_app --factory --host 0.0.0.0 --port 8000
```

Check logs for `system_roles.synced` message.

- [ ] **Step 3: Test login by username via docs**

Open `http://localhost:8000/docs`, try `POST /auth/login` with `{"login": "admin", "password": "..."}`.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: final adjustments for unified username"
```
