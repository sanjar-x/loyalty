"""Data Mapper for the Recipient aggregate (shipping-coordinate slice).

Post-Sprint-1.5 Part 2: customs PII mapped through the ``passport``
module's repository instead. Recipient round-trip is name + phone +
email + archive flag.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.recipient.domain.entities import Recipient
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.modules.recipient.domain.value_objects import Email, FullName, Phone
from src.modules.recipient.infrastructure.models import RecipientModel


class RecipientRepository(IRecipientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, recipient: Recipient) -> Recipient:
        row = _to_orm(recipient)
        self._session.add(row)
        await self._session.flush()
        return recipient

    async def get(self, recipient_id: uuid.UUID) -> Recipient | None:
        row = await self._session.get(RecipientModel, recipient_id)
        return _to_domain(row) if row else None

    async def get_for_update(self, recipient_id: uuid.UUID) -> Recipient | None:
        stmt = (
            select(RecipientModel)
            .where(RecipientModel.id == recipient_id)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, recipient: Recipient) -> Recipient:
        stmt = select(RecipientModel).where(RecipientModel.id == recipient.id)
        row = (await self._session.execute(stmt)).scalar_one()
        row.full_name_ru = recipient.full_name.ru
        row.full_name_lat = recipient.full_name.lat
        row.phone = recipient.phone.e164
        row.email = recipient.email.value
        row.is_archived = recipient.is_archived
        row.version = recipient.version + 1
        row.updated_at = recipient.updated_at
        await self._session.flush()
        return recipient

    async def list_by_identity(
        self,
        identity_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[Recipient]:
        stmt = (
            select(RecipientModel)
            .where(RecipientModel.identity_id == identity_id)
            .order_by(RecipientModel.created_at.desc())
        )
        if not include_archived:
            stmt = stmt.where(RecipientModel.is_archived.is_(False))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]


def _to_orm(recipient: Recipient) -> RecipientModel:
    return RecipientModel(
        id=recipient.id,
        identity_id=recipient.identity_id,
        full_name_ru=recipient.full_name.ru,
        full_name_lat=recipient.full_name.lat,
        phone=recipient.phone.e164,
        email=recipient.email.value,
        is_archived=recipient.is_archived,
        version=recipient.version,
        created_at=recipient.created_at,
        updated_at=recipient.updated_at,
    )


def _to_domain(row: RecipientModel) -> Recipient:
    return Recipient(
        id=row.id,
        identity_id=row.identity_id,
        full_name=FullName(ru=row.full_name_ru, lat=row.full_name_lat),
        phone=Phone(e164=row.phone),
        email=Email(value=row.email),
        is_archived=row.is_archived,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )
