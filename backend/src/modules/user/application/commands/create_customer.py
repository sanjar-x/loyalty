"""Create customer command and handler.

Provides the customer creation workflow triggered by an IdentityRegisteredEvent
(account_type=CUSTOMER) from the Identity module via the outbox consumer.
Also used as a self-healing fallback from profile endpoints when the async
event pipeline has not yet created the customer record.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.entities import Customer
from src.modules.user.domain.interfaces import ICustomerRepository
from src.modules.user.domain.services import generate_referral_code
from src.shared.exceptions import ConflictError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateCustomerCommand:
    """Command to create a customer from an identity registration.

    Attributes:
        identity_id: The Identity aggregate ID (shared PK).
        profile_email: Optional display email.
        referred_by: Customer ID of the referrer, if any.
        first_name: First name from provider metadata (e.g. Telegram).
        last_name: Last name from provider metadata.
        username: Username from provider metadata.
        photo_url: Profile photo URL from provider metadata.
    """

    identity_id: uuid.UUID
    profile_email: str | None = None
    referred_by: uuid.UUID | None = None
    first_name: str = ""
    last_name: str = ""
    username: str | None = None
    photo_url: str | None = None


class CreateCustomerHandler:
    """Handler for creating a Customer from an identity registration event.

    Idempotent: if a customer with the given ID already exists, creation is skipped.
    Race-safe: concurrent creation attempts are tolerated (ConflictError caught).
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
                first_name=command.first_name,
                last_name=command.last_name,
                username=command.username,
                photo_url=command.photo_url,
                referral_code=referral_code,
                referred_by=command.referred_by,
            )
            await self._customer_repo.add(customer)
            try:
                await self._uow.commit()
            except ConflictError:
                self._logger.info(
                    "customer.concurrent_creation",
                    identity_id=str(command.identity_id),
                )
                return

        self._logger.info(
            "customer.created",
            customer_id=str(command.identity_id),
            referral_code=referral_code,
        )
