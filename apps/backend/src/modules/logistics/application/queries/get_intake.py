"""
Query handler: fetch the current status of an intake from the provider.
"""

from dataclasses import dataclass

from src.modules.logistics.application.dto import GetIntakeResult
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import ProviderCode
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetIntakeQuery:
    """Input for intake-status lookup.

    Attributes:
        provider_code: Logistics provider that owns the intake.
        provider_intake_id: Provider's UUID of the intake.
    """

    provider_code: ProviderCode
    provider_intake_id: str


class GetIntakeHandler:
    """Fetch intake status from the provider."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="GetIntakeHandler")

    async def handle(self, query: GetIntakeQuery) -> GetIntakeResult:
        provider = self._registry.get_intake_provider(query.provider_code)
        status = await provider.get_intake(query.provider_intake_id)
        return GetIntakeResult(
            provider_intake_id=query.provider_intake_id,
            status=status,
        )
