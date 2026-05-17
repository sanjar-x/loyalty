"""Query handler for listing staff members with pagination and filtering.

"Staff" is defined as either:

* ``identities.account_type = 'STAFF'`` (the canonical path — created via
  the invitation flow), OR
* an identity with at least one role whose ``target_account_type='STAFF'``
  (a data anomaly carried over from legacy seed scripts / direct
  ``identity_roles`` inserts; surfaced here so the admin panel can see
  and fix it instead of the row being silently invisible).

The handler reports two diagnostic booleans per row so the frontend can
flag rows that need attention:

* ``account_type_mismatch`` — true when a CUSTOMER identity carries a
  staff role.
* ``has_staff_member_profile`` — false when ``identities.account_type='STAFF'``
  exists but no ``staff_members`` row was provisioned (outbox lost the
  event, or a legacy admin was inserted by hand). The list still shows
  the row, with profile fields nulled out.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class StaffListItem(BaseModel):
    """Read model for a single staff member in the paginated list.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email from local_credentials (None for OIDC-only).
        first_name: Staff member's first name (None when no staff_members row).
        last_name: Staff member's last name (None when no staff_members row).
        position: Job position/title (None when no staff_members row).
        department: Department within the organization.
        roles: List of role names assigned to this identity.
        is_active: Whether the identity is currently active.
        created_at: When the identity was created.
        account_type_mismatch: True when a CUSTOMER identity carries a
            role marked as ``target_account_type='STAFF'`` — a data
            anomaly the admin panel should highlight.
        has_staff_member_profile: True when ``staff_members`` carries a
            row for this identity. False rows still appear (so the admin
            can see them) but their profile fields are nulled out.
    """

    identity_id: uuid.UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    position: str | None
    department: str | None
    roles: list[str]
    is_active: bool
    created_at: datetime
    account_type_mismatch: bool
    has_staff_member_profile: bool


class StaffListResult(BaseModel):
    """Read model for the paginated staff list response.

    Attributes:
        items: List of staff items for the current page.
        total: Total number of matching staff members.
        offset: Current offset.
        limit: Page size.
    """

    items: list[StaffListItem]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ListStaffQuery:
    """Query parameters for listing staff members.

    Attributes:
        offset: Pagination offset.
        limit: Page size.
        search: Optional ILIKE search term for email, first_name, last_name.
        role_id: Optional filter by role UUID.
        is_active: Optional filter by active status.
        sort_by: Column to sort by (created_at, email, last_name).
        sort_order: Sort direction (asc, desc).
    """

    offset: int = 0
    limit: int = 20
    search: str | None = None
    role_id: uuid.UUID | None = None
    is_active: bool | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


_SORT_COLUMNS = {
    "created_at": "i.created_at",
    "email": "lc.email",
    "last_name": "sm.last_name",
}

# Identity counts as "staff" if either signal is present. EXISTS rather
# than a JOIN keeps the subquery from multiplying rows when an identity
# holds more than one staff role.
_STAFF_SIGNAL_SQL = (
    "(i.account_type = 'STAFF' OR EXISTS ("
    " SELECT 1 FROM identity_roles ir_staff "
    " JOIN roles r_staff ON r_staff.id = ir_staff.role_id "
    " WHERE ir_staff.identity_id = i.id "
    " AND r_staff.target_account_type = 'STAFF'"
    "))"
)

_ROLE_NAMES_SQL = text(
    "SELECT ir.identity_id, r.name, r.target_account_type "
    "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
    "WHERE ir.identity_id = ANY(:identity_ids)"
)


class ListStaffHandler:
    """Handles listing staff members with pagination, filtering, and search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListStaffQuery) -> StaffListResult:
        """Execute the query and return a paginated staff list."""
        where_clauses: list[str] = [_STAFF_SIGNAL_SQL]
        params: dict[str, object] = {}

        if query.search is not None:
            where_clauses.append(
                "(lc.email ILIKE :search OR sm.first_name ILIKE :search "
                "OR sm.last_name ILIKE :search)"
            )
            params["search"] = f"%{query.search}%"

        if query.role_id is not None:
            where_clauses.append(
                "EXISTS (SELECT 1 FROM identity_roles ir "
                "WHERE ir.identity_id = i.id AND ir.role_id = :role_id)"
            )
            params["role_id"] = query.role_id

        if query.is_active is not None:
            where_clauses.append("i.is_active = :is_active")
            params["is_active"] = query.is_active

        where_sql = " WHERE " + " AND ".join(where_clauses)

        count_sql = (
            "SELECT COUNT(*) FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "LEFT JOIN staff_members sm ON sm.id = i.id" + where_sql
        )
        count_result = await self._session.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        if total == 0:
            return StaffListResult(
                items=[], total=0, offset=query.offset, limit=query.limit
            )

        sort_col = _SORT_COLUMNS.get(query.sort_by, "i.created_at")
        sort_dir = "ASC" if query.sort_order == "asc" else "DESC"
        list_sql = (
            "SELECT i.id AS identity_id, i.account_type, lc.email, i.is_active, "
            "sm.first_name, sm.last_name, sm.position, sm.department, "
            "i.created_at, (sm.id IS NOT NULL) AS has_staff_member_profile "
            "FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "LEFT JOIN staff_members sm ON sm.id = i.id"
            + where_sql
            + f" ORDER BY {sort_col} {sort_dir} LIMIT :limit OFFSET :offset"
        )
        params["limit"] = query.limit
        params["offset"] = query.offset

        list_result = await self._session.execute(text(list_sql), params)
        rows = list_result.mappings().all()

        if not rows:
            return StaffListResult(
                items=[], total=total, offset=query.offset, limit=query.limit
            )

        identity_ids = [row["identity_id"] for row in rows]
        role_result = await self._session.execute(
            _ROLE_NAMES_SQL, {"identity_ids": identity_ids}
        )
        role_rows = role_result.mappings().all()

        roles_by_identity: dict[uuid.UUID, list[str]] = {}
        has_staff_role: dict[uuid.UUID, bool] = {}
        for rr in role_rows:
            roles_by_identity.setdefault(rr["identity_id"], []).append(rr["name"])
            if rr["target_account_type"] == "STAFF":
                has_staff_role[rr["identity_id"]] = True

        items = [
            StaffListItem(
                identity_id=row["identity_id"],
                email=row["email"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                position=row["position"],
                department=row["department"],
                roles=roles_by_identity.get(row["identity_id"], []),
                is_active=row["is_active"],
                created_at=row["created_at"],
                account_type_mismatch=(
                    row["account_type"] != "STAFF"
                    and has_staff_role.get(row["identity_id"], False)
                ),
                has_staff_member_profile=row["has_staff_member_profile"],
            )
            for row in rows
        ]

        return StaffListResult(
            items=items, total=total, offset=query.offset, limit=query.limit
        )
