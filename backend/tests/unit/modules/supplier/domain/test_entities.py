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
            region="Moscow",
        )
        assert supplier.name == "Moscow Supplier"
        assert supplier.type == SupplierType.LOCAL
        assert supplier.region == "Moscow"
        assert supplier.is_active is True
        assert supplier.version == 1
        assert len(supplier.domain_events) == 1
        assert supplier.domain_events[0].event_type == "supplier.created"

    def test_create_cross_border_supplier(self):
        supplier = Supplier.create(
            name="Poizon",
            supplier_type=SupplierType.CROSS_BORDER,
            region="China",
        )
        assert supplier.type == SupplierType.CROSS_BORDER

    def test_create_with_fixed_id(self):
        fixed_id = uuid.uuid4()
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="SPB",
            supplier_id=fixed_id,
        )
        assert supplier.id == fixed_id

    def test_create_empty_name_raises(self):
        with pytest.raises(ValueError, match="name is required"):
            Supplier.create(name="", supplier_type=SupplierType.LOCAL, region="Moscow")

    def test_create_empty_region_raises(self):
        with pytest.raises(ValueError, match="region is required"):
            Supplier.create(name="Test", supplier_type=SupplierType.LOCAL, region="")

    def test_create_strips_whitespace(self):
        supplier = Supplier.create(
            name="  Spaced  ", supplier_type=SupplierType.LOCAL, region="  Moscow  ",
        )
        assert supplier.name == "Spaced"
        assert supplier.region == "Moscow"


class TestSupplierUpdate:
    def test_update_name(self):
        supplier = Supplier.create(
            name="Old Name", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.clear_domain_events()
        supplier.update(name="New Name")
        assert supplier.name == "New Name"
        assert len(supplier.domain_events) == 1
        assert supplier.domain_events[0].event_type == "supplier.updated"

    def test_update_region(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.update(region="SPB")
        assert supplier.region == "SPB"

    def test_update_unknown_field_raises(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            supplier.update(type=SupplierType.CROSS_BORDER)


class TestSupplierTypeImmutability:
    def test_type_cannot_be_changed_after_creation(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        with pytest.raises(AttributeError, match="immutable"):
            supplier.type = SupplierType.CROSS_BORDER


class TestSupplierActivation:
    def test_deactivate(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.clear_domain_events()
        supplier.deactivate()
        assert supplier.is_active is False
        assert supplier.domain_events[0].event_type == "supplier.deactivated"

    def test_deactivate_already_inactive_raises(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.deactivate()
        with pytest.raises(SupplierAlreadyInactiveError):
            supplier.deactivate()

    def test_activate(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.deactivate()
        supplier.clear_domain_events()
        supplier.activate()
        assert supplier.is_active is True
        assert supplier.domain_events[0].event_type == "supplier.activated"

    def test_activate_already_active_raises(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        with pytest.raises(SupplierAlreadyActiveError):
            supplier.activate()
