"""Issue a fresh :class:`ReferralCode` for a Customer.

Triggered by every ``IdentityRegisteredEvent`` (account_type=CUSTOMER)
and every ``LinkedAccountCreatedEvent`` (is_new_identity=True). The
handler is idempotent — if the customer already owns a code (the
unique index on ``customer_id`` enforces 1:1) the handler short-
circuits.

Code-collision retry is local: the issuer-side ``UNIQUE(code)``
constraint may reject a generated value (probability ≈ 1 / 30⁸ at the
default 8-char length, but we still defend against it). The handler
loops with a fresh code up to ``_MAX_COLLISION_RETRIES`` times before
giving up — a hard fail at that point indicates either an alphabet /
length misconfiguration or a deeper integrity issue worth surfacing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.referral.domain.aggregates import ReferralCode
from src.modules.referral.domain.exceptions import (
    ReferralCodeAlreadyIssuedError,
)
from src.modules.referral.domain.ports import (
    ICodeGenerator,
    IReferralCodeRepository,
)
from src.shared.exceptions import ConflictError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

_MAX_COLLISION_RETRIES = 8


@dataclass(frozen=True)
class IssueReferralCodeCommand:
    customer_id: uuid.UUID


@dataclass(frozen=True)
class IssueReferralCodeResult:
    code_id: uuid.UUID
    code: str
    deduplicated: bool


class IssueReferralCodeHandler:
    def __init__(
        self,
        code_repo: IReferralCodeRepository,
        code_generator: ICodeGenerator,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._code_repo = code_repo
        self._code_generator = code_generator
        self._uow = uow
        self._logger = logger.bind(handler="IssueReferralCodeHandler")

    async def handle(
        self, command: IssueReferralCodeCommand
    ) -> IssueReferralCodeResult:
        existing = await self._code_repo.get_by_customer(command.customer_id)
        if existing is not None:
            self._logger.info(
                "referral_code.already_issued",
                customer_id=str(command.customer_id),
                code=existing.code,
            )
            return IssueReferralCodeResult(
                code_id=existing.id, code=existing.code, deduplicated=True
            )

        last_error: Exception | None = None
        for attempt in range(_MAX_COLLISION_RETRIES):
            generated = self._code_generator.generate()
            code = ReferralCode.issue(customer_id=command.customer_id, code=generated)
            try:
                async with self._uow:
                    await self._code_repo.add(code)
                    self._uow.register_aggregate(code)
                    await self._uow.commit()
            except ReferralCodeAlreadyIssuedError as exc:
                # Could be either the (customer_id) uniqueness — the
                # repository returns a generic AlreadyIssuedError because
                # SQL doesn't expose which constraint fired — or the
                # (code) one. Re-fetch to disambiguate.
                last_error = exc
                refetched = await self._code_repo.get_by_customer(command.customer_id)
                if refetched is not None:
                    self._logger.info(
                        "referral_code.race_won_by_other_writer",
                        customer_id=str(command.customer_id),
                        code=refetched.code,
                    )
                    return IssueReferralCodeResult(
                        code_id=refetched.id,
                        code=refetched.code,
                        deduplicated=True,
                    )
                # Otherwise it's a code-collision — retry.
                self._logger.warning(
                    "referral_code.collision_retry",
                    customer_id=str(command.customer_id),
                    attempt=attempt,
                    code=generated,
                )
                continue
            else:
                self._logger.info(
                    "referral_code.issued",
                    customer_id=str(command.customer_id),
                    code=generated,
                )
                return IssueReferralCodeResult(
                    code_id=code.id, code=generated, deduplicated=False
                )

        # Loop exhausted: surfacing as ConflictError keeps the
        # diagnostic visible without leaking infrastructure details.
        raise ConflictError(
            message="Referral code generation exceeded retry budget",
            error_code="REFERRAL_CODE_COLLISION_RETRY_EXHAUSTED",
            details={"attempts": _MAX_COLLISION_RETRIES},
        ) from last_error
