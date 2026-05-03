"""Command: create a PaymentIntent for an order (two-step authorize-only).

Idempotent: if a PaymentIntent already exists for the supplied
``idempotency_key`` it is returned as-is (replays return the original
intent without re-calling the provider).

Capture is **deferred** to a separate command (``CapturePaymentIntent``)
invoked when the manager procures the goods on the Chinese marketplace
(research (5) §3 — two-step semantics for physical goods).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.bootstrap.config import settings
from src.modules.payment.domain.entities import PaymentIntent
from src.modules.payment.domain.exceptions import PaymentProviderError
from src.modules.payment.domain.interfaces import (
    IPaymentIntentRepository,
    IPaymentProvider,
)
from src.modules.payment.domain.value_objects import ProviderCode
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreatePaymentIntentCommand:
    order_id: uuid.UUID
    amount: int
    currency: str
    idempotency_key: str
    provider: ProviderCode = ProviderCode.FAKE


@dataclass(frozen=True)
class CreatePaymentIntentResult:
    intent_id: uuid.UUID
    client_secret: str | None
    auto_captured: bool


class CreatePaymentIntentHandler:
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
        self._logger = logger.bind(handler="CreatePaymentIntentHandler")

    async def handle(
        self, command: CreatePaymentIntentCommand
    ) -> CreatePaymentIntentResult:
        async with self._uow:
            existing = await self._repo.get_by_idempotency_key(command.idempotency_key)
            if existing is not None:
                return CreatePaymentIntentResult(
                    intent_id=existing.id,
                    client_secret=existing.client_secret,
                    auto_captured=existing.status.value == "captured",
                )

            intent = PaymentIntent.initiate(
                order_id=command.order_id,
                provider=command.provider,
                amount=command.amount,
                currency=command.currency,
                idempotency_key=command.idempotency_key,
            )
            intent = await self._repo.add(intent)

            try:
                authorization = await self._provider.authorize(
                    intent_id=intent.id,
                    amount=intent.amount,
                    currency=intent.currency,
                    idempotency_key=intent.idempotency_key,
                    order_id=intent.order_id,
                )
            except PaymentProviderError as err:
                intent.fail(reason=err.error_code)
                await self._repo.update(intent)
                self._uow.register_aggregate(intent)
                await self._uow.commit()
                raise

            auth_expires_at = datetime.now(UTC) + timedelta(
                days=settings.PAYMENT_AUTH_TTL_DAYS
            )
            intent.authorize(
                provider_reference=authorization.provider_reference,
                client_secret=authorization.client_secret,
                auth_expires_at=auth_expires_at,
            )
            if authorization.auto_captured:
                intent.capture()
            await self._repo.update(intent)
            self._uow.register_aggregate(intent)
            await self._uow.commit()

            self._logger.info(
                "payment.intent_created",
                intent_id=str(intent.id),
                order_id=str(intent.order_id),
                provider=intent.provider.value,
                auto_captured=authorization.auto_captured,
            )
            return CreatePaymentIntentResult(
                intent_id=intent.id,
                client_secret=intent.client_secret,
                auto_captured=authorization.auto_captured,
            )
