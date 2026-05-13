"""
Shipment repository — Data Mapper implementation.

Translates between the ``Shipment`` domain aggregate and the
``ShipmentModel`` / ``ShipmentTrackingEventModel`` ORM tables.
"""

import uuid

import attrs
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.value_objects import (
    Address,
    CashOnDelivery,
    ContactInfo,
    DeliveryType,
    Dimensions,
    EditTaskKind,
    EditTaskStatus,
    EstimatedDelivery,
    IntakeStatus,
    Money,
    Parcel,
    ParcelItem,
    PendingEditTask,
    ProviderCode,
    RegisteredReturn,
    ScheduledIntake,
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
        # Tracking events are synced via INSERT ... ON CONFLICT before
        # the column flush so the version-locked UPDATE below sees the
        # latest event count and can race safely with webhook ingest.
        await self._sync_tracking_events(orm, shipment)
        await self._session.flush()
        return self._to_domain(orm)

    async def list_with_pending_edit_tasks(self, *, limit: int = 100) -> list[Shipment]:
        # ``pending_edit_tasks_json`` is JSONB; an empty array literal
        # is the persisted ``[]``. ``jsonb_array_length`` is the
        # cheapest way to filter at the index-friendly column level
        # — a partial index on this expression can be added later if
        # the table grows large.
        stmt = (
            select(ShipmentModel)
            .where(
                ShipmentModel.pending_edit_tasks_json.isnot(None),
                ShipmentModel.pending_edit_tasks_json != [],
            )
            .order_by(ShipmentModel.updated_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

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
            sender_json=self._contact_to_dict(entity.sender),
            recipient_json=self._contact_to_dict(entity.recipient),
            parcels_json=[self._parcel_to_dict(p) for p in entity.parcels],
            quoted_cost_amount=entity.quoted_cost.amount,
            quoted_cost_currency=entity.quoted_cost.currency_code,
            cod_json=self._cod_to_dict(entity.cod),
            provider_shipment_id=entity.provider_shipment_id,
            tracking_number=entity.tracking_number,
            provider_payload=entity.provider_payload,
            latest_tracking_status=entity.latest_tracking_status,
            failure_reason=entity.failure_reason,
            estimated_delivery_json=self._estimated_delivery_to_dict(
                entity.estimated_delivery
            ),
            pending_edit_tasks_json=[
                self._pending_edit_task_to_dict(t) for t in entity.pending_edit_tasks
            ],
            scheduled_intake_json=self._scheduled_intake_to_dict(
                entity.scheduled_intake
            ),
            registered_returns_json=[
                self._registered_return_to_dict(r) for r in entity.registered_returns
            ],
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            booked_at=entity.booked_at,
            cancelled_at=entity.cancelled_at,
            cross_border_arrived_at=entity.cross_border_arrived_at,
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
        orm.failure_reason = entity.failure_reason
        orm.estimated_delivery_json = self._estimated_delivery_to_dict(
            entity.estimated_delivery
        )
        # Edit / intake / return state — also a column-level update so
        # the same optimistic lock guards mutations from the new
        # handlers.
        orm.recipient_json = self._contact_to_dict(entity.recipient)
        orm.destination_json = self._address_to_dict(entity.destination)
        orm.delivery_type = entity.delivery_type
        orm.pending_edit_tasks_json = [
            self._pending_edit_task_to_dict(t) for t in entity.pending_edit_tasks
        ]
        orm.scheduled_intake_json = self._scheduled_intake_to_dict(
            entity.scheduled_intake
        )
        orm.registered_returns_json = [
            self._registered_return_to_dict(r) for r in entity.registered_returns
        ]
        orm.updated_at = entity.updated_at
        orm.booked_at = entity.booked_at
        orm.cancelled_at = entity.cancelled_at
        orm.cross_border_arrived_at = entity.cross_border_arrived_at
        orm.version = entity.version

    async def _sync_tracking_events(self, orm: ShipmentModel, entity: Shipment) -> None:
        """Insert / upgrade tracking events, racing safely with concurrent writers.

        The unique constraint ``uq_tracking_events_shipment_ts_status``
        is the source of truth: a concurrent webhook + poll for the
        same ``(shipment_id, timestamp, status)`` would otherwise
        produce ``IntegrityError``. We use Postgres
        ``INSERT ... ON CONFLICT DO UPDATE`` so the second writer
        upserts richer ``location`` / ``description`` text the
        carrier may have included on a delayed webhook — the
        in-memory ``Shipment.append_tracking_event`` already
        normalises this in the aggregate, but without a real UPDATE
        the DB would keep the original (less-rich) row.

        ``COALESCE`` preserves whichever side has non-null text so
        a sparse late event does not overwrite a richer existing
        one — only blanks get filled.
        """
        new_rows: list[dict] = [
            {
                "shipment_id": entity.id,
                "status": event.status,
                "provider_status_code": event.provider_status_code,
                "provider_status_name": event.provider_status_name,
                "timestamp": event.timestamp,
                "location": event.location,
                "description": event.description,
            }
            for event in entity.tracking_events
        ]
        if not new_rows:
            return

        stmt = pg_insert(ShipmentTrackingEventModel).values(new_rows)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            constraint="uq_tracking_events_shipment_ts_status",
            set_={
                "location": func.coalesce(
                    excluded.location, ShipmentTrackingEventModel.location
                ),
                "description": func.coalesce(
                    excluded.description,
                    ShipmentTrackingEventModel.description,
                ),
                "provider_status_name": func.coalesce(
                    excluded.provider_status_name,
                    ShipmentTrackingEventModel.provider_status_name,
                ),
            },
        )
        await self._session.execute(stmt)
        # Refresh the relationship so subsequent reads in the same
        # session see the freshly-upserted rows.
        await self._session.refresh(orm, attribute_names=["tracking_events"])

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
            sender=self._dict_to_contact(orm.sender_json),
            recipient=self._dict_to_contact(orm.recipient_json),
            parcels=[self._dict_to_parcel(p) for p in orm.parcels_json],
            quoted_cost=Money(
                amount=orm.quoted_cost_amount,
                currency_code=orm.quoted_cost_currency,
            ),
            cod=self._dict_to_cod(orm.cod_json),
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
            failure_reason=orm.failure_reason,
            estimated_delivery=self._dict_to_estimated_delivery(
                orm.estimated_delivery_json
            ),
            pending_edit_tasks=[
                self._dict_to_pending_edit_task(t)
                for t in (orm.pending_edit_tasks_json or [])
            ],
            scheduled_intake=self._dict_to_scheduled_intake(orm.scheduled_intake_json),
            registered_returns=[
                self._dict_to_registered_return(r)
                for r in (orm.registered_returns_json or [])
            ],
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            booked_at=orm.booked_at,
            cancelled_at=orm.cancelled_at,
            cross_border_arrived_at=orm.cross_border_arrived_at,
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

        items = []
        for item_data in d.get("items", []):
            unit_price = None
            if item_data.get("unit_price"):
                unit_price = Money(**item_data["unit_price"])
            item_weight = None
            if item_data.get("weight"):
                item_weight = Weight(grams=item_data["weight"]["grams"])
            items.append(
                ParcelItem(
                    name=item_data["name"],
                    quantity=item_data.get("quantity", 1),
                    sku=item_data.get("sku"),
                    unit_price=unit_price,
                    weight=item_weight,
                    country_of_origin=item_data.get("country_of_origin"),
                    hs_code=item_data.get("hs_code"),
                )
            )

        return Parcel(
            weight=weight,
            dimensions=dims,
            declared_value=declared_value,
            description=d.get("description"),
            items=items,
        )

    @staticmethod
    def _cod_to_dict(cod: CashOnDelivery | None) -> dict | None:
        if cod is None:
            return None
        return attrs.asdict(cod)

    @staticmethod
    def _dict_to_cod(d: dict | None) -> CashOnDelivery | None:
        if d is None:
            return None
        return CashOnDelivery(
            amount=Money(**d["amount"]),
            payment_method=d.get("payment_method"),
        )

    @staticmethod
    def _estimated_delivery_to_dict(ed: EstimatedDelivery | None) -> dict | None:
        if ed is None:
            return None
        return attrs.asdict(ed)

    @staticmethod
    def _dict_to_estimated_delivery(d: dict | None) -> EstimatedDelivery | None:
        if d is None:
            return None
        return EstimatedDelivery(**d)

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

    # -- Edit / intake / return state ---------------------------------------

    @staticmethod
    def _pending_edit_task_to_dict(task: PendingEditTask) -> dict:
        return {
            "task_id": task.task_id,
            "kind": task.kind.value,
            "submitted_at": task.submitted_at.isoformat(),
            "initial_status": task.initial_status.value,
        }

    @staticmethod
    def _dict_to_pending_edit_task(d: dict) -> PendingEditTask:
        from datetime import datetime as _datetime

        return PendingEditTask(
            task_id=d["task_id"],
            kind=EditTaskKind(d["kind"]),
            submitted_at=_datetime.fromisoformat(d["submitted_at"]),
            initial_status=EditTaskStatus(
                d.get("initial_status", EditTaskStatus.PENDING.value)
            ),
        )

    @staticmethod
    def _scheduled_intake_to_dict(intake: ScheduledIntake | None) -> dict | None:
        if intake is None:
            return None
        return {
            "provider_intake_id": intake.provider_intake_id,
            "status": intake.status.value,
            "scheduled_at": intake.scheduled_at.isoformat(),
        }

    @staticmethod
    def _dict_to_scheduled_intake(d: dict | None) -> ScheduledIntake | None:
        if d is None:
            return None
        from datetime import datetime as _datetime

        return ScheduledIntake(
            provider_intake_id=d["provider_intake_id"],
            status=IntakeStatus(d["status"]),
            scheduled_at=_datetime.fromisoformat(d["scheduled_at"]),
        )

    @staticmethod
    def _registered_return_to_dict(r: RegisteredReturn) -> dict:
        return {
            "kind": r.kind,
            "provider_return_id": r.provider_return_id,
            "reason": r.reason,
            "registered_at": (
                r.registered_at.isoformat() if r.registered_at is not None else None
            ),
        }

    @staticmethod
    def _dict_to_registered_return(d: dict) -> RegisteredReturn:
        from datetime import datetime as _datetime

        registered_at_raw = d.get("registered_at")
        return RegisteredReturn(
            kind=d["kind"],
            provider_return_id=d.get("provider_return_id"),
            reason=d.get("reason"),
            registered_at=(
                _datetime.fromisoformat(registered_at_raw)
                if registered_at_raw
                else None
            ),
        )
