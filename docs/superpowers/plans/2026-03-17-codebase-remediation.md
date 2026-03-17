# Codebase Remediation Roadmap — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate all 46 violations identified by the multi-agent codebase audit, grouped into 8 execution phases ordered by severity and dependency.

**Architecture:** Fixes are organized so each phase can be committed independently. Phases 1-2 are zero-code-dependency config fixes. Phases 3-5 address architecture/domain violations. Phases 6-8 handle quality/style. Each task targets specific files with exact code changes.

**Tech Stack:** Python 3.14+, FastAPI, SQLAlchemy 2.1 (async), attrs, Pydantic v2, Dishka DI, Redis, TaskIQ, structlog

---

## Phase 1: P0 — Security Configuration (No Code Dependencies)

> These are configuration-only changes that eliminate the two highest-impact attack vectors. Deploy immediately.

### Task 1.1: Generate Cryptographically Random SECRET_KEY

**Fixes:** CR-1 (Weak SECRET_KEY)
**Severity:** CRITICAL

**Files:**
- Modify: `.env`

- [ ] **Step 1: Generate a new secret key**

Run:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

- [ ] **Step 2: Replace the SECRET_KEY in `.env`**

Replace the current `SECRET_KEY=7b8b965bc1012353721382583802e3cb98e56117d9171b3127521e6490606d28` (line 4 of `.env`) with the generated value. Example:

```env
SECRET_KEY=<output-from-step-1>
```

- [ ] **Step 3: Verify the app still starts**

Run: `uv run python -c "from src.bootstrap.config import settings; print(len(settings.SECRET_KEY.get_secret_value()))"`
Expected: `64` (32 bytes hex-encoded)

- [ ] **Step 4: Verify `.env` is in `.gitignore`**

`.env` is already in `.gitignore` (confirmed). Do NOT commit `.env` to git — the change is local-only. If deploying to staging/production, update the environment variable through your deployment mechanism (e.g., Docker secrets, Kubernetes ConfigMap, CI/CD env vars).

> **IMPORTANT:** Check if `.env` has ever been committed to git history: `git log --all --full-history -- .env`. If it has, rotate ALL credentials (DB, Redis, S3, RabbitMQ) immediately.

---

### Task 1.2: Fix Access Token Expiry

**Fixes:** CR-2 (7-day irrevocable access token)
**Severity:** CRITICAL

**Files:**
- Modify: `.env`

- [ ] **Step 1: Change ACCESS_TOKEN_EXPIRE_MINUTES in `.env`**

Replace:
```env
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```
With:
```env
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

- [ ] **Step 2: Verify**

Run: `uv run python -c "from src.bootstrap.config import settings; print(settings.ACCESS_TOKEN_EXPIRE_MINUTES)"`
Expected: `15`

- [ ] **Step 3: Commit**

```bash
git add .env
git commit -m "security: reduce access token expiry from 7 days to 15 minutes"
```

---

## Phase 2: P0 — Security Hardening (Presentation/Config Layer)

> These fixes address missing authentication, input validation, and CORS configuration.

### Task 2.1: Add Authentication to Catalog Write Endpoints

**Fixes:** MJ-1 (All catalog CRUD endpoints lack authentication)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/catalog/presentation/router.py:1-7, 72-78, 161-166, 190-194, 210-215, 291-296, 317-322, 330-334`

- [ ] **Step 1: Add Depends import and RequirePermission import**

At the top of `src/modules/catalog/presentation/router.py`, add the auth dependency import. Change:
```python
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status
```
To:
```python
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import RequirePermission
```

- [ ] **Step 2: Add `dependencies` to all write endpoints**

Add `dependencies=[Depends(RequirePermission("catalog:manage"))]` to every `POST`, `PATCH`, and `DELETE` decorator:

**`create_category` (line 72):**
```python
@category_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryCreateResponse,
    summary="Создать новую категорию",
    description="Создает категорию.",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

**`update_category` (line 161):**
```python
@category_router.patch(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Обновить категорию",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

**`delete_category` (line 190):**
```python
@category_router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

**`create_brand` (line 210):**
```python
@brand_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BrandCreateResponse,
    summary="Создать новый бренд",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

**`update_brand` (line 291):**
```python
@brand_router.patch(
    "/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Обновить бренд",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

**`delete_brand` (line 317):**
```python
@brand_router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бренд",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

**`confirm_logo_upload` (line 330):**
```python
@brand_router.post(
    "/{brand_id}/logo/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Подтвердить загрузку логотипа",
    dependencies=[Depends(RequirePermission("catalog:manage"))],
)
```

- [ ] **Step 3: Verify no import errors**

Run: `uv run python -c "from src.modules.catalog.presentation.router import category_router, brand_router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run existing e2e tests**

Run: `uv run pytest tests/e2e/api/v1/test_brands.py tests/e2e/api/v1/test_categories.py -v`
Expected: Tests may need auth token fixtures updated — note any failures.

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/presentation/router.py
git commit -m "security: add RequirePermission to all catalog write endpoints"
```

---

### Task 2.2: Validate X-Request-ID Header

**Fixes:** MJ-10 (Untrusted X-Request-ID allows log injection)
**Severity:** MAJOR

**Files:**
- Modify: `src/api/middlewares/logger.py:31-36`

- [ ] **Step 1: Add regex import and validate the header**

At the top of `src/api/middlewares/logger.py`, add:
```python
import re
```

Replace lines 31-36:
```python
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        ip: str = request.headers.get("X-Forwarded-For", "")
        if not ip:
            ip: str = request.client.host if request.client else "unknown"
        else:
            ip: str = ip.split(",")[0].strip()
```

With:
```python
        raw_request_id = request.headers.get("X-Request-ID", "")
        if raw_request_id and re.match(r"^[a-zA-Z0-9\-]{1,64}$", raw_request_id):
            request_id = raw_request_id
        else:
            request_id = uuid.uuid4().hex

        forwarded = request.headers.get("X-Forwarded-For", "")
        ip: str
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
```

Note: This also fixes the triple `ip: str` re-annotation issue (MJ-7 from code quality).

- [ ] **Step 2: Also fix `raise e` to bare `raise` on line 79**

Replace:
```python
            raise e
```
With:
```python
            raise
```

- [ ] **Step 3: Run lint**

Run: `uv run ruff check src/api/middlewares/logger.py --fix && uv run ruff format src/api/middlewares/logger.py`

- [ ] **Step 4: Commit**

```bash
git add src/api/middlewares/logger.py
git commit -m "security: validate X-Request-ID header, fix ip annotation and bare raise"
```

---

### Task 2.3: Restrict CORS Methods and Headers

**Fixes:** MJ-11 (CORS allows all methods and all headers)
**Severity:** MAJOR

**Files:**
- Modify: `src/bootstrap/web.py:59-65`

- [ ] **Step 1: Replace wildcard CORS config**

In `src/bootstrap/web.py`, replace:
```python
        app.add_middleware(
            CORSMiddleware,  # ty:ignore[invalid-argument-type]
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
```

With:
```python
        app.add_middleware(
            CORSMiddleware,  # ty:ignore[invalid-argument-type]
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
```

- [ ] **Step 2: Also add return type to health_check on line 73**

Replace:
```python
    @app.get("/health", tags=["System"])
    async def health_check():
```
With:
```python
    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
```

- [ ] **Step 3: Commit**

```bash
git add src/bootstrap/web.py
git commit -m "security: restrict CORS to explicit methods/headers, type health_check"
```

---

### Task 2.4: Validate LogoMetadataRequest content_type

**Fixes:** MJ-12 (Arbitrary content_type enables stored XSS via S3)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/catalog/presentation/schemas.py:11-14`

- [ ] **Step 1: Add content_type whitelist**

Replace:
```python
class LogoMetadataRequest(CamelModel):
    filename: str
    content_type: str
    size: int | None = None
```

With:
```python
class LogoMetadataRequest(CamelModel):
    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., pattern=r"^image/(jpeg|png|webp|gif|svg\+xml)$")
    size: int | None = None
```

- [ ] **Step 2: Also fix BrandCreateRequest slug validation (m-7)**

Replace:
```python
class BrandCreateRequest(CamelModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    logo: LogoMetadataRequest | None = None
```

With:
```python
class BrandCreateRequest(CamelModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo: LogoMetadataRequest | None = None
```

- [ ] **Step 3: Remove dead ConfirmLogoRequest (m-11)**

Delete:
```python
class ConfirmLogoRequest(CamelModel):
    pass
```

And remove `ConfirmLogoRequest` from the import in `router.py` and the `request` parameter from `confirm_logo_upload` endpoint.

- [ ] **Step 4: Run lint and verify**

Run: `uv run ruff check src/modules/catalog/presentation/ --fix && uv run ruff format src/modules/catalog/presentation/`

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/presentation/schemas.py src/modules/catalog/presentation/router.py
git commit -m "security: validate logo content_type, add brand slug constraints, remove dead ConfirmLogoRequest"
```

---

### Task 2.5: Add max_length to LoginRequest.password

**Fixes:** m-1 (HashDoS via Argon2id)
**Severity:** MINOR (but easy high-value fix)

**Files:**
- Modify: `src/modules/identity/presentation/schemas.py:25-27`

- [ ] **Step 1: Add max_length**

Replace:
```python
class LoginRequest(CamelModel):
    email: EmailStr
    password: str
```

With:
```python
class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(..., max_length=128)
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/presentation/schemas.py
git commit -m "security: add max_length to LoginRequest.password to prevent HashDoS"
```

---

### Task 2.6: Remove Email from IdentityAlreadyExistsError Details

**Fixes:** m-2 (User enumeration via registration error)
**Severity:** MINOR

**Files:**
- Modify: `src/modules/identity/domain/exceptions.py:21-29`

- [ ] **Step 1: Remove email from details**

Replace:
```python
class IdentityAlreadyExistsError(ConflictError):
    """Email already registered."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message="Email already registered",
            error_code="IDENTITY_ALREADY_EXISTS",
            details={"email": email},
        )
```

With:
```python
class IdentityAlreadyExistsError(ConflictError):
    """Email already registered."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message="Email already registered",
            error_code="IDENTITY_ALREADY_EXISTS",
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/identity/domain/exceptions.py
git commit -m "security: remove email from IdentityAlreadyExistsError to prevent user enumeration"
```

---

### Task 2.7: Make S3 Credentials SecretStr

**Fixes:** m-4 (S3 keys not SecretStr)
**Severity:** MINOR

**Files:**
- Modify: `src/bootstrap/config.py:63-64`
- Modify: Any file that reads `settings.S3_ACCESS_KEY` / `settings.S3_SECRET_KEY` directly

- [ ] **Step 1: Change types in Settings**

Replace:
```python
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
```

With:
```python
    S3_ACCESS_KEY: SecretStr
    S3_SECRET_KEY: SecretStr
```

- [ ] **Step 2: Update the S3 client construction to use `.get_secret_value()`**

The S3 keys are consumed in `src/modules/storage/presentation/dependencies.py` (lines 21-22):

Replace:
```python
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
```
With:
```python
            access_key=settings.S3_ACCESS_KEY.get_secret_value(),
            secret_key=settings.S3_SECRET_KEY.get_secret_value(),
```

Also check `tests/conftest.py` — if test fixtures reference `settings.S3_ACCESS_KEY` directly, they will need `.get_secret_value()` too.

- [ ] **Step 3: Also fix database_url to use URL.create (m-5)**

The `URL` import already exists at line 8. Replace the `database_url` computed field:
```python
    @computed_field
    @property
    def database_url(self) -> str | URL:
        password: str = self.PGPASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.PGUSER}:{password}"
            f"@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
        )
```

With:
```python
    @computed_field
    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.PGUSER,
            password=self.PGPASSWORD.get_secret_value(),
            host=self.PGHOST,
            port=self.PGPORT,
            database=self.PGDATABASE,
        )
```

- [ ] **Step 4: Verify config loads**

Run: `uv run python -c "from src.bootstrap.config import settings; print(type(settings.database_url))"`

- [ ] **Step 5: Commit**

```bash
git add src/bootstrap/config.py src/modules/storage/presentation/dependencies.py
git commit -m "security: make S3 keys SecretStr, use URL.create for database_url"
```

---

## Phase 3: Architecture — Application Layer Boundary Fixes

> These fixes remove ORM model imports from the application layer, the most pervasive architectural violation.

### Task 3.1: Rewrite Identity Query Handlers to Use Raw SQL

**Fixes:** CR-3 (6 query handlers import ORM models)
**Severity:** CRITICAL

**Files:**
- Modify: `src/modules/identity/application/queries/list_roles.py`
- Modify: `src/modules/identity/application/queries/list_permissions.py`
- Modify: `src/modules/identity/application/queries/get_identity_roles.py`
- Modify: `src/modules/identity/application/queries/get_my_sessions.py`

**Pattern to follow:** `src/modules/catalog/application/queries/get_brand.py` — uses `sqlalchemy.text()` + Pydantic read models, zero ORM imports.

**Note:** `get_session_permissions.py` is already clean — it uses `IPermissionResolver` (an interface), not ORM models. No changes needed for that file.

- [ ] **Step 1: Rewrite `list_roles.py`**

Replace entire file content:
```python
# src/modules/identity/application/queries/list_roles.py
import uuid

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RoleWithPermissions(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]


_LIST_ROLES_SQL = text(
    "SELECT r.id, r.name, r.description, r.is_system "
    "FROM roles r "
    "ORDER BY r.name"
)

_ROLE_PERMISSIONS_SQL = text(
    "SELECT rp.role_id, p.codename "
    "FROM role_permissions rp "
    "JOIN permissions p ON p.id = rp.permission_id "
    "WHERE rp.role_id = ANY(:role_ids)"
)


class ListRolesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[RoleWithPermissions]:
        result = await self._session.execute(_LIST_ROLES_SQL)
        rows = result.mappings().all()

        if not rows:
            return []

        role_ids = [row["id"] for row in rows]
        perm_result = await self._session.execute(
            _ROLE_PERMISSIONS_SQL, {"role_ids": role_ids}
        )
        perm_rows = perm_result.mappings().all()

        perms_by_role: dict[uuid.UUID, list[str]] = {}
        for pr in perm_rows:
            perms_by_role.setdefault(pr["role_id"], []).append(pr["codename"])

        return [
            RoleWithPermissions(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                is_system=row["is_system"],
                permissions=perms_by_role.get(row["id"], []),
            )
            for row in rows
        ]
```

- [ ] **Step 2: Rewrite `list_permissions.py`**

Replace entire file content:
```python
# src/modules/identity/application/queries/list_permissions.py
import uuid

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionInfo(BaseModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None


_LIST_PERMISSIONS_SQL = text(
    "SELECT id, codename, resource, action, description "
    "FROM permissions "
    "ORDER BY codename"
)


class ListPermissionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[PermissionInfo]:
        result = await self._session.execute(_LIST_PERMISSIONS_SQL)
        return [
            PermissionInfo(
                id=row["id"],
                codename=row["codename"],
                resource=row["resource"],
                action=row["action"],
                description=row["description"],
            )
            for row in result.mappings().all()
        ]
```

- [ ] **Step 3: Rewrite `get_identity_roles.py`**

Replace entire file content:
```python
# src/modules/identity/application/queries/get_identity_roles.py
import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class IdentityRoleInfo(BaseModel):
    role_id: uuid.UUID
    role_name: str
    is_system: bool


@dataclass(frozen=True)
class GetIdentityRolesQuery:
    identity_id: uuid.UUID


_IDENTITY_ROLES_SQL = text(
    "SELECT r.id AS role_id, r.name AS role_name, r.is_system "
    "FROM roles r "
    "JOIN identity_roles ir ON ir.role_id = r.id "
    "WHERE ir.identity_id = :identity_id "
    "ORDER BY r.name"
)


class GetIdentityRolesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetIdentityRolesQuery) -> list[IdentityRoleInfo]:
        result = await self._session.execute(
            _IDENTITY_ROLES_SQL, {"identity_id": query.identity_id}
        )
        return [
            IdentityRoleInfo(
                role_id=row["role_id"],
                role_name=row["role_name"],
                is_system=row["is_system"],
            )
            for row in result.mappings().all()
        ]
```

- [ ] **Step 4: Rewrite `get_my_sessions.py`**

Replace entire file content:
```python
# src/modules/identity/application/queries/get_my_sessions.py
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SessionInfo(BaseModel):
    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    is_revoked: bool
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


@dataclass(frozen=True)
class GetMySessionsQuery:
    identity_id: uuid.UUID
    current_session_id: uuid.UUID


_MY_SESSIONS_SQL = text(
    "SELECT id, ip_address, user_agent, is_revoked, created_at, expires_at "
    "FROM sessions "
    "WHERE identity_id = :identity_id AND is_revoked = false "
    "ORDER BY created_at DESC"
)


class GetMySessionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMySessionsQuery) -> list[SessionInfo]:
        result = await self._session.execute(
            _MY_SESSIONS_SQL, {"identity_id": query.identity_id}
        )
        return [
            SessionInfo(
                id=row["id"],
                ip_address=str(row["ip_address"]) if row["ip_address"] else None,
                user_agent=row["user_agent"],
                is_revoked=row["is_revoked"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                is_current=(row["id"] == query.current_session_id),
            )
            for row in result.mappings().all()
        ]
```

- [ ] **Step 5: Run lint on all modified files**

Run: `uv run ruff check src/modules/identity/application/queries/ --fix && uv run ruff format src/modules/identity/application/queries/`

- [ ] **Step 6: Run existing tests**

Run: `uv run pytest tests/ -v -k "identity" --timeout=30`

- [ ] **Step 7: Commit**

```bash
git add src/modules/identity/application/queries/
git commit -m "refactor: rewrite identity query handlers to use raw SQL, remove ORM imports from application layer"
```

---

### Task 3.2: Rewrite User Query Handlers to Use Raw SQL

**Fixes:** CR-3 (continued — user module)
**Severity:** CRITICAL

**Files:**
- Modify: `src/modules/user/application/queries/get_my_profile.py`
- Modify: `src/modules/user/application/queries/get_user_by_identity.py`

- [ ] **Step 1: Rewrite `get_my_profile.py`**

Replace entire file content:
```python
# src/modules/user/application/queries/get_my_profile.py
import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.exceptions import UserNotFoundError


class UserProfile(BaseModel):
    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


@dataclass(frozen=True)
class GetMyProfileQuery:
    user_id: uuid.UUID


_GET_PROFILE_SQL = text(
    "SELECT id, profile_email, first_name, last_name, phone "
    "FROM users "
    "WHERE id = :user_id"
)


class GetMyProfileHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMyProfileQuery) -> UserProfile:
        result = await self._session.execute(
            _GET_PROFILE_SQL, {"user_id": query.user_id}
        )
        row = result.mappings().first()
        if row is None:
            raise UserNotFoundError(query.user_id)

        return UserProfile(
            id=row["id"],
            profile_email=row["profile_email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
        )
```

- [ ] **Step 2: Rewrite `get_user_by_identity.py`**

Replace entire file content:
```python
# src/modules/user/application/queries/get_user_by_identity.py
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class GetUserByIdentityQuery:
    identity_id: uuid.UUID


_GET_USER_ID_SQL = text(
    "SELECT id FROM users WHERE id = :identity_id"
)


class GetUserByIdentityHandler:
    """Internal: used by backward-compatible get_current_user_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetUserByIdentityQuery) -> uuid.UUID | None:
        """Returns user_id if user exists, None otherwise."""
        result = await self._session.execute(
            _GET_USER_ID_SQL, {"identity_id": query.identity_id}
        )
        row = result.mappings().first()
        return row["id"] if row else None
```

- [ ] **Step 3: Run lint**

Run: `uv run ruff check src/modules/user/application/queries/ --fix && uv run ruff format src/modules/user/application/queries/`

- [ ] **Step 4: Commit**

```bash
git add src/modules/user/application/queries/
git commit -m "refactor: rewrite user query handlers to use raw SQL, remove ORM imports from application layer"
```

---

### Task 3.3: Fix Consumer to Use ICacheService Instead of RedisService

**Fixes:** CR-4 (Consumer imports concrete RedisService)
**Severity:** CRITICAL

**Files:**
- Modify: `src/modules/identity/application/consumers/role_events.py:18-19, 35`

- [ ] **Step 1: Replace RedisService with ICacheService and remove ORM import**

Replace:
```python
from src.infrastructure.cache.redis import RedisService
from src.modules.identity.infrastructure.models import SessionModel
```

With:
```python
from sqlalchemy import text

from src.shared.interfaces.cache import ICacheService
```

- [ ] **Step 2: Update the function signature and body**

Replace the entire function:
```python
@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="identity.role_assignment_changed",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def invalidate_permissions_cache_on_role_change(
    identity_id: str,
    redis: FromDishka[RedisService],
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
```

With:
```python
_ACTIVE_SESSIONS_SQL = text(
    "SELECT id FROM sessions "
    "WHERE identity_id = :identity_id AND is_revoked = false"
)


@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="identity.role_assignment_changed",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def invalidate_permissions_cache_on_role_change(
    identity_id: str,
    cache: FromDishka[ICacheService],
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
```

And update the body to use raw SQL + `cache` instead of `redis`:
```python
    identity_uuid = uuid.UUID(identity_id)

    async with session_factory() as session:
        result = await session.execute(
            _ACTIVE_SESSIONS_SQL, {"identity_id": identity_uuid}
        )
        session_ids = [row[0] for row in result.all()]

    deleted_count = 0
    for sid in session_ids:
        cache_key = f"perms:{sid}"
        await cache.delete(cache_key)
        deleted_count += 1

    logger.info(
        "permissions_cache.invalidated",
        identity_id=str(identity_uuid),
        sessions_affected=deleted_count,
    )

    return {"status": "success", "sessions_invalidated": deleted_count}
```

- [ ] **Step 3: Run lint**

Run: `uv run ruff check src/modules/identity/application/consumers/ --fix && uv run ruff format src/modules/identity/application/consumers/`

- [ ] **Step 4: Commit**

```bash
git add src/modules/identity/application/consumers/role_events.py
git commit -m "refactor: replace RedisService with ICacheService, use raw SQL in role_events consumer"
```

---

### Task 3.4: Fix Cross-Module Boundary Violation in User Router

**Fixes:** MJ-6 (user.presentation imports identity.application)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/user/presentation/router.py` — remove lines 5-13, 82-113
- Create: `src/modules/identity/presentation/router_account.py` — new router for account management
- Modify: `src/api/router.py` — register the new router

**Approach:** Create a dedicated `identity_account_router` (prefix `/users`) inside the identity module for identity-owned operations that live under the `/users` URL path. This keeps URLs stable while fixing the boundary violation.

- [ ] **Step 1: Create `src/modules/identity/presentation/router_account.py`**

```python
# src/modules/identity/presentation/router_account.py
"""Account management endpoints owned by the identity module."""
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

from src.modules.identity.application.commands.deactivate_identity import (
    DeactivateIdentityCommand,
    DeactivateIdentityHandler,
)
from src.modules.identity.application.queries.get_my_sessions import (
    GetMySessionsHandler,
    GetMySessionsQuery,
    SessionInfo,
)
from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_auth_context,
)
from src.modules.identity.presentation.schemas import MessageResponse
from src.shared.interfaces.auth import AuthContext

identity_account_router = APIRouter(
    prefix="/users",
    tags=["Account Management"],
    route_class=DishkaRoute,
)


@identity_account_router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete my account (GDPR)",
    dependencies=[Depends(RequirePermission("users:delete"))],
)
async def delete_my_account(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[DeactivateIdentityHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    command = DeactivateIdentityCommand(
        identity_id=auth.identity_id,
        reason="user_request",
    )
    await handler.handle(command)
    return MessageResponse(message="Account deactivated. PII will be anonymized.")


@identity_account_router.get(
    "/me/sessions",
    response_model=list[SessionInfo],
    summary="List my active sessions",
)
async def get_my_sessions(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[GetMySessionsHandler] = ...,  # type: ignore[assignment]
) -> list[SessionInfo]:
    query = GetMySessionsQuery(
        identity_id=auth.identity_id,
        current_session_id=auth.session_id,
    )
    return await handler.handle(query)
```

- [ ] **Step 2: Clean up `src/modules/user/presentation/router.py`**

Remove lines 5-13 (identity.application imports) and lines 82-113 (the two endpoints). The file should retain only `get_my_profile` and `update_profile`. Also remove unused imports (`DeactivateIdentityCommand`, `DeactivateIdentityHandler`, `GetMySessionsHandler`, `GetMySessionsQuery`, `SessionInfo`).

- [ ] **Step 3: Register the new router in `src/api/router.py`**

Add: `from src.modules.identity.presentation.router_account import identity_account_router`
Add: `router.include_router(identity_account_router)`

- [ ] **Step 4: Run lint and verify**

Run: `uv run ruff check src/modules/identity/presentation/ src/modules/user/presentation/ src/api/ --fix`
Run: `uv run pytest tests/e2e/ -v --timeout=30`

- [ ] **Step 5: Commit**

```bash
git add src/modules/user/presentation/router.py src/modules/identity/presentation/router_account.py src/api/router.py
git commit -m "refactor: move deactivate/sessions endpoints to identity module, fix cross-module boundary"
```

---

## Phase 4: Domain Logic & UoW Fixes

> These fixes address missing aggregate registration, domain event type safety, and UoW bypasses.

### Task 4.1: Register Aggregate Before Commit in CreateCategoryHandler

**Fixes:** MJ-7 (CreateCategoryHandler doesn't register aggregate)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/catalog/application/commands/create_category.py:74-76`

- [ ] **Step 1: Add register_aggregate call and move cache invalidation outside UoW**

Replace lines 74-86 (the end of the `async with self._uow:` block):
```python
            category = await self._category_repo.add(category)
            await self._uow.commit()
            await self._cache.delete(CACHE_KEY)

            return CreateCategoryResult(
                id=category.id,
                name=category.name,
                slug=category.slug,
                full_slug=category.full_slug,
                level=category.level,
                sort_order=category.sort_order,
                parent_id=category.parent_id,
            )
```

With:
```python
            category = await self._category_repo.add(category)
            self._uow.register_aggregate(category)
            await self._uow.commit()

        try:
            await self._cache.delete(CACHE_KEY)
        except Exception:
            pass  # Cache miss is acceptable; it will expire naturally

        return CreateCategoryResult(
            id=category.id,
            name=category.name,
            slug=category.slug,
            full_slug=category.full_slug,
            level=category.level,
            sort_order=category.sort_order,
            parent_id=category.parent_id,
        )
```

Note: This combines the aggregate registration fix (MJ-7) and cache invalidation fix (CR-7) into one atomic change for this file.

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/application/commands/create_category.py
git commit -m "fix: register category aggregate before commit to capture domain events"
```

---

### Task 4.2: Register Aggregates in Delete Handlers

**Fixes:** MJ-8 (Delete handlers don't register aggregates)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/catalog/application/commands/delete_brand.py:27-33`
- Modify: `src/modules/catalog/application/commands/delete_category.py:35-46`

- [ ] **Step 1: Add register_aggregate in DeleteBrandHandler**

In `delete_brand.py`, after `brand = await self._brand_repo.get(command.brand_id)` and before `await self._brand_repo.delete(...)`, add:
```python
            self._uow.register_aggregate(brand)
```

- [ ] **Step 2: Add register_aggregate in DeleteCategoryHandler**

In `delete_category.py`, after `category = await self._category_repo.get(command.category_id)` and before `await self._category_repo.delete(...)`, add:
```python
            self._uow.register_aggregate(category)
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/delete_brand.py src/modules/catalog/application/commands/delete_category.py
git commit -m "fix: register aggregates in delete handlers to preserve domain events"
```

---

### Task 4.3: Fix User Module Consumers to Use DI

**Fixes:** MJ-9 (Consumers bypass UoW, manually construct repositories)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/user/application/consumers/identity_events.py`

- [ ] **Step 1: Rewrite `create_user_on_identity_registered`**

Replace the function to use Dishka-injected `IUserRepository` and `IUnitOfWork`:

```python
from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.uow import IUnitOfWork


@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="user.identity_registered",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def create_user_on_identity_registered(
    identity_id: str,
    email: str,
    user_repo: FromDishka[IUserRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """Create User row with Shared PK when identity registers."""
    identity_uuid = uuid.UUID(identity_id)

    existing = await user_repo.get(identity_uuid)
    if existing:
        logger.info("user.already_exists", identity_id=identity_id)
        return {"status": "skipped", "reason": "already_exists"}

    user = User.create_from_identity(
        identity_id=identity_uuid,
        profile_email=email,
    )
    async with uow:
        await user_repo.add(user)
        uow.register_aggregate(user)
        await uow.commit()

    logger.info("user.created_from_event", identity_id=identity_id)
    return {"status": "success"}
```

- [ ] **Step 2: Rewrite `anonymize_user_on_identity_deactivated` similarly**

```python
@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="user.identity_deactivated",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def anonymize_user_on_identity_deactivated(
    identity_id: str,
    user_repo: FromDishka[IUserRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """GDPR: Anonymize user PII when identity is deactivated."""
    identity_uuid = uuid.UUID(identity_id)

    user = await user_repo.get(identity_uuid)
    if not user:
        logger.warning("user.not_found_for_anonymization", identity_id=identity_id)
        return {"status": "skipped", "reason": "user_not_found"}

    user.anonymize()
    async with uow:
        await user_repo.update(user)
        uow.register_aggregate(user)
        await uow.commit()

    logger.info("user.anonymized", identity_id=identity_id)
    return {"status": "success"}
```

- [ ] **Step 3: Remove unused imports**

Remove `from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker` since it's no longer needed.

- [ ] **Step 4: Run lint**

Run: `uv run ruff check src/modules/user/application/consumers/ --fix && uv run ruff format src/modules/user/application/consumers/`

- [ ] **Step 5: Commit**

```bash
git add src/modules/user/application/consumers/identity_events.py
git commit -m "refactor: use Dishka DI for user consumers, proper UoW pattern"
```

---

### Task 4.4: Consolidate CACHE_KEY Constant

**Fixes:** MJ-14 (CACHE_KEY duplicated in 4 files)
**Severity:** MAJOR

**Files:**
- Create: `src/modules/catalog/application/constants.py` (already exists — check first)
- Modify: `src/modules/catalog/application/commands/create_category.py:14`
- Modify: `src/modules/catalog/application/commands/update_category.py:14`
- Modify: `src/modules/catalog/application/commands/delete_category.py:13`
- Modify: `src/modules/catalog/application/queries/get_category_tree.py:19`

- [ ] **Step 1: Append the constant to the existing `constants.py`**

The file `src/modules/catalog/application/constants.py` already exists with `raw_logo_key()` and `public_logo_key()` functions. Append at the end:
```python

CATEGORY_TREE_CACHE_KEY = "catalog:category_tree"
```

- [ ] **Step 2: Update all 4 files to import from constants**

In each file, replace:
```python
CACHE_KEY = "catalog:category_tree"
```

With:
```python
from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
```

And replace all references to `CACHE_KEY` with `CATEGORY_TREE_CACHE_KEY` in each file.

- [ ] **Step 3: Run lint**

Run: `uv run ruff check src/modules/catalog/application/ --fix && uv run ruff format src/modules/catalog/application/`

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/application/
git commit -m "refactor: consolidate CACHE_KEY into constants.py, remove duplication"
```

---

### Task 4.5: Fix Domain Event None Defaults

**Fixes:** MJ-16 (Domain events allow None for required UUID fields)
**Severity:** MAJOR

**Files:**
- Modify: `src/modules/catalog/domain/events.py:23`
- Modify: `src/modules/identity/domain/events.py:23, 43, 63-64`

- [ ] **Step 1: Add `__post_init__` validation to `BrandCreatedEvent`**

In `src/modules/catalog/domain/events.py`, add after `BrandCreatedEvent`:
```python
    def __post_init__(self) -> None:
        if self.brand_id is None:
            raise ValueError("brand_id is required for BrandCreatedEvent")
        if not self.aggregate_id:
            self.aggregate_id = str(self.brand_id)
```

Apply the same pattern to `BrandLogoConfirmedEvent` and `BrandLogoProcessedEvent`.

- [ ] **Step 2: Enhance existing `__post_init__` methods in identity events**

`IdentityRegisteredEvent`, `IdentityDeactivatedEvent`, and `RoleAssignmentChangedEvent` already have `__post_init__` methods. Enhance `RoleAssignmentChangedEvent.__post_init__` (line 69) to add None validation:

Replace:
```python
    def __post_init__(self) -> None:
        if self.identity_id is not None and not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
```
With:
```python
    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.role_id is None:
            raise ValueError("role_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
```

- [ ] **Step 3: Run existing event tests**

Run: `uv run pytest tests/unit/modules/catalog/domain/test_events.py tests/unit/modules/identity/domain/test_events.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/domain/events.py src/modules/identity/domain/events.py
git commit -m "fix: add __post_init__ validation to domain events, prevent None UUIDs"
```

---

## Phase 5: Concurrency & Infrastructure Fixes

### Task 5.1: Move Cache Invalidation Outside UoW Block (update_category & delete_category)

**Fixes:** CR-7 (Cache invalidation race condition) — for the two files NOT already fixed in Task 4.1
**Severity:** CRITICAL

**Note:** `create_category.py` was already fixed in Task 4.1 (combined with aggregate registration). This task fixes the remaining two files.

**Files:**
- Modify: `src/modules/catalog/application/commands/update_category.py:79-92`
- Modify: `src/modules/catalog/application/commands/delete_category.py:44-48`

**Dependency:** If Task 4.4 (CACHE_KEY consolidation) has been applied, use `CATEGORY_TREE_CACHE_KEY`. If not, use the local `CACHE_KEY`. Both refer to the same string.

- [ ] **Step 1: Fix `update_category.py`**

Move `await self._cache.delete(CACHE_KEY)` outside the `async with self._uow:` block. Replace:
```python
            await self._uow.commit()
            await self._cache.delete(CACHE_KEY)

        self._logger.info("Категория обновлена", category_id=str(category.id))
```
With:
```python
            await self._uow.commit()

        try:
            await self._cache.delete(CACHE_KEY)
        except Exception:
            pass

        self._logger.info("Категория обновлена", category_id=str(category.id))
```

- [ ] **Step 2: Fix `delete_category.py` similarly**

Replace:
```python
            await self._category_repo.delete(command.category_id)
            await self._uow.commit()
            await self._cache.delete(CACHE_KEY)

        self._logger.info("Категория удалена", category_id=str(command.category_id))
```
With:
```python
            await self._category_repo.delete(command.category_id)
            await self._uow.commit()

        try:
            await self._cache.delete(CACHE_KEY)
        except Exception:
            pass

        self._logger.info("Категория удалена", category_id=str(command.category_id))
```

- [ ] **Step 4: Run lint and tests**

Run: `uv run ruff check src/modules/catalog/application/commands/ --fix && uv run ruff format src/modules/catalog/application/commands/`
Run: `uv run pytest tests/ -k "category" -v`

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/application/commands/
git commit -m "fix: move cache invalidation outside UoW block to prevent post-commit failures"
```

---

### Task 5.2: Remove Duplicate Database Session Module

**Fixes:** CR-5 (Duplicated engine/session configuration)
**Severity:** CRITICAL

**Files:**
- Modify: `src/infrastructure/database/session.py`

- [ ] **Step 1: Search for imports of session.py**

Run: Search for `from src.infrastructure.database.session import` across codebase to identify all consumers.

- [ ] **Step 2: Migrate any consumers to use Dishka-provided sessions**

If any file imports `get_session`, `engine`, or `async_session_maker` from `session.py`, update it to receive the session via DI instead.

- [ ] **Step 3: Replace session.py content with a deprecation guard**

```python
# src/infrastructure/database/session.py
"""
DEPRECATED: Use DatabaseProvider via Dishka DI instead.
This module exists only for backward compatibility during migration.
"""

raise ImportError(
    "Direct import from session.py is deprecated. "
    "Use Dishka DI to inject AsyncSession or async_sessionmaker."
)
```

Or simply delete it if no imports remain.

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=60`

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/database/session.py
git commit -m "refactor: remove duplicate database session module, enforce DI-only access"
```

---

### Task 5.3: Fix Blocking Sync I/O in Async Media Processor

**Fixes:** CR-6 (Pillow blocking the event loop)
**Severity:** CRITICAL

**Files:**
- Modify: `src/modules/catalog/application/services/media_processor.py`

- [ ] **Step 1: Wrap blocking call in `anyio.to_thread.run_sync`**

In `src/modules/catalog/application/services/media_processor.py`, `_convert_to_webp` is a `@staticmethod` with signature `(raw_data: bytes, log: ILogger) -> bytes`. Since `anyio.to_thread.run_sync` takes a single callable with no extra positional args, use `functools.partial`.

Add import at top:
```python
import functools
import anyio
```

Replace line 41:
```python
            processed_data = self._convert_to_webp(raw_data, log)
```
With:
```python
            processed_data = await anyio.to_thread.run_sync(
                functools.partial(self._convert_to_webp, raw_data, log)
            )
```

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src/modules/catalog/application/services/ --fix`

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/services/media_processor.py
git commit -m "fix: run Pillow image conversion in thread pool to unblock async event loop"
```

---

## Phase 6: Code Quality — Consistency & DRY

### Task 6.1: Extract Shared CamelModel

**Fixes:** m-10 (CamelModel duplicated in 3 schema files)
**Severity:** MINOR

**Files:**
- Create: `src/shared/schemas.py`
- Modify: `src/modules/catalog/presentation/schemas.py:7-8`
- Modify: `src/modules/identity/presentation/schemas.py:8-9`
- Modify: `src/modules/user/presentation/schemas.py:8-9`

- [ ] **Step 1: Create shared schema file**

Create `src/shared/schemas.py`:
```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
```

- [ ] **Step 2: Update all 3 schema files to import from shared**

In each file, replace the local `CamelModel` definition with:
```python
from src.shared.schemas import CamelModel
```

Remove the now-unused `ConfigDict` and `to_camel` imports.

- [ ] **Step 3: Run lint and verify**

Run: `uv run ruff check src/modules/*/presentation/schemas.py src/shared/schemas.py --fix && uv run ruff format src/modules/*/presentation/schemas.py src/shared/schemas.py`

- [ ] **Step 4: Commit**

```bash
git add src/shared/schemas.py src/modules/catalog/presentation/schemas.py src/modules/identity/presentation/schemas.py src/modules/user/presentation/schemas.py
git commit -m "refactor: extract shared CamelModel to src/shared/schemas.py"
```

---

### Task 6.2: Standardize StorageFile to attrs

**Fixes:** m-8 (StorageFile uses dataclasses.dataclass instead of attr.dataclass)
**Severity:** MINOR

**Files:**
- Modify: `src/modules/storage/domain/entities.py`

- [ ] **Step 1: Replace stdlib dataclasses with attrs**

Check how other domain entities import attrs. The project uses `from attr import dataclass` (e.g., `catalog/domain/entities.py`). Replace:
```python
from dataclasses import dataclass
```
With:
```python
from attr import dataclass
```

This is a drop-in replacement since both provide `@dataclass`. Note: The project convention is `from attr import dataclass`, not `import attrs` with `@attrs.define`.

- [ ] **Step 2: Run storage unit tests**

Run: `uv run pytest tests/unit/modules/storage/ -v`

- [ ] **Step 3: Commit**

```bash
git add src/modules/storage/domain/entities.py
git commit -m "refactor: migrate StorageFile from stdlib dataclass to attr.dataclass for consistency"
```

---

### Task 6.3: Add UpdateProfileRequest Validator

**Fixes:** m-6 (Empty body allowed)
**Severity:** MINOR

**Files:**
- Modify: `src/modules/user/presentation/schemas.py:20-24`

- [ ] **Step 1: Add model_validator**

Replace:
```python
class UpdateProfileRequest(CamelModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    profile_email: str | None = Field(None, max_length=320)
```

With:
```python
class UpdateProfileRequest(CamelModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    profile_email: str | None = Field(None, max_length=320)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateProfileRequest":
        if all(
            v is None
            for v in (self.first_name, self.last_name, self.phone, self.profile_email)
        ):
            raise ValueError("At least one field must be provided")
        return self
```

Add `model_validator` to the import: `from pydantic import BaseModel, ConfigDict, Field, model_validator`

- [ ] **Step 2: Commit**

```bash
git add src/modules/user/presentation/schemas.py
git commit -m "fix: add at_least_one_field validator to UpdateProfileRequest"
```

---

### Task 6.4: Fix Remaining Style Issues

**Fixes:** m-15 (Dict→dict), m-17 (raise e → raise), m-18 (return Any), m-19 (EventHandler=Any), m-20 (typo "loyality"), m-21 (f-string in structlog)
**Severity:** MINOR

**Files:**
- Modify: `src/shared/interfaces/storage.py:4, 55, 88` — replace `Dict` with `dict`
- Modify: `src/modules/catalog/presentation/router.py:102` — return type `Any` → `list[CategoryTreeResponse]`
- Modify: `src/infrastructure/outbox/relay.py:25` — proper `EventHandler` type alias
- Modify: `src/infrastructure/database/provider.py:22` — fix "loyality" typo
- Modify: `src/infrastructure/cache/provider.py:33` — fix f-string in structlog

- [ ] **Step 1: Fix `storage.py` — replace Dict with dict**

Replace:
```python
from typing import Any, Dict, Protocol
```
With:
```python
from typing import Any, Protocol
```

Replace both `Dict[str, Any]` occurrences with `dict[str, Any]`.

- [ ] **Step 2: Fix router.py return type and remove unused import**

Replace:
```python
async def get_category_tree(
    handler: FromDishka[GetCategoryTreeHandler],
) -> Any:
```
With:
```python
async def get_category_tree(
    handler: FromDishka[GetCategoryTreeHandler],
) -> list[CategoryTreeResponse]:
```

Also remove the entire `from typing import Any` import on line 3 (no other usage in the file).

- [ ] **Step 3: Fix EventHandler type in relay.py**

Replace:
```python
EventHandler = Any  # Callable[[dict, str | None], Awaitable[None]]
```
With:
```python
from collections.abc import Awaitable, Callable

EventHandler = Callable[[dict[str, Any], str | None], Awaitable[None]]
```

- [ ] **Step 4: Fix "loyality" typo in provider.py**

Replace:
```python
        "application_name": "loyality",
```
With:
```python
        "application_name": "enterprise_api",
```

- [ ] **Step 5: Fix f-string in cache provider.py**

Replace:
```python
        logger.info(
            f"Соединение с Redis успешно установлено (Ping {await client.ping()})"
        )
```
With:
```python
        logger.info(
            "Redis connection established",
            ping=await client.ping(),
        )
```

- [ ] **Step 6: Fix debug log in redis.py (m-3)**

In `src/infrastructure/cache/redis.py`, replace:
```python
            logger.debug("Redis SET", key=key, value=value)
```
With:
```python
            logger.debug("Redis SET", key=key)
```

- [ ] **Step 7: Run lint on all modified files**

Run: `uv run ruff check src/ --fix && uv run ruff format src/`

- [ ] **Step 8: Commit**

```bash
git add src/shared/interfaces/storage.py src/modules/catalog/presentation/router.py src/infrastructure/outbox/relay.py src/infrastructure/database/provider.py src/infrastructure/cache/provider.py src/infrastructure/cache/redis.py
git commit -m "fix: assorted style fixes — Dict→dict, typos, type annotations, structured logging"
```

---

## Phase 7: Code Quality — Dead Code & Missing Config

### Task 7.1: Remove Dead Code

**Fixes:** m-9 (PermissionCode unused), m-12 (Empty SqlCategoryQueryService), m-13 (Empty order module)
**Severity:** MINOR

**Files:**
- Modify: `src/modules/identity/domain/value_objects.py` — remove `PermissionCode` if unused
- Delete: `src/modules/catalog/infrastructure/queries.py` — empty class
- Optionally remove: `src/modules/order/` — all empty files (discuss with team first)

- [ ] **Step 1: Keep PermissionCode — it is tested and reserved for future use**

`PermissionCode` is tested in `tests/unit/modules/identity/domain/test_value_objects.py` (lines 17-40). While it is not used in production code yet, it is a valid domain value object with passing tests. **Do not remove it.** Instead, add a usage TODO in the `Permission` entity or keep as-is for future integration. Mark m-9 as "intentionally deferred — tested value object reserved for future use".

- [ ] **Step 2: Remove empty SqlCategoryQueryService**

Delete `src/modules/catalog/infrastructure/queries.py` or replace with a TODO comment.

- [ ] **Step 3: Commit**

```bash
git add -u
git commit -m "chore: remove dead code — unused PermissionCode, empty SqlCategoryQueryService"
```

---

### Task 7.2: Add ruff and mypy Configuration

**Fixes:** MJ-18 (Missing tool configuration)
**Severity:** MAJOR

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add ruff configuration**

Add to `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py314"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

- [ ] **Step 2: Add mypy configuration**

```toml
[tool.mypy]
python_version = "3.14"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

- [ ] **Step 3: Run both tools**

Run: `uv run ruff check . --fix && uv run ruff format .`
Run: `uv run mypy src/ --ignore-missing-imports` (note any new failures)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add ruff and mypy configuration to pyproject.toml"
```

---

## Phase 8: DomainEvent Base Class & BrandRepository Consistency

### Task 8.1: Enforce DomainEvent Subclass Overrides

**Fixes:** MJ-17 (DomainEvent base class doesn't enforce subclass overrides)
**Severity:** MAJOR

**Files:**
- Modify: `src/shared/interfaces/entities.py:23-37`

- [ ] **Step 1: Add `__init_subclass__` validation**

In `DomainEvent`, add:
```python
@dataclass
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    aggregate_type: str = ""
    aggregate_id: str = ""
    event_type: str = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.aggregate_type == "" or cls.event_type == "":
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' and 'event_type'"
            )
```

- [ ] **Step 2: Verify all event subclasses pass validation**

Run: `uv run python -c "from src.modules.catalog.domain.events import BrandCreatedEvent; print('OK')"`
Run: `uv run python -c "from src.modules.identity.domain.events import IdentityRegisteredEvent; print('OK')"`

- [ ] **Step 3: Run unit tests**

Run: `uv run pytest tests/unit/ -v`

- [ ] **Step 4: Commit**

```bash
git add src/shared/interfaces/entities.py
git commit -m "fix: enforce DomainEvent subclass must override aggregate_type and event_type"
```

---

### Task 8.2: Make BrandRepository Extend BaseRepository (Optional)

**Fixes:** MJ-15 (BrandRepository doesn't inherit BaseRepository)
**Severity:** MAJOR (code quality, not correctness)

**Files:**
- Modify: `src/modules/catalog/infrastructure/repositories/brand.py`

- [ ] **Step 1: Evaluate trade-offs**

`BrandRepository` has additional methods (`get_by_slug`, `check_slug_exists`, `check_slug_exists_excluding`, `get_for_update`) that `BaseRepository` doesn't support. The `delete()` also calls `flush()` while `BaseRepository.delete()` doesn't.

Two options:
- **Option A:** Extend BaseRepository, add the extra methods, remove `flush()` from delete.
- **Option B:** Keep separate but remove the redundant `flush()` from `delete()` to align with UoW-controlled transaction boundaries.

**Recommended:** Option B (least risk).

- [ ] **Step 2: Remove flush() from BrandRepository.delete()**

Replace:
```python
    async def delete(self, id: uuid.UUID) -> None:
        statement = delete(OrmBrand).where(OrmBrand.id == id)
        await self._session.execute(statement)
        await self._session.flush()
```
With:
```python
    async def delete(self, id: uuid.UUID) -> None:
        statement = delete(OrmBrand).where(OrmBrand.id == id)
        await self._session.execute(statement)
```

- [ ] **Step 3: Run integration tests**

Run: `uv run pytest tests/integration/modules/catalog/ -v`

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/infrastructure/repositories/brand.py
git commit -m "fix: remove redundant flush() from BrandRepository.delete(), UoW controls transactions"
```

---

## Violation ↔ Task Cross-Reference

| Violation ID | Severity | Task | Phase |
|--------------|----------|------|-------|
|     CR-1     | CRITICAL | 1.1  |   1   |
|     CR-2     | CRITICAL | 1.2  |   1   |
|     CR-3     | CRITICAL | 3.1, 3.2, 3.3 | 3 |
|     CR-4     | CRITICAL | 3.3  |   3   |
|     CR-5     | CRITICAL | 5.2  |   5   |
|     CR-6     | CRITICAL | 5.3  |   5   |
|     CR-7     | CRITICAL | 5.1  |   5   |
|     MJ-1     |  MAJOR   | 2.1  |   2   |
|     MJ-2     |  MAJOR   | — (design decision, not code-only fix) | — |
|     MJ-3     |  MAJOR   | — (design decision, not code-only fix) | — |
|     MJ-4     |  MAJOR   | — (requires design: session family tracking) | — |
|     MJ-5     |  MAJOR   | — (requires Redis rate limiter middleware) | — |
|     MJ-6     |  MAJOR   | 3.4  |   3   |
|     MJ-7     |  MAJOR   | 4.1  |   4   |
|     MJ-8     |  MAJOR   | 4.2  |   4   |
|     MJ-9     |  MAJOR   | 4.3  |   4   |
| MJ-10 | MAJOR | 2.2 | 2 |
| MJ-11 | MAJOR | 2.3 | 2 |
| MJ-12 | MAJOR | 2.4 | 2 |
| MJ-13 | MAJOR | — (blocked: domain entities not yet defined) | — |
| MJ-14 | MAJOR | 4.4 | 4 |
| MJ-15 | MAJOR | 8.2 | 8 |
| MJ-16 | MAJOR | 4.5 | 4 |
| MJ-17 | MAJOR | 8.1 | 8 |
| MJ-18 | MAJOR | 7.2 | 7 |
| m-1 | MINOR | 2.5 | 2 |
| m-2 | MINOR | 2.6 | 2 |
| m-3 | MINOR | 6.4 | 6 |
| m-4 | MINOR | 2.7 | 2 |
| m-5 | MINOR | 2.7 | 2 |
| m-6 | MINOR | 6.3 | 6 |
| m-7 | MINOR | 2.4 | 2 |
| m-8 | MINOR | 6.2 | 6 |
| m-9 | MINOR | — (tested VO, keep for future use) | — |
| m-10 | MINOR | 6.1 | 6 |
| m-11 | MINOR | 2.4 | 2 |
| m-12 | MINOR | 7.1 | 7 |
| m-13 | MINOR | 7.1 | 7 |
| m-14 | MINOR | — (mixed language, team decision) | — |
| m-15 | MINOR | 6.4 | 6 |
| m-16 | MINOR | 2.2 | 2 |
| m-17 | MINOR | 2.2 | 2 |
| m-18 | MINOR | 6.4 | 6 |
| m-19 | MINOR | 6.4 | 6 |
| m-20 | MINOR | 6.4 | 6 |
| m-21 | MINOR | 6.4 | 6 |

### Violations Deferred (Require Design Decisions)

| ID | Reason | Recommendation |
|----|--------|---------------|
| MJ-2 | TOCTOU on email uniqueness requires architectural decision (SELECT FOR UPDATE vs catch IntegrityError) | Brainstorm session recommended |
| MJ-3 | TOCTOU on slug uniqueness — same pattern as MJ-2 | Bundle with MJ-2 |
| MJ-4 | Refresh token reuse revocation requires session family tracking design | Separate spec + plan |
| MJ-5 | Rate limiting requires new middleware + Redis integration | Separate spec + plan |
| MJ-13 | Product/Attribute ORM leak — blocked until domain entities are defined | Part of future product module work |
| m-14 | Mixed Russian/English error messages — team convention decision | Discuss in team meeting |
