"""
Query handler: ask the provider whether a reverse-shipment route is
feasible for a hypothetical order *before* it is created.

This is a *route validation*, not a per-shipment lookup — CDEK only
evaluates direction, tariff and contact phones; it doesn't accept an
existing order UUID. Run from the storefront / checkout flow to surface
"return path unavailable" messages early.
"""

from dataclasses import dataclass

from src.modules.logistics.application.dto import CheckReverseAvailabilityResult
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import (
    Address,
    ProviderCode,
    ReverseAvailabilityRequest,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class CheckReverseAvailabilityQuery:
    """Input for reverse-shipment route validation.

    Attributes:
        provider_code: Logistics provider to query.
        tariff_code: Provider tariff code (CDEK Приложение 14 for returns).
        sender_phones: Sender's phone numbers (E.164, with leading ``+``).
        recipient_phones: Recipient's phone numbers (E.164).
        from_location: Origin address (mutually exclusive with shipment_point).
        to_location: Destination address (mutually exclusive with delivery_point).
        shipment_point: CDEK pickup-point code at origin.
        delivery_point: CDEK pickup-point code at destination.
        sender_contragent_type: Optional ``LEGAL_ENTITY`` / ``INDIVIDUAL``.
        recipient_contragent_type: Optional ``LEGAL_ENTITY`` / ``INDIVIDUAL``.
    """

    provider_code: ProviderCode
    tariff_code: int
    sender_phones: tuple[str, ...]
    recipient_phones: tuple[str, ...]
    from_location: Address | None = None
    to_location: Address | None = None
    shipment_point: str | None = None
    delivery_point: str | None = None
    sender_contragent_type: str | None = None
    recipient_contragent_type: str | None = None


class CheckReverseAvailabilityHandler:
    """Validate that a reverse-shipment route exists for the chosen tariff."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._logger = logger.bind(handler="CheckReverseAvailabilityHandler")

    async def handle(
        self, query: CheckReverseAvailabilityQuery
    ) -> CheckReverseAvailabilityResult:
        provider = self._registry.get_return_provider(query.provider_code)
        request = ReverseAvailabilityRequest(
            tariff_code=query.tariff_code,
            sender_phones=query.sender_phones,
            recipient_phones=query.recipient_phones,
            from_location=query.from_location,
            to_location=query.to_location,
            shipment_point=query.shipment_point,
            delivery_point=query.delivery_point,
            sender_contragent_type=query.sender_contragent_type,
            recipient_contragent_type=query.recipient_contragent_type,
        )
        result = await provider.check_reverse_availability(request)
        return CheckReverseAvailabilityResult(
            provider_code=query.provider_code,
            is_available=result.is_available,
            reason=result.reason,
        )
