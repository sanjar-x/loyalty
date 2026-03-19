"""SQLAlchemy implementation of the User repository.

Provides the concrete persistence logic for the User aggregate,
mapping between domain entities and ORM models using the Data Mapper
pattern.
"""

import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository
from src.modules.user.infrastructure.models import UserModel


class UserRepository(IUserRepository):
    """SQLAlchemy-based implementation of ``IUserRepository``.

    Uses the Data Mapper pattern to translate between ``User`` domain
    entities and ``UserModel`` ORM objects. All database operations
    participate in the session's transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: Async SQLAlchemy session for database operations.
        """
        self._session = session

    def _to_domain(self, orm: UserModel) -> User:
        """Map an ORM model to a domain entity.

        Args:
            orm: The SQLAlchemy ORM model instance.

        Returns:
            A User domain entity with values copied from the ORM model.
        """
        return User(
            id=orm.id,
            profile_email=orm.profile_email,
            first_name=orm.first_name,
            last_name=orm.last_name,
            phone=orm.phone,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, user: User) -> User:
        """Persist a new User aggregate to the database.

        Args:
            user: The User domain entity to persist.

        Returns:
            The persisted User entity with server-generated defaults applied.
        """
        orm = UserModel(
            id=user.id,
            profile_email=user.profile_email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, user_id: uuid.UUID) -> User | None:
        """Retrieve a User by ID from the database.

        Args:
            user_id: The UUID of the user to retrieve.

        Returns:
            The User domain entity if found, or None otherwise.
        """
        orm = await self._session.get(UserModel, user_id)
        return self._to_domain(orm) if orm else None

    async def update(self, user: User) -> None:
        """Persist updated User fields to the database.

        Uses an explicit UPDATE statement rather than session dirty-tracking
        to ensure only the intended fields are written.

        Args:
            user: The User domain entity with updated field values.
        """
        stmt = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                profile_email=user.profile_email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
            )
        )
        await self._session.execute(stmt)
