"""
Command handler: delete a brand.

Verifies the brand exists and removes it from the repository. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import BrandDeletedEvent
from src.modules.catalog.domain.exceptions import (
    BrandHasProductsError,
    BrandNotFoundError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteBrandCommand:
    """Input for deleting a brand.

    Attributes:
        brand_id: UUID of the brand to delete.
    """

    brand_id: uuid.UUID


class DeleteBrandHandler:
    """Delete an existing brand by ID."""

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteBrandHandler")

    async def handle(self, command: DeleteBrandCommand) -> None:
        """Execute the delete-brand command.

        Args:
            command: Brand deletion parameters.

        Raises:
            BrandNotFoundError: If the brand does not exist.
            BrandHasProductsError: If the brand still has associated products.
        """
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            has_products = await self._brand_repo.has_products(command.brand_id)
            if has_products:
                raise BrandHasProductsError(brand_id=command.brand_id)

            brand.add_domain_event(
                BrandDeletedEvent(
                    brand_id=brand.id,
                    aggregate_id=str(brand.id),
                )
            )
            self._uow.register_aggregate(brand)
            await self._brand_repo.delete(command.brand_id)
            await self._uow.commit()

        self._logger.info("Brand deleted", brand_id=str(command.brand_id))
