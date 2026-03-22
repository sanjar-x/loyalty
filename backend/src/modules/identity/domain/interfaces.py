"""Repository interfaces for the Identity module.

Defines abstract contracts for persistence of Identity, Session, Role,
Permission, and LinkedAccount aggregates/entities. Implementations live in the
infrastructure layer and are injected via Dishka DI.
"""

import uuid
from abc import ABC, abstractmethod

from src.modules.identity.domain.entities import (
    Identity,
    LinkedAccount,
    LocalCredentials,
    Permission,
    Role,
    Session,
    StaffInvitation,
)
from src.modules.identity.domain.value_objects import InvitationStatus, TelegramUserData


class IIdentityRepository(ABC):
    """Repository contract for Identity aggregate persistence."""

    @abstractmethod
    async def add(self, identity: Identity) -> Identity:
        """Persist a new identity.

        Args:
            identity: The identity to persist.

        Returns:
            The persisted identity (with any server-generated defaults applied).
        """
        pass

    @abstractmethod
    async def get(self, identity_id: uuid.UUID) -> Identity | None:
        """Retrieve an identity by its unique identifier.

        Args:
            identity_id: The identity's UUID.

        Returns:
            The identity if found, or None.
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> tuple[Identity, LocalCredentials] | None:
        """Retrieve an identity with its local credentials by email.

        Args:
            email: The login email address to look up.

        Returns:
            A tuple of (Identity, LocalCredentials) if found, or None.
        """
        pass

    @abstractmethod
    async def get_with_credentials(
        self,
        identity_id: uuid.UUID,
    ) -> tuple[Identity, LocalCredentials] | None:
        """Retrieve an identity with its local credentials by identity ID.

        Args:
            identity_id: The identity's UUID.

        Returns:
            A tuple of (Identity, LocalCredentials) if found, or None.
        """
        pass

    @abstractmethod
    async def add_credentials(self, credentials: LocalCredentials) -> LocalCredentials:
        """Persist new local credentials for an identity.

        Args:
            credentials: The credentials to persist.

        Returns:
            The persisted credentials.
        """
        pass

    @abstractmethod
    async def update_credentials(self, credentials: LocalCredentials) -> None:
        """Update the password hash for existing credentials.

        Used for transparent Argon2id rehash on login.

        Args:
            credentials: The credentials with the updated password hash.
        """
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Check whether an email address is already registered.

        Args:
            email: The email address to check.

        Returns:
            True if the email is already in use.
        """
        pass

    @abstractmethod
    async def update(self, identity: Identity) -> None:
        """Update an existing identity's mutable fields.

        Args:
            identity: The identity with updated fields.
        """
        pass


class ISessionRepository(ABC):
    """Repository contract for Session entity persistence."""

    @abstractmethod
    async def add(self, session: Session) -> Session:
        """Persist a new session.

        Args:
            session: The session to persist.

        Returns:
            The persisted session.
        """
        pass

    @abstractmethod
    async def get(self, session_id: uuid.UUID) -> Session | None:
        """Retrieve a session by its unique identifier.

        Args:
            session_id: The session's UUID.

        Returns:
            The session if found, or None.
        """
        pass

    @abstractmethod
    async def get_by_refresh_token_hash(self, token_hash: str) -> Session | None:
        """Retrieve a session by its refresh token SHA-256 hash.

        Args:
            token_hash: The SHA-256 hex digest of the refresh token.

        Returns:
            The session if found, or None.
        """
        pass

    @abstractmethod
    async def update(self, session: Session) -> None:
        """Update an existing session (e.g. after token rotation or revocation).

        Args:
            session: The session with updated fields.
        """
        pass

    @abstractmethod
    async def revoke_all_for_identity(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Revoke all active sessions for an identity.

        Args:
            identity_id: The identity whose sessions should be revoked.

        Returns:
            List of revoked session IDs (for cache invalidation).
        """
        pass

    @abstractmethod
    async def count_active(self, identity_id: uuid.UUID) -> int:
        """Count non-revoked, non-expired sessions for an identity.

        Args:
            identity_id: The identity to count sessions for.

        Returns:
            The number of active sessions.
        """
        pass

    @abstractmethod
    async def get_active_session_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Retrieve IDs of all active sessions for an identity.

        Used for cache invalidation when roles change.

        Args:
            identity_id: The identity to query.

        Returns:
            List of active session UUIDs.
        """
        pass

    @abstractmethod
    async def add_session_roles(self, session_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
        """Activate roles for a session (NIST session-role activation).

        Args:
            session_id: The session to add roles to.
            role_ids: The role IDs to activate.
        """
        pass

    @abstractmethod
    async def remove_session_role(self, session_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Remove a role from a session's activated roles.

        Args:
            session_id: The session to remove the role from.
            role_id: The role ID to deactivate.
        """
        pass

    @abstractmethod
    async def get_active_session_ids_bulk(
        self,
        identity_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        """Retrieve IDs of all active sessions for multiple identities in one query.

        Args:
            identity_ids: The identities to query.

        Returns:
            List of active session UUIDs across all given identities.
        """
        pass

    @abstractmethod
    async def revoke_oldest_active(self, identity_id: uuid.UUID) -> uuid.UUID | None:
        """Revoke oldest active session. Returns session_id for cache invalidation."""
        pass


class IRoleRepository(ABC):
    """Repository contract for Role entity persistence."""

    @abstractmethod
    async def add(self, role: Role) -> Role:
        """Persist a new role.

        Args:
            role: The role to persist.

        Returns:
            The persisted role.
        """
        pass

    @abstractmethod
    async def get(self, role_id: uuid.UUID) -> Role | None:
        """Retrieve a role by its unique identifier.

        Args:
            role_id: The role's UUID.

        Returns:
            The role if found, or None.
        """
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Role | None:
        """Retrieve a role by its unique name.

        Args:
            name: The role name to look up.

        Returns:
            The role if found, or None.
        """
        pass

    @abstractmethod
    async def delete(self, role_id: uuid.UUID) -> None:
        """Delete a role by its unique identifier.

        Args:
            role_id: The role's UUID.
        """
        pass

    @abstractmethod
    async def get_all(self) -> list[Role]:
        """Retrieve all roles ordered by name.

        Returns:
            List of all roles.
        """
        pass

    @abstractmethod
    async def get_identity_role_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Retrieve role IDs assigned to an identity.

        Args:
            identity_id: The identity to query.

        Returns:
            List of assigned role UUIDs.
        """
        pass

    @abstractmethod
    async def is_role_assigned(self, identity_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Check if a role is already assigned to an identity.

        Args:
            identity_id: The identity to check.
            role_id: The role to check.

        Returns:
            True if the role is already assigned.
        """
        pass

    @abstractmethod
    async def assign_to_identity(
        self,
        identity_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
    ) -> None:
        """Assign a role to an identity.

        Args:
            identity_id: The identity to assign the role to.
            role_id: The role to assign.
            assigned_by: The admin identity who performed the assignment, if any.
        """
        pass

    @abstractmethod
    async def revoke_from_identity(self, identity_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Revoke a role from an identity.

        Args:
            identity_id: The identity to revoke the role from.
            role_id: The role to revoke.
        """
        pass

    @abstractmethod
    async def update(self, role: Role) -> None:
        """Update an existing role's name and/or description.

        Args:
            role: The role with updated fields.
        """
        pass

    @abstractmethod
    async def count_identities_with_role(self, role_name: str) -> int:
        """Count active identities that have a role with the given name.

        Args:
            role_name: The name of the role to count assignments for.

        Returns:
            Number of active identities with this role.
        """
        pass

    @abstractmethod
    async def get_identity_ids_with_role(self, role_id: uuid.UUID) -> list[uuid.UUID]:
        """Get all identity IDs that have this role assigned.

        Args:
            role_id: The role ID to query assignments for.

        Returns:
            List of identity IDs with this role.
        """
        pass

    @abstractmethod
    async def set_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
        """Full-replace permissions for a role (DELETE existing + INSERT new).

        Args:
            role_id: The role to update permissions for.
            permission_ids: Complete set of permission IDs to assign.
        """
        pass


class IPermissionRepository(ABC):
    """Repository contract for Permission entity persistence."""

    @abstractmethod
    async def get_all(self) -> list[Permission]:
        """Retrieve all permissions ordered by codename.

        Returns:
            List of all permissions.
        """
        pass

    @abstractmethod
    async def get_by_codename(self, codename: str) -> Permission | None:
        """Retrieve a permission by its codename.

        Args:
            codename: The permission codename (e.g. "orders:read").

        Returns:
            The permission if found, or None.
        """
        pass

    @abstractmethod
    async def get_by_ids(self, permission_ids: list[uuid.UUID]) -> list[Permission]:
        """Retrieve permissions by a list of IDs.

        Args:
            permission_ids: List of permission IDs to retrieve.

        Returns:
            List of found permissions (may be shorter than input if some IDs don't exist).
        """
        pass


class ILinkedAccountRepository(ABC):
    """Repository contract for LinkedAccount entity persistence."""

    @abstractmethod
    async def add(self, account: LinkedAccount) -> LinkedAccount:
        """Persist a new linked external account.

        Args:
            account: The linked account to persist.

        Returns:
            The persisted linked account.
        """
        pass

    @abstractmethod
    async def get_by_provider(
        self,
        provider: str,
        provider_sub_id: str,
    ) -> tuple[Identity, LinkedAccount] | None:
        """Find a linked account by provider and subject identifier.

        Args:
            provider: The OIDC provider name (e.g. "google").
            provider_sub_id: The provider's unique subject ID.

        Returns:
            A tuple of (Identity, LinkedAccount) if found, or None.
        """
        pass

    @abstractmethod
    async def get_all_for_identity(self, identity_id: uuid.UUID) -> list[LinkedAccount]:
        """Retrieve all linked accounts for an identity.

        Args:
            identity_id: The identity to query.

        Returns:
            List of linked accounts.
        """
        pass

    @abstractmethod
    async def update(self, account: LinkedAccount) -> None: ...

    @abstractmethod
    async def get_by_identity_and_provider(
        self, identity_id: uuid.UUID, provider: str
    ) -> LinkedAccount | None: ...

    @abstractmethod
    async def find_by_verified_email(self, email: str) -> tuple[Identity, LinkedAccount] | None: ...

    @abstractmethod
    async def count_for_identity(self, identity_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def delete(self, account_id: uuid.UUID) -> None: ...


class ITelegramInitDataValidator(ABC):
    """Contract for Telegram initData validation and parsing."""

    @abstractmethod
    def validate_and_parse(self, init_data_raw: str) -> TelegramUserData: ...


class IStaffInvitationRepository(ABC):
    """Repository contract for StaffInvitation aggregate persistence."""

    @abstractmethod
    async def add(self, invitation: StaffInvitation) -> StaffInvitation:
        """Persist a new staff invitation."""

    @abstractmethod
    async def get(self, invitation_id: uuid.UUID) -> StaffInvitation | None:
        """Get invitation by ID."""

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> StaffInvitation | None:
        """Get invitation by SHA-256 token hash."""

    @abstractmethod
    async def get_pending_by_email(self, email: str) -> StaffInvitation | None:
        """Get active (PENDING) invitation for the given email."""

    @abstractmethod
    async def update(self, invitation: StaffInvitation) -> None:
        """Update an existing invitation."""

    @abstractmethod
    async def list_all(
        self,
        offset: int = 0,
        limit: int = 20,
        status: InvitationStatus | None = None,
    ) -> tuple[list[StaffInvitation], int]:
        """List invitations with optional status filter. Returns (items, total)."""
