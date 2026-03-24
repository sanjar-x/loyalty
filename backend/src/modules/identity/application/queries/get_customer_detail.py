"""Query handler for getting a single customer's detail.

Returns the full detail of a customer including identity info,
customer-specific fields, and assigned roles with metadata.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import NotFoundError


class CustomerRoleInfo(BaseModel):
    """Read model for a role assigned to a customer.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional description of the role.
        is_system: Whether this is a system-managed role.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


class CustomerDetail(BaseModel):
    """Read model for a customer's full detail view.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email from local_credentials (None for OIDC-only).
        auth_type: Authentication method (LOCAL or OIDC).
        is_active: Whether the identity is currently active.
        first_name: Customer's first name.
        last_name: Customer's last name.
        phone: Customer's phone number, if available.
        referral_code: Customer's unique referral code.
        username: Customer's username, if available.
        auth_methods: List of auth methods (e.g. 'local', 'google', 'telegram').
        referred_by: UUID of the customer who referred this one.
        roles: List of roles with full metadata.
        created_at: When the identity was created.
        deactivated_at: When the identity was deactivated, if applicable.
        deactivated_by: UUID of the admin who deactivated this identity.
    """

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str | None
    username: str | None = None
    auth_methods: list[str] = []
    referred_by: uuid.UUID | None
    roles: list[CustomerRoleInfo]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None


@dataclass(frozen=True)
class GetCustomerDetailQuery:
    """Query parameters for getting a customer's detail.

    Attributes:
        identity_id: The identity UUID of the customer to fetch.
    """

    identity_id: uuid.UUID


class GetCustomerDetailHandler:
    """Handles fetching a single customer's full detail."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetCustomerDetailQuery) -> CustomerDetail:
        """Fetch the customer's detail by identity ID.

        Args:
            query: The get customer detail query with the identity ID.

        Returns:
            Full customer detail including roles.

        Raises:
            NotFoundError: If no customer with the given ID exists.
        """
        sql = text(
            "SELECT i.id AS identity_id, lc.email, i.type AS auth_type, "
            "i.is_active, c.first_name, c.last_name, c.phone, "
            "c.referral_code, c.username, c.referred_by, "
            "i.created_at, i.deactivated_at, i.deactivated_by "
            "FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "JOIN customers c ON c.id = i.id "
            "WHERE i.id = :identity_id AND i.account_type = 'CUSTOMER'"
        )
        result = await self._session.execute(sql, {"identity_id": query.identity_id})
        row = result.mappings().first()
        if row is None:
            raise NotFoundError(
                message="Customer not found",
                error_code="CUSTOMER_NOT_FOUND",
            )

        # Fetch roles with full metadata
        roles_sql = text(
            "SELECT r.id, r.name, r.description, r.is_system "
            "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
            "WHERE ir.identity_id = :identity_id"
        )
        roles_result = await self._session.execute(
            roles_sql, {"identity_id": query.identity_id}
        )
        roles = [
            CustomerRoleInfo(
                id=rr["id"],
                name=rr["name"],
                description=rr["description"],
                is_system=rr["is_system"],
            )
            for rr in roles_result.mappings().all()
        ]

        # Fetch linked account providers
        la_sql = text("SELECT provider FROM linked_accounts WHERE identity_id = :id")
        la_result = await self._session.execute(la_sql, {"id": query.identity_id})
        providers = [la_row["provider"] for la_row in la_result.mappings()]

        auth_methods: list[str] = []
        if row["email"]:
            auth_methods.append("local")
        auth_methods.extend(providers)

        return CustomerDetail(
            identity_id=row["identity_id"],
            email=row["email"],
            auth_type=row["auth_type"],
            is_active=row["is_active"],
            first_name=row["first_name"] or "",
            last_name=row["last_name"] or "",
            phone=row["phone"],
            referral_code=row["referral_code"],
            username=row["username"],
            auth_methods=auth_methods,
            referred_by=row["referred_by"],
            roles=roles,
            created_at=row["created_at"],
            deactivated_at=row["deactivated_at"],
            deactivated_by=row["deactivated_by"],
        )
