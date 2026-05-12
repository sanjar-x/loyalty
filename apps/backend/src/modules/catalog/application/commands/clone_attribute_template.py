"""
Command handler: clone an existing attribute template (template).

Duplicates a template with all its attribute bindings under a new code
and name, emitting an ``AttributeTemplateCreatedEvent`` for the clone.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import (
    AttributeTemplate,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.events import AttributeTemplateCreatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateCodeAlreadyExistsError,
    AttributeTemplateNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeTemplateRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import validate_i18n_completeness
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CloneAttributeTemplateCommand:
    """Input for cloning an attribute template.

    Attributes:
        source_template_id: UUID of the template to clone.
        new_code: Unique machine-readable code for the clone.
        new_name_i18n: Multilingual display name for the clone.
        new_description_i18n: Optional multilingual description for the clone.
    """

    source_template_id: uuid.UUID
    new_code: str
    new_name_i18n: dict[str, str]
    new_description_i18n: dict[str, str] | None = None


@dataclass(frozen=True)
class CloneAttributeTemplateResult:
    """Output of attribute template cloning.

    Attributes:
        id: UUID of the newly created template.
        bindings_copied: Number of attribute bindings copied from the source.
    """

    id: uuid.UUID
    bindings_copied: int


class CloneAttributeTemplateHandler:
    """Clone an existing attribute template with all its bindings."""

    def __init__(
        self,
        template_repo: IAttributeTemplateRepository,
        binding_repo: ITemplateAttributeBindingRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._template_repo = template_repo
        self._binding_repo = binding_repo
        self._uow = uow
        self._logger = logger.bind(handler="CloneAttributeTemplateHandler")

    async def handle(
        self, command: CloneAttributeTemplateCommand
    ) -> CloneAttributeTemplateResult:
        """Execute the clone-attribute-template command.

        Args:
            command: Clone parameters including source ID and new identifiers.

        Returns:
            Result containing the new template's ID and count of copied bindings.

        Raises:
            AttributeTemplateNotFoundError: If the source template does not exist.
            AttributeTemplateCodeAlreadyExistsError: If the new code is already taken.
        """
        validate_i18n_completeness(command.new_name_i18n, "new_name_i18n")

        async with self._uow:
            # 1. Load source template
            source = await self._template_repo.get(command.source_template_id)
            if source is None:
                raise AttributeTemplateNotFoundError(
                    template_id=command.source_template_id
                )

            # 2. Check new code uniqueness
            if await self._template_repo.check_code_exists(command.new_code):
                raise AttributeTemplateCodeAlreadyExistsError(code=command.new_code)

            # 3. Create new template
            new_template = AttributeTemplate.create(
                code=command.new_code,
                name_i18n=command.new_name_i18n,
                description_i18n=command.new_description_i18n,
                sort_order=source.sort_order,
            )

            # 4. Load all bindings for source template
            bindings_map = await self._binding_repo.get_bindings_for_templates(
                [command.source_template_id]
            )
            source_bindings = bindings_map.get(command.source_template_id, [])

            # 5. Create new bindings for the cloned template
            for binding in source_bindings:
                new_binding = TemplateAttributeBinding.create(
                    template_id=new_template.id,
                    attribute_id=binding.attribute_id,
                    sort_order=binding.sort_order,
                    requirement_level=binding.requirement_level,
                    filter_settings=binding.filter_settings,
                )
                await self._binding_repo.add(new_binding)

            # 6. Emit event and persist
            new_template.add_domain_event(
                AttributeTemplateCreatedEvent(
                    template_id=new_template.id,
                    code=new_template.code,
                    aggregate_id=str(new_template.id),
                )
            )

            new_template = await self._template_repo.add(new_template)
            self._uow.register_aggregate(new_template)
            await self._uow.commit()

        return CloneAttributeTemplateResult(
            id=new_template.id,
            bindings_copied=len(source_bindings),
        )
