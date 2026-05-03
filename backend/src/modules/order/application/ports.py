"""ACL port contracts used by Order command handlers.

These ports decouple Order's application layer from the concrete
gateway adapters living in ``infrastructure/adapters/`` (which is the
only place allowed to import Logistics / Payment internals — see
``ALLOWED_CROSS_MODULE`` in tests/architecture).
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from attrs import frozen

from src.modules.order.domain.value_objects import PickupPointPreference


@frozen
class PaymentTicket:
    intent_id: uuid.UUID
    client_secret: str | None


class IPaymentGateway(ABC):
    @abstractmethod
    async def authorize(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        amount: int,
        currency: str,
        idempotency_key: str,
        provider: str,
    ) -> PaymentTicket: ...

    @abstractmethod
    async def capture(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None: ...

    @abstractmethod
    async def refund(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None: ...


class IDobroPostGateway(ABC):
    """ACL into logistics — DobroPost cross-border shipment booking."""

    @abstractmethod
    async def book_cross_border(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        incoming_declaration: str,
        idempotency_key: str,
    ) -> uuid.UUID:
        """Book a DobroPost shipment and return its shipment_id."""

    @abstractmethod
    async def cancel_cross_border(
        self, *, shipment_id: uuid.UUID, idempotency_key: str
    ) -> None: ...

    @abstractmethod
    async def update_recipient(
        self,
        *,
        order_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        """Push the order's current RecipientSnapshot to DobroPost.

        Used after ``RefreshRecipientSnapshotHandler`` succeeds: pulls
        the int-id from the side mapping and PUTs ``/api/shipment`` so
        the customs officer re-validates with corrected passport data.
        """


@frozen
class DobroPostShipmentMappingRecord:
    """Read projection of a DobroPost int-id ↔ UUID mapping row."""

    order_id: uuid.UUID
    shipment_uuid: uuid.UUID
    dp_shipment_id: int
    incoming_declaration: str
    dp_track_number: str | None
    last_status_id: int | None
    last_status_at: datetime | None


class IDobroPostShipmentMappingRepository(ABC):
    @abstractmethod
    async def add(
        self,
        *,
        order_id: uuid.UUID,
        shipment_uuid: uuid.UUID,
        dp_shipment_id: int,
        incoming_declaration: str,
        dp_track_number: str | None,
    ) -> None: ...

    @abstractmethod
    async def get_by_shipment_uuid(
        self, shipment_uuid: uuid.UUID
    ) -> DobroPostShipmentMappingRecord | None: ...

    @abstractmethod
    async def get_by_dp_shipment_id(
        self, dp_shipment_id: int
    ) -> DobroPostShipmentMappingRecord | None: ...

    @abstractmethod
    async def get_by_order_id(
        self, order_id: uuid.UUID
    ) -> DobroPostShipmentMappingRecord | None: ...

    @abstractmethod
    async def update_status(
        self,
        *,
        dp_shipment_id: int,
        last_status_id: int,
        dp_track_number: str | None = None,
    ) -> None: ...


class IRussianCarrierGateway(ABC):
    """ACL into logistics — russian carrier last-mile shipment booking."""

    @abstractmethod
    async def book_last_mile(
        self,
        *,
        order_id: uuid.UUID,
        cross_border_shipment_id: uuid.UUID,
        pickup_point: PickupPointPreference,
        idempotency_key: str,
    ) -> uuid.UUID:
        """Book a russian carrier shipment and return its shipment_id."""
