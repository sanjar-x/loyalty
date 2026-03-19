"""User domain repository interfaces.

Defines the abstract repository contracts for the User bounded context aggregates.
Infrastructure implementations must fulfill these interfaces without leaking
persistence concerns into the domain layer.
"""

import uuid
from abc import ABC, abstractmethod

from src.modules.user.domain.entities import Customer, StaffMember, User


class IUserRepository(ABC):
    """Abstract repository for User aggregate persistence.

    .. deprecated::
        Use :class:`ICustomerRepository` or :class:`IStaffMemberRepository` instead.

    Implementations must provide transactional consistency for all
    operations. The repository operates on domain entities, never on
    ORM models or DTOs.
    """

    # deprecated — use ICustomerRepository or IStaffMemberRepository instead

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


class ICustomerRepository(ABC):
    """Repository contract for Customer aggregate persistence.

    Implementations must provide transactional consistency for all
    operations. The repository operates on domain entities, never on
    ORM models or DTOs.
    """

    @abstractmethod
    async def add(self, customer: Customer) -> Customer:
        """Persist a new customer.

        Args:
            customer: The Customer domain entity to persist.

        Returns:
            The persisted Customer entity.
        """

    @abstractmethod
    async def get(self, customer_id: uuid.UUID) -> Customer | None:
        """Retrieve a customer by ID.

        Args:
            customer_id: The UUID of the customer to retrieve.

        Returns:
            The Customer domain entity if found, or None.
        """

    @abstractmethod
    async def update(self, customer: Customer) -> None:
        """Update an existing customer.

        Args:
            customer: The Customer domain entity with updated field values.
        """

    @abstractmethod
    async def get_by_referral_code(self, code: str) -> Customer | None:
        """Retrieve a customer by referral code.

        Args:
            code: The referral code to search for.

        Returns:
            The Customer domain entity if found, or None.
        """


class IStaffMemberRepository(ABC):
    """Repository contract for StaffMember aggregate persistence.

    Implementations must provide transactional consistency for all
    operations. The repository operates on domain entities, never on
    ORM models or DTOs.
    """

    @abstractmethod
    async def add(self, staff: StaffMember) -> StaffMember:
        """Persist a new staff member.

        Args:
            staff: The StaffMember domain entity to persist.

        Returns:
            The persisted StaffMember entity.
        """

    @abstractmethod
    async def get(self, staff_id: uuid.UUID) -> StaffMember | None:
        """Retrieve a staff member by ID.

        Args:
            staff_id: The UUID of the staff member to retrieve.

        Returns:
            The StaffMember domain entity if found, or None.
        """

    @abstractmethod
    async def update(self, staff: StaffMember) -> None:
        """Update an existing staff member.

        Args:
            staff: The StaffMember domain entity with updated field values.
        """
