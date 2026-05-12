"""Identity-event consumers for the referral module.

Subscribes to:

* ``IdentityRegisteredEvent`` — local / OIDC signup, account_type=CUSTOMER.
* ``LinkedAccountCreatedEvent`` — Telegram / OIDC linked-account
  creation, ``is_new_identity=True``.

Both consumers ensure that every customer ends up with a referral
code; the :class:`IssueReferralCodeHandler` itself is idempotent.

Attribution for invitees who arrive with a ``start_param`` is the job
of a separate ``AttributeReferralCommand`` (PR 3) — kept out of this
file so the issuance flow stays simple.
"""

from __future__ import annotations

import uuid

from src.modules.referral.application.commands.issue_referral_code import (
    IssueReferralCodeCommand,
    IssueReferralCodeHandler,
)
from shared.interfaces.logger import ILogger


class IssueCodeOnIdentityRegisteredConsumer:
    """Reacts to ``IdentityRegisteredEvent`` payloads (local / OIDC signup)."""

    def __init__(
        self,
        issue_handler: IssueReferralCodeHandler,
        logger: ILogger,
    ) -> None:
        self._handler = issue_handler
        self._logger = logger.bind(consumer="IssueCodeOnIdentityRegistered")

    async def handle(self, payload: dict) -> None:
        if payload.get("account_type", "CUSTOMER") != "CUSTOMER":
            return  # staff identities never carry a referral code
        try:
            customer_id = uuid.UUID(str(payload["identity_id"]))
        except KeyError, TypeError, ValueError:
            self._logger.warning("identity_registered.skip", reason="bad_identity_id")
            return
        await self._handler.handle(IssueReferralCodeCommand(customer_id=customer_id))


class IssueCodeOnLinkedAccountCreatedConsumer:
    """Reacts to ``LinkedAccountCreatedEvent`` for Telegram / OIDC signups."""

    def __init__(
        self,
        issue_handler: IssueReferralCodeHandler,
        logger: ILogger,
    ) -> None:
        self._handler = issue_handler
        self._logger = logger.bind(consumer="IssueCodeOnLinkedAccountCreated")

    async def handle(self, payload: dict) -> None:
        if not payload.get("is_new_identity", False):
            return  # only the first link triggers code issuance
        try:
            customer_id = uuid.UUID(str(payload["identity_id"]))
        except KeyError, TypeError, ValueError:
            self._logger.warning(
                "linked_account_created.skip", reason="bad_identity_id"
            )
            return
        await self._handler.handle(IssueReferralCodeCommand(customer_id=customer_id))
