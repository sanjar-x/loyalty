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


class IUsernameUniquenessChecker(ABC):
    """Check username availability across customers and staff_members."""

    @abstractmethod
    async def is_available(
        self,
        username: str,
        exclude_identity_id: uuid.UUID | None = None,
    ) -> bool:
        """Return True if username is not taken (case-insensitive)."""


class ILinkedAccountReader(ABC):
    """Anti-corruption port to identity's ``linked_accounts`` table (USR-001).

    Customer auto-provisioning seeds first_name / last_name / username /
    photo_url from the most recent linked account's ``provider_metadata``
    (Telegram / OIDC). The data lives in the identity module's table —
    user-side code reads it through this port via
    :class:`src.modules.user.infrastructure.adapters.linked_account_reader.LinkedAccountReader`,
    which is whitelisted in ``ALLOWED_CROSS_MODULE`` as the only file
    in the user module allowed to import identity ORM models.

    Replaces a raw ``text("SELECT provider_metadata FROM linked_accounts ...")``
    in ``user/presentation/router_profile.py`` that was invisible to
    pytest-archon's cross-module rule.
    """

    @abstractmethod
    async def get_latest_provider_metadata(
        self, identity_id: uuid.UUID
    ) -> dict[str, object]:
        """Return ``provider_metadata`` of the most recent linked account.

        Returns an empty dict when the identity has no linked account
        yet — auto-provisioning falls back to empty profile fields in
        that case (the user can fill them in via PATCH later).
        """
