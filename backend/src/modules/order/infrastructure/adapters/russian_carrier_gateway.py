"""Russian carrier gateway — stub implementation.

Returns a deterministic UUID derived from
``(order_id, cross_border_shipment_id, pickup carrier+point)`` so retries
remain idempotent. To be replaced with real CDEK / Yandex / Boxberry /
Pochta calls via the logistics module's public command handlers in a
future SPEC.
"""

import hashlib
import uuid

from src.modules.order.application.ports import IRussianCarrierGateway
from src.modules.order.domain.value_objects import PickupPointPreference
from src.shared.interfaces.logger import ILogger


class RussianCarrierGatewayStub(IRussianCarrierGateway):
    def __init__(self, logger: ILogger) -> None:
        self._logger = logger.bind(adapter="RussianCarrierGatewayStub")

    async def book_last_mile(
        self,
        *,
        order_id: uuid.UUID,
        cross_border_shipment_id: uuid.UUID,
        pickup_point: PickupPointPreference,
        idempotency_key: str,
    ) -> uuid.UUID:
        seed = (
            f"lastmile:{order_id}:{cross_border_shipment_id}:"
            f"{pickup_point.carrier.value}:{pickup_point.point_id}"
        )
        shipment_id = uuid.UUID(
            bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16]
        )
        self._logger.info(
            "russian_carrier.stub.book_last_mile",
            order_id=str(order_id),
            cross_border_shipment_id=str(cross_border_shipment_id),
            shipment_id=str(shipment_id),
            carrier=pickup_point.carrier.value,
            point_id=pickup_point.point_id,
            idempotency_key=idempotency_key,
        )
        return shipment_id
