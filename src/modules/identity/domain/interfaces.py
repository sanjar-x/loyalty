# src/modules/identity/domain/interfaces.py
import uuid
from abc import ABC, abstractmethod

from src.modules.identity.domain.entities import (
    Identity,
    LinkedAccount,
    LocalCredentials,
    Permission,
    Role,
    Session,
)


class IIdentityRepository(ABC):
    @abstractmethod
    async def add(self, identity: Identity) -> Identity:
        pass

    @abstractmethod
    async def get(self, identity_id: uuid.UUID) -> Identity | None:
        pass

    @abstractmethod
    async def get_by_email(
        self, email: str
    ) -> tuple[Identity, LocalCredentials] | None:
        """Get identity with local credentials by email. Returns None if not found."""
        pass

    @abstractmethod
    async def add_credentials(self, credentials: LocalCredentials) -> LocalCredentials:
        pass

    @abstractmethod
    async def update_credentials(self, credentials: LocalCredentials) -> None:
        """Update password hash (for Argon2id rehash on login)."""
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        pass


class ISessionRepository(ABC):
    @abstractmethod
    async def add(self, session: Session) -> Session:
        pass

    @abstractmethod
    async def get(self, session_id: uuid.UUID) -> Session | None:
        pass

    @abstractmethod
    async def get_by_refresh_token_hash(self, token_hash: str) -> Session | None:
        pass

    @abstractmethod
    async def update(self, session: Session) -> None:
        pass

    @abstractmethod
    async def revoke_all_for_identity(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Revoke all active sessions. Returns list of revoked session_ids (for cache invalidation)."""
        pass

    @abstractmethod
    async def count_active(self, identity_id: uuid.UUID) -> int:
        """Count non-revoked, non-expired sessions for identity."""
        pass

    @abstractmethod
    async def get_active_session_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Get IDs of all active sessions for identity (for cache invalidation)."""
        pass

    @abstractmethod
    async def add_session_roles(
        self, session_id: uuid.UUID, role_ids: list[uuid.UUID]
    ) -> None:
        """Insert session_roles rows (NIST session-role activation)."""
        pass

    @abstractmethod
    async def remove_session_role(
        self, session_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        """Remove a role from session_roles."""
        pass


class IRoleRepository(ABC):
    @abstractmethod
    async def add(self, role: Role) -> Role:
        pass

    @abstractmethod
    async def get(self, role_id: uuid.UUID) -> Role | None:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Role | None:
        pass

    @abstractmethod
    async def delete(self, role_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    async def get_all(self) -> list[Role]:
        pass

    @abstractmethod
    async def get_identity_role_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Get role IDs assigned to identity (from identity_roles)."""
        pass

    @abstractmethod
    async def assign_to_identity(
        self,
        identity_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
    ) -> None:
        """Insert identity_roles row."""
        pass

    @abstractmethod
    async def revoke_from_identity(
        self, identity_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        """Delete identity_roles row."""
        pass


class IPermissionRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[Permission]:
        pass

    @abstractmethod
    async def get_by_codename(self, codename: str) -> Permission | None:
        pass


class ILinkedAccountRepository(ABC):
    @abstractmethod
    async def add(self, account: LinkedAccount) -> LinkedAccount:
        pass

    @abstractmethod
    async def get_by_provider(
        self,
        provider: str,
        provider_sub_id: str,
    ) -> LinkedAccount | None:
        pass

    @abstractmethod
    async def get_all_for_identity(self, identity_id: uuid.UUID) -> list[LinkedAccount]:
        pass
