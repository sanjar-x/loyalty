# tests/unit/modules/identity/domain/test_events.py
"""Tests for Identity domain event field population."""

import uuid
from datetime import datetime

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


class TestIdentityDeactivatedEvent:
    def test_fields_populated(self):
        identity_id = uuid.uuid4()
        event = IdentityDeactivatedEvent(identity_id=identity_id, reason="user_request")
        assert event.aggregate_type == "Identity"
        assert event.event_type == "IdentityDeactivatedEvent"
        assert event.reason == "user_request"
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
