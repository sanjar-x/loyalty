"""ACL adapter: order → recipient.

The only file in the order module allowed to import the recipient
module's ORM — narrowly whitelisted in tests/architecture as
``("order","recipient")``. Reads the recipients table directly (CQRS
read-side) and projects into the order-side ``RecipientLookupResult``.

Ownership of the Recipient is enforced earlier on the cart side: a
checkout snapshot is only created with a recipient_id that belongs to
the cart's identity_id. By the time the Order module looks it up, the
trust boundary is already passed.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.domain.interfaces import (
    IRecipientLookup,
    RecipientLookupResult,
)
from src.modules.recipient.infrastructure.models import RecipientModel


class RecipientLookupAdapter(IRecipientLookup):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, recipient_id: uuid.UUID) -> RecipientLookupResult | None:
        stmt = select(RecipientModel).where(RecipientModel.id == recipient_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return RecipientLookupResult(
            recipient_id=row.id,
            identity_id=row.identity_id,
            full_name_ru=row.full_name_ru,
            full_name_lat=row.full_name_lat,
            phone=row.phone,
            email=row.email,
            is_archived=row.is_archived,
        )
