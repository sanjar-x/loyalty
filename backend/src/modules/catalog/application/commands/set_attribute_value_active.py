"""
Command handler: activate or deactivate an attribute value.

Toggles the ``is_active`` flag on a value. Deactivated values are hidden
from storefront filters but existing product assignments are preserved.
Invalidates storefront caches for all categories whose templates bind
the parent attribute.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_template_attributes import (
    invalidate_template_effective_cache,
)
from src.modules.catalog.domain.events import AttributeValueUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    AttributeValueNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    ITemplateAttributeBindingRepository,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class SetAttributeValueActiveCommand:
    """Input for toggling is_active on an attribute value."""

    attribute_id: uuid.UUID
    value_id: uuid.UUID
    is_active: bool


@dataclass(frozen=True)
class SetAttributeValueActiveResult:
    """Output after toggling is_active."""

    id: uuid.UUID
    is_active: bool


class SetAttributeValueActiveHandler:
    """Toggle the is_active flag on an attribute value and invalidate caches."""

    def __init__(
        self,
        attribute_repo: IAttributeRepository,
        value_repo: IAttributeValueRepository,
        binding_repo: ITemplateAttributeBindingRepository,
        template_repo: IAttributeTemplateRepository,
        cache: ICacheService,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._attribute_repo = attribute_repo
        self._value_repo = value_repo
        self._binding_repo = binding_repo
        self._template_repo = template_repo
        self._cache = cache
        self._uow = uow
        self._logger = logger.bind(handler="SetAttributeValueActiveHandler")

    async def handle(
        self, command: SetAttributeValueActiveCommand
    ) -> SetAttributeValueActiveResult:
        """Execute the set-active command.

        Raises:
            AttributeNotFoundError: If the parent attribute does not exist.
            AttributeValueNotFoundError: If the value does not exist.
        """
        async with self._uow:
            attribute = await self._attribute_repo.get(command.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=command.attribute_id)

            value = await self._value_repo.get(command.value_id)
            if value is None or value.attribute_id != command.attribute_id:
                raise AttributeValueNotFoundError(value_id=command.value_id)

            value.update(is_active=command.is_active)

            attribute.add_domain_event(
                AttributeValueUpdatedEvent(
                    attribute_id=attribute.id,
                    value_id=value.id,
                    aggregate_id=str(attribute.id),
                )
            )

            await self._value_repo.update(value)
            self._uow.register_aggregate(attribute)
            await self._uow.commit()

        # Invalidate storefront caches for all templates that bind this attribute.
        try:
            template_ids = await self._binding_repo.get_template_ids_for_attribute(
                command.attribute_id
            )
            for tid in template_ids:
                await invalidate_template_effective_cache(
                    self._cache, self._template_repo, tid
                )
        except Exception as exc:
            self._logger.warning("cache_invalidation_failed", error=str(exc))

        return SetAttributeValueActiveResult(
            id=value.id,
            is_active=value.is_active,
        )
