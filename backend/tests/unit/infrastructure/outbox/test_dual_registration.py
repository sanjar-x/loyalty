"""REFACT-001 PR-4 outbox dual-registration acceptance test.

Each renamed event has TWO registrations in
``src.infrastructure.outbox.tasks``: one against the legacy
snake_case / dotted ``event_type`` (still present in pre-PR-4 outbox
records or slow consumer paths) and one against the canonical
PascalCase ``event_type`` introduced by the events.py migration.

Both pairs MUST resolve to the same handler -- otherwise a relay
dispatching a legacy-format event after PR-4 merge would silently fall
through to the «unknown event_type, skipping» branch and lose the
business effect.

Removed in REFACT-008 (7 days post-PR-4 merge) once snake_case shims
age out of the outbox.
"""

from __future__ import annotations

import pytest

# Importing the module side-effect-registers all handlers.
import src.infrastructure.outbox.tasks  # noqa: F401
from src.infrastructure.outbox.relay import _EVENT_HANDLERS

pytestmark = pytest.mark.unit


# ``(legacy_event_type, canonical_event_type)`` pairs that MUST share a handler.
_DUAL_REGISTRATION_PAIRS: tuple[tuple[str, str], ...] = (
    # Identity (4 pairs)
    ("identity_registered", "IdentityRegisteredEvent"),
    ("identity_deactivated", "IdentityDeactivatedEvent"),
    ("role_assignment_changed", "RoleAssignmentChangedEvent"),
    ("linked_account_created", "LinkedAccountCreatedEvent"),
    # Supplier (4 pairs)
    ("supplier.created", "SupplierCreatedEvent"),
    ("supplier.updated", "SupplierUpdatedEvent"),
    ("supplier.deactivated", "SupplierDeactivatedEvent"),
    ("supplier.activated", "SupplierActivatedEvent"),
)


@pytest.mark.parametrize(("legacy", "canonical"), _DUAL_REGISTRATION_PAIRS)
def test_legacy_and_canonical_resolve_to_same_handler(
    legacy: str, canonical: str
) -> None:
    """Both event_types must be registered AND point at the same handler."""
    assert legacy in _EVENT_HANDLERS, (
        f"Legacy event_type '{legacy}' is not registered -- pre-PR-4 "
        f"outbox records would be silently dropped (REFACT-001 PR-4)."
    )
    assert canonical in _EVENT_HANDLERS, (
        f"Canonical event_type '{canonical}' is not registered -- "
        f"post-PR-4 events would be silently dropped (REFACT-001 PR-4)."
    )
    assert _EVENT_HANDLERS[legacy] is _EVENT_HANDLERS[canonical], (
        f"Dual registration mismatch: '{legacy}' and '{canonical}' "
        f"resolve to different handlers. Both must point at the same "
        f"function so dispatch is event-name-agnostic during the "
        f"REFACT-008 transition window."
    )


def test_dual_registration_pairs_count_matches_spike() -> None:
    """Spike v3 + CC-001 fix: 4 identity + 4 supplier = 8 pairs total."""
    assert len(_DUAL_REGISTRATION_PAIRS) == 8
