"""
Regression tests for the Yandex Delivery mappers.

Covers the doc-divergence fixes:

- ``build_physical_dims`` axis mapping (dx=Длина, dy=Высота, dz=Ширина).
- ``_build_location_details`` emits the country as a display name.
- ``parse_pickup_points`` decodes the country back to an ISO code and
  reports payment capabilities honestly.
- ``build_offers_create_request`` forwards ``merchant_id`` only when
  configured and strips the ``+`` from the recipient phone.
- ``build_pickup_points_request`` requires a bound (lat/lng box or
  ``geo_id``) and rejects an unbounded query.
- ``parse_tracking_history`` keeps an unknown status non-terminal.
- ``parse_editable_actions`` reads 3.03 ``available_actions``, degrading
  any payload gap to "allowed" so the pre-check never over-blocks.
"""

from __future__ import annotations

import uuid

import pytest

from src.modules.logistics.domain.value_objects import (
    Address,
    BookingRequest,
    ContactInfo,
    DeliveryType,
    Dimensions,
    EditableActions,
    Parcel,
    PickupPointQuery,
    TrackingStatus,
    Weight,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.mappers import (
    _build_location_details,
    build_offers_create_request,
    build_physical_dims,
    build_pickup_points_request,
    parse_editable_actions,
    parse_pickup_points,
    parse_tracking_history,
)

pytestmark = pytest.mark.unit


def _booking_request(
    *,
    delivery_type: DeliveryType = DeliveryType.COURIER,
    parcels: list[Parcel] | None = None,
) -> BookingRequest:
    return BookingRequest(
        shipment_id=uuid.uuid4(),
        origin=Address(
            country_code="RU",
            city="Москва",
            metadata={"platform_station_id": "src-station"},
        ),
        destination=Address(
            country_code="RU",
            city="Москва",
            street="Пролетарский проспект",
            house="19",
            metadata=(
                {"platform_station_id": "dst-station"}
                if delivery_type == DeliveryType.PICKUP_POINT
                else {}
            ),
        ),
        sender=ContactInfo(
            first_name="Склад", last_name="Лоялити", phone="+74950000000"
        ),
        recipient=ContactInfo(
            first_name="Иван",
            last_name="Иванов",
            phone="+7 (995) 123-45-67",
        ),
        parcels=parcels or [Parcel(weight=Weight(grams=500))],
        service_code="time_interval",
        delivery_type=delivery_type,
        provider_payload="{}",
    )


class TestBuildPhysicalDims:
    def test_axes_map_by_meaning_not_position(self) -> None:
        # Non-cube dimensions so a dy/dz swap is observable. Yandex docs:
        # dx = Длина (length), dy = Высота (height), dz = Ширина (width).
        dims = build_physical_dims(
            1200, Dimensions(length_cm=30, width_cm=20, height_cm=10)
        )
        assert dims == {"weight_gross": 1200, "dx": 30, "dy": 10, "dz": 20}

    def test_weight_only_when_no_dimensions(self) -> None:
        assert build_physical_dims(750, None) == {"weight_gross": 750}


class TestBuildLocationDetails:
    def test_country_code_becomes_display_name(self) -> None:
        addr = Address(
            country_code="RU",
            city="Москва",
            street="Пролетарский проспект",
            house="19",
        )
        details = _build_location_details(addr)
        assert details["country"] == "Россия"
        assert details["locality"] == "Москва"


class TestBuildOffersCreateRequest:
    def test_merchant_id_forwarded_when_configured(self) -> None:
        body = build_offers_create_request(
            _booking_request(), {"merchant_id": "merchant-42"}
        )
        assert body["info"]["merchant_id"] == "merchant-42"
        assert body["info"]["operator_request_id"]

    def test_merchant_id_omitted_when_absent(self) -> None:
        body = build_offers_create_request(_booking_request(), {})
        assert "merchant_id" not in body["info"]

    def test_recipient_phone_has_no_leading_plus(self) -> None:
        body = build_offers_create_request(_booking_request(), {})
        assert body["recipient_info"]["phone"] == "79951234567"

    def test_courier_destination_carries_country_display_name(self) -> None:
        body = build_offers_create_request(
            _booking_request(delivery_type=DeliveryType.COURIER), {}
        )
        assert body["destination"]["type"] == "custom_location"
        details = body["destination"]["custom_location"]["details"]
        assert details["country"] == "Россия"


class TestParsePickupPoints:
    def _raw_point(self, payment_methods: list[str]) -> dict:
        return {
            "points": [
                {
                    "id": "pvz-1",
                    "name": "ПВЗ на Пролетарском",
                    "type": "pickup_point",
                    "position": {"latitude": 55.66, "longitude": 37.51},
                    "address": {
                        "country": "Россия",
                        "locality": "Москва",
                        "street": "Пролетарский проспект",
                        "house": "19",
                        "full_address": "Москва, Пролетарский проспект, 19",
                    },
                    "payment_methods": payment_methods,
                }
            ]
        }

    def test_country_decoded_to_iso_code(self) -> None:
        [point] = parse_pickup_points(self._raw_point(["already_paid"]))
        # Was "Россия"[:2] → "Ро"; now a proper ISO alpha-2 code.
        assert point.address.country_code == "RU"

    def test_cash_is_always_false(self) -> None:
        # Yandex "Other Day" has no cash-on-delivery payment method.
        [point] = parse_pickup_points(self._raw_point(["card_on_receipt"]))
        assert point.is_cash_allowed is False

    def test_card_allowed_for_card_on_receipt_and_postpay(self) -> None:
        # ``card_on_receipt`` and ``postpay`` are both card-based
        # payment-at-receipt; ``already_paid`` is prepaid-only.
        [with_card] = parse_pickup_points(self._raw_point(["card_on_receipt"]))
        [with_postpay] = parse_pickup_points(self._raw_point(["postpay"]))
        [prepaid_only] = parse_pickup_points(self._raw_point(["already_paid"]))
        assert with_card.is_card_allowed is True
        assert with_postpay.is_card_allowed is True
        assert prepaid_only.is_card_allowed is False


class TestBuildPickupPointsRequest:
    def test_geo_id_bounds_the_request(self) -> None:
        body = build_pickup_points_request(PickupPointQuery(city="Москва"), geo_id=213)
        assert body == {"geo_id": 213}

    def test_lat_lng_box_still_supported(self) -> None:
        body = build_pickup_points_request(
            PickupPointQuery(latitude=55.75, longitude=37.61, radius_km=5)
        )
        assert "latitude" in body and "longitude" in body
        assert body["latitude"]["from"] < 55.75 < body["latitude"]["to"]

    def test_geo_id_and_box_combine(self) -> None:
        body = build_pickup_points_request(
            PickupPointQuery(latitude=55.75, longitude=37.61), geo_id=213
        )
        assert body["geo_id"] == 213
        assert "latitude" in body

    def test_unbounded_query_rejected(self) -> None:
        # City alone is not a valid filter — without a resolved geo_id the
        # request would pull the whole catalogue.
        with pytest.raises(ValueError, match="latitude"):
            build_pickup_points_request(PickupPointQuery(city="Москва"))


class TestParseTrackingHistory:
    def test_unknown_status_stays_non_terminal(self) -> None:
        data = {
            "state_history": [
                {
                    "status": "SOME_FUTURE_STATUS",
                    "description": "Новый статус Яндекса",
                    "timestamp_utc": "2026-01-18T07:00:00.000000Z",
                }
            ]
        }
        [event] = parse_tracking_history(data)
        assert event.status is TrackingStatus.IN_TRANSIT
        # Raw code is preserved verbatim for triage.
        assert event.provider_status_code == "SOME_FUTURE_STATUS"

    def test_known_status_maps_through(self) -> None:
        data = {
            "state_history": [
                {
                    "status": "DELIVERY_DELIVERED",
                    "description": "Заказ вручен",
                    "timestamp_utc": "2026-01-18T15:00:00.000000Z",
                }
            ]
        }
        [event] = parse_tracking_history(data)
        assert event.status is TrackingStatus.DELIVERED


class TestParseEditableActions:
    def test_parses_full_available_actions(self) -> None:
        data = {
            "request": {
                "available_actions": {
                    "update_recipient": True,
                    "update_address_available": False,
                    "update_dates_available": True,
                    "update_items": False,
                    "update_places": True,
                }
            }
        }
        assert parse_editable_actions(data) == EditableActions(
            update_recipient=True,
            update_address=False,
            update_dates=True,
            update_items=False,
            update_places=True,
        )

    def test_missing_flags_default_to_true(self) -> None:
        # A gap in the carrier payload must never block an edit.
        actions = parse_editable_actions({"request": {"available_actions": {}}})
        assert actions == EditableActions()  # every flag True

    def test_malformed_payload_degrades_to_all_true(self) -> None:
        default = EditableActions()
        assert parse_editable_actions({}) == default
        assert parse_editable_actions({"request": {}}) == default
        assert (
            parse_editable_actions({"request": {"available_actions": None}}) == default
        )
        assert parse_editable_actions({"request": "broken"}) == default
