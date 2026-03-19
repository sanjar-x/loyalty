"""Get user by identity ID query and handler.

Provides an internal CQRS query to check whether a User record exists
for a given Identity ID. Used by the backward-compatible
``get_current_user_id`` dependency.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class GetUserByIdentityQuery:
    """Query to look up a user ID by their identity ID.

    Attributes:
        identity_id: The Identity aggregate ID to search for.
    """

    identity_id: uuid.UUID


_GET_USER_ID_SQL = text("SELECT id FROM users WHERE id = :identity_id")


class GetUserByIdentityHandler:
    """Handler for looking up a user by their identity ID.

    This is an internal handler used by backward-compatible authentication
    dependencies to resolve a user ID from an identity ID.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the handler with a database session.

        Args:
            session: Async SQLAlchemy session for read queries.
        """
        self._session = session

    async def handle(self, query: GetUserByIdentityQuery) -> uuid.UUID | None:
        """Execute the lookup query.

        Args:
            query: The query containing the identity ID to search for.

        Returns:
            The user's UUID if a matching user exists, or None otherwise.
        """
        result = await self._session.execute(_GET_USER_ID_SQL, {"identity_id": query.identity_id})
        row = result.mappings().first()
        return row["id"] if row else None
