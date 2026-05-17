"""
Command handler: change a product's lifecycle status.

Delegates FSM validation to ``Product.transition_status()`` in the domain
layer. The handler only orchestrates: fetch (with pessimistic lock),
transition, persist, commit. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    ProductNotReadyError,
)
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.shared.interfaces.cache import ICacheService
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
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._uow = uow
        self._cache = cache
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

            # SEC-09 — pre-publication readiness: a reviewer-ready or
            # published product must carry at least one media asset.
            # ``Product.transition_status`` enforces SKU pricing for the
            # same two states, but media live in a sibling aggregate
            # (loaded via ``IMediaAssetRepository``) so the check has to
            # sit at the application layer. The earlier version only
            # gated PUBLISHED, which let reviewers open the workflow on
            # a media-less product just to hit the wall at publish time.
            if command.new_status in (
                ProductStatus.READY_FOR_REVIEW,
                ProductStatus.PUBLISHED,
            ):
                media_assets = await self._media_repo.list_by_product(
                    command.product_id
                )
                if not media_assets:
                    raise ProductNotReadyError(
                        product_id=command.product_id,
                        reason=(
                            f"Cannot transition to {command.new_status.value} "
                            "without at least one media asset (image)"
                        ),
                    )

            product.transition_status(command.new_status)

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        # After-commit: invalidate the PDP cache keyed by product slug so
        # the storefront reflects the new lifecycle status immediately.
        # PLP caches have a 60s TTL and self-heal.
        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except Exception as exc:  # pragma: no cover — graceful cache-degrade
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))
