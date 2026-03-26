"""
Command handler: update an existing attribute template.

Applies partial updates (name_i18n, description_i18n, sort_order) to an
attribute template. Code is immutable after creation.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.events import AttributeTemplateUpdatedEvent
from src.modules.catalog.domain.exceptions import AttributeTemplateNotFoundError
from src.modules.catalog.domain.interfaces import IAttributeTemplateRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateAttributeTemplateCommand:
    """Input for updating an attribute template.

    Attributes:
        template_id: UUID of the attribute template to update.
        name_i18n: New multilingual name, or None to keep current.
        description_i18n: New multilingual description, or None to keep current.
        sort_order: New sort position, or None to keep current.
        _provided_fields: Set of field names explicitly provided by the caller.
    """

    template_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    sort_order: int | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateAttributeTemplateResult:
    """Output of attribute template update.

    Attributes:
        id: UUID of the updated template.
        code: Machine-readable template code (immutable).
        name_i18n: Updated multilingual name.
        description_i18n: Updated multilingual description.
        sort_order: Updated sort position.
    """

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    sort_order: int


class UpdateAttributeTemplateHandler:
    """Apply partial updates to an existing attribute template."""

    def __init__(
        self,
        template_repo: IAttributeTemplateRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._template_repo = template_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateAttributeTemplateHandler")

    async def handle(
        self, command: UpdateAttributeTemplateCommand
    ) -> UpdateAttributeTemplateResult:
        """Execute the update-attribute-template command.

        Args:
            command: Attribute template update parameters.

        Returns:
            Result containing the updated template state.

        Raises:
            AttributeTemplateNotFoundError: If the template does not exist.
        """
        async with self._uow:
            template = await self._template_repo.get(command.template_id)
            if template is None:
                raise AttributeTemplateNotFoundError(template_id=command.template_id)

            _SAFE_FIELDS = frozenset({"name_i18n", "description_i18n", "sort_order"})
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }
            template.update(**update_kwargs)

            template.add_domain_event(
                AttributeTemplateUpdatedEvent(
                    template_id=template.id,
                    aggregate_id=str(template.id),
                )
            )

            await self._template_repo.update(template)
            self._uow.register_aggregate(template)
            await self._uow.commit()

        self._logger.info("Attribute template updated", template_id=str(template.id))

        return UpdateAttributeTemplateResult(
            id=template.id,
            code=template.code,
            name_i18n=template.name_i18n,
            description_i18n=template.description_i18n,
            sort_order=template.sort_order,
        )
