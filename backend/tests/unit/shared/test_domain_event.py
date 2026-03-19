# tests/unit/shared/test_domain_event.py
"""Tests for DomainEvent base class — __init_subclass__ enforcement."""

import uuid

import pytest

from src.shared.interfaces.entities import DomainEvent


class TestDomainEventInitSubclass:
    def test_rejects_subclass_without_aggregate_type(self):
        with pytest.raises(TypeError, match="must override 'aggregate_type' and 'event_type'"):

            class BadEvent(DomainEvent):
                event_type: str = "SomeEvent"

    def test_rejects_subclass_without_event_type(self):
        with pytest.raises(TypeError, match="must override 'aggregate_type' and 'event_type'"):

            class BadEvent(DomainEvent):
                aggregate_type: str = "SomeAggregate"

    def test_rejects_subclass_with_both_empty(self):
        with pytest.raises(TypeError, match="must override 'aggregate_type' and 'event_type'"):

            class BadEvent(DomainEvent):
                pass

    def test_accepts_valid_subclass(self):
        from dataclasses import dataclass

        @dataclass
        class GoodEvent(DomainEvent):
            aggregate_type: str = "TestAggregate"
            event_type: str = "GoodEvent"

        event = GoodEvent()
        assert event.aggregate_type == "TestAggregate"
        assert event.event_type == "GoodEvent"
        assert isinstance(event.event_id, uuid.UUID)
