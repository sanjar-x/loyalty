"""
Command handler: register a client return shipment with the provider.

A client return is the recipient sending the goods *back* to the sender
after delivery (e.g. defective product). The provider creates a fresh
return order linked to the original delivery.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import RegisterReturnResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    ClientReturnRequest,
    ContactInfo,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RegisterClientReturnCommand:
    """Input for registering a client return.

    Attributes:
        shipment_id: UUID of the original (delivered) shipment.
        tariff_code: Provider tariff code for the return shipment.
        return_address: Where the courier should pick up the goods.
        sender: Contact at the pickup (= original recipient).
        recipient: Contact at the destination (= original sender).
    """

    shipment_id: uuid.UUID
    tariff_code: int
    return_address: Address
    sender: ContactInfo
    recipient: ContactInfo


class RegisterClientReturnHandler:
    """Register a client return with the shipment's provider."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._uow = uow
        self._logger = logger.bind(handler="RegisterClientReturnHandler")

    async def handle(
        self, command: RegisterClientReturnCommand
    ) -> RegisterReturnResult:
        # Phase 1: validate.
        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )

        # Phase 2: provider call.
        provider = self._registry.get_return_provider(shipment.provider_code)
        request = ClientReturnRequest(
            order_provider_id=shipment.provider_shipment_id or "",
            tariff_code=command.tariff_code,
            return_address=command.return_address,
            sender=command.sender,
            recipient=command.recipient,
            parcels=list(shipment.parcels),
        )
        result = await provider.register_client_return(request)

        # Phase 3: persist + emit event only on success. A rejected
        # return does not mutate state — caller sees ``success=False``
        # plus the reason, no audit row added.
        if result.success:
            async with self._uow:
                shipment = await self._shipment_repo.get_by_id(command.shipment_id)
                if shipment is None:
                    self._logger.error(
                        "Shipment vanished between client_return submit and persist",
                        shipment_id=str(command.shipment_id),
                        provider_return_id=result.provider_return_id,
                    )
                    raise ShipmentNotFoundError(
                        details={"shipment_id": str(command.shipment_id)}
                    )
                shipment.record_return(
                    provider_return_id=result.provider_return_id,
                    reason=result.reason,
                )
                await self._shipment_repo.update(shipment)
                self._uow.register_aggregate(shipment)
                await self._uow.commit()

            self._logger.info(
                "Client return registered",
                shipment_id=str(command.shipment_id),
                provider_return_id=result.provider_return_id,
            )
        else:
            self._logger.warning(
                "Client return rejected by provider",
                shipment_id=str(command.shipment_id),
                reason=result.reason,
            )
        return RegisterReturnResult(
            shipment_id=command.shipment_id,
            success=result.success,
            provider_return_id=result.provider_return_id,
            reason=result.reason,
        )
