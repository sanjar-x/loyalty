"""SQLAlchemy implementation of the Identity repository.

Maps between IdentityModel/LocalCredentialsModel ORM objects and their
corresponding domain entities using the Data Mapper pattern.
"""

import uuid

from sqlalchemy import exists, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.modules.identity.domain.entities import Identity, LocalCredentials
from src.modules.identity.domain.interfaces import IIdentityRepository
from src.modules.identity.domain.value_objects import AccountType, PrimaryAuthMethod
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
            type=PrimaryAuthMethod(orm.primary_auth_method),
            account_type=AccountType(orm.account_type),
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deactivated_at=orm.deactivated_at,
            deactivated_by=orm.deactivated_by,
            token_version=orm.token_version,
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
            primary_auth_method=identity.type.value,
            account_type=identity.account_type.value,
            is_active=identity.is_active,
            token_version=identity.token_version,
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

    async def get_by_login(
        self,
        login: str,
    ) -> tuple[Identity, LocalCredentials] | None:
        """Retrieve an identity by email or username.

        If login contains '@', look up by email. Otherwise look up by
        username across customers and staff_members via raw SQL JOIN.
        """
        if "@" in login:
            return await self.get_by_email(login)

        stmt = text("""
            SELECT i.id, i.primary_auth_method, i.account_type, i.is_active,
                   i.created_at, i.updated_at, i.deactivated_at, i.deactivated_by,
                   i.token_version,
                   lc.identity_id AS lc_identity_id, lc.email, lc.password_hash,
                   lc.created_at AS lc_created_at, lc.updated_at AS lc_updated_at
            FROM identities i
            JOIN local_credentials lc ON lc.identity_id = i.id
            LEFT JOIN customers c ON c.id = i.id
            LEFT JOIN staff_members s ON s.id = i.id
            WHERE LOWER(c.username) = LOWER(:login)
               OR LOWER(s.username) = LOWER(:login)
            LIMIT 1
        """)
        result = await self._session.execute(stmt, {"login": login})
        row = result.mappings().first()
        if row is None:
            return None

        identity = Identity(
            id=row["id"],
            type=PrimaryAuthMethod(row["primary_auth_method"]),
            account_type=AccountType(row["account_type"]),
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deactivated_at=row["deactivated_at"],
            deactivated_by=row["deactivated_by"],
            token_version=row["token_version"],
        )
        credentials = LocalCredentials(
            identity_id=row["lc_identity_id"],
            email=row["email"],
            password_hash=row["password_hash"],
            created_at=row["lc_created_at"],
            updated_at=row["lc_updated_at"],
        )
        return identity, credentials

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
        stmt = (
            select(IdentityModel)
            .options(joinedload(IdentityModel.credentials))
            .where(IdentityModel.id == identity_id)
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
                token_version=identity.token_version,
            )
        )
        await self._session.execute(stmt)
