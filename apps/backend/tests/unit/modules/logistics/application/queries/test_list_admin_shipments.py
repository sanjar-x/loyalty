"""Unit tests for the admin shipments list helper logic (LOG-003).

The handler itself runs a real SQL query, so filter / pagination
behaviour is covered by the integration test under
``tests/integration/modules/logistics/test_list_admin_shipments.py``.
This file pins down the pure ``_to_summary`` mapping that turns an
ORM row into the read-model projection — the only piece worth
isolating without spinning up Postgres.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.modules.logistics.application.queries.list_admin_shipments import (
    _to_summary,
)
from src.modules.logistics.domain.value_objects import (
    DeliveryType,
    ShipmentStatus,
    TrackingStatus,
)
from src.modules.logistics.infrastructure.models import ShipmentModel

pytestmark = pytest.mark.unit


def _orm_row(**overrides: Any) -> ShipmentModel:
    """Build a ShipmentModel without touching the DB.

    SQLAlchemy declarative classes accept kwargs so we can populate the
    column attributes directly. The tests only inspect attribute reads;
    no flush happens.
    """
    base = {
        "id": uuid.uuid4(),
        "order_id": uuid.uuid4(),
        "provider_code": "cdek",
        "service_code": "136",
        "delivery_type": "pickup_point",
        "status": ShipmentStatus.BOOKED.value,
        "origin_json": {},
        "destination_json": {"city": "Москва"},
        "recipient_json": {},
        "sender_json": {},
        "parcels_json": [],
        "quoted_cost_amount": 50_000,
        "quoted_cost_currency": "RUB",
        "cod_json": None,
        "provider_shipment_id": "CDEK-12345",
        "tracking_number": "RU123456789",
        "provider_payload": "{}",
        "latest_tracking_status": TrackingStatus.IN_TRANSIT,
        "failure_reason": None,
        "estimated_delivery_json": None,
        "pending_edit_tasks_json": [],
        "scheduled_intake_json": None,
        "registered_returns_json": [],
        "created_at": datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 5, 2, 11, 0, tzinfo=UTC),
        "booked_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "cancelled_at": None,
        "cross_border_arrived_at": None,
        "version": 1,
    }
    base.update(overrides)
    return ShipmentModel(**base)


def test_to_summary_maps_all_fields() -> None:
    row = _orm_row()
    summary = _to_summary(row)

    assert summary.id == row.id
    assert summary.order_id == row.order_id
    assert summary.provider_code == "cdek"
    assert summary.status == "booked"
    assert summary.tracking_number == "RU123456789"
    assert summary.delivery_type == "pickup_point"
    assert summary.destination_city == "Москва"
    assert summary.quoted_cost_amount == 50_000
    assert summary.quoted_cost_currency == "RUB"
    assert summary.latest_tracking_status == "in_transit"
    assert summary.created_at == row.created_at
    assert summary.updated_at == row.updated_at
    assert summary.booked_at == row.booked_at


def test_to_summary_handles_missing_destination_city() -> None:
    """Legacy rows seeded before ``city`` was required must not crash."""
    row = _orm_row(destination_json={})
    summary = _to_summary(row)
    assert summary.destination_city == ""


def test_to_summary_handles_non_dict_destination() -> None:
    """A malformed JSONB blob (string instead of object) falls back gracefully."""
    row = _orm_row(destination_json=cast_destination("garbage"))  # type: ignore[arg-type]
    summary = _to_summary(row)
    assert summary.destination_city == ""


def cast_destination(value: Any) -> Any:
    """Helper to bypass type checker for the malformed-JSON test."""
    return value


def test_to_summary_handles_null_optional_fields() -> None:
    row = _orm_row(
        order_id=None,
        tracking_number=None,
        latest_tracking_status=None,
        booked_at=None,
    )
    summary = _to_summary(row)
    assert summary.order_id is None
    assert summary.tracking_number is None
    assert summary.latest_tracking_status is None
    assert summary.booked_at is None


def test_to_summary_handles_string_status_column() -> None:
    """SQLAlchemy enum columns may surface as plain strings on certain
    flushed rows depending on how the value was set; the mapper must
    cope with both ``Enum`` and ``str``."""
    row = _orm_row(
        status="cancelled",
        delivery_type="courier",
        latest_tracking_status="delivered",
    )
    summary = _to_summary(row)
    assert summary.status == "cancelled"
    assert summary.delivery_type == "courier"
    assert summary.latest_tracking_status == "delivered"


def test_to_summary_status_value_mirrors_enum_member() -> None:
    """Enum-backed status surfaces via ``.value``."""
    row = _orm_row(
        status=ShipmentStatus.FAILED,
        delivery_type=DeliveryType.COURIER,
    )
    summary = _to_summary(row)
    assert summary.status == "failed"
    assert summary.delivery_type == "courier"
