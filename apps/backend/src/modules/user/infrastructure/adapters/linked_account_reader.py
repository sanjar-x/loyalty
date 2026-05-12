"""Anti-corruption adapter for identity's ``linked_accounts`` table (USR-001).

Implements :class:`src.modules.user.domain.interfaces.ILinkedAccountReader`
by reading the identity module's ORM model directly. This is the ONE
file in the user module allowed to import ``identity.infrastructure.*``
— the cross-module access is whitelisted in
``tests/architecture/test_boundaries.py:ALLOWED_CROSS_MODULE`` exactly
analogous to the cart→catalog ``CatalogSkuAdapter`` pattern.

Replaces a raw ``text("SELECT provider_metadata FROM linked_accounts
...")`` block in ``user/presentation/router_profile.py`` that was
invisible to the architecture fitness rule and broke the layered
architecture loop.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import LinkedAccountModel
from src.modules.user.domain.interfaces import ILinkedAccountReader


class LinkedAccountReader(ILinkedAccountReader):
    """Reads ``provider_metadata`` from the identity-owned ORM model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_provider_metadata(
        self, identity_id: uuid.UUID
    ) -> dict[str, object]:
        stmt = (
            select(LinkedAccountModel.provider_metadata)
            .where(LinkedAccountModel.identity_id == identity_id)
            .order_by(LinkedAccountModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        metadata = result.scalar_one_or_none()
        if metadata is None:
            return {}
        return dict(metadata)
