# Admin RBAC Backend API — Design Spec (Refined)

**Date:** 2026-03-19
**Scope:** New backend endpoints for admin user listing, role management (update, permission assignment), identity deactivation/reactivation, and grouped permissions listing. All within existing DDD/CQRS/Modular Monolith architecture.
**Module:** `identity` (read models cross-join with `users` table on query side)

---

## Revision Notes

Changes made vs. original spec after deep codebase analysis:

### ADDITIONS
1. **Alembic migration required** — `identities` table has NO `deactivated_at` or `deactivated_by` columns. A new migration must add them.
2. **`IdentityDeactivatedEvent` needs `deactivated_by` field** — current event only has `identity_id` and `reason`. Must add optional `deactivated_by: uuid.UUID | None`.
3. **`Identity.deactivate()` signature change** — current method takes only `reason: str`. Must extend to accept `deactivated_by: uuid.UUID | None = None` and store both new fields.
4. **`IIdentityRepository.update()` method missing** — current interface has `add`, `get`, `get_by_email`, `add_credentials`, `update_credentials`, `email_exists`. Need to add `update(identity: Identity)` for deactivation/reactivation state persistence. The ORM flush in `_uow.commit()` handles this via the existing `IdentityModel` already loaded in session, but the repo pattern requires explicit `update`.
5. **`IRoleRepository` needs 3 new methods** — `update(role: Role)`, `count_identities_with_role(role_name: str) -> int`, `get_role_permissions(role_id) -> list[Permission]`.
6. **`IPermissionRepository` needs `get_by_ids(ids: list[UUID]) -> list[Permission]`** — for batch validation in `SetRolePermissionsHandler`.
7. **New `IdentityNotFoundError` exception** — existing code uses inline `NotFoundError(error_code="IDENTITY_NOT_FOUND")`. For admin endpoints, add a dedicated domain exception for consistency.
8. **New `RoleNotFoundError` exception** — same reasoning as above; existing `DeleteRoleHandler` already uses inline `NotFoundError`.
9. **`IdentityReactivatedEvent`** — reactivation should emit a domain event so the User module can reverse anonymization if within the retention window.
10. **DI registrations for 7 new handlers** — must be added to `IdentityProvider` in `provider.py`.
11. **Pagination uses `offset`/`limit`** — matches spec; confirmed this is fine (no existing `page`/`page_size` pattern in codebase). However, the response envelope should use `offset`/`limit` NOT `page`/`page_size` (no `total_pages` field) to stay simple.
12. **Admin `GET /admin/identities/{id}` needs `deactivated_at`, `deactivated_by` fields** in read model.
13. **`identities:manage` permission EXISTS in seed** — confirmed in migration `d2bb038b00e3`. It is assigned to `super_admin` only, not to `manager`. This is correct.
14. **`roles:manage` permission EXISTS in seed** — confirmed. Assigned to `super_admin` only.
15. **`SetRolePermissionsHandler` needs to invalidate cache for ALL identities that have the role** — not just "sessions with this role". Must query `identity_roles` to find affected identities, then their sessions.
16. **Router uses `role_id` in path params** — confirmed from `delete_role` endpoint: `role_id: uuid.UUID` as a path parameter. Keep consistent naming.
17. **The existing `DeactivateIdentityHandler` is a self-service handler** — it does NO admin checks (no self-deactivation guard, no last-admin guard). The new `AdminDeactivateIdentityHandler` must be a SEPARATE handler class that adds these guards and passes `deactivated_by`.

### MODIFICATIONS
1. **`@dataclass` is `from attr import dataclass`** — NOT stdlib `dataclasses.dataclass`. Domain entities use `attrs` (`from attr import dataclass`). Domain events and commands use stdlib `@dataclass(frozen=True)`. The spec must reflect this.
2. **`AggregateRoot` import path is `src.shared.interfaces.entities`** — not `src.shared.entities`.
3. **Query handlers inject `AsyncSession`** — constructor pattern is `def __init__(self, session: AsyncSession)`. NOT a repo interface. Confirmed across `ListRolesHandler`, `ListPermissionsHandler`, `GetIdentityRolesHandler`, `GetMySessionsHandler`.
4. **SQL uses `text()` with `:param` binding** — confirmed. Raw `text()` queries with `{"param": value}` dicts. No f-strings in SQL.
5. **Read models use `BaseModel`** — NOT `CamelModel`. Query handler read models (`RoleWithPermissions`, `PermissionInfo`, `SessionInfo`, `IdentityRoleInfo`) all use plain `pydantic.BaseModel`. Presentation schemas use `CamelModel`.
6. **Read models are defined INLINE in query handler files** — not in separate files. Confirmed in every query handler.
7. **`RolePermissionModel` is a proper ORM model** — not just an association table. It has its own class in `models.py` with `role_id` and `permission_id` as composite PK.
8. **Router variable is `admin_router`** — confirmed. Uses `APIRouter(prefix="/admin", tags=["Admin — IAM"], route_class=DishkaRoute)`.
9. **Path params are accessed directly** — FastAPI path parameter injection, e.g., `role_id: uuid.UUID`.
10. **`RequirePermission` import is `from src.modules.identity.presentation.dependencies import RequirePermission`**.
11. **`get_auth_context` import is same file** — `from src.modules.identity.presentation.dependencies import get_auth_context`.
12. **`AuthContext` has exactly 2 fields** — `identity_id: uuid.UUID` and `session_id: uuid.UUID`. No other fields. Defined in `src.shared.interfaces.auth`.
13. **Original spec listed `RoleAlreadyExistsError`** — but existing `CreateRoleHandler` uses `ConflictError(error_code="ROLE_ALREADY_EXISTS")` from shared exceptions. Keep this pattern for consistency, do NOT add a domain-specific exception class for it.
14. **Command handler constructors use interface deps injected via Dishka** — confirmed: `IIdentityRepository`, `IRoleRepository`, `ISessionRepository`, `IUnitOfWork`, `IPermissionResolver`, `ILogger`. Commands are `@dataclass(frozen=True)` from stdlib.
15. **Logging pattern** — confirmed: `self._logger = logger.bind(handler="ClassName")`, then `self._logger.info("event.name", key=value)` AFTER commit (outside `async with self._uow` block).
16. **UoW pattern** — `async with self._uow:` then operations, then `self._uow.register_aggregate(entity)`, then `await self._uow.commit()`. Cache invalidation happens AFTER the `async with` block exits.
17. **`list[PermissionInfo]` is the current permissions response** — NOT grouped. Enhancement changes this to `list[PermissionGroupResponse]`.
18. **Spec said `UpdateRoleRequest` pattern `^[a-z_]+$`** — this matches existing `CreateRoleRequest` pattern. Keep it.
19. **Privilege escalation check uses `IPermissionResolver.get_permissions(session_id)`** — confirmed. Returns `frozenset[str]` of codenames. The admin's session_id comes from `AuthContext`.
20. **`IdentityModel` has NO `deactivated_at`/`deactivated_by` columns** — confirmed. The ORM model only has: `id`, `type`, `is_active`, `created_at`, `updated_at`. A migration and ORM model change are needed.

### DELETIONS
1. **Removed `reactivate()` method on `IIdentityRepository`** — reactivation is a domain state change on the Identity entity, persisted via `update()`. No need for a separate repo method.
2. **Removed audit log table from scope** — the best practices doc suggests it, but it's a cross-cutting concern that should be its own feature/MT. Not part of this RBAC endpoint spec.
3. **Removed rate limiting from scope** — infrastructure concern, not part of this API design.
4. **Removed role hierarchy management endpoints** — the best practices doc mentions `GET/PUT /admin/roles/{id}/hierarchy`. These are not in the original scope and the hierarchy already exists via seed migration. Defer to a future feature.
5. **Removed batch operations** — `POST /admin/roles/{id}/assignments` (batch assign). Not in scope.
6. **Removed `last_login_at` from read model** — would require joining sessions with aggregation. Over-engineered for MVP. Can add later.
7. **Removed `session_count` from read model** — same reasoning.
8. **Removed `PermissionNotFoundError` as a domain exception** — use `NotFoundError(error_code="PERMISSION_NOT_FOUND")` from shared, consistent with existing `ROLE_NOT_FOUND` and `IDENTITY_NOT_FOUND` patterns.

---

## 1. New Endpoints Summary

| # | Method | Path | Permission | CQRS | Purpose |
|---|--------|------|------------|------|---------|
| 1 | GET | `/admin/identities` | `identities:manage` | Query | Paginated list of all users with roles |
| 2 | GET | `/admin/identities/{identity_id}` | `identities:manage` | Query | Single user detail with roles |
| 3 | POST | `/admin/identities/{identity_id}/deactivate` | `identities:manage` | Command | Admin deactivates user |
| 4 | POST | `/admin/identities/{identity_id}/reactivate` | `identities:manage` | Command | Admin reactivates user |
| 5 | GET | `/admin/roles/{role_id}` | `roles:manage` | Query | Single role detail with permissions |
| 6 | PATCH | `/admin/roles/{role_id}` | `roles:manage` | Command | Update role name/description |
| 7 | PUT | `/admin/roles/{role_id}/permissions` | `roles:manage` | Command | Full-replace permissions set for role |
| 8 | GET | `/admin/permissions` | `roles:manage` | Query | List permissions grouped by resource (replaces existing flat list) |

Existing endpoints unchanged: `GET /admin/roles`, `POST /admin/roles`, `DELETE /admin/roles/{role_id}`, `POST /admin/identities/{identity_id}/roles`, `DELETE /admin/identities/{identity_id}/roles/{role_id}`.

---

## 2. Endpoint Details

### 2.1 GET /admin/identities — Paginated User List

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `offset` | int | 0 | Offset for pagination |
| `limit` | int | 20 | Page size (1-100) |
| `search` | str? | null | ILIKE search on email, first_name, last_name |
| `role_id` | uuid? | null | Filter by role |
| `is_active` | bool? | null | Filter by status |
| `sort_by` | str | `created_at` | Sort column: `created_at`, `email`, `last_name` |
| `sort_order` | str | `desc` | Sort direction: `asc`, `desc` |

**Query handler:** `ListIdentitiesHandler` in `identity/application/queries/list_identities.py`

Cross-context read model (query-side join across `identities`, `local_credentials`, `users`, `identity_roles`, `roles`). Acceptable in CQRS — queries bypass domain models.

**Read model** (defined inline in the query handler file, uses `BaseModel`):
```python
class AdminIdentityListItem(BaseModel):
    identity_id: uuid.UUID
    email: str | None          # from local_credentials
    auth_type: str             # LOCAL | OIDC
    is_active: bool
    first_name: str            # from users
    last_name: str
    phone: str | None
    roles: list[str]           # role names
    created_at: datetime
```

**Presentation response schema** (in `schemas.py`, uses `CamelModel`):
```python
class AdminIdentityListResponse(CamelModel):
    items: list[AdminIdentityResponse]
    total: int
    offset: int
    limit: int

class AdminIdentityResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    roles: list[str]
    created_at: datetime
```

**SQL:** Raw `text()` query with dynamic WHERE clauses, ILIKE for search, sub-select for role filter, sub-select for role names aggregation.

**SQL pattern:**
```python
# Base query counts total, then fetches page
_COUNT_SQL_PARTS = [
    "SELECT COUNT(DISTINCT i.id) FROM identities i",
    "LEFT JOIN local_credentials lc ON lc.identity_id = i.id",
    "LEFT JOIN users u ON u.id = i.id",
]

_LIST_SQL_PARTS = [
    "SELECT i.id AS identity_id, lc.email, i.type AS auth_type, i.is_active,",
    "u.first_name, u.last_name, u.phone, i.created_at",
    "FROM identities i",
    "LEFT JOIN local_credentials lc ON lc.identity_id = i.id",
    "LEFT JOIN users u ON u.id = i.id",
]

# Dynamic WHERE built by handler:
# - search: AND (lc.email ILIKE :search OR u.first_name ILIKE :search OR u.last_name ILIKE :search)
# - role_id: AND EXISTS (SELECT 1 FROM identity_roles ir WHERE ir.identity_id = i.id AND ir.role_id = :role_id)
# - is_active: AND i.is_active = :is_active

# Sort column whitelist to prevent SQL injection:
_SORT_COLUMNS = {
    "created_at": "i.created_at",
    "email": "lc.email",
    "last_name": "u.last_name",
}

# Role names fetched as a second query (same pattern as ListRolesHandler):
_IDENTITY_ROLE_NAMES_SQL = text(
    "SELECT ir.identity_id, r.name "
    "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
    "WHERE ir.identity_id = ANY(:identity_ids)"
)
```

**Handler constructor:**
```python
class ListIdentitiesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
```

---

### 2.2 GET /admin/identities/{identity_id} — Single User Detail

Returns detailed identity info with full role objects (not just names).

**Read model** (inline in query handler file, `BaseModel`):
```python
class RoleInfo(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool

class AdminIdentityDetail(BaseModel):
    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    roles: list[RoleInfo]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None
```

**Presentation response** (in `schemas.py`, `CamelModel`):
```python
class AdminIdentityDetailResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    roles: list[RoleInfoResponse]  # {id, name, description, isSystem}
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None

class RoleInfoResponse(CamelModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
```

**Error:** `NotFoundError(error_code="IDENTITY_NOT_FOUND")` (404) if identity doesn't exist.

**SQL:**
```python
_IDENTITY_DETAIL_SQL = text(
    "SELECT i.id AS identity_id, lc.email, i.type AS auth_type, i.is_active, "
    "u.first_name, u.last_name, u.phone, i.created_at, "
    "i.deactivated_at, i.deactivated_by "
    "FROM identities i "
    "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
    "LEFT JOIN users u ON u.id = i.id "
    "WHERE i.id = :identity_id"
)

_IDENTITY_ROLES_SQL = text(
    "SELECT r.id, r.name, r.description, r.is_system "
    "FROM roles r "
    "JOIN identity_roles ir ON ir.role_id = r.id "
    "WHERE ir.identity_id = :identity_id "
    "ORDER BY r.name"
)
```

**Handler constructor:**
```python
class GetIdentityDetailHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
```

---

### 2.3 POST /admin/identities/{identity_id}/deactivate — Admin Deactivation

**Request body:**
```python
class AdminDeactivateRequest(CamelModel):
    reason: str = Field(..., min_length=1, max_length=200)
```

**Handler:** `AdminDeactivateIdentityHandler` — a NEW handler separate from the existing self-service `DeactivateIdentityHandler`.

**Command:**
```python
@dataclass(frozen=True)
class AdminDeactivateIdentityCommand:
    identity_id: uuid.UUID
    reason: str
    deactivated_by: uuid.UUID
```

**Handler constructor:**
```python
class AdminDeactivateIdentityHandler:
    def __init__(
        self,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
```

**Logic:**
1. `async with self._uow:`
2. Get identity → `NotFoundError(error_code="IDENTITY_NOT_FOUND")` if None
3. Check `identity.is_active is True` → `ConflictError(error_code="IDENTITY_ALREADY_DEACTIVATED")` if already deactivated
4. Check `command.identity_id != command.deactivated_by` → `ForbiddenError(error_code="SELF_DEACTIVATION_FORBIDDEN")` if same
5. Check not last `super_admin`: `count = await self._role_repo.count_identities_with_role("super_admin")` → if count <= 1 AND target has super_admin role, raise `ForbiddenError(error_code="LAST_ADMIN_PROTECTION")`
6. `identity.deactivate(reason=command.reason, deactivated_by=command.deactivated_by)`
7. `revoked_ids = await self._session_repo.revoke_all_for_identity(command.identity_id)`
8. `self._uow.register_aggregate(identity)` then `await self._uow.commit()`
9. After `async with` block: invalidate permission cache for each `revoked_id`
10. Log `"identity.admin_deactivated"`
11. Return `None`

**Response:** `MessageResponse(message="Identity deactivated")`

---

### 2.4 POST /admin/identities/{identity_id}/reactivate — Admin Reactivation

**Request body:** none

**Command:**
```python
@dataclass(frozen=True)
class ReactivateIdentityCommand:
    identity_id: uuid.UUID
    reactivated_by: uuid.UUID
```

**Handler constructor:**
```python
class ReactivateIdentityHandler:
    def __init__(
        self,
        identity_repo: IIdentityRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
```

**Logic:**
1. `async with self._uow:`
2. Get identity → `NotFoundError(error_code="IDENTITY_NOT_FOUND")` if None
3. Check `identity.is_active is False` → `ConflictError(error_code="IDENTITY_ALREADY_ACTIVE")` if already active
4. `identity.reactivate()` — new domain method: sets `is_active = True`, clears `deactivated_at` and `deactivated_by`, sets `updated_at`, emits `IdentityReactivatedEvent`
5. `self._uow.register_aggregate(identity)` then `await self._uow.commit()`
6. Log `"identity.reactivated"`

**Response:** `MessageResponse(message="Identity reactivated")`

---

### 2.5 GET /admin/roles/{role_id} — Single Role Detail

**Read model** (inline in query handler file, `BaseModel`):
```python
class PermissionDetail(BaseModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None

class RoleDetail(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionDetail]
```

**Presentation response** (in `schemas.py`, `CamelModel`):
```python
class RoleDetailResponse(CamelModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionDetailResponse]

class PermissionDetailResponse(CamelModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None
```

**Error:** `NotFoundError(error_code="ROLE_NOT_FOUND")` (404)

**SQL:**
```python
_ROLE_SQL = text("SELECT id, name, description, is_system FROM roles WHERE id = :role_id")

_ROLE_PERMS_SQL = text(
    "SELECT p.id, p.codename, p.resource, p.action, p.description "
    "FROM permissions p "
    "JOIN role_permissions rp ON rp.permission_id = p.id "
    "WHERE rp.role_id = :role_id "
    "ORDER BY p.codename"
)
```

**Handler constructor:**
```python
class GetRoleDetailHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
```

---

### 2.6 PATCH /admin/roles/{role_id} — Update Role

**Request:**
```python
class UpdateRoleRequest(CamelModel):
    name: str | None = Field(None, min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateRoleRequest:
        if self.name is None and self.description is None:
            raise ValueError("At least one field (name or description) must be provided")
        return self
```

**Command:**
```python
@dataclass(frozen=True)
class UpdateRoleCommand:
    role_id: uuid.UUID
    name: str | None = None
    description: str | None = None
```

**Handler constructor:**
```python
class UpdateRoleHandler:
    def __init__(
        self,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
```

**Logic:**
1. `async with self._uow:`
2. Get role → `NotFoundError(error_code="ROLE_NOT_FOUND")` if None
3. If `command.name is not None` and role is system → `SystemRoleModificationError(role_name=role.name)` (existing exception)
4. If `command.name is not None`: check uniqueness via `role_repo.get_by_name(command.name)` → `ConflictError(error_code="ROLE_ALREADY_EXISTS")` if exists and is a different role
5. Apply updates to domain entity: `role.name = command.name` (if provided), `role.description = command.description` (if provided)
6. `await self._role_repo.update(role)` then `await self._uow.commit()`
7. Log `"role.updated"`

**Response:** `RoleDetailResponse` — fetch fresh data via the `GetRoleDetailHandler` query inline, or return from the updated domain entity. Prefer returning from domain entity to avoid extra query.

**Note on returning `RoleDetailResponse`:** Since the command handler returns `UpdateRoleResult(role_id)`, the router calls `GetRoleDetailHandler` to build the response. This follows the CQRS pattern where commands return minimal data and queries build read models.

---

### 2.7 PUT /admin/roles/{role_id}/permissions — Set Role Permissions

**Request:**
```python
class SetRolePermissionsRequest(CamelModel):
    permission_ids: list[uuid.UUID]
```

Full-replace semantics — DELETE all existing, INSERT new set.

**Command:**
```python
@dataclass(frozen=True)
class SetRolePermissionsCommand:
    role_id: uuid.UUID
    permission_ids: list[uuid.UUID]
    session_id: uuid.UUID  # admin's session for escalation check
```

**Handler constructor:**
```python
class SetRolePermissionsHandler:
    def __init__(
        self,
        role_repo: IRoleRepository,
        permission_repo: IPermissionRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
```

**Logic:**
1. `async with self._uow:`
2. Get role → `NotFoundError(error_code="ROLE_NOT_FOUND")` if None
3. Validate all permission IDs exist: `existing = await self._permission_repo.get_by_ids(command.permission_ids)` → if `len(existing) != len(command.permission_ids)`, compute missing IDs, raise `NotFoundError(error_code="PERMISSION_NOT_FOUND", details={"missing_ids": [...]})`
4. **Privilege escalation check:** `admin_perms = await self._permission_resolver.get_permissions(command.session_id)` → `requested_codenames = {p.codename for p in existing}` → `escalation = requested_codenames - admin_perms` → if escalation, raise `ForbiddenError(error_code="PRIVILEGE_ESCALATION", details={"escalated_permissions": sorted(escalation)})`
5. Delete existing: `DELETE FROM role_permissions WHERE role_id = :role_id`
6. Insert new set: `INSERT INTO role_permissions (role_id, permission_id) VALUES ...`
7. `await self._uow.commit()`
8. After `async with` block: invalidate cache for all identities with this role:
   - Query `identity_roles WHERE role_id = :role_id` to get affected identity_ids
   - For each identity: get active session IDs, invalidate each
9. Log `"role.permissions_set"`

**Response:** `RoleDetailResponse` (fetched via `GetRoleDetailHandler` in router)

**New repo methods needed on `IRoleRepository`:**
```python
@abstractmethod
async def set_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
    """Full-replace permissions for a role (DELETE + INSERT)."""
    pass

@abstractmethod
async def get_identity_ids_with_role(self, role_id: uuid.UUID) -> list[uuid.UUID]:
    """Get all identity IDs that have this role assigned."""
    pass
```

---

### 2.8 GET /admin/permissions — Grouped Permissions (enhanced)

**Current behavior:** Returns `list[PermissionInfo]` (flat).

**Enhanced behavior:** Returns `list[PermissionGroupResponse]` (grouped by resource).

**Read model** (inline in query handler file, modifying existing `list_permissions.py`):
```python
# Keep existing PermissionInfo as-is

class PermissionGroup(BaseModel):
    resource: str
    permissions: list[PermissionInfo]
```

**Presentation response** (in `schemas.py`, `CamelModel`):
```python
class PermissionGroupResponse(CamelModel):
    resource: str
    permissions: list[PermissionInfoResponse]

class PermissionInfoResponse(CamelModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None
```

**Handler change:** Modify existing `ListPermissionsHandler.handle()` to group by resource:
```python
async def handle(self) -> list[PermissionGroup]:
    result = await self._session.execute(_LIST_PERMISSIONS_SQL)
    rows = result.mappings().all()

    groups: dict[str, list[PermissionInfo]] = {}
    for row in rows:
        info = PermissionInfo(
            id=row["id"],
            codename=row["codename"],
            resource=row["resource"],
            action=row["action"],
            description=row["description"],
        )
        groups.setdefault(info.resource, []).append(info)

    return [
        PermissionGroup(resource=resource, permissions=perms)
        for resource, perms in sorted(groups.items())
    ]
```

**Router change:** Update return type from `list[PermissionInfo]` to `list[PermissionGroupResponse]`.

---

## 3. Domain Layer Changes

### 3.1 Identity Entity (`identity/domain/entities.py`)

**Modify `Identity` class:**

Add two new fields:
```python
@dataclass
class Identity(AggregateRoot):
    id: uuid.UUID
    type: IdentityType
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None       # NEW
    deactivated_by: uuid.UUID | None = None      # NEW
```

**Modify `deactivate()` method:**
```python
def deactivate(self, reason: str, deactivated_by: uuid.UUID | None = None) -> None:
    self.is_active = False
    self.deactivated_at = datetime.now(UTC)
    self.deactivated_by = deactivated_by
    self.updated_at = self.deactivated_at
    self.add_domain_event(
        IdentityDeactivatedEvent(
            identity_id=self.id,
            reason=reason,
            deactivated_by=deactivated_by,
            aggregate_id=str(self.id),
        )
    )
```

**Add `reactivate()` method:**
```python
def reactivate(self) -> None:
    """Reactivate a deactivated identity."""
    self.is_active = True
    self.deactivated_at = None
    self.deactivated_by = None
    self.updated_at = datetime.now(UTC)
    self.add_domain_event(
        IdentityReactivatedEvent(
            identity_id=self.id,
            aggregate_id=str(self.id),
        )
    )
```

### 3.2 Domain Events (`identity/domain/events.py`)

**Modify `IdentityDeactivatedEvent`** — add `deactivated_by` field:
```python
@dataclass
class IdentityDeactivatedEvent(DomainEvent):
    identity_id: uuid.UUID | None = None
    reason: str = ""
    deactivated_by: uuid.UUID | None = None      # NEW
    deactivated_at: datetime | None = None
    aggregate_type: str = "Identity"
    event_type: str = "IdentityDeactivatedEvent"
```

**Add `IdentityReactivatedEvent`:**
```python
@dataclass
class IdentityReactivatedEvent(DomainEvent):
    identity_id: uuid.UUID | None = None
    reactivated_at: datetime | None = None
    aggregate_type: str = "Identity"
    event_type: str = "IdentityReactivatedEvent"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if self.reactivated_at is None:
            self.reactivated_at = datetime.now(UTC)
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
```

### 3.3 Domain Exceptions (`identity/domain/exceptions.py`)

Add these new exceptions, following the exact pattern of existing exceptions:

```python
class IdentityAlreadyDeactivatedError(ConflictError):
    """Raised when attempting to deactivate an already-deactivated identity."""
    def __init__(self) -> None:
        super().__init__(
            message="Identity is already deactivated",
            error_code="IDENTITY_ALREADY_DEACTIVATED",
        )

class IdentityAlreadyActiveError(ConflictError):
    """Raised when attempting to reactivate an already-active identity."""
    def __init__(self) -> None:
        super().__init__(
            message="Identity is already active",
            error_code="IDENTITY_ALREADY_ACTIVE",
        )

class SelfDeactivationError(ForbiddenError):
    """Raised when an admin attempts to deactivate their own identity."""
    def __init__(self) -> None:
        super().__init__(
            message="Cannot deactivate your own identity",
            error_code="SELF_DEACTIVATION_FORBIDDEN",
        )

class LastAdminProtectionError(ForbiddenError):
    """Raised when attempting to deactivate/remove the last super_admin."""
    def __init__(self) -> None:
        super().__init__(
            message="Cannot remove the last super_admin",
            error_code="LAST_ADMIN_PROTECTION",
        )

class PrivilegeEscalationError(ForbiddenError):
    """Raised when an admin attempts to grant permissions they don't hold."""
    def __init__(self, escalated_permissions: list[str]) -> None:
        super().__init__(
            message="Cannot grant permissions you don't hold",
            error_code="PRIVILEGE_ESCALATION",
            details={"escalated_permissions": escalated_permissions},
        )
```

---

## 4. Interface Layer Changes

### 4.1 `IIdentityRepository` (`identity/domain/interfaces.py`)

Add one new method:
```python
@abstractmethod
async def update(self, identity: Identity) -> None:
    """Update an existing identity's mutable fields (is_active, deactivated_at, etc.)."""
    pass
```

### 4.2 `IRoleRepository` (`identity/domain/interfaces.py`)

Add these methods:
```python
@abstractmethod
async def update(self, role: Role) -> None:
    """Update an existing role's name and/or description."""
    pass

@abstractmethod
async def count_identities_with_role(self, role_name: str) -> int:
    """Count active identities that have a role with the given name."""
    pass

@abstractmethod
async def get_identity_ids_with_role(self, role_id: uuid.UUID) -> list[uuid.UUID]:
    """Get all identity IDs that have this role assigned."""
    pass

@abstractmethod
async def set_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
    """Full-replace permissions for a role (DELETE existing + INSERT new)."""
    pass
```

### 4.3 `IPermissionRepository` (`identity/domain/interfaces.py`)

Add one new method:
```python
@abstractmethod
async def get_by_ids(self, permission_ids: list[uuid.UUID]) -> list[Permission]:
    """Retrieve permissions by a list of IDs. Returns only those that exist."""
    pass
```

---

## 5. Infrastructure Layer Changes

### 5.1 ORM Model (`identity/infrastructure/models.py`)

**Modify `IdentityModel`** — add two columns:
```python
deactivated_at: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
    comment="When the identity was deactivated",
)
deactivated_by: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    nullable=True,
    comment="Identity ID of admin who deactivated this identity (null=self)",
)
```

### 5.2 Alembic Migration

New migration: `add_identity_deactivation_fields`

```python
def upgrade() -> None:
    op.add_column("identities", sa.Column(
        "deactivated_at", sa.TIMESTAMP(timezone=True), nullable=True,
    ))
    op.add_column("identities", sa.Column(
        "deactivated_by", sa.UUID(), nullable=True,
    ))

def downgrade() -> None:
    op.drop_column("identities", "deactivated_by")
    op.drop_column("identities", "deactivated_at")
```

### 5.3 Repository Implementations

**`IdentityRepository`** — add `update()` and modify `_identity_to_domain()`:
```python
def _identity_to_domain(self, orm: IdentityModel) -> Identity:
    return Identity(
        id=orm.id,
        type=IdentityType(orm.type),
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        deactivated_at=orm.deactivated_at,    # NEW
        deactivated_by=orm.deactivated_by,    # NEW
    )

async def update(self, identity: Identity) -> None:
    stmt = (
        update(IdentityModel)
        .where(IdentityModel.id == identity.id)
        .values(
            is_active=identity.is_active,
            deactivated_at=identity.deactivated_at,
            deactivated_by=identity.deactivated_by,
            updated_at=identity.updated_at,
        )
    )
    await self._session.execute(stmt)
```

**`RoleRepository`** — add 4 new methods:
```python
async def update(self, role: Role) -> None:
    stmt = (
        update(RoleModel)
        .where(RoleModel.id == role.id)
        .values(name=role.name, description=role.description)
    )
    await self._session.execute(stmt)

async def count_identities_with_role(self, role_name: str) -> int:
    stmt = (
        select(func.count())
        .select_from(IdentityRoleModel)
        .join(RoleModel, RoleModel.id == IdentityRoleModel.role_id)
        .join(IdentityModel, IdentityModel.id == IdentityRoleModel.identity_id)
        .where(RoleModel.name == role_name, IdentityModel.is_active.is_(True))
    )
    result = await self._session.execute(stmt)
    return result.scalar() or 0

async def get_identity_ids_with_role(self, role_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(IdentityRoleModel.identity_id).where(
        IdentityRoleModel.role_id == role_id
    )
    result = await self._session.execute(stmt)
    return [row[0] for row in result.all()]

async def set_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
    # Delete existing
    del_stmt = delete(RolePermissionModel).where(RolePermissionModel.role_id == role_id)
    await self._session.execute(del_stmt)
    # Insert new
    if permission_ids:
        values = [{"role_id": role_id, "permission_id": pid} for pid in permission_ids]
        ins_stmt = insert(RolePermissionModel).values(values)
        await self._session.execute(ins_stmt)
```

Note: `RoleRepository` will need additional import of `RolePermissionModel`, `IdentityModel`, and `func` from sqlalchemy.

**`PermissionRepository`** — add `get_by_ids()`:
```python
async def get_by_ids(self, permission_ids: list[uuid.UUID]) -> list[Permission]:
    if not permission_ids:
        return []
    stmt = select(PermissionModel).where(PermissionModel.id.in_(permission_ids))
    result = await self._session.execute(stmt)
    return [self._to_domain(orm) for orm in result.scalars().all()]
```

### 5.4 DI Provider (`identity/infrastructure/provider.py`)

Add registrations for all 7 new handlers:
```python
from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityHandler,
)
from src.modules.identity.application.commands.update_role import UpdateRoleHandler
from src.modules.identity.application.commands.set_role_permissions import (
    SetRolePermissionsHandler,
)
from src.modules.identity.application.queries.list_identities import (
    ListIdentitiesHandler,
)
from src.modules.identity.application.queries.get_identity_detail import (
    GetIdentityDetailHandler,
)
from src.modules.identity.application.queries.get_role_detail import (
    GetRoleDetailHandler,
)

# Add to IdentityProvider class:
admin_deactivate_handler: CompositeDependencySource = provide(
    AdminDeactivateIdentityHandler, scope=Scope.REQUEST
)
reactivate_handler: CompositeDependencySource = provide(
    ReactivateIdentityHandler, scope=Scope.REQUEST
)
update_role_handler: CompositeDependencySource = provide(
    UpdateRoleHandler, scope=Scope.REQUEST
)
set_role_permissions_handler: CompositeDependencySource = provide(
    SetRolePermissionsHandler, scope=Scope.REQUEST
)
list_identities_handler: CompositeDependencySource = provide(
    ListIdentitiesHandler, scope=Scope.REQUEST
)
get_identity_detail_handler: CompositeDependencySource = provide(
    GetIdentityDetailHandler, scope=Scope.REQUEST
)
get_role_detail_handler: CompositeDependencySource = provide(
    GetRoleDetailHandler, scope=Scope.REQUEST
)
```

---

## 6. Presentation Layer Changes

### 6.1 New Schemas (`identity/presentation/schemas.py`)

Add to existing file:

```python
# Admin Identity schemas
class AdminIdentityResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    roles: list[str]
    created_at: datetime

class AdminIdentityListResponse(CamelModel):
    items: list[AdminIdentityResponse]
    total: int
    offset: int
    limit: int

class RoleInfoResponse(CamelModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool

class AdminIdentityDetailResponse(CamelModel):
    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    roles: list[RoleInfoResponse]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None

# Admin Deactivation schemas
class AdminDeactivateRequest(CamelModel):
    reason: str = Field(..., min_length=1, max_length=200)

# Role Management schemas
class UpdateRoleRequest(CamelModel):
    name: str | None = Field(None, min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateRoleRequest:
        if self.name is None and self.description is None:
            raise ValueError("At least one field must be provided")
        return self

class SetRolePermissionsRequest(CamelModel):
    permission_ids: list[uuid.UUID]

class PermissionDetailResponse(CamelModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None

class RoleDetailResponse(CamelModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionDetailResponse]

class PermissionInfoResponse(CamelModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None

class PermissionGroupResponse(CamelModel):
    resource: str
    permissions: list[PermissionInfoResponse]
```

### 6.2 Router Updates (`identity/presentation/router_admin.py`)

Add 8 new endpoints to the existing `admin_router`. Follow the exact same patterns as existing endpoints:

```python
# New imports needed:
from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityCommand,
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityCommand,
    ReactivateIdentityHandler,
)
from src.modules.identity.application.commands.update_role import (
    UpdateRoleCommand,
    UpdateRoleHandler,
)
from src.modules.identity.application.commands.set_role_permissions import (
    SetRolePermissionsCommand,
    SetRolePermissionsHandler,
)
from src.modules.identity.application.queries.list_identities import (
    ListIdentitiesHandler,
    ListIdentitiesQuery,
)
from src.modules.identity.application.queries.get_identity_detail import (
    GetIdentityDetailHandler,
    GetIdentityDetailQuery,
)
from src.modules.identity.application.queries.get_role_detail import (
    GetRoleDetailHandler,
    GetRoleDetailQuery,
)
from src.modules.identity.presentation.schemas import (
    AdminDeactivateRequest,
    AdminIdentityDetailResponse,
    AdminIdentityListResponse,
    PermissionGroupResponse,
    RoleDetailResponse,
    SetRolePermissionsRequest,
    UpdateRoleRequest,
)

# New endpoints:

@admin_router.get(
    "/identities",
    response_model=AdminIdentityListResponse,
    summary="List all identities (paginated)",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def list_identities(
    handler: FromDishka[ListIdentitiesHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    role_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("created_at", pattern=r"^(created_at|email|last_name)$"),
    sort_order: str = Query("desc", pattern=r"^(asc|desc)$"),
) -> AdminIdentityListResponse:
    ...

@admin_router.get(
    "/identities/{identity_id}",
    response_model=AdminIdentityDetailResponse,
    summary="Get identity detail",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def get_identity_detail(
    identity_id: uuid.UUID,
    handler: FromDishka[GetIdentityDetailHandler],
) -> AdminIdentityDetailResponse:
    ...

@admin_router.post(
    "/identities/{identity_id}/deactivate",
    response_model=MessageResponse,
    summary="Admin deactivate identity",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def admin_deactivate_identity(
    identity_id: uuid.UUID,
    body: AdminDeactivateRequest,
    handler: FromDishka[AdminDeactivateIdentityHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    ...

@admin_router.post(
    "/identities/{identity_id}/reactivate",
    response_model=MessageResponse,
    summary="Admin reactivate identity",
    dependencies=[Depends(RequirePermission("identities:manage"))],
)
async def admin_reactivate_identity(
    identity_id: uuid.UUID,
    handler: FromDishka[ReactivateIdentityHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> MessageResponse:
    ...

@admin_router.get(
    "/roles/{role_id}",
    response_model=RoleDetailResponse,
    summary="Get role detail with permissions",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def get_role_detail(
    role_id: uuid.UUID,
    handler: FromDishka[GetRoleDetailHandler],
) -> RoleDetailResponse:
    ...

@admin_router.patch(
    "/roles/{role_id}",
    response_model=RoleDetailResponse,
    summary="Update role name/description",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def update_role(
    role_id: uuid.UUID,
    body: UpdateRoleRequest,
    handler: FromDishka[UpdateRoleHandler],
    detail_handler: FromDishka[GetRoleDetailHandler],
) -> RoleDetailResponse:
    ...

@admin_router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleDetailResponse,
    summary="Set role permissions (full replace)",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def set_role_permissions(
    role_id: uuid.UUID,
    body: SetRolePermissionsRequest,
    handler: FromDishka[SetRolePermissionsHandler],
    detail_handler: FromDishka[GetRoleDetailHandler],
    auth: AuthContext = Depends(get_auth_context),
) -> RoleDetailResponse:
    ...
```

**Modify existing `list_permissions` endpoint** to return grouped response:
```python
@admin_router.get(
    "/permissions",
    response_model=list[PermissionGroupResponse],  # CHANGED from list[PermissionInfo]
    summary="List all permissions (grouped by resource)",
    dependencies=[Depends(RequirePermission("roles:manage"))],
)
async def list_permissions(
    handler: FromDishka[ListPermissionsHandler],
) -> list[PermissionGroupResponse]:
    ...
```

---

## 7. New Files Summary

| Layer | File | Purpose |
|-------|------|---------|
| Application (Command) | `identity/application/commands/admin_deactivate_identity.py` | Admin deactivation with guards |
| Application (Command) | `identity/application/commands/reactivate_identity.py` | Reactivation |
| Application (Command) | `identity/application/commands/update_role.py` | Update role name/description |
| Application (Command) | `identity/application/commands/set_role_permissions.py` | Full-replace permissions |
| Application (Query) | `identity/application/queries/list_identities.py` | Paginated identity list |
| Application (Query) | `identity/application/queries/get_identity_detail.py` | Single identity detail |
| Application (Query) | `identity/application/queries/get_role_detail.py` | Single role detail |
| Infrastructure | `alembic/versions/XXXX_add_identity_deactivation_fields.py` | Migration for new columns |

**Modified files:**
| File | Changes |
|------|---------|
| `identity/domain/entities.py` | Add `deactivated_at`, `deactivated_by` fields; modify `deactivate()`; add `reactivate()` |
| `identity/domain/events.py` | Add `deactivated_by` to `IdentityDeactivatedEvent`; add `IdentityReactivatedEvent` |
| `identity/domain/exceptions.py` | Add 4 new exception classes |
| `identity/domain/interfaces.py` | Add methods to `IIdentityRepository`, `IRoleRepository`, `IPermissionRepository` |
| `identity/infrastructure/models.py` | Add 2 columns to `IdentityModel` |
| `identity/infrastructure/repositories/identity_repository.py` | Add `update()`, modify `_identity_to_domain()` |
| `identity/infrastructure/repositories/role_repository.py` | Add `update()`, `count_identities_with_role()`, `get_identity_ids_with_role()`, `set_permissions()` |
| `identity/infrastructure/repositories/permission_repository.py` | Add `get_by_ids()` |
| `identity/infrastructure/provider.py` | Register 7 new handlers |
| `identity/presentation/router_admin.py` | Add 7 new endpoints, modify 1 existing |
| `identity/presentation/schemas.py` | Add ~12 new schema classes |
| `identity/application/queries/list_permissions.py` | Change return type to grouped |

---

## 8. Security Guards

### 8.1 Privilege Escalation Prevention

Applied in `SetRolePermissionsHandler`:
- Get admin's effective permissions via `IPermissionResolver.get_permissions(session_id)` (returns `frozenset[str]`)
- Get requested permissions' codenames from the validated `Permission` entities
- Compute `escalation = requested_codenames - admin_permissions`
- If non-empty, raise `PrivilegeEscalationError(escalated_permissions=sorted(escalation))`

### 8.2 Self-Modification Guards

- `AdminDeactivateIdentityHandler`: reject if `command.identity_id == command.deactivated_by` → `SelfDeactivationError()`
- Last super_admin guard: `count = await role_repo.count_identities_with_role("super_admin")` — count only ACTIVE identities. If count <= 1 AND target identity has `super_admin` role, raise `LastAdminProtectionError()`.
- To check if target has super_admin: `role_ids = await role_repo.get_identity_role_ids(target_id)`, then check if any role with name `super_admin` is in the set. Alternatively, pass the target's role check into the handler via a query.

### 8.3 System Role Protection

- `UpdateRoleHandler`: system roles cannot have `name` changed. `description` IS editable for all roles.
- `SetRolePermissionsHandler`: system roles CAN have permissions changed (permissions evolve as features are added).
- `DeleteRoleHandler`: system roles cannot be deleted (existing behavior, already implemented).

---

## 9. Architecture Compliance

All new code follows the EXACT patterns found in the existing codebase:

| Pattern | Codebase Evidence |
|---------|-------------------|
| Domain entities use `from attr import dataclass` | `identity/domain/entities.py` line 13 |
| Domain events use stdlib `from dataclasses import dataclass` | `identity/domain/events.py` line 8 |
| Commands use stdlib `@dataclass(frozen=True)` | Every command handler file (e.g., `assign_role.py` line 20) |
| `AggregateRoot` import: `from src.shared.interfaces.entities import AggregateRoot` | `identity/domain/entities.py` line 23 |
| Query handlers take `session: AsyncSession` in constructor | `list_roles.py` line 47, `list_permissions.py` line 40 |
| Query read models use `pydantic.BaseModel` (NOT `CamelModel`) | `list_roles.py` line 14, `list_permissions.py` line 14 |
| SQL uses `text()` with `:param` named parameters | All query handlers |
| Command handlers inject interfaces + `IUnitOfWork` | All command handler files |
| Logger pattern: `self._logger = logger.bind(handler="ClassName")` | All command handlers |
| Logging after commit, outside `async with self._uow:` block | `deactivate_identity.py` lines 76-85 |
| Cache invalidation outside UoW transaction | `deactivate_identity.py` lines 77-78 |
| `self._uow.register_aggregate(entity)` before `await self._uow.commit()` | `assign_role.py` lines 108-109 |
| Presentation schemas use `CamelModel` from `src.shared.schemas` | `identity/presentation/schemas.py` |
| DI: `provide(HandlerClass, scope=Scope.REQUEST)` in `IdentityProvider` | `identity/infrastructure/provider.py` |
| Router: `admin_router = APIRouter(prefix="/admin", ...)` with `DishkaRoute` | `identity/presentation/router_admin.py` line 49 |
| Permission check: `dependencies=[Depends(RequirePermission("codename"))]` | All admin router endpoints |
| Error raising: `raise NotFoundError(message=..., error_code="...")` | `assign_role.py` lines 72-75 |
| Test helpers: `make_uow()`, `make_logger()`, `AsyncMock` repos | `tests/unit/.../test_commands.py` |

---

## 10. Test Plan

### 10.1 Unit Tests (new file: `tests/unit/modules/identity/application/commands/test_admin_commands.py`)

**`TestAdminDeactivateIdentityHandler`:**
- `test_admin_deactivate_success` — identity found, active, not self, not last admin → deactivated
- `test_admin_deactivate_identity_not_found` → `NotFoundError`
- `test_admin_deactivate_already_deactivated` → `ConflictError(IDENTITY_ALREADY_DEACTIVATED)`
- `test_admin_deactivate_self` → `SelfDeactivationError`
- `test_admin_deactivate_last_super_admin` → `LastAdminProtectionError`
- `test_admin_deactivate_revokes_sessions_and_invalidates_cache`
- `test_admin_deactivate_emits_event_with_deactivated_by`

**`TestReactivateIdentityHandler`:**
- `test_reactivate_success` — identity found, deactivated → reactivated
- `test_reactivate_identity_not_found` → `NotFoundError`
- `test_reactivate_already_active` → `ConflictError(IDENTITY_ALREADY_ACTIVE)`
- `test_reactivate_emits_event`

**`TestUpdateRoleHandler`:**
- `test_update_name_success`
- `test_update_description_success`
- `test_update_role_not_found` → `NotFoundError`
- `test_update_system_role_name` → `SystemRoleModificationError`
- `test_update_system_role_description_allowed`
- `test_update_duplicate_name` → `ConflictError(ROLE_ALREADY_EXISTS)`

**`TestSetRolePermissionsHandler`:**
- `test_set_permissions_success`
- `test_set_permissions_role_not_found` → `NotFoundError`
- `test_set_permissions_permission_not_found` → `NotFoundError(PERMISSION_NOT_FOUND)`
- `test_set_permissions_privilege_escalation` → `PrivilegeEscalationError`
- `test_set_permissions_invalidates_cache_for_affected_sessions`
- `test_set_permissions_empty_list_clears_all`

### 10.2 Unit Tests — Domain (add to `tests/unit/modules/identity/domain/test_entities.py`)

- `test_deactivate_sets_deactivated_by`
- `test_deactivate_sets_deactivated_at`
- `test_reactivate_clears_deactivated_fields`
- `test_reactivate_sets_active_true`
- `test_reactivate_emits_event`

### 10.3 Unit Tests — Schemas (add to `tests/unit/modules/identity/presentation/test_schemas.py`)

- `test_update_role_request_requires_at_least_one_field`
- `test_update_role_request_name_pattern_validation`
- `test_admin_deactivate_request_reason_required`
- `test_set_role_permissions_request_accepts_uuid_list`

### 10.4 Architecture Tests

Existing `test_boundaries.py` should pass without changes — new code follows the same module structure. Verify after implementation.

### 10.5 Integration Tests (future)

- Query handlers with real DB: `test_list_identities.py`, `test_get_identity_detail.py`, `test_get_role_detail.py`
- Repository methods: `test_role_repo_extended.py` (add tests for `set_permissions`, `count_identities_with_role`, `get_identity_ids_with_role`)
- Repository methods: `test_identity_repo_extended.py` (add test for `update`)
- Repository methods: `test_permission_repo.py` (add test for `get_by_ids`)
