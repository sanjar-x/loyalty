"""Unit tests for Supplier domain entity."""

import uuid

import pytest

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.exceptions import (
    SupplierAlreadyActiveError,
    SupplierAlreadyInactiveError,
)
from src.modules.supplier.domain.value_objects import SupplierType


class TestSupplierCreate:
    def test_create_local_supplier(self):
        supplier = Supplier.create(
            name="Moscow Supplier",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
            subdivision_code="RU-MOW",
        )
        assert supplier.name == "Moscow Supplier"
        assert supplier.type == SupplierType.LOCAL
        assert supplier.country_code == "RU"
        assert supplier.subdivision_code == "RU-MOW"
        assert supplier.is_active is True
        assert supplier.version == 1
        assert len(supplier.domain_events) == 1
        assert supplier.domain_events[0].event_type == "supplier.created"

    def test_create_cross_border_supplier(self):
        supplier = Supplier.create(
            name="Poizon",
            supplier_type=SupplierType.CROSS_BORDER,
            country_code="CN",
        )
        assert supplier.type == SupplierType.CROSS_BORDER
        assert supplier.country_code == "CN"
        assert supplier.subdivision_code is None

    def test_create_with_fixed_id(self):
        fixed_id = uuid.uuid4()
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
            supplier_id=fixed_id,
        )
        assert supplier.id == fixed_id

    def test_create_empty_name_raises(self):
        with pytest.raises(ValueError, match="name is required"):
            Supplier.create(name="", supplier_type=SupplierType.LOCAL, country_code="RU")

    def test_create_invalid_country_code_raises(self):
        with pytest.raises(ValueError, match="Invalid country_code"):
            Supplier.create(name="Test", supplier_type=SupplierType.LOCAL, country_code="X")

    def test_create_invalid_subdivision_code_raises(self):
        with pytest.raises(ValueError, match="Invalid subdivision_code"):
            Supplier.create(
                name="Test",
                supplier_type=SupplierType.LOCAL,
                country_code="RU",
                subdivision_code="INVALID",
            )

    def test_create_subdivision_country_mismatch_raises(self):
        with pytest.raises(ValueError, match="does not belong to country"):
            Supplier.create(
                name="Test",
                supplier_type=SupplierType.LOCAL,
                country_code="RU",
                subdivision_code="CN-BJ",
            )

    def test_create_strips_and_uppercases(self):
        supplier = Supplier.create(
            name="  Spaced  ",
            supplier_type=SupplierType.LOCAL,
            country_code="ru",
            subdivision_code="ru-mow",
        )
        assert supplier.name == "Spaced"
        assert supplier.country_code == "RU"
        assert supplier.subdivision_code == "RU-MOW"


class TestSupplierUpdate:
    def test_update_name(self):
        supplier = Supplier.create(
            name="Old Name",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        supplier.clear_domain_events()
        supplier.update(name="New Name")
        assert supplier.name == "New Name"
        assert len(supplier.domain_events) == 1
        assert supplier.domain_events[0].event_type == "supplier.updated"

    def test_update_country_code(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
            subdivision_code="RU-MOW",
        )
        supplier.update(country_code="CN", subdivision_code=None)
        assert supplier.country_code == "CN"
        assert supplier.subdivision_code is None

    def test_update_subdivision_code(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        supplier.update(subdivision_code="RU-SPE")
        assert supplier.subdivision_code == "RU-SPE"

    def test_update_clear_subdivision(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
            subdivision_code="RU-MOW",
        )
        supplier.update(subdivision_code=None)
        assert supplier.subdivision_code is None

    def test_update_unknown_field_raises(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            supplier.update(type=SupplierType.CROSS_BORDER)


class TestSupplierTypeImmutability:
    def test_type_cannot_be_changed_after_creation(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        with pytest.raises(AttributeError, match="immutable"):
            supplier.type = SupplierType.CROSS_BORDER


class TestSupplierActivation:
    def test_deactivate(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        supplier.clear_domain_events()
        supplier.deactivate()
        assert supplier.is_active is False
        assert supplier.domain_events[0].event_type == "supplier.deactivated"

    def test_deactivate_already_inactive_raises(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        supplier.deactivate()
        with pytest.raises(SupplierAlreadyInactiveError):
            supplier.deactivate()

    def test_activate(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        supplier.deactivate()
        supplier.clear_domain_events()
        supplier.activate()
        assert supplier.is_active is True
        assert supplier.domain_events[0].event_type == "supplier.activated"

    def test_activate_already_active_raises(self):
        supplier = Supplier.create(
            name="Test",
            supplier_type=SupplierType.LOCAL,
            country_code="RU",
        )
        with pytest.raises(SupplierAlreadyActiveError):
            supplier.activate()
