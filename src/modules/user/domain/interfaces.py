"""User domain repository interfaces.

Defines the abstract repository contract for the User aggregate root.
Infrastructure implementations must fulfill this interface without leaking
persistence concerns into the domain layer.
"""

import uuid
from abc import ABC, abstractmethod

from src.modules.user.domain.entities import User


class IUserRepository(ABC):
    """Abstract repository for User aggregate persistence.

    Implementations must provide transactional consistency for all
    operations. The repository operates on domain entities, never on
    ORM models or DTOs.
    """

    @abstractmethod
    async def add(self, user: User) -> User:
        """Persist a new User aggregate.

        Args:
            user: The User domain entity to persist.

        Returns:
            The persisted User entity, potentially with server-generated
            defaults applied.
        """

    @abstractmethod
    async def get(self, user_id: uuid.UUID) -> User | None:
        """Retrieve a User by its unique identifier.

        Args:
            user_id: The UUID of the user to retrieve.

        Returns:
            The User domain entity if found, or None if no user exists
            with the given ID.
        """

    @abstractmethod
    async def update(self, user: User) -> None:
        """Persist changes to an existing User aggregate.

        Args:
            user: The User domain entity with updated field values.
        """
