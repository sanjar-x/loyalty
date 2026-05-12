"""Query handler for listing staff members with pagination and filtering.

Returns a paginated list of staff identities joined with staff_members data
and role names. Used by admin interfaces for staff management.
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
        first_name: Staff member's first name.
        last_name: Staff member's last name.
        position: Job position/title.
        department: Department within the organization.
        roles: List of role names assigned to this identity.
        is_active: Whether the identity is currently active.
        created_at: When the identity was created.
    """

    identity_id: uuid.UUID
    email: str | None
    first_name: str
    last_name: str
    position: str | None
    department: str | None
    roles: list[str]
    is_active: bool
    created_at: datetime


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

_ROLE_NAMES_SQL = text(
    "SELECT ir.identity_id, r.name "
    "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
    "WHERE ir.identity_id = ANY(:identity_ids)"
)


class ListStaffHandler:
    """Handles listing staff members with pagination, filtering, and search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListStaffQuery) -> StaffListResult:
        """Execute the query and return a paginated staff list.

        Args:
            query: The list staff query parameters.

        Returns:
            Paginated list of staff members with role names.
        """
        where_clauses: list[str] = ["i.account_type = 'STAFF'"]
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

        # Count total
        count_sql = (
            "SELECT COUNT(DISTINCT i.id) FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "JOIN staff_members sm ON sm.id = i.id" + where_sql
        )
        count_result = await self._session.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        if total == 0:
            return StaffListResult(
                items=[], total=0, offset=query.offset, limit=query.limit
            )

        # Fetch page
        sort_col = _SORT_COLUMNS.get(query.sort_by, "i.created_at")
        sort_dir = "ASC" if query.sort_order == "asc" else "DESC"
        list_sql = (
            "SELECT i.id AS identity_id, lc.email, i.is_active, "
            "sm.first_name, sm.last_name, sm.position, sm.department, i.created_at "
            "FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "JOIN staff_members sm ON sm.id = i.id"
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

        # Fetch role names
        identity_ids = [row["identity_id"] for row in rows]
        role_result = await self._session.execute(
            _ROLE_NAMES_SQL, {"identity_ids": identity_ids}
        )
        role_rows = role_result.mappings().all()

        roles_by_identity: dict[uuid.UUID, list[str]] = {}
        for rr in role_rows:
            roles_by_identity.setdefault(rr["identity_id"], []).append(rr["name"])

        items = [
            StaffListItem(
                identity_id=row["identity_id"],
                email=row["email"],
                first_name=row["first_name"] or "",
                last_name=row["last_name"] or "",
                position=row["position"],
                department=row["department"],
                roles=roles_by_identity.get(row["identity_id"], []),
                is_active=row["is_active"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return StaffListResult(
            items=items, total=total, offset=query.offset, limit=query.limit
        )
