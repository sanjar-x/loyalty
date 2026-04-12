"""
Command handler: merge guest cart into authenticated cart.

Validates anonymous token, deterministic locking order (lower UUID first),
transfers items with qty summing, marks source as MERGED.
"""

import uuid
from dataclasses import dataclass

from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class MergeCartsCommand:
    """Input for merging a guest cart into an authenticated cart.

    Attributes:
        identity_id: Authenticated user ID (merge target).
        anonymous_token: Guest token (merge source).
    """

    identity_id: uuid.UUID
    anonymous_token: str


@dataclass(frozen=True)
class MergeCartsResult:
    """Output of cart merge.

    Attributes:
        target_cart_id: Cart that received the items.
        items_transferred: Number of items moved.
        skipped_sku_ids: SKUs skipped due to duplicates or limits.
    """

    target_cart_id: uuid.UUID
    items_transferred: int
    skipped_sku_ids: list[uuid.UUID]


class MergeCartsHandler:
    """Merge a guest cart into the authenticated user's cart."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._uow = uow
        self._logger = logger.bind(handler="MergeCartsHandler")

    async def handle(self, command: MergeCartsCommand) -> MergeCartsResult:
        async with self._uow:
            # Find both carts
            source = await self._cart_repo.get_active_by_anonymous(
                command.anonymous_token
            )
            if source is None:
                raise CartNotFoundError()

            target = await self._cart_repo.get_active_by_identity(command.identity_id)
            if target is None:
                # No auth cart exists — reassign the guest cart
                source.assign_owner(command.identity_id)
                await self._cart_repo.update(source)
                self._uow.register_aggregate(source)
                await self._uow.commit()
                return MergeCartsResult(
                    target_cart_id=source.id,
                    items_transferred=len(source.items),
                    skipped_sku_ids=[],
                )

            # Deterministic lock order (lower UUID first) to prevent deadlocks
            first_id, second_id = sorted([target.id, source.id])
            locked_first = await self._cart_repo.get_for_update(first_id)
            locked_second = await self._cart_repo.get_for_update(second_id)

            # Use locked versions to avoid stale state
            if target.id == first_id:
                target, source = locked_first, locked_second
            else:
                target, source = locked_second, locked_first

            transferred, skipped = target.merge_from(source)
            await self._cart_repo.update(target)
            await self._cart_repo.update(source)
            self._uow.register_aggregate(target)
            self._uow.register_aggregate(source)
            await self._uow.commit()

        return MergeCartsResult(
            target_cart_id=target.id,
            items_transferred=transferred,
            skipped_sku_ids=skipped,
        )
