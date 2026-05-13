"""Delete a ``Variable`` (blocked while references exist)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    VariableInUseError,
    VariableNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    IProductPricingProfileRepository,
    IVariableRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteVariableCommand:
    """Input for ``DeleteVariableHandler``."""

    variable_id: uuid.UUID
    actor_id: uuid.UUID


class DeleteVariableHandler:
    """Hard-delete a variable after verifying no references remain.

    v1 reference sources checked:
        - ``ProductPricingProfile.values`` (scope=product_input)

    Future slices should extend this handler with checks against:
        - Formula AST ``{var: code}`` nodes
        - ``CategoryPricingSettings.values`` and ``ranges``
        - ``SupplierPricingSettings`` values
        - Global context values
    """

    def __init__(
        self,
        variable_repo: IVariableRepository,
        profile_repo: IProductPricingProfileRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._variable_repo = variable_repo
        self._profile_repo = profile_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteVariableHandler")

    async def handle(self, command: DeleteVariableCommand) -> None:
        async with self._uow:
            variable = await self._variable_repo.get_by_id(command.variable_id)
            if variable is None:
                raise VariableNotFoundError(variable_id=command.variable_id)

            reference_count = (
                await self._profile_repo.count_references_to_variable_code(
                    variable.code
                )
            )
            if reference_count > 0:
                raise VariableInUseError(
                    variable_id=variable.id,
                    code=variable.code,
                    reference_count=reference_count,
                    reference_kind="product_pricing_profile_values",
                )

            variable.mark_deleted(actor_id=command.actor_id)
            await self._variable_repo.delete(variable.id)
            self._uow.register_aggregate(variable)
            await self._uow.commit()

            self._logger.info(
                "pricing_variable_deleted",
                variable_id=str(variable.id),
                code=variable.code,
            )
