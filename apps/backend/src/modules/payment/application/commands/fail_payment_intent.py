"""Command: explicitly fail a PaymentIntent (provider rejection)."""

import uuid
from dataclasses import dataclass

from src.modules.payment.domain.exceptions import PaymentIntentNotFoundError
from src.modules.payment.domain.interfaces import IPaymentIntentRepository
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class FailPaymentIntentCommand:
    intent_id: uuid.UUID
    reason: str


class FailPaymentIntentHandler:
    def __init__(
        self,
        repo: IPaymentIntentRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="FailPaymentIntentHandler")

    async def handle(self, command: FailPaymentIntentCommand) -> None:
        async with self._uow:
            intent = await self._repo.get_for_update(command.intent_id)
            if intent is None:
                raise PaymentIntentNotFoundError(intent_id=str(command.intent_id))
            if intent.is_terminal:
                return
            intent.fail(reason=command.reason)
            await self._repo.update(intent)
            self._uow.register_aggregate(intent)
            await self._uow.commit()
            self._logger.info(
                "payment.failed",
                intent_id=str(intent.id),
                reason=command.reason,
            )
