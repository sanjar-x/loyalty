"""SQLAlchemy implementation of the Identity repository.

Maps between IdentityModel/LocalCredentialsModel ORM objects and their
corresponding domain entities using the Data Mapper pattern.
"""

import uuid

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.modules.identity.domain.entities import Identity, LocalCredentials
from src.modules.identity.domain.interfaces import IIdentityRepository
from src.modules.identity.domain.value_objects import AccountType, IdentityType
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    LocalCredentialsModel,
)


class IdentityRepository(IIdentityRepository):
    """Concrete repository for Identity aggregate persistence via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _identity_to_domain(self, orm: IdentityModel) -> Identity:
        """Map an IdentityModel ORM instance to a domain Identity entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return Identity(
            id=orm.id,
            type=IdentityType(orm.type),
            account_type=AccountType(getattr(orm, "account_type", "CUSTOMER")),
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deactivated_at=orm.deactivated_at,
            deactivated_by=orm.deactivated_by,
        )

    def _credentials_to_domain(self, orm: LocalCredentialsModel) -> LocalCredentials:
        """Map a LocalCredentialsModel ORM instance to a domain entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return LocalCredentials(
            identity_id=orm.identity_id,
            email=orm.email,
            password_hash=orm.password_hash,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, identity: Identity) -> Identity:
        """Persist a new identity.

        Args:
            identity: The domain identity to persist.

        Returns:
            The persisted identity with server-generated defaults applied.
        """
        orm = IdentityModel(
            id=identity.id,
            type=identity.type.value,
            account_type=identity.account_type.value,
            is_active=identity.is_active,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._identity_to_domain(orm)

    async def get(self, identity_id: uuid.UUID) -> Identity | None:
        """Retrieve an identity by its UUID.

        Args:
            identity_id: The identity's UUID.

        Returns:
            The identity if found, or None.
        """
        orm = await self._session.get(IdentityModel, identity_id)
        return self._identity_to_domain(orm) if orm else None

    async def get_by_email(
        self,
        email: str,
    ) -> tuple[Identity, LocalCredentials] | None:
        """Retrieve an identity with its local credentials by email.

        Args:
            email: The login email address.

        Returns:
            A tuple of (Identity, LocalCredentials) if found, or None.
        """
        stmt = (
            select(IdentityModel)
            .join(LocalCredentialsModel)
            .options(joinedload(IdentityModel.credentials))
            .where(LocalCredentialsModel.email == email)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        if orm is None or orm.credentials is None:
            return None
        return (
            self._identity_to_domain(orm),
            self._credentials_to_domain(orm.credentials),
        )

    async def add_credentials(self, credentials: LocalCredentials) -> LocalCredentials:
        """Persist new local credentials for an identity.

        Args:
            credentials: The domain credentials to persist.

        Returns:
            The persisted credentials.
        """
        orm = LocalCredentialsModel(
            identity_id=credentials.identity_id,
            email=credentials.email,
            password_hash=credentials.password_hash,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._credentials_to_domain(orm)

    async def update_credentials(self, credentials: LocalCredentials) -> None:
        """Update the password hash for existing credentials.

        Args:
            credentials: The credentials with the updated password hash.
        """
        stmt = (
            update(LocalCredentialsModel)
            .where(LocalCredentialsModel.identity_id == credentials.identity_id)
            .values(password_hash=credentials.password_hash)
        )
        await self._session.execute(stmt)

    async def email_exists(self, email: str) -> bool:
        """Check whether an email address is already registered.

        Args:
            email: The email address to check.

        Returns:
            True if the email is already in use.
        """
        stmt = select(exists().where(LocalCredentialsModel.email == email))
        result = await self._session.execute(stmt)
        return result.scalar() or False

    async def update(self, identity: Identity) -> None:
        """Update an existing identity's mutable fields."""
        stmt = (
            update(IdentityModel)
            .where(IdentityModel.id == identity.id)
            .values(
                is_active=identity.is_active,
                account_type=identity.account_type.value,
                deactivated_at=identity.deactivated_at,
                deactivated_by=identity.deactivated_by,
                updated_at=identity.updated_at,
            )
        )
        await self._session.execute(stmt)
