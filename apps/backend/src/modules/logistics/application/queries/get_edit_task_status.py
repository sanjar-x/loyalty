"""
Query handler: poll the status of an asynchronous edit task.

Wraps Yandex's ``POST /request/edit/status`` (3.13).
"""

from dataclasses import dataclass

from src.modules.logistics.application.dto import GetEditTaskStatusResult
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import ProviderCode
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class GetEditTaskStatusQuery:
    """Input for an edit-task status lookup."""

    provider_code: ProviderCode
    task_id: str


class GetEditTaskStatusHandler:
    """Fetch the current status of an edit task from the provider."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="GetEditTaskStatusHandler")

    async def handle(self, query: GetEditTaskStatusQuery) -> GetEditTaskStatusResult:
        provider = self._registry.get_edit_provider(query.provider_code)
        status = await provider.get_edit_status(query.task_id)
        return GetEditTaskStatusResult(
            provider_code=query.provider_code,
            task_id=query.task_id,
            status=status,
        )
