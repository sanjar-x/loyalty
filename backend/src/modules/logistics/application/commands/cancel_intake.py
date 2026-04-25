"""
Command handler: cancel a previously scheduled courier intake.
"""

from dataclasses import dataclass

from src.modules.logistics.application.dto import CancelIntakeResult
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import ProviderCode
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class CancelIntakeCommand:
    """Input for intake cancellation.

    Attributes:
        provider_code: Logistics provider that owns the intake.
        provider_intake_id: Provider's UUID of the intake to cancel.
    """

    provider_code: ProviderCode
    provider_intake_id: str


class CancelIntakeHandler:
    """Cancel a courier intake with the provider."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="CancelIntakeHandler")

    async def handle(self, command: CancelIntakeCommand) -> CancelIntakeResult:
        provider = self._registry.get_intake_provider(command.provider_code)
        success = await provider.cancel_intake(command.provider_intake_id)
        self._logger.info(
            "Intake cancellation",
            provider_code=command.provider_code,
            provider_intake_id=command.provider_intake_id,
            success=success,
        )
        return CancelIntakeResult(success=success)
