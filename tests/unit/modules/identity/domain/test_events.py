# tests/unit/modules/identity/domain/test_events.py
"""Tests for Identity domain events — field population and __post_init__ validators."""

import uuid
from datetime import datetime

import pytest

from src.modules.identity.domain.events import (
    IdentityDeactivatedEvent,
    IdentityRegisteredEvent,
    RoleAssignmentChangedEvent,
)


class TestIdentityRegisteredEvent:
    def test_fields_populated(self):
        event = IdentityRegisteredEvent(
            identity_id=uuid.uuid4(),
            email="test@example.com",
        )
        assert event.aggregate_type == "Identity"
        assert event.event_type == "IdentityRegisteredEvent"
        assert event.email == "test@example.com"
        assert isinstance(event.registered_at, datetime)

    def test_aggregate_id_set_from_identity_id(self):
        identity_id = uuid.uuid4()
        event = IdentityRegisteredEvent(identity_id=identity_id, email="a@b.com")
        assert event.aggregate_id == str(identity_id)

    def test_raises_value_error_when_identity_id_is_none(self):
        with pytest.raises(ValueError, match="identity_id is required"):
            IdentityRegisteredEvent(identity_id=None, email="test@example.com")

    def test_auto_sets_registered_at_when_none(self):
        event = IdentityRegisteredEvent(identity_id=uuid.uuid4(), email="a@b.com")
        assert isinstance(event.registered_at, datetime)


class TestIdentityDeactivatedEvent:
    def test_fields_populated(self):
        identity_id = uuid.uuid4()
        event = IdentityDeactivatedEvent(identity_id=identity_id, reason="user_request")
        assert event.aggregate_type == "Identity"
        assert event.event_type == "IdentityDeactivatedEvent"
        assert event.reason == "user_request"
        assert isinstance(event.deactivated_at, datetime)

    def test_raises_value_error_when_identity_id_is_none(self):
        with pytest.raises(ValueError, match="identity_id is required"):
            IdentityDeactivatedEvent(identity_id=None, reason="test")

    def test_auto_sets_aggregate_id(self):
        identity_id = uuid.uuid4()
        event = IdentityDeactivatedEvent(identity_id=identity_id, reason="test")
        assert event.aggregate_id == str(identity_id)

    def test_auto_sets_deactivated_at_when_none(self):
        event = IdentityDeactivatedEvent(identity_id=uuid.uuid4(), reason="test")
        assert isinstance(event.deactivated_at, datetime)


class TestRoleAssignmentChangedEvent:
    def test_assigned_action(self):
        event = RoleAssignmentChangedEvent(
            identity_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            action="assigned",
        )
        assert event.action == "assigned"
        assert event.aggregate_type == "Identity"

    def test_revoked_action(self):
        event = RoleAssignmentChangedEvent(
            identity_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            action="revoked",
        )
        assert event.action == "revoked"

    def test_raises_value_error_when_identity_id_is_none(self):
        with pytest.raises(ValueError, match="identity_id is required"):
            RoleAssignmentChangedEvent(
                identity_id=None, role_id=uuid.uuid4(), action="assigned"
            )

    def test_raises_value_error_when_role_id_is_none(self):
        with pytest.raises(ValueError, match="role_id is required"):
            RoleAssignmentChangedEvent(
                identity_id=uuid.uuid4(), role_id=None, action="assigned"
            )

    def test_auto_sets_aggregate_id(self):
        identity_id = uuid.uuid4()
        event = RoleAssignmentChangedEvent(
            identity_id=identity_id, role_id=uuid.uuid4(), action="assigned"
        )
        assert event.aggregate_id == str(identity_id)
