"""Consumer: DobroPost passport-validation webhook → mark Recipient verified/invalid.

Triggered by ``DobroPostPassportInvalidEvent`` from the order outbox
(emitted by the DobroPost webhook receiver). The event carries
``recipient_id`` so we can update the recipient's validation_status —
this lets the customer see in their UI which recipient needs an
update.
"""

import uuid

from src.modules.recipient.application.commands.mark_validation_status import (
    MarkRecipientInvalidCommand,
    MarkRecipientInvalidHandler,
    MarkRecipientVerifiedCommand,
    MarkRecipientVerifiedHandler,
)
from src.modules.recipient.domain.exceptions import RecipientNotFoundError
from shared.interfaces.logger import ILogger


class DobroPostPassportValidatedConsumer:
    def __init__(
        self,
        verified_handler: MarkRecipientVerifiedHandler,
        invalid_handler: MarkRecipientInvalidHandler,
        logger: ILogger,
    ) -> None:
        self._verified = verified_handler
        self._invalid = invalid_handler
        self._logger = logger.bind(consumer="DobroPostPassportValidatedConsumer")

    async def handle(self, payload: dict) -> None:
        recipient_id_raw = payload.get("recipient_id")
        if recipient_id_raw is None:
            return
        try:
            recipient_id = uuid.UUID(str(recipient_id_raw))
        except TypeError, ValueError:
            return
        is_valid = payload.get("passportValidationStatus")
        try:
            if is_valid is True:
                await self._verified.handle(
                    MarkRecipientVerifiedCommand(recipient_id=recipient_id)
                )
            elif is_valid is False:
                reason = str(
                    payload.get("reason") or "DobroPost passport validation failed"
                )
                await self._invalid.handle(
                    MarkRecipientInvalidCommand(
                        recipient_id=recipient_id, reason=reason
                    )
                )
        except RecipientNotFoundError:
            self._logger.warning(
                "recipient.dobropost_passport.skip",
                reason="not_found",
                recipient_id=str(recipient_id),
            )
