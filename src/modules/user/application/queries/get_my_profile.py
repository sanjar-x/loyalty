"""Get current user's profile query and handler.

Provides a read-only CQRS query that fetches the authenticated user's
profile data directly from the database, bypassing the domain layer
for optimal read performance.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.exceptions import UserNotFoundError


class UserProfile(BaseModel):
    """Read model representing a user's profile data.

    Attributes:
        id: The user's unique identifier.
        profile_email: Optional display email address.
        first_name: User's first name.
        last_name: User's last name.
        phone: Optional phone number.
    """

    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


@dataclass(frozen=True)
class GetMyProfileQuery:
    """Query to retrieve the current user's profile.

    Attributes:
        user_id: The UUID of the user whose profile to fetch.
    """

    user_id: uuid.UUID


_GET_PROFILE_SQL = text(
    "SELECT id, profile_email, first_name, last_name, phone FROM users WHERE id = :user_id"
)


class GetMyProfileHandler:
    """Handler for retrieving the current user's profile.

    Executes a raw SQL query for read-optimized access, returning
    a lightweight Pydantic read model instead of a full domain entity.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the handler with a database session.

        Args:
            session: Async SQLAlchemy session for read queries.
        """
        self._session = session

    async def handle(self, query: GetMyProfileQuery) -> UserProfile:
        """Execute the profile query and return the result.

        Args:
            query: The query containing the target user's ID.

        Returns:
            A UserProfile read model with the user's profile data.

        Raises:
            UserNotFoundError: If no user exists with the given ID.
        """
        result = await self._session.execute(_GET_PROFILE_SQL, {"user_id": query.user_id})
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
