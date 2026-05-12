"""
Command handler: create a new attribute template.

Validates code uniqueness, creates the template, and emits
an ``AttributeTemplateCreatedEvent``. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import AttributeTemplate
from src.modules.catalog.domain.events import AttributeTemplateCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateCodeAlreadyExistsError,
)
from src.modules.catalog.domain.interfaces import IAttributeTemplateRepository
from src.modules.catalog.domain.value_objects import validate_i18n_completeness
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateAttributeTemplateCommand:
    """Input for creating a new attribute template.

    Attributes:
        code: Machine-readable unique code (e.g. "electronics", "clothing").
        name_i18n: Multilingual display name. Must have at least one entry.
        description_i18n: Optional multilingual description.
        sort_order: Display ordering.
    """

    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class CreateAttributeTemplateResult:
    """Output of attribute template creation.

    Attributes:
        id: UUID of the newly created attribute template.
    """

    id: uuid.UUID


class CreateAttributeTemplateHandler:
    """Create a new attribute template with code uniqueness validation."""

    def __init__(
        self,
        template_repo: IAttributeTemplateRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._template_repo = template_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateAttributeTemplateHandler")

    async def handle(
        self, command: CreateAttributeTemplateCommand
    ) -> CreateAttributeTemplateResult:
        """Execute the create-attribute-template command.

        Args:
            command: Attribute template creation parameters.

        Returns:
            Result containing the new template's ID.

        Raises:
            AttributeTemplateCodeAlreadyExistsError: If the code is already taken.
        """
        validate_i18n_completeness(command.name_i18n, "name_i18n")

        async with self._uow:
            if await self._template_repo.check_code_exists(command.code):
                raise AttributeTemplateCodeAlreadyExistsError(code=command.code)

            template = AttributeTemplate.create(
                code=command.code,
                name_i18n=command.name_i18n,
                description_i18n=command.description_i18n,
                sort_order=command.sort_order,
            )

            template.add_domain_event(
                AttributeTemplateCreatedEvent(
                    template_id=template.id,
                    code=template.code,
                    aggregate_id=str(template.id),
                )
            )

            template = await self._template_repo.add(template)
            self._uow.register_aggregate(template)
            await self._uow.commit()

        return CreateAttributeTemplateResult(id=template.id)
