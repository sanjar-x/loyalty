"""Update customer profile command and handler.

Provides the workflow for partial updates to a customer's profile fields.
Only non-None fields in the command are applied to the aggregate.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.exceptions import CustomerNotFoundError
from src.modules.user.domain.interfaces import ICustomerRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateProfileCommand:
    """Command to update a customer's profile fields.

    Only fields set to non-None values will be applied. All fields
    default to None, meaning "no change".

    Attributes:
        customer_id: The UUID of the customer to update.
        first_name: New first name, or None to leave unchanged.
        last_name: New last name, or None to leave unchanged.
        phone: New phone number, or None to leave unchanged.
        profile_email: New display email, or None to leave unchanged.
    """

    customer_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    profile_email: str | None = None


class UpdateProfileHandler:
    """Handler for partial customer profile updates.

    Applies only the provided (non-None) fields to the Customer aggregate
    and persists the changes within a unit of work.
    """

    def __init__(
        self,
        customer_repo: ICustomerRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._customer_repo = customer_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateProfileHandler")

    async def handle(self, command: UpdateProfileCommand) -> None:
        """Execute a partial profile update.

        Args:
            command: The update command with fields to change.

        Raises:
            CustomerNotFoundError: If no customer exists with the given ID.
        """
        async with self._uow:
            customer = await self._customer_repo.get(command.customer_id)
            if customer is None:
                raise CustomerNotFoundError(command.customer_id)

            updates = {}
            if command.first_name is not None:
                updates["first_name"] = command.first_name
            if command.last_name is not None:
                updates["last_name"] = command.last_name
            if command.phone is not None:
                updates["phone"] = command.phone
            if command.profile_email is not None:
                updates["profile_email"] = command.profile_email

            if updates:
                customer.update_profile(**updates)
                await self._customer_repo.update(customer)

            await self._uow.commit()

        self._logger.info(
            "customer.profile_updated", customer_id=str(command.customer_id)
        )
