"""Get current customer's profile query and handler.

Provides a read-only CQRS query that fetches the authenticated customer's
profile data directly from the database, bypassing the domain layer
for optimal read performance.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.exceptions import CustomerNotFoundError


class CustomerProfile(BaseModel):
    """Read model representing a customer's profile data.

    Attributes:
        id: The customer's unique identifier.
        profile_email: Optional display email address.
        first_name: Customer's first name.
        last_name: Customer's last name.
        phone: Optional phone number.
    """

    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


@dataclass(frozen=True)
class GetMyProfileQuery:
    """Query to retrieve the current customer's profile.

    Attributes:
        customer_id: The UUID of the customer whose profile to fetch.
    """

    customer_id: uuid.UUID


_GET_PROFILE_SQL = text(
    "SELECT id, profile_email, first_name, last_name, phone FROM customers WHERE id = :customer_id"
)


class GetMyProfileHandler:
    """Handler for retrieving the current customer's profile.

    Executes a raw SQL query for read-optimized access, returning
    a lightweight Pydantic read model instead of a full domain entity.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetMyProfileQuery) -> CustomerProfile:
        """Execute the profile query and return the result.

        Args:
            query: The query containing the target customer's ID.

        Returns:
            A CustomerProfile read model with the customer's profile data.

        Raises:
            CustomerNotFoundError: If no customer exists with the given ID.
        """
        result = await self._session.execute(
            _GET_PROFILE_SQL, {"customer_id": query.customer_id}
        )
        row = result.mappings().first()
        if row is None:
            raise CustomerNotFoundError(query.customer_id)

        return CustomerProfile(
            id=row["id"],
            profile_email=row["profile_email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
        )
