"""
Command handler: change a product's lifecycle status.

Delegates FSM validation to ``Product.transition_status()`` in the domain
layer. The handler only orchestrates: fetch (with pessimistic lock),
transition, persist, commit. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    ProductNotReadyError,
)
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ChangeProductStatusCommand:
    """Input for transitioning a product to a new lifecycle status.

    Attributes:
        product_id: UUID of the product whose status should change.
        new_status: The target ``ProductStatus`` value.
    """

    product_id: uuid.UUID
    new_status: ProductStatus


class ChangeProductStatusHandler:
    """Transition a product through its lifecycle FSM.

    Orchestrates: fetch (FOR UPDATE) -> transition_status -> persist -> commit.
    FSM rules (allowed transitions, ``published_at`` stamping) are
    enforced entirely by the domain entity. A ``ProductStatusChangedEvent``
    is emitted via the Unit of Work aggregate registration.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._uow = uow
        self._logger = logger.bind(handler="ChangeProductStatusHandler")

    async def handle(self, command: ChangeProductStatusCommand) -> None:
        """Execute the change-product-status command.

        Args:
            command: Status transition parameters.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            InvalidStatusTransitionError: If the transition violates FSM rules
                (raised by ``Product.transition_status``).
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # SEC-09: Pre-publication readiness check — ensure the product
            # has at least one media asset before allowing PUBLISHED status.
            if command.new_status == ProductStatus.PUBLISHED:
                media_assets = await self._media_repo.list_by_product(
                    command.product_id
                )
                if not media_assets:
                    raise ProductNotReadyError(
                        product_id=command.product_id,
                        reason="Cannot publish product without at least one media asset (image)",
                    )

            product.transition_status(command.new_status)

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()
