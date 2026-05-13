"""Check whether a customer record exists for a given identity ID.

Provides an internal CQRS query used by authentication dependencies.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class GetCustomerByIdentityQuery:
    """Query to look up a customer ID by their identity ID.

    Attributes:
        identity_id: The Identity aggregate ID to search for.
    """

    identity_id: uuid.UUID


_GET_CUSTOMER_ID_SQL = text("SELECT id FROM customers WHERE id = :identity_id")


class GetCustomerByIdentityHandler:
    """Handler for looking up a customer by their identity ID.

    This is an internal handler used by authentication dependencies
    to resolve a customer ID from an identity ID.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetCustomerByIdentityQuery) -> uuid.UUID | None:
        """Execute the lookup query.

        Args:
            query: The query containing the identity ID to search for.

        Returns:
            The customer's UUID if a matching record exists, or None otherwise.
        """
        result = await self._session.execute(
            _GET_CUSTOMER_ID_SQL, {"identity_id": query.identity_id}
        )
        row = result.mappings().first()
        return row["id"] if row else None
