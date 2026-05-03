"""Cart → Recipient ACL adapter.

Read-only ownership check used by ``InitiateCheckoutHandler``. Reads
``recipients`` ORM directly to keep the cart layer thin; whitelisted
in tests/architecture as ``("cart","recipient")``.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.cart.domain.interfaces import ICartRecipientLookup
from src.modules.recipient.infrastructure.models import RecipientModel


class CartRecipientLookup(ICartRecipientLookup):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def belongs_to_identity(
        self, *, recipient_id: uuid.UUID, identity_id: uuid.UUID
    ) -> bool:
        stmt = (
            select(RecipientModel.id)
            .where(RecipientModel.id == recipient_id)
            .where(RecipientModel.identity_id == identity_id)
            .where(RecipientModel.is_archived.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
