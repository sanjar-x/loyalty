"""Domain unit tests for ``ProductPricingProfile``."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.events import (
    ProductPricingProfileCreatedEvent,
    ProductPricingProfileDeletedEvent,
    ProductPricingProfileUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import PricingProfileValidationError
from src.modules.pricing.domain.value_objects import ProfileStatus

pytestmark = pytest.mark.unit


def _actor() -> uuid.UUID:
    return uuid.uuid4()


def _product() -> uuid.UUID:
    return uuid.uuid4()


class TestCreate:
    def test_create_sets_defaults_and_emits_created_event(self) -> None:
        actor = _actor()
        product_id = _product()
        profile = ProductPricingProfile.create(
            product_id=product_id,
            values={"purchase_price_cny": Decimal("199.50")},
            actor_id=actor,
        )

        assert profile.product_id == product_id
        assert profile.status is ProfileStatus.DRAFT
        assert profile.version_lock == 0
        assert profile.is_deleted is False
        assert profile.updated_by == actor
        assert profile.values == {"purchase_price_cny": Decimal("199.50")}

        events = profile.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ProductPricingProfileCreatedEvent)
        assert event.product_id == product_id
        assert event.values == {"purchase_price_cny": "199.50"}

    def test_create_with_empty_values_is_allowed(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(), values={}, actor_id=_actor()
        )
        assert profile.values == {}

    def test_create_rejects_invalid_variable_code(self) -> None:
        with pytest.raises(PricingProfileValidationError):
            ProductPricingProfile.create(
                product_id=_product(),
                values={"BadCode": Decimal("1")},
                actor_id=_actor(),
            )

    def test_create_rejects_non_decimal_value(self) -> None:
        with pytest.raises(PricingProfileValidationError):
            ProductPricingProfile.create(
                product_id=_product(),
                values={"price": 1.23},  # type: ignore[dict-item]
                actor_id=_actor(),
            )

    def test_create_rejects_non_finite_decimal(self) -> None:
        with pytest.raises(PricingProfileValidationError):
            ProductPricingProfile.create(
                product_id=_product(),
                values={"price": Decimal("NaN")},
                actor_id=_actor(),
            )


class TestUpdateValues:
    def test_update_replaces_values_and_bumps_version(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(),
            values={"a": Decimal("1")},
            actor_id=_actor(),
        )
        profile.clear_domain_events()

        new_actor = _actor()
        profile.update_values(
            values={"b": Decimal("2"), "c": Decimal("3")},
            actor_id=new_actor,
        )

        assert profile.values == {"b": Decimal("2"), "c": Decimal("3")}
        assert profile.version_lock == 1
        assert profile.updated_by == new_actor
        events = profile.domain_events
        assert len(events) == 1
        assert isinstance(events[0], ProductPricingProfileUpdatedEvent)

    def test_update_with_status_changes_status(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(), values={}, actor_id=_actor()
        )
        profile.update_values(values={}, actor_id=_actor(), status=ProfileStatus.READY)
        assert profile.status is ProfileStatus.READY

    def test_update_without_context_id_provided_preserves_existing(self) -> None:
        original_ctx = uuid.uuid4()
        profile = ProductPricingProfile.create(
            product_id=_product(),
            values={},
            actor_id=_actor(),
            context_id=original_ctx,
        )
        profile.update_values(values={"a": Decimal("1")}, actor_id=_actor())
        assert profile.context_id == original_ctx

    def test_update_with_context_id_provided_none_clears_it(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(),
            values={},
            actor_id=_actor(),
            context_id=uuid.uuid4(),
        )
        profile.update_values(
            values={},
            actor_id=_actor(),
            context_id=None,
            context_id_provided=True,
        )
        assert profile.context_id is None

    def test_update_rejects_invalid_values(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(), values={}, actor_id=_actor()
        )
        with pytest.raises(PricingProfileValidationError):
            profile.update_values(values={"BAD": Decimal("1")}, actor_id=_actor())


class TestMarkStale:
    def test_mark_stale_transitions_and_bumps_version(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(), values={}, actor_id=_actor()
        )
        profile.clear_domain_events()

        profile.mark_stale(actor_id=_actor())
        assert profile.status is ProfileStatus.STALE
        assert profile.version_lock == 1
        events = profile.domain_events
        assert len(events) == 1

    def test_mark_stale_is_idempotent(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(),
            values={},
            actor_id=_actor(),
            status=ProfileStatus.STALE,
        )
        profile.clear_domain_events()

        profile.mark_stale()
        assert profile.version_lock == 0
        assert profile.domain_events == []


class TestSoftDelete:
    def test_soft_delete_sets_flag_and_emits_event(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(), values={}, actor_id=_actor()
        )
        profile.clear_domain_events()
        actor = _actor()

        profile.soft_delete(actor_id=actor)
        assert profile.is_deleted is True
        assert profile.updated_by == actor
        assert profile.version_lock == 1
        events = profile.domain_events
        assert len(events) == 1
        assert isinstance(events[0], ProductPricingProfileDeletedEvent)

    def test_soft_delete_is_idempotent(self) -> None:
        profile = ProductPricingProfile.create(
            product_id=_product(), values={}, actor_id=_actor()
        )
        profile.clear_domain_events()
        profile.soft_delete()
        profile.clear_domain_events()

        profile.soft_delete()
        assert profile.version_lock == 1
        assert profile.domain_events == []
