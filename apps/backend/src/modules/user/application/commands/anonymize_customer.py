"""Anonymize customer command and handler.

Provides GDPR-compliant anonymization for customer profiles.
Triggered by an IdentityDeactivatedEvent for CUSTOMER accounts.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.interfaces import ICustomerRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AnonymizeCustomerCommand:
    """Command to anonymize a customer's PII data.

    Attributes:
        customer_id: The UUID of the customer to anonymize.
    """

    customer_id: uuid.UUID


class AnonymizeCustomerHandler:
    """Handler for GDPR customer anonymization.

    Replaces all PII fields with placeholder values. Idempotent.
    """

    def __init__(
        self,
        customer_repo: ICustomerRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._customer_repo = customer_repo
        self._uow = uow
        self._logger = logger.bind(handler="AnonymizeCustomerHandler")

    async def handle(self, command: AnonymizeCustomerCommand) -> None:
        """Execute customer PII anonymization.

        Args:
            command: The anonymization command.
        """
        async with self._uow:
            customer = await self._customer_repo.get(command.customer_id)
            if customer is None:
                self._logger.warning(
                    "customer.not_found_for_anonymization",
                    customer_id=str(command.customer_id),
                )
                return

            customer.anonymize()
            await self._customer_repo.update(customer)
            await self._uow.commit()

        self._logger.info(
            "customer.anonymized",
            customer_id=str(command.customer_id),
        )
