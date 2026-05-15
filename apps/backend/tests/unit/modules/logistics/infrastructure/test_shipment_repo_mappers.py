"""
M-2 regression tests for ``ShipmentRepository`` ↔ domain mappers.

Two things this pins down:

* **ParcelItem round-trip preserves CDEK marked-goods fields.**
  Pre-M-2 ``_dict_to_parcel`` dropped ``marking_code``, ``brand``,
  ``material``, ``name_i18n``, ``product_url``, ``cargo_types`` on every
  ``get_by_id`` — so any retry path that rebuilt ``BookingRequest`` from
  the persisted shipment ended up with a request CDEK rejects for
  marked-goods categories (jewelry → ``cargo_type=80``, tobacco,
  footwear, international orders).

* **``_is_richer`` agrees with the aggregate's ``_has_richer_info``** —
  the persistence-side "should I upsert this event?" predicate must
  match the in-memory one or ``REPLACED`` outcomes from
  ``Shipment.append_tracking_event`` won't reach disk.
"""

from __future__ import annotations

import pytest

from src.modules.logistics.domain.value_objects import (
    Dimensions,
    Money,
    Parcel,
    ParcelItem,
    Weight,
)
from src.modules.logistics.infrastructure.repositories.shipment import (
    ShipmentRepository,
    _is_richer,
)

pytestmark = pytest.mark.unit


class TestParcelRoundTrip:
    def test_full_parcel_item_round_trip_preserves_all_fields(self) -> None:
        original = Parcel(
            weight=Weight(grams=1500),
            dimensions=Dimensions(length_cm=30, width_cm=20, height_cm=10),
            declared_value=Money(amount=500000, currency_code="RUB"),
            description="хрупкое",
            items=[
                ParcelItem(
                    name="Кольцо золотое",
                    quantity=1,
                    sku="JWL-001",
                    unit_price=Money(amount=500000, currency_code="RUB"),
                    weight=Weight(grams=15),
                    country_of_origin="RU",
                    hs_code="7113190000",
                    marking_code="010468008549838921AAA0005255832",
                    brand="Sokolov",
                    material="11",
                    name_i18n="Gold Ring",
                    product_url="https://shop/jwl-001",
                    cargo_types=("80",),
                ),
            ],
        )

        as_dict = ShipmentRepository._parcel_to_dict(original)
        reloaded = ShipmentRepository._dict_to_parcel(as_dict)

        # Every field on the item survived the round-trip.
        item = reloaded.items[0]
        assert item.name == "Кольцо золотое"
        assert item.sku == "JWL-001"
        assert item.marking_code == "010468008549838921AAA0005255832"
        assert item.brand == "Sokolov"
        assert item.material == "11"
        assert item.name_i18n == "Gold Ring"
        assert item.product_url == "https://shop/jwl-001"
        assert item.country_of_origin == "RU"
        assert item.hs_code == "7113190000"
        # ``cargo_types`` was a tuple on the VO; attrs serialises tuples
        # as lists, so the loader coerces back. Confirm the result is a
        # tuple (matching the VO contract) and carries the same values.
        assert isinstance(item.cargo_types, tuple)
        assert item.cargo_types == ("80",)

    def test_minimal_parcel_item_keeps_defaults(self) -> None:
        original = Parcel(
            weight=Weight(grams=500),
            items=[ParcelItem(name="Минимальный", quantity=2)],
        )
        reloaded = ShipmentRepository._dict_to_parcel(
            ShipmentRepository._parcel_to_dict(original)
        )

        item = reloaded.items[0]
        assert item.name == "Минимальный"
        assert item.quantity == 2
        assert item.marking_code is None
        assert item.brand is None
        assert item.cargo_types == ()


class TestIsRicher:
    """``_is_richer`` must agree with ``Shipment._has_richer_info``."""

    @pytest.mark.parametrize(
        "new_val,existing_val,expected",
        [
            (None, "anything", False),
            ("", "anything", False),
            ("filled", None, True),
            ("filled", "", True),
            ("longer text", "short", True),
            ("short", "longer text", False),
            ("same length", "same length", False),
        ],
    )
    def test_predicate(
        self, new_val: str | None, existing_val: str | None, expected: bool
    ) -> None:
        assert _is_richer(new_val, existing_val) is expected
