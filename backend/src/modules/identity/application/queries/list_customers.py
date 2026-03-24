"""Query handler for listing customers with pagination and filtering.

Returns a paginated list of customer identities joined with customers data
and role names. Used by admin interfaces for customer management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CustomerListItem(BaseModel):
    """Read model for a single customer in the paginated list.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email from local_credentials (None for OIDC-only).
        first_name: Customer's first name.
        last_name: Customer's last name.
        phone: Customer's phone number, if available.
        referral_code: Customer's unique referral code.
        username: Customer's username, if available.
        auth_methods: List of auth methods (e.g. 'local', 'google', 'telegram').
        roles: List of role names assigned to this identity.
        is_active: Whether the identity is currently active.
        created_at: When the identity was created.
    """

    identity_id: uuid.UUID
    email: str | None
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str | None
    username: str | None = None
    auth_methods: list[str] = []
    roles: list[str]
    is_active: bool
    created_at: datetime


class CustomerListResult(BaseModel):
    """Read model for the paginated customer list response.

    Attributes:
        items: List of customer items for the current page.
        total: Total number of matching customers.
        offset: Current offset.
        limit: Page size.
    """

    items: list[CustomerListItem]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ListCustomersQuery:
    """Query parameters for listing customers.

    Attributes:
        offset: Pagination offset.
        limit: Page size.
        search: Optional ILIKE search term for email, first_name, last_name.
        is_active: Optional filter by active status.
        sort_by: Column to sort by (created_at, email, last_name).
        sort_order: Sort direction (asc, desc).
    """

    offset: int = 0
    limit: int = 20
    search: str | None = None
    is_active: bool | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


_SORT_COLUMNS = {
    "created_at": "i.created_at",
    "email": "lc.email",
    "last_name": "c.last_name",
}

_ROLE_NAMES_SQL = text(
    "SELECT ir.identity_id, r.name "
    "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
    "WHERE ir.identity_id = ANY(:identity_ids)"
)


class ListCustomersHandler:
    """Handles listing customers with pagination, filtering, and search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListCustomersQuery) -> CustomerListResult:
        """Execute the query and return a paginated customer list.

        Args:
            query: The list customers query parameters.

        Returns:
            Paginated list of customers with role names.
        """
        where_clauses: list[str] = ["i.account_type = 'CUSTOMER'"]
        params: dict[str, object] = {}

        if query.search is not None:
            where_clauses.append(
                "(lc.email ILIKE :search OR c.first_name ILIKE :search "
                "OR c.last_name ILIKE :search)"
            )
            params["search"] = f"%{query.search}%"

        if query.is_active is not None:
            where_clauses.append("i.is_active = :is_active")
            params["is_active"] = query.is_active

        where_sql = " WHERE " + " AND ".join(where_clauses)

        # Count total
        count_sql = (
            "SELECT COUNT(DISTINCT i.id) FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "JOIN customers c ON c.id = i.id" + where_sql
        )
        count_result = await self._session.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        if total == 0:
            return CustomerListResult(
                items=[], total=0, offset=query.offset, limit=query.limit
            )

        # Fetch page
        sort_col = _SORT_COLUMNS.get(query.sort_by, "i.created_at")
        sort_dir = "ASC" if query.sort_order == "asc" else "DESC"
        list_sql = (
            "SELECT i.id AS identity_id, lc.email, i.is_active, "
            "c.first_name, c.last_name, c.phone, c.referral_code, "
            "c.username, i.created_at "
            "FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "JOIN customers c ON c.id = i.id"
            + where_sql
            + f" ORDER BY {sort_col} {sort_dir} LIMIT :limit OFFSET :offset"
        )
        params["limit"] = query.limit
        params["offset"] = query.offset

        list_result = await self._session.execute(text(list_sql), params)
        rows = list_result.mappings().all()

        if not rows:
            return CustomerListResult(
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

        # Batch query: auth methods per customer
        la_stmt = text(
            "SELECT identity_id, provider FROM linked_accounts WHERE identity_id = ANY(:ids)"
        )
        la_result = await self._session.execute(la_stmt, {"ids": identity_ids})
        providers_by_identity: dict[uuid.UUID, list[str]] = {}
        for la_row in la_result.mappings():
            providers_by_identity.setdefault(la_row["identity_id"], []).append(
                la_row["provider"]
            )

        items = []
        for row in rows:
            auth_methods: list[str] = []
            if row["email"]:
                auth_methods.append("local")
            auth_methods.extend(providers_by_identity.get(row["identity_id"], []))

            items.append(
                CustomerListItem(
                    identity_id=row["identity_id"],
                    email=row["email"],
                    first_name=row["first_name"] or "",
                    last_name=row["last_name"] or "",
                    phone=row["phone"],
                    referral_code=row["referral_code"],
                    username=row["username"],
                    auth_methods=auth_methods,
                    roles=roles_by_identity.get(row["identity_id"], []),
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                )
            )

        return CustomerListResult(
            items=items, total=total, offset=query.offset, limit=query.limit
        )
