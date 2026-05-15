"""
Phase-1 regression tests for CDEK order / calculator / tracking mappers:

* ``cdek_currency_to_iso`` + ``parse_tariff_list_response`` label quotes
  in their real currency instead of hard-coding RUB.
* ``cdek_reason_code_label`` / ``cdek_status_name`` decode Приложение 1/2
  integers; ``parse_tracking_events`` folds the reason into the
  description.
* ``build_order_request`` reads the ``cdek_order`` extras block out of
  ``provider_payload`` (seller, comment, additional order types, extra
  services, contact passport / contragent_type, per-item fields) while
  staying backward-compatible when the block is absent.
* ``parse_order_related_entities`` / ``parse_order_delivery_problems``
  extract the structured data ``BookingResult`` has no typed slot for.
"""

from __future__ import annotations

import json
import uuid

import pytest

from src.modules.logistics.domain.value_objects import (
    Address,
    BookingRequest,
    ContactInfo,
    DeliveryType,
    Money,
    Parcel,
    ParcelItem,
    TrackingStatus,
    Weight,
)
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    cdek_currency_to_iso,
    cdek_reason_code_label,
    cdek_status_name,
)
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    build_order_request,
    parse_order_delivery_problems,
    parse_order_related_entities,
    parse_tariff_list_response,
    parse_tracking_events,
)

pytestmark = pytest.mark.unit


class TestCurrency:
    @pytest.mark.parametrize(
        "numeric,expected",
        [(1, "RUB"), (2, "KZT"), (6, "CNY"), (55, "JPY"), ("2", "KZT")],
    )
    def test_numeric_code_maps_to_iso(self, numeric: int | str, expected: str) -> None:
        assert cdek_currency_to_iso(numeric) == expected

    @pytest.mark.parametrize("bad", [None, 999, "x", ""])
    def test_unknown_falls_back_to_rub(self, bad: int | str | None) -> None:
        assert cdek_currency_to_iso(bad) == "RUB"

    def test_tariff_list_labels_quotes_in_requested_currency(self) -> None:
        data = {
            "tariff_codes": [
                {
                    "tariff_code": 136,
                    "tariff_name": "Посылка склад-склад",
                    "delivery_mode": 1,
                    "delivery_sum": 450.0,
                    "period_min": 2,
                    "period_max": 4,
                }
            ]
        }

        kzt_quotes = parse_tariff_list_response(data, requested_currency_iso="KZT")
        assert kzt_quotes[0].rate.total_cost.currency_code == "KZT"
        assert kzt_quotes[0].rate.base_cost.currency_code == "KZT"

    def test_tariff_list_defaults_to_rub(self) -> None:
        data = {"tariff_codes": [{"tariff_code": 136, "delivery_sum": 450.0}]}
        quotes = parse_tariff_list_response(data)
        assert quotes[0].rate.total_cost.currency_code == "RUB"


class TestReasonAndStatusLabels:
    @pytest.mark.parametrize(
        "code,expected",
        [
            ("3", "Возврат: адресат не проживает"),
            (11, "Отказ от получения: без объяснения"),
            ("24", "Возврат: не прошёл таможню"),
        ],
    )
    def test_reason_code_label_known(self, code: str | int, expected: str) -> None:
        assert cdek_reason_code_label(code) == expected

    @pytest.mark.parametrize("bad", [None, "", "999"])
    def test_reason_code_label_unknown(self, bad: str | None) -> None:
        assert cdek_reason_code_label(bad) is None

    def test_status_name_known_and_fallback(self) -> None:
        assert cdek_status_name("DELIVERED") == "Вручён"
        assert cdek_status_name("MYSTERY") == "MYSTERY"
        assert cdek_status_name("MYSTERY", fallback="x") == "x"

    def test_tracking_events_fold_reason_into_description(self) -> None:
        statuses = [
            {
                "code": "NOT_DELIVERED",
                "name": "Не вручен",
                "date_time": "2026-05-01T10:00:00+03:00",
                "reason_code": "11",
                "city": "Москва",
            }
        ]

        events = parse_tracking_events(statuses)

        assert events[0].status is TrackingStatus.EXCEPTION
        assert events[0].provider_status_name == "Не вручен"
        assert events[0].description == (
            "Не вручен — Отказ от получения: без объяснения"
        )

    def test_tracking_events_fall_back_to_name_map(self) -> None:
        statuses = [{"code": "DELIVERED", "date_time": "2026-05-01T10:00:00+03:00"}]
        events = parse_tracking_events(statuses)
        assert events[0].provider_status_name == "Вручён"
        assert events[0].description == "Вручён"


def _booking_request(provider_payload: str) -> BookingRequest:
    return BookingRequest(
        shipment_id=uuid.uuid4(),
        origin=Address(country_code="RU", city="Москва"),
        destination=Address(country_code="RU", city="Санкт-Петербург"),
        sender=ContactInfo(first_name="Иван", last_name="Петров", phone="+79991112233"),
        recipient=ContactInfo(
            first_name="Пётр", last_name="Сидоров", phone="+79994445566"
        ),
        parcels=[
            Parcel(
                weight=Weight(grams=1000),
                items=[ParcelItem(name="Кольцо", sku="SKU-1", quantity=1)],
            )
        ],
        service_code="136",
        delivery_type=DeliveryType.COURIER,
        provider_payload=provider_payload,
    )


class TestBuildOrderRequest:
    def test_reads_cdek_order_extras_block(self) -> None:
        request = _booking_request(
            json.dumps(
                {
                    "tariff_code": 136,
                    "cdek_order": {
                        "comment": "хрупкое",
                        "additional_order_types": [15, "2"],
                        "seller": {"name": "ООО Продавец", "inn": "1234567890"},
                        "delivery_recipient_cost": {"value": 0},
                        "services": [{"code": "SMS", "parameter": "+79991112233"}],
                        "recipient": {
                            "contragent_type": "INDIVIDUAL",
                            "passport_series": "4509",
                        },
                        "items": {
                            "SKU-1": {"weight_gross": 1200, "jewel_uin": "UIN-42"}
                        },
                    },
                }
            )
        )

        body = build_order_request(request)

        assert body["tariff_code"] == 136
        assert body["comment"] == "хрупкое"
        assert body["additional_order_types"] == [15, 2]
        assert body["seller"] == {"name": "ООО Продавец", "inn": "1234567890"}
        assert body["delivery_recipient_cost"] == {"value": 0}
        assert {"code": "SMS", "parameter": "+79991112233"} in body["services"]
        assert body["recipient"]["contragent_type"] == "INDIVIDUAL"
        assert body["recipient"]["passport_series"] == "4509"
        item = body["packages"][0]["items"][0]
        assert item["weight_gross"] == 1200
        assert item["jewel_uin"] == "UIN-42"

    def test_backward_compatible_without_extras(self) -> None:
        body = build_order_request(_booking_request(json.dumps({"tariff_code": 136})))

        assert body["tariff_code"] == 136
        assert "comment" not in body
        assert "seller" not in body
        assert "additional_order_types" not in body
        # No extras → no item-level CDEK-only fields leak in.
        assert "weight_gross" not in body["packages"][0]["items"][0]

    def test_extra_services_merge_with_cod(self) -> None:
        request = _booking_request(
            json.dumps(
                {
                    "tariff_code": 136,
                    "cdek_order": {"services": [{"code": "DANGER_CARGO"}]},
                }
            )
        )
        # COD attached on the domain VO must coexist with extras services.
        request = BookingRequest(
            shipment_id=request.shipment_id,
            origin=request.origin,
            destination=request.destination,
            sender=request.sender,
            recipient=request.recipient,
            parcels=request.parcels,
            service_code=request.service_code,
            delivery_type=request.delivery_type,
            provider_payload=request.provider_payload,
            cod=request.cod,
            declared_value=Money(amount=500000, currency_code="RUB"),
        )

        body = build_order_request(request)
        codes = {svc["code"] for svc in body["services"]}
        assert "DANGER_CARGO" in codes
        assert "INSURANCE" in codes


class TestParseOrderHelpers:
    def test_related_entities_normalised(self) -> None:
        data = {
            "entity": {
                "related_entities": [
                    {
                        "type": "return_order",
                        "cdek_number": "555",
                        "uuid": "ret-uuid",
                    },
                    {"type": "waybill", "url": "http://x/wb.pdf", "uuid": "wb-uuid"},
                    "garbage",
                    {},
                ]
            }
        }

        result = parse_order_related_entities(data)

        assert len(result) == 2
        assert result[0]["type"] == "return_order"
        assert result[0]["cdek_number"] == "555"
        assert result[1]["url"] == "http://x/wb.pdf"

    def test_delivery_problems_decoded(self) -> None:
        entity = {
            "delivery_problem": [
                {"code": "13", "create_date": "2026-05-01"},
                {"code": "999"},
            ]
        }

        # Works on both the bare entity and the full {"entity": ...} payload.
        for payload in (entity, {"entity": entity}):
            result = parse_order_delivery_problems(payload)
            assert result[0]["code"] == "13"
            assert result[0]["label"] == "Контактное лицо отсутствует"
            assert result[1]["label"] == "999"

    def test_helpers_tolerate_missing_data(self) -> None:
        assert parse_order_related_entities({}) == []
        assert parse_order_related_entities({"entity": {}}) == []
        assert parse_order_delivery_problems({}) == []
