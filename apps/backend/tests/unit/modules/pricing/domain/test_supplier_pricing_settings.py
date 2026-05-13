"""Unit tests for the ``SupplierPricingSettings`` aggregate."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.pricing.domain.entities.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.domain.events import (
    SupplierPricingSettingsCreatedEvent,
    SupplierPricingSettingsDeletedEvent,
    SupplierPricingSettingsUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import (
    SupplierPricingSettingsValidationError,
)


class TestSupplierPricingSettingsCreate:
    def test_creates_with_valid_values(self) -> None:
        supplier_id, actor_id = uuid.uuid4(), uuid.uuid4()
        settings = SupplierPricingSettings.create(
            supplier_id=supplier_id,
            values={"supplier_margin": Decimal("0.12")},
            actor_id=actor_id,
        )

        assert settings.supplier_id == supplier_id
        assert settings.values == {"supplier_margin": Decimal("0.12")}
        assert settings.version_lock == 0
        assert settings.updated_by == actor_id

        events = list(settings.domain_events)
        assert len(events) == 1
        evt = events[0]
        assert isinstance(evt, SupplierPricingSettingsCreatedEvent)
        assert evt.supplier_id == supplier_id
        assert evt.values == {"supplier_margin": "0.12"}

    def test_empty_values_is_allowed(self) -> None:
        settings = SupplierPricingSettings.create(
            supplier_id=uuid.uuid4(),
            values={},
            actor_id=uuid.uuid4(),
        )
        assert settings.values == {}

    def test_rejects_invalid_variable_code(self) -> None:
        with pytest.raises(SupplierPricingSettingsValidationError) as exc:
            SupplierPricingSettings.create(
                supplier_id=uuid.uuid4(),
                values={"Invalid-Code": Decimal("1")},
                actor_id=uuid.uuid4(),
            )
        assert exc.value.error_code == "PRICING_SUPPLIER_SETTINGS_VARIABLE_CODE_INVALID"

    def test_rejects_non_decimal_value(self) -> None:
        with pytest.raises(SupplierPricingSettingsValidationError) as exc:
            SupplierPricingSettings.create(
                supplier_id=uuid.uuid4(),
                values={"ok": 1.5},  # ty: ignore[invalid-argument-type]
                actor_id=uuid.uuid4(),
            )
        assert exc.value.error_code == "PRICING_SUPPLIER_SETTINGS_DECIMAL_TYPE"

    def test_rejects_non_finite_decimal(self) -> None:
        with pytest.raises(SupplierPricingSettingsValidationError) as exc:
            SupplierPricingSettings.create(
                supplier_id=uuid.uuid4(),
                values={"ok": Decimal("Infinity")},
                actor_id=uuid.uuid4(),
            )
        assert exc.value.error_code == "PRICING_SUPPLIER_SETTINGS_DECIMAL_NOT_FINITE"

    def test_rejects_too_many_values(self) -> None:
        oversized = {f"v{i}": Decimal(i) for i in range(200)}
        with pytest.raises(SupplierPricingSettingsValidationError) as exc:
            SupplierPricingSettings.create(
                supplier_id=uuid.uuid4(),
                values=oversized,
                actor_id=uuid.uuid4(),
            )
        assert exc.value.error_code == "PRICING_SUPPLIER_SETTINGS_VALUES_TOO_LARGE"


class TestSupplierPricingSettingsReplace:
    def _build(self) -> tuple[SupplierPricingSettings, uuid.UUID]:
        actor_id = uuid.uuid4()
        settings = SupplierPricingSettings.create(
            supplier_id=uuid.uuid4(),
            values={"aa": Decimal("1")},
            actor_id=actor_id,
        )
        settings.clear_domain_events()
        return settings, actor_id

    def test_replace_updates_values_and_bumps_version(self) -> None:
        settings, _ = self._build()
        other = uuid.uuid4()
        settings.replace(values={"bb": Decimal("2")}, actor_id=other)

        assert settings.values == {"bb": Decimal("2")}
        assert settings.version_lock == 1
        assert settings.updated_by == other

        events = list(settings.domain_events)
        assert len(events) == 1
        assert isinstance(events[0], SupplierPricingSettingsUpdatedEvent)
        assert events[0].values == {"bb": "2"}

    def test_replace_validates_input(self) -> None:
        settings, actor_id = self._build()
        with pytest.raises(SupplierPricingSettingsValidationError):
            settings.replace(values={"BAD": Decimal("1")}, actor_id=actor_id)
        # unchanged
        assert settings.values == {"aa": Decimal("1")}
        assert settings.version_lock == 0


class TestSupplierPricingSettingsMarkDeleted:
    def test_emits_deleted_event(self) -> None:
        settings = SupplierPricingSettings.create(
            supplier_id=uuid.uuid4(),
            values={},
            actor_id=uuid.uuid4(),
        )
        settings.clear_domain_events()
        actor_id = uuid.uuid4()
        settings.mark_deleted(actor_id=actor_id)

        events = list(settings.domain_events)
        assert len(events) == 1
        assert isinstance(events[0], SupplierPricingSettingsDeletedEvent)
        assert events[0].supplier_id == settings.supplier_id
        assert events[0].updated_by == actor_id
