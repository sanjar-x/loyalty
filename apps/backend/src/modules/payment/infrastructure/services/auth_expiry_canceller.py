"""Background service: fail PaymentIntents whose authorization hold elapsed.

Visa-стандартный auth hold живёт ``PAYMENT_AUTH_TTL_DAYS=7`` (см.
``settings.PAYMENT_AUTH_TTL_DAYS``). После истечения провайдер
отклонит ``capture()`` с ошибкой, и Order застрянет в PAID без
возможности продвинуться через ``ProcureOrderHandler``. Этот service
проактивно переводит такие intents в ``FAILED`` с
``failure_reason="auth_expired"``, что эмитит
:class:`PaymentFailedEvent` и через outbox триггерит
``PaymentFailedConsumer`` в Order, который отменяет заказ с
:class:`CancellationReason.SYSTEM_AUTH_EXPIRED`.

Stateless service — каждый ``run()`` выполняет один tick. Cron
дёргает его раз в 6 часов (``0 */6 * * *``); параллельные запуски
безопасны, потому что ``FailPaymentIntentHandler`` идемпотентен на
терминальных intents (early return).
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.modules.payment.application.commands.fail_payment_intent import (
    FailPaymentIntentCommand,
    FailPaymentIntentHandler,
)
from src.modules.payment.domain.exceptions import PaymentIntentNotFoundError
from src.modules.payment.domain.interfaces import IPaymentIntentRepository
from src.shared.interfaces.logger import ILogger

AUTH_EXPIRED_REASON = "auth_expired"
"""Sentinel reason string. Order's PaymentFailedConsumer matches on this
verbatim to pick :class:`CancellationReason.SYSTEM_AUTH_EXPIRED` instead
of the generic ``SYSTEM_PAYMENT_FAILED``."""


class AuthExpiryCanceller:
    """One-tick canceller for expired AUTHORIZED PaymentIntents.

    Args:
        repo: Read-side selector for expired intents (id projection only).
        fail_handler: Issues ``FailPaymentIntentCommand`` per intent in
            its own UoW so a transient failure on one intent doesn't
            poison the rest of the batch.
        logger: Bound to ``service="AuthExpiryCanceller"`` on init.
    """

    def __init__(
        self,
        repo: IPaymentIntentRepository,
        fail_handler: FailPaymentIntentHandler,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._fail_handler = fail_handler
        self._logger = logger.bind(service="AuthExpiryCanceller")

    async def run(self, *, batch_size: int = 100) -> int:
        """Fail every AUTHORIZED intent whose ``auth_expires_at`` is past.

        Returns the number of intents successfully failed in this tick.
        """
        now = datetime.now(UTC)
        expired_ids = await self._repo.find_expired_authorized(
            now=now, limit=batch_size
        )
        if not expired_ids:
            return 0

        failed = 0
        for intent_id in expired_ids:
            try:
                await self._fail_handler.handle(
                    FailPaymentIntentCommand(
                        intent_id=intent_id,
                        reason=AUTH_EXPIRED_REASON,
                    )
                )
                failed += 1
            except PaymentIntentNotFoundError:
                # Race: intent was deleted between selector and handler.
                # Not an error — just an empty round-trip.
                self._logger.info(
                    "auth_expiry.skip",
                    intent_id=str(intent_id),
                    reason="not_found",
                )
            except Exception:
                # Per-intent isolation: log + continue. The cron's
                # next tick (in 6 hours) will retry whatever stayed
                # AUTHORIZED past auth_expires_at.
                self._logger.exception(
                    "auth_expiry.fail_handler_error",
                    intent_id=str(intent_id),
                )

        self._logger.info(
            "auth_expiry.tick",
            scanned=len(expired_ids),
            failed=failed,
        )
        return failed
