"""Command: capture an authorized PaymentIntent.

Used both by the real-provider webhook handler and by the dev-only
``simulate_capture`` endpoint.
"""

import uuid
from dataclasses import dataclass

from src.modules.payment.domain.exceptions import (
    PaymentIntentNotFoundError,
    PaymentProviderError,
)
from src.modules.payment.domain.interfaces import (
    IPaymentIntentRepository,
    IPaymentProvider,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CapturePaymentIntentCommand:
    intent_id: uuid.UUID
    idempotency_key: str


class CapturePaymentIntentHandler:
    def __init__(
        self,
        repo: IPaymentIntentRepository,
        provider: IPaymentProvider,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._provider = provider
        self._uow = uow
        self._logger = logger.bind(handler="CapturePaymentIntentHandler")

    async def handle(self, command: CapturePaymentIntentCommand) -> None:
        async with self._uow:
            intent = await self._repo.get_for_update(command.intent_id)
            if intent is None:
                raise PaymentIntentNotFoundError(intent_id=str(command.intent_id))

            if intent.status.value == "captured":
                self._logger.info(
                    "payment.capture.noop",
                    intent_id=str(intent.id),
                )
                return

            try:
                await self._provider.capture(
                    intent_id=intent.id,
                    provider_reference=intent.provider_reference or "",
                    idempotency_key=command.idempotency_key,
                )
            except PaymentProviderError as err:
                intent.fail(reason=err.error_code)
                await self._repo.update(intent)
                self._uow.register_aggregate(intent)
                await self._uow.commit()
                raise

            intent.capture()
            await self._repo.update(intent)
            self._uow.register_aggregate(intent)
            await self._uow.commit()
            self._logger.info("payment.captured", intent_id=str(intent.id))
