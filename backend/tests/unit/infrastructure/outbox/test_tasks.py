# tests/unit/infrastructure/outbox/test_tasks.py
"""Tests for Outbox TaskIQ tasks: _build_labels, event handler registrations,
outbox_relay_task, and outbox_pruning_task."""

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.outbox.relay import _EVENT_HANDLERS
from src.infrastructure.outbox.tasks import (
    _build_labels,
    outbox_pruning_task,
    outbox_relay_task,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# _build_labels
# ---------------------------------------------------------------------------


class TestBuildLabels:
    async def test_build_labels_with_correlation_id(self):
        result = _build_labels("abc")
        assert result == {"correlation_id": "abc"}

    async def test_build_labels_without_correlation_id(self):
        result = _build_labels(None)
        assert result == {}


# ---------------------------------------------------------------------------
# Event handler registrations
# ---------------------------------------------------------------------------


class TestEventHandlerRegistrations:
    async def test_event_handlers_registered(self):
        """After module-level registration, all 6 event types must be present."""
        expected_types = {
            "BrandCreatedEvent",
            "BrandLogoConfirmedEvent",
            "BrandLogoProcessedEvent",
            "IdentityRegisteredEvent",
            "IdentityDeactivatedEvent",
            "RoleAssignmentChangedEvent",
        }
        assert expected_types.issubset(set(_EVENT_HANDLERS.keys()))


# ---------------------------------------------------------------------------
# Unwrap TaskIQ + Dishka decorators to get the raw async functions
# ---------------------------------------------------------------------------


def _unwrap_dishka_task(task: Any) -> Callable[..., Any]:
    """Unwrap TaskIQ + Dishka decorators: task.original_func.__dishka_orig_func__"""
    return cast(Callable[..., Any], task.original_func.__dishka_orig_func__)


_relay_fn = _unwrap_dishka_task(outbox_relay_task)
_pruning_fn = _unwrap_dishka_task(outbox_pruning_task)


# ---------------------------------------------------------------------------
# outbox_relay_task
# ---------------------------------------------------------------------------


class TestOutboxRelayTask:
    async def test_outbox_relay_task_success(self):
        with patch(
            "src.infrastructure.outbox.tasks.relay_outbox_batch",
            new_callable=AsyncMock,
        ) as mock_relay:
            mock_relay.return_value = 5

            result = await _relay_fn(session_factory=AsyncMock())

            assert result == {"status": "success", "processed": 5}
            mock_relay.assert_awaited_once()

    async def test_outbox_relay_task_error(self):
        with patch(
            "src.infrastructure.outbox.tasks.relay_outbox_batch",
            new_callable=AsyncMock,
        ) as mock_relay:
            mock_relay.side_effect = RuntimeError("db connection lost")

            result = await _relay_fn(session_factory=AsyncMock())

            assert result == {"status": "error", "processed": 0}


# ---------------------------------------------------------------------------
# outbox_pruning_task
# ---------------------------------------------------------------------------


class TestOutboxPruningTask:
    async def test_outbox_pruning_task_success(self):
        with patch(
            "src.infrastructure.outbox.tasks.prune_processed_messages",
            new_callable=AsyncMock,
        ) as mock_prune:
            mock_prune.return_value = 42

            result = await _pruning_fn(session_factory=AsyncMock())

            assert result == {"status": "success", "deleted": 42}
            mock_prune.assert_awaited_once()
