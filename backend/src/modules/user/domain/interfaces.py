"""Domain repository interfaces for customer and staff member profiles.

Defines the abstract repository contracts for the Customer and StaffMember
aggregates. Infrastructure implementations must fulfill these interfaces
without leaking persistence concerns into the domain layer.
"""

import uuid
from abc import ABC, abstractmethod

from src.modules.user.domain.entities import Customer, StaffMember


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
