"""Read-side ACL adapter: identity → Telegram chat_id (T-2 / D3.1).

Whitelisted single touch-point into the identity bounded context for
the customer-notification consumer. Same anti-corruption pattern as
``cart→catalog`` ``CatalogSkuAdapter``: one file, one query, narrow
return type, no domain entity leakage across the boundary.

Why direct ORM read instead of a query handler:

* The consumer fans out a high-volume of point lookups (one per
  shipment-state change × every linked customer); a query-handler
  call goes through Dishka REQUEST scope on every invocation, which
  is overkill for a single ``SELECT provider_sub_id``.
* The shape returned (a single ``int``) is too thin to justify a
  dedicated read model — the adapter casts the ``provider_sub_id``
  string to ``int`` and returns it.

When linked-accounts schema changes (new column, alternate provider
discriminator) update *this* file alone — the rest of the order
module talks to ``ITelegramChatLookup`` only.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import LinkedAccountModel
from src.modules.order.application.ports import ITelegramChatLookup

logger = structlog.get_logger(__name__)

_TELEGRAM_PROVIDER = "telegram"


class TelegramChatLookup(ITelegramChatLookup):
    """SQL-backed implementation of :class:`ITelegramChatLookup`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_chat_id(self, identity_id: uuid.UUID) -> int | None:
        stmt = (
            select(LinkedAccountModel.provider_sub_id)
            .where(
                LinkedAccountModel.identity_id == identity_id,
                LinkedAccountModel.provider == _TELEGRAM_PROVIDER,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        provider_sub_id = result.scalar_one_or_none()
        if provider_sub_id is None:
            return None
        try:
            return int(provider_sub_id)
        except TypeError, ValueError:
            # Telegram provider_sub_id is the numeric chat_id stored as
            # ``str``. A non-numeric value indicates schema corruption
            # or a non-Telegram provider mistakenly using the same
            # discriminator — log loud, do NOT raise (consumer must
            # tolerate one bad row without crashing the whole batch).
            logger.error(
                "telegram_chat_lookup.bad_provider_sub_id",
                identity_id=str(identity_id),
                provider_sub_id=str(provider_sub_id),
            )
            return None
