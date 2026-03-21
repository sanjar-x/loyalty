"""SQLAlchemy implementation of the LinkedAccount repository.

Maps between LinkedAccountModel ORM objects and domain LinkedAccount
entities using the Data Mapper pattern.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity, LinkedAccount
from src.modules.identity.domain.interfaces import ILinkedAccountRepository
from src.modules.identity.domain.value_objects import AccountType, PrimaryAuthMethod
from src.modules.identity.infrastructure.models import IdentityModel, LinkedAccountModel


class LinkedAccountRepository(ILinkedAccountRepository):
    """Concrete repository for LinkedAccount persistence via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: LinkedAccountModel) -> LinkedAccount:
        """Map a LinkedAccountModel ORM instance to a domain entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return LinkedAccount(
            id=orm.id,
            identity_id=orm.identity_id,
            provider=orm.provider,
            provider_sub_id=orm.provider_sub_id,
            provider_email=orm.provider_email,
            email_verified=orm.email_verified,
            provider_metadata=orm.provider_metadata,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_identity_domain(self, orm: IdentityModel) -> Identity:
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

    async def add(self, account: LinkedAccount) -> LinkedAccount:
        """Persist a new linked account.

        Args:
            account: The domain linked account to persist.

        Returns:
            The persisted linked account.
        """
        orm = LinkedAccountModel(
            id=account.id,
            identity_id=account.identity_id,
            provider=account.provider,
            provider_sub_id=account.provider_sub_id,
            provider_email=account.provider_email,
            email_verified=account.email_verified,
            provider_metadata=account.provider_metadata,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get_by_provider(
        self,
        provider: str,
        provider_sub_id: str,
    ) -> tuple[Identity, LinkedAccount] | None:
        """Find a linked account by provider and subject identifier.

        Args:
            provider: The OIDC provider name.
            provider_sub_id: The provider's unique subject ID.

        Returns:
            A tuple of (Identity, LinkedAccount) if found, or None.
        """
        stmt = (
            select(LinkedAccountModel, IdentityModel)
            .join(IdentityModel, LinkedAccountModel.identity_id == IdentityModel.id)
            .where(
                LinkedAccountModel.provider == provider,
                LinkedAccountModel.provider_sub_id == provider_sub_id,
            )
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return self._to_identity_domain(row[1]), self._to_domain(row[0])

    async def get_all_for_identity(
        self,
        identity_id: uuid.UUID,
    ) -> list[LinkedAccount]:
        """Retrieve all linked accounts for an identity.

        Args:
            identity_id: The identity whose linked accounts to retrieve.

        Returns:
            List of linked accounts.
        """
        stmt = select(LinkedAccountModel).where(LinkedAccountModel.identity_id == identity_id)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, account: LinkedAccount) -> None:
        """Update mutable fields of a linked account.

        Args:
            account: The linked account with updated fields.
        """
        stmt = select(LinkedAccountModel).where(LinkedAccountModel.id == account.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        orm.provider_email = account.provider_email
        orm.email_verified = account.email_verified
        orm.provider_metadata = account.provider_metadata
        orm.updated_at = account.updated_at
        await self._session.flush()

    async def get_by_identity_and_provider(
        self,
        identity_id: uuid.UUID,
        provider: str,
    ) -> LinkedAccount | None:
        """Find a linked account by identity and provider name.

        Args:
            identity_id: The identity UUID.
            provider: The provider name (e.g. "telegram").

        Returns:
            The linked account if found, or None.
        """
        stmt = select(LinkedAccountModel).where(
            LinkedAccountModel.identity_id == identity_id,
            LinkedAccountModel.provider == provider,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_verified_email(
        self,
        email: str,
    ) -> tuple[Identity, LinkedAccount] | None:
        """Find a linked account with a verified email address.

        Args:
            email: The email address to search for.

        Returns:
            A tuple of (Identity, LinkedAccount) if found, or None.
        """
        stmt = (
            select(LinkedAccountModel, IdentityModel)
            .join(IdentityModel, LinkedAccountModel.identity_id == IdentityModel.id)
            .where(
                LinkedAccountModel.provider_email == email,
                LinkedAccountModel.email_verified == True,  # noqa: E712
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return self._to_identity_domain(row[1]), self._to_domain(row[0])

    async def count_for_identity(self, identity_id: uuid.UUID) -> int:
        """Count linked accounts for an identity.

        Args:
            identity_id: The identity to count linked accounts for.

        Returns:
            The number of linked accounts.
        """
        from sqlalchemy import func as sa_func

        stmt = (
            select(sa_func.count())
            .select_from(LinkedAccountModel)
            .where(LinkedAccountModel.identity_id == identity_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete(self, account_id: uuid.UUID) -> None:
        """Delete a linked account by ID.

        Args:
            account_id: The linked account's UUID.
        """
        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(LinkedAccountModel).where(LinkedAccountModel.id == account_id)
        await self._session.execute(stmt)
        await self._session.flush()
