"""
Shipment repository — Data Mapper implementation.

Translates between the ``Shipment`` domain aggregate and the
``ShipmentModel`` / ``ShipmentTrackingEventModel`` ORM tables.
"""

import uuid

import attrs
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.value_objects import (
    Address,
    ContactInfo,
    DeliveryType,
    Dimensions,
    Money,
    Parcel,
    ProviderCode,
    ShipmentStatus,
    TrackingEvent,
    TrackingStatus,
    Weight,
)
from src.modules.logistics.infrastructure.models import (
    ShipmentModel,
    ShipmentTrackingEventModel,
)


class ShipmentRepository(IShipmentRepository):
    """Data Mapper repository for the Shipment aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Public interface ---------------------------------------------------

    async def add(self, shipment: Shipment) -> Shipment:
        orm = self._to_orm(shipment)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get_by_id(self, shipment_id: uuid.UUID) -> Shipment | None:
        orm = await self._session.get(ShipmentModel, shipment_id)
        return self._to_domain(orm) if orm else None

    async def get_by_provider_shipment_id(
        self,
        provider_code: ProviderCode,
        provider_shipment_id: str,
    ) -> Shipment | None:
        stmt = select(ShipmentModel).where(
            ShipmentModel.provider_code == provider_code,
            ShipmentModel.provider_shipment_id == provider_shipment_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, shipment: Shipment) -> Shipment:
        orm = await self._session.get(ShipmentModel, shipment.id)
        if orm is None:
            raise ValueError(f"Shipment {shipment.id} not found")

        self._update_orm(orm, shipment)
        await self._session.flush()
        return self._to_domain(orm)

    # -- Mapping: Domain → ORM ----------------------------------------------

    def _to_orm(self, entity: Shipment) -> ShipmentModel:
        orm = ShipmentModel(
            id=entity.id,
            order_id=entity.order_id,
            provider_code=entity.provider_code,
            service_code=entity.service_code,
            delivery_type=entity.delivery_type,
            status=entity.status,
            origin_json=self._address_to_dict(entity.origin),
            destination_json=self._address_to_dict(entity.destination),
            recipient_json=self._contact_to_dict(entity.recipient),
            parcels_json=[self._parcel_to_dict(p) for p in entity.parcels],
            quoted_cost_amount=entity.quoted_cost.amount,
            quoted_cost_currency=entity.quoted_cost.currency_code,
            provider_shipment_id=entity.provider_shipment_id,
            tracking_number=entity.tracking_number,
            provider_payload=entity.provider_payload,
            latest_tracking_status=entity.latest_tracking_status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            booked_at=entity.booked_at,
            cancelled_at=entity.cancelled_at,
            version=entity.version,
        )
        for event in entity.tracking_events:
            orm.tracking_events.append(self._tracking_event_to_orm(event, entity.id))
        return orm

    def _update_orm(self, orm: ShipmentModel, entity: Shipment) -> None:
        orm.status = entity.status
        orm.provider_shipment_id = entity.provider_shipment_id
        orm.tracking_number = entity.tracking_number
        orm.provider_payload = entity.provider_payload
        orm.latest_tracking_status = entity.latest_tracking_status
        orm.updated_at = entity.updated_at
        orm.booked_at = entity.booked_at
        orm.cancelled_at = entity.cancelled_at
        orm.version = entity.version

        # Sync tracking events (append-only)
        existing_ids = {e.id for e in orm.tracking_events}
        for event in entity.tracking_events:
            event_orm = self._tracking_event_to_orm(event, entity.id)
            if event_orm.id not in existing_ids:
                orm.tracking_events.append(event_orm)

    # -- Mapping: ORM → Domain ----------------------------------------------

    def _to_domain(self, orm: ShipmentModel) -> Shipment:
        return Shipment(
            id=orm.id,
            order_id=orm.order_id,
            provider_code=ProviderCode(orm.provider_code),
            service_code=orm.service_code,
            delivery_type=DeliveryType(orm.delivery_type),
            status=ShipmentStatus(orm.status),
            origin=self._dict_to_address(orm.origin_json),
            destination=self._dict_to_address(orm.destination_json),
            recipient=self._dict_to_contact(orm.recipient_json),
            parcels=[self._dict_to_parcel(p) for p in orm.parcels_json],
            quoted_cost=Money(
                amount=orm.quoted_cost_amount,
                currency_code=orm.quoted_cost_currency,
            ),
            provider_shipment_id=orm.provider_shipment_id,
            tracking_number=orm.tracking_number,
            provider_payload=orm.provider_payload,
            tracking_events=[
                self._orm_to_tracking_event(e) for e in orm.tracking_events
            ],
            latest_tracking_status=(
                TrackingStatus(orm.latest_tracking_status)
                if orm.latest_tracking_status
                else None
            ),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            booked_at=orm.booked_at,
            cancelled_at=orm.cancelled_at,
            version=orm.version,
        )

    # -- Value object serialization helpers ---------------------------------

    @staticmethod
    def _address_to_dict(addr: Address) -> dict:
        return attrs.asdict(addr)

    @staticmethod
    def _dict_to_address(d: dict) -> Address:
        return Address(**d)

    @staticmethod
    def _contact_to_dict(contact: ContactInfo) -> dict:
        return attrs.asdict(contact)

    @staticmethod
    def _dict_to_contact(d: dict) -> ContactInfo:
        return ContactInfo(**d)

    @staticmethod
    def _parcel_to_dict(parcel: Parcel) -> dict:
        return attrs.asdict(parcel)

    @staticmethod
    def _dict_to_parcel(d: dict) -> Parcel:
        weight_data = d["weight"]
        weight = Weight(grams=weight_data["grams"])

        dims = None
        if d.get("dimensions"):
            dims = Dimensions(**d["dimensions"])

        declared_value = None
        if d.get("declared_value"):
            declared_value = Money(**d["declared_value"])

        return Parcel(
            weight=weight,
            dimensions=dims,
            declared_value=declared_value,
            description=d.get("description"),
        )

    @staticmethod
    def _tracking_event_to_orm(
        event: TrackingEvent, shipment_id: uuid.UUID
    ) -> ShipmentTrackingEventModel:
        return ShipmentTrackingEventModel(
            id=uuid.uuid4(),
            shipment_id=shipment_id,
            status=event.status,
            provider_status_code=event.provider_status_code,
            provider_status_name=event.provider_status_name,
            timestamp=event.timestamp,
            location=event.location,
            description=event.description,
        )

    @staticmethod
    def _orm_to_tracking_event(
        orm: ShipmentTrackingEventModel,
    ) -> TrackingEvent:
        return TrackingEvent(
            status=TrackingStatus(orm.status),
            provider_status_code=orm.provider_status_code,
            provider_status_name=orm.provider_status_name,
            timestamp=orm.timestamp,
            location=orm.location,
            description=orm.description,
        )
