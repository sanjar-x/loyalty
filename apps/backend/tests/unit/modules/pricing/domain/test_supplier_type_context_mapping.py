"""Unit tests for ``SupplierTypeContextMapping`` aggregate."""

from __future__ import annotations

import uuid

import pytest

from src.modules.pricing.domain.entities.supplier_type_context_mapping import (
    SupplierTypeContextMapping,
)
from src.modules.pricing.domain.events import (
    SupplierTypeContextMappingCreatedEvent,
    SupplierTypeContextMappingDeletedEvent,
    SupplierTypeContextMappingUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import (
    SupplierTypeContextMappingValidationError,
)

ACTOR = uuid.uuid4()


class TestCreate:
    def test_create_emits_created_event(self) -> None:
        ctx = uuid.uuid4()
        m = SupplierTypeContextMapping.create(
            supplier_type="cross_border",
            context_id=ctx,
            actor_id=ACTOR,
        )

        assert m.supplier_type == "cross_border"
        assert m.context_id == ctx
        assert m.version_lock == 0
        assert m.updated_by == ACTOR
        events = m.domain_events
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, SupplierTypeContextMappingCreatedEvent)
        assert ev.supplier_type == "cross_border"
        assert ev.context_id == ctx

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "Cross_Border",  # uppercase
            "1local",  # leading digit
            "_local",  # leading underscore
            "has space",
            "has-dash",
            "a" * 65,  # too long
            "локал",  # non-ascii
        ],
    )
    def test_create_rejects_invalid_supplier_type(self, bad: str) -> None:
        with pytest.raises(SupplierTypeContextMappingValidationError):
            SupplierTypeContextMapping.create(
                supplier_type=bad,
                context_id=uuid.uuid4(),
                actor_id=ACTOR,
            )

    @pytest.mark.parametrize(
        "good",
        ["a", "local", "cross_border", "a1_b2", "x" + "y" * 63],
    )
    def test_create_accepts_valid_supplier_type(self, good: str) -> None:
        m = SupplierTypeContextMapping.create(
            supplier_type=good,
            context_id=uuid.uuid4(),
            actor_id=ACTOR,
        )
        assert m.supplier_type == good


class TestChangeContext:
    def _fresh(self) -> SupplierTypeContextMapping:
        m = SupplierTypeContextMapping.create(
            supplier_type="local",
            context_id=uuid.uuid4(),
            actor_id=ACTOR,
        )
        m.clear_domain_events()
        return m

    def test_change_context_bumps_version_and_emits_event(self) -> None:
        m = self._fresh()
        old_ctx = m.context_id
        old_version = m.version_lock
        old_updated_at = m.updated_at

        new_ctx = uuid.uuid4()
        new_actor = uuid.uuid4()
        m.change_context(new_context_id=new_ctx, actor_id=new_actor)

        assert m.context_id == new_ctx
        assert m.version_lock == old_version + 1
        assert m.updated_by == new_actor
        assert m.updated_at >= old_updated_at

        events = m.domain_events
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, SupplierTypeContextMappingUpdatedEvent)
        assert ev.previous_context_id == old_ctx
        assert ev.context_id == new_ctx
        assert ev.supplier_type == "local"

    def test_change_context_noop_when_same(self) -> None:
        m = self._fresh()
        same_ctx = m.context_id
        v = m.version_lock

        m.change_context(new_context_id=same_ctx, actor_id=ACTOR)

        assert m.version_lock == v
        assert m.domain_events == []


class TestMarkDeleted:
    def test_mark_deleted_emits_event(self) -> None:
        m = SupplierTypeContextMapping.create(
            supplier_type="local",
            context_id=uuid.uuid4(),
            actor_id=ACTOR,
        )
        m.clear_domain_events()

        actor = uuid.uuid4()
        m.mark_deleted(actor_id=actor)

        events = m.domain_events
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, SupplierTypeContextMappingDeletedEvent)
        assert ev.mapping_id == m.id
        assert ev.supplier_type == "local"
        assert ev.updated_by == actor
