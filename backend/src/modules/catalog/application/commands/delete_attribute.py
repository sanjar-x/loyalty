"""
Command handler: delete an attribute.

Verifies the attribute exists and is not bound to any families or products
before deletion. Emits ``AttributeDeletedEvent``.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import AttributeDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeHasFamilyBindingsError,
    AttributeInUseByProductsError,
    AttributeNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IFamilyAttributeBindingRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteAttributeCommand:
    """Input for deleting an attribute.

    Attributes:
        attribute_id: UUID of the attribute to delete.
    """

    attribute_id: uuid.UUID


class DeleteAttributeHandler:
    """Delete an existing attribute by ID."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        family_binding_repo: IFamilyAttributeBindingRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._attribute_repo = attribute_repo
        self._family_binding_repo = family_binding_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteAttributeHandler")

    async def handle(self, command: DeleteAttributeCommand) -> None:
        """Execute the delete-attribute command.

        Args:
            command: Attribute deletion parameters.

        Raises:
            AttributeNotFoundError: If the attribute does not exist.
            AttributeHasFamilyBindingsError: If the attribute is bound to families.
            AttributeInUseByProductsError: If products reference this attribute.
        """
        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            if await self._family_binding_repo.has_bindings_for_attribute(
                command.attribute_id
            ):
                raise AttributeHasFamilyBindingsError(
                    attribute_id=command.attribute_id
                )

            if await self._attribute_repo.has_product_attribute_values(
                command.attribute_id
            ):
                raise AttributeInUseByProductsError(attribute_id=command.attribute_id)

            attribute.add_domain_event(
                AttributeDeletedEvent(
                    attribute_id=attribute.id,
                    code=attribute.code,
                    aggregate_id=str(attribute.id),
                )
            )

            self._uow.register_aggregate(attribute)
            await self._attribute_repo.delete(command.attribute_id)
            await self._uow.commit()
