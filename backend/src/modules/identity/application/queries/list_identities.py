"""Query handler for listing identities with pagination, search, and filtering.

Returns a paginated list of identities joined with user data and role names.
Used by admin interfaces for user management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AdminIdentityListItem(BaseModel):
    """Read model for a single identity in the paginated list.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email from local_credentials (None for OIDC-only).
        auth_type: Authentication method (LOCAL or OIDC).
        is_active: Whether the identity is currently active.
        first_name: User's first name.
        last_name: User's last name.
        phone: User's phone number, if available.
        roles: List of role names assigned to this identity.
        created_at: When the identity was created.
    """

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str | None
    last_name: str | None
    phone: str | None
    roles: list[str]
    created_at: datetime


class AdminIdentityListResult(BaseModel):
    """Read model for the paginated identity list response.

    Attributes:
        items: List of identity items for the current page.
        total: Total number of matching identities.
        offset: Current offset.
        limit: Page size.
    """

    items: list[AdminIdentityListItem]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ListIdentitiesQuery:
    """Query parameters for listing identities.

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

_SORT_COLUMNS = {
    "created_at": "i.created_at",
    "email": "lc.email",
    "last_name": "u.last_name",
}

_IDENTITY_ROLE_NAMES_SQL = text(
    "SELECT ir.identity_id, r.name "
    "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
    "WHERE ir.identity_id = ANY(:identity_ids)"
)


class ListIdentitiesHandler:
    """Handles the list-identities query with pagination, filtering, and search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListIdentitiesQuery) -> AdminIdentityListResult:
        """Execute the query and return a paginated identity list.

        Args:
            query: The list identities query parameters.

        Returns:
            Paginated list of identities with role names.
        """
        where_clauses: list[str] = []
        params: dict[str, object] = {}

        if query.search is not None:
            where_clauses.append(
                "(lc.email ILIKE :search OR u.first_name ILIKE :search "
                "OR u.last_name ILIKE :search)"
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

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Count total
        count_sql = " ".join(_COUNT_SQL_PARTS) + where_sql
        count_result = await self._session.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        if total == 0:
            return AdminIdentityListResult(
                items=[], total=0, offset=query.offset, limit=query.limit
            )

        # Fetch page
        sort_col = _SORT_COLUMNS.get(query.sort_by, "i.created_at")
        sort_dir = "ASC" if query.sort_order == "asc" else "DESC"
        list_sql = (
            " ".join(_LIST_SQL_PARTS)
            + where_sql
            + f" ORDER BY {sort_col} {sort_dir}"
            + " LIMIT :limit OFFSET :offset"
        )
        params["limit"] = query.limit
        params["offset"] = query.offset

        list_result = await self._session.execute(text(list_sql), params)
        rows = list_result.mappings().all()

        if not rows:
            return AdminIdentityListResult(
                items=[], total=total, offset=query.offset, limit=query.limit
            )

        # Fetch role names
        identity_ids = [row["identity_id"] for row in rows]
        role_result = await self._session.execute(
            _IDENTITY_ROLE_NAMES_SQL, {"identity_ids": identity_ids}
        )
        role_rows = role_result.mappings().all()

        roles_by_identity: dict[uuid.UUID, list[str]] = {}
        for rr in role_rows:
            roles_by_identity.setdefault(rr["identity_id"], []).append(rr["name"])

        items = [
            AdminIdentityListItem(
                identity_id=row["identity_id"],
                email=row["email"],
                auth_type=row["auth_type"],
                is_active=row["is_active"],
                first_name=row["first_name"] or "",
                last_name=row["last_name"] or "",
                phone=row["phone"],
                roles=roles_by_identity.get(row["identity_id"], []),
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return AdminIdentityListResult(
            items=items, total=total, offset=query.offset, limit=query.limit
        )
