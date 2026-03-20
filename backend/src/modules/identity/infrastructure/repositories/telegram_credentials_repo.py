"""SQLAlchemy implementation of the TelegramCredentials repository.

Maps between TelegramCredentialsModel/IdentityModel ORM objects and their
corresponding domain entities using the Data Mapper pattern.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.modules.identity.domain.entities import Identity, TelegramCredentials
from src.modules.identity.domain.interfaces import ITelegramCredentialsRepository
from src.modules.identity.domain.value_objects import AccountType, IdentityType
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    TelegramCredentialsModel,
)


class TelegramCredentialsRepository(ITelegramCredentialsRepository):
    """Concrete repository for TelegramCredentials persistence via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_identity_domain(self, orm: IdentityModel) -> Identity:
        """Map an IdentityModel ORM instance to a domain Identity entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return Identity(
            id=orm.id,
            type=IdentityType(orm.type),
            account_type=AccountType(orm.account_type),
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deactivated_at=orm.deactivated_at,
            deactivated_by=orm.deactivated_by,
        )

    def _to_credentials_domain(self, orm: TelegramCredentialsModel) -> TelegramCredentials:
        """Map a TelegramCredentialsModel ORM instance to a domain entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return TelegramCredentials(
            identity_id=orm.identity_id,
            telegram_id=orm.telegram_id,
            first_name=orm.first_name,
            last_name=orm.last_name,
            username=orm.username,
            language_code=orm.language_code,
            is_premium=orm.is_premium,
            photo_url=orm.photo_url,
            allows_write_to_pm=orm.allows_write_to_pm,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, credentials: TelegramCredentials) -> TelegramCredentials:
        """Persist new Telegram credentials for an identity.

        Args:
            credentials: The domain credentials to persist.

        Returns:
            The persisted credentials.
        """
        orm = TelegramCredentialsModel(
            identity_id=credentials.identity_id,
            telegram_id=credentials.telegram_id,
            first_name=credentials.first_name,
            last_name=credentials.last_name,
            username=credentials.username,
            language_code=credentials.language_code,
            is_premium=credentials.is_premium,
            photo_url=credentials.photo_url,
            allows_write_to_pm=credentials.allows_write_to_pm,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_credentials_domain(orm)

    async def get_by_telegram_id(
        self,
        telegram_id: int,
    ) -> tuple[Identity, TelegramCredentials] | None:
        """Retrieve an identity with its Telegram credentials by Telegram user ID.

        Args:
            telegram_id: The Telegram user ID to look up.

        Returns:
            A tuple of (Identity, TelegramCredentials) if found, or None.
        """
        stmt = (
            select(IdentityModel)
            .join(TelegramCredentialsModel)
            .options(joinedload(IdentityModel.telegram_credentials))
            .where(TelegramCredentialsModel.telegram_id == telegram_id)
        )
        result = await self._session.execute(stmt)
        orm = result.unique().scalar_one_or_none()
        if orm is None or orm.telegram_credentials is None:
            return None
        return (
            self._to_identity_domain(orm),
            self._to_credentials_domain(orm.telegram_credentials),
        )

    async def update(self, credentials: TelegramCredentials) -> None:
        """Update Telegram credentials for an identity.

        Args:
            credentials: The credentials with updated fields.
        """
        stmt = (
            update(TelegramCredentialsModel)
            .where(TelegramCredentialsModel.identity_id == credentials.identity_id)
            .values(
                telegram_id=credentials.telegram_id,
                first_name=credentials.first_name,
                last_name=credentials.last_name,
                username=credentials.username,
                language_code=credentials.language_code,
                is_premium=credentials.is_premium,
                photo_url=credentials.photo_url,
                allows_write_to_pm=credentials.allows_write_to_pm,
                updated_at=credentials.updated_at,
            )
        )
        await self._session.execute(stmt)
