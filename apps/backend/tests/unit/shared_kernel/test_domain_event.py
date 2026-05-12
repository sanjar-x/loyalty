"""Tests for ``DomainEvent`` and ``ModuleDomainEvent`` base classes.

Covers:

* :class:`DomainEvent` — ``__init_subclass__`` rejects subclasses that do
  not override ``aggregate_type`` / ``event_type`` (unless explicitly
  declared abstract).
* :class:`ModuleDomainEvent` — declarative ``required_fields`` /
  ``aggregate_id_field`` validation and integrity checks at class
  declaration time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from shared.interfaces.entities import DomainEvent, ModuleDomainEvent

# ---------------------------------------------------------------------------
# DomainEvent — concrete-subclass integrity check
# ---------------------------------------------------------------------------


class TestDomainEventInitSubclass:
    def test_rejects_subclass_without_aggregate_type(self) -> None:
        with pytest.raises(
            TypeError, match="must override 'aggregate_type' and 'event_type'"
        ):

            class BadEvent(DomainEvent):
                event_type: str = "SomeEvent"

    def test_rejects_subclass_without_event_type(self) -> None:
        with pytest.raises(
            TypeError, match="must override 'aggregate_type' and 'event_type'"
        ):

            class BadEvent(DomainEvent):
                aggregate_type: str = "SomeAggregate"

    def test_rejects_subclass_with_both_empty(self) -> None:
        with pytest.raises(
            TypeError, match="must override 'aggregate_type' and 'event_type'"
        ):

            class BadEvent(DomainEvent):
                pass

    def test_accepts_valid_subclass(self) -> None:
        @dataclass(frozen=True)
        class GoodEvent(DomainEvent):
            aggregate_type: str = "TestAggregate"
            event_type: str = "GoodEvent"

        event = GoodEvent()
        assert event.aggregate_type == "TestAggregate"
        assert event.event_type == "GoodEvent"
        assert isinstance(event.event_id, uuid.UUID)

    def test_abstract_intermediate_skips_check(self) -> None:
        """``abstract=True`` lets intermediate bases omit the defaults."""

        class IntermediateEvent(DomainEvent, abstract=True):
            pass

        assert IntermediateEvent.__abstract_event__ is True


# ---------------------------------------------------------------------------
# ModuleDomainEvent — declarative validation contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SampleModuleEvent(ModuleDomainEvent, abstract=True):
    """Reusable abstract base for unit tests.

    Provides non-empty defaults for ``aggregate_type`` and ``event_type``
    so that concrete subclasses pass :class:`DomainEvent`'s integrity
    check; the ``ModuleDomainEvent``-level guard then verifies that the
    subclass *itself* declared its own ``event_type`` (not just inherited
    the placeholder).
    """

    aggregate_type: str = "sample"
    event_type: str = "_SampleModuleEvent"


class TestModuleDomainEventValidation:
    def test_required_field_none_raises_on_construction(self) -> None:
        @dataclass(frozen=True)
        class SampleCreatedEvent(
            _SampleModuleEvent,
            required_fields=("entity_id",),
            aggregate_id_field="entity_id",
        ):
            entity_id: uuid.UUID | None = None
            event_type: str = "SampleCreatedEvent"

        with pytest.raises(ValueError, match="entity_id is required"):
            SampleCreatedEvent()

    def test_required_field_present_constructs_successfully(self) -> None:
        @dataclass(frozen=True)
        class SampleCreatedEvent(
            _SampleModuleEvent,
            required_fields=("entity_id",),
            aggregate_id_field="entity_id",
        ):
            entity_id: uuid.UUID | None = None
            event_type: str = "SampleCreatedEvent"

        entity_id = uuid.uuid4()
        event = SampleCreatedEvent(entity_id=entity_id)
        assert event.aggregate_id == str(entity_id)
        assert event.aggregate_type == "sample"
        assert event.event_type == "SampleCreatedEvent"

    def test_aggregate_id_auto_filled_from_named_field(self) -> None:
        @dataclass(frozen=True)
        class SampleEvent(
            _SampleModuleEvent,
            required_fields=("payload_id",),
            aggregate_id_field="payload_id",
        ):
            payload_id: uuid.UUID | None = None
            event_type: str = "SampleEvent"

        payload_id = uuid.uuid4()
        event = SampleEvent(payload_id=payload_id)
        assert event.aggregate_id == str(payload_id)

    def test_explicit_aggregate_id_is_preserved(self) -> None:
        @dataclass(frozen=True)
        class SampleEvent(
            _SampleModuleEvent,
            required_fields=("payload_id",),
            aggregate_id_field="payload_id",
        ):
            payload_id: uuid.UUID | None = None
            event_type: str = "SampleEvent"

        payload_id = uuid.uuid4()
        explicit = "explicitly-set"
        event = SampleEvent(payload_id=payload_id, aggregate_id=explicit)
        assert event.aggregate_id == explicit

    def test_required_fields_without_event_type_override_rejected(self) -> None:
        with pytest.raises(
            TypeError,
            match="declares required_fields but does not override 'event_type'",
        ):

            @dataclass(frozen=True)
            class BadEvent(
                _SampleModuleEvent,
                required_fields=("entity_id",),
                aggregate_id_field="entity_id",
            ):
                entity_id: uuid.UUID | None = None
                # missing: event_type override

    def test_multiple_required_fields_validated_together(self) -> None:
        @dataclass(frozen=True)
        class MultiFieldEvent(
            _SampleModuleEvent,
            required_fields=("entity_id", "actor_id"),
            aggregate_id_field="entity_id",
        ):
            entity_id: uuid.UUID | None = None
            actor_id: uuid.UUID | None = None
            event_type: str = "MultiFieldEvent"

        # missing actor_id
        with pytest.raises(ValueError, match="actor_id is required"):
            MultiFieldEvent(entity_id=uuid.uuid4())

        # both supplied
        event = MultiFieldEvent(entity_id=uuid.uuid4(), actor_id=uuid.uuid4())
        assert event.aggregate_id == str(event.entity_id)
