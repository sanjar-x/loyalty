"""
Command handler: delete an attribute template.

Validates the template exists and is not referenced by categories before
removing it. Emits ``AttributeTemplateDeletedEvent``.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import AttributeTemplateDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateHasCategoryReferencesError,
    AttributeTemplateNotFoundError,
)
from src.modules.catalog.domain.interfaces import IAttributeTemplateRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteAttributeTemplateCommand:
    """Input for deleting an attribute template.

    Attributes:
        template_id: UUID of the attribute template to delete.
    """

    template_id: uuid.UUID


class DeleteAttributeTemplateHandler:
    """Delete an attribute template with no category references.

    Attributes:
        _template_repo: AttributeTemplate repository port.
        _uow: Unit of Work for transactional writes.
        _logger: Structured logger with handler context.
    """

    def __init__(
        self,
        template_repo: IAttributeTemplateRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._template_repo = template_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteAttributeTemplateHandler")

    async def handle(self, command: DeleteAttributeTemplateCommand) -> None:
        """Execute the delete-attribute-template command.

        Args:
            command: Attribute template deletion parameters.

        Raises:
            AttributeTemplateNotFoundError: If the template does not exist.
            AttributeTemplateHasCategoryReferencesError: If categories reference this template.
        """
        async with self._uow:
            template = await self._template_repo.get(command.template_id)
            if template is None:
                raise AttributeTemplateNotFoundError(template_id=command.template_id)

            has_category_refs = await self._template_repo.has_category_references(
                command.template_id
            )
            if has_category_refs:
                raise AttributeTemplateHasCategoryReferencesError(
                    template_id=command.template_id
                )

            template.add_domain_event(
                AttributeTemplateDeletedEvent(
                    template_id=template.id,
                    code=template.code,
                    aggregate_id=str(template.id),
                )
            )
            self._uow.register_aggregate(template)
            await self._template_repo.delete(command.template_id)
            await self._uow.commit()

        self._logger.info(
            "Attribute template deleted", template_id=str(command.template_id)
        )
