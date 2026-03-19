"""Create customer command and handler.

Provides the customer creation workflow triggered by an IdentityRegisteredEvent
(account_type=CUSTOMER) from the Identity module via the outbox consumer.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.entities import Customer
from src.modules.user.domain.interfaces import ICustomerRepository
from src.modules.user.domain.services import generate_referral_code
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateCustomerCommand:
    """Command to create a customer from an identity registration.

    Attributes:
        identity_id: The Identity aggregate ID (shared PK).
        profile_email: Optional display email.
        referred_by: Customer ID of the referrer, if any.
    """

    identity_id: uuid.UUID
    profile_email: str | None = None
    referred_by: uuid.UUID | None = None


class CreateCustomerHandler:
    """Handler for creating a Customer from an identity registration event.

    Idempotent: if a customer with the given ID already exists, creation is skipped.
    Generates a unique referral code automatically.
    """

    def __init__(
        self,
        customer_repo: ICustomerRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._customer_repo = customer_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateCustomerHandler")

    async def handle(self, command: CreateCustomerCommand) -> None:
        """Execute customer creation.

        Args:
            command: The creation command.
        """
        async with self._uow:
            existing = await self._customer_repo.get(command.identity_id)
            if existing:
                self._logger.warning(
                    "customer.already_exists",
                    identity_id=str(command.identity_id),
                )
                return

            referral_code = generate_referral_code()
            customer = Customer.create_from_identity(
                identity_id=command.identity_id,
                profile_email=command.profile_email,
                referral_code=referral_code,
                referred_by=command.referred_by,
            )
            await self._customer_repo.add(customer)
            await self._uow.commit()

        self._logger.info(
            "customer.created",
            customer_id=str(command.identity_id),
            referral_code=referral_code,
        )
