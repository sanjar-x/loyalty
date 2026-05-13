# tests/unit/infrastructure/outbox/test_relay.py
"""Tests for Outbox Relay batch processing and pruning."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.infrastructure.outbox.relay import (
    _EVENT_HANDLERS,
    prune_processed_messages,
    register_event_handler,
    relay_outbox_batch,
)

pytestmark: MarkDecorator = pytest.mark.asyncio


def _make_row(event_id=1, event_type="TestEvent", payload=None, correlation_id=None):
    """Create a mock outbox row."""
    row = MagicMock()
    row.id = event_id
    row.event_type = event_type
    row.payload = payload or {"key": "value"}
    row.correlation_id = correlation_id
    return row


def _make_session_factory(
    fetch_rows=None,
    lock_rows=None,
    rowcount=0,
):
    """
    Build a mock async session factory.

    fetch_rows: rows returned by the initial batch fetch.
    lock_rows: per-event rows returned by the per-event lock query.
               If None, defaults to returning the corresponding fetch_row.
    """
    fetch_rows = fetch_rows or []
    call_count = 0

    async def _execute_side_effect(sql, params=None):
        nonlocal call_count
        result = MagicMock()

        sql_text = str(sql)
        if "FOR UPDATE SKIP LOCKED" in sql_text and "id = :event_id" not in sql_text:
            # Batch fetch query
            result.fetchall = MagicMock(return_value=fetch_rows)
        elif "id = :event_id" in sql_text:
            # Per-event lock query
            if lock_rows is not None:
                idx = min(call_count, len(lock_rows) - 1)
                result.fetchone = MagicMock(return_value=lock_rows[idx])
                call_count += 1
            elif fetch_rows:
                # Default: return the matching row
                eid = params.get("event_id") if params else None
                matched = next((r for r in fetch_rows if r.id == eid), fetch_rows[0])
                result.fetchone = MagicMock(return_value=matched)
            else:
                result.fetchone = MagicMock(return_value=None)
        elif "DELETE FROM outbox_messages" in sql_text:
            result.rowcount = rowcount
        else:
            # Mark processed or other queries
            result.rowcount = 1

        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute_side_effect)

    begin_ctx = AsyncMock()
    begin_ctx.__aenter__ = AsyncMock()
    begin_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=begin_ctx)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value: AsyncMock = ctx

    return factory, session


@pytest.fixture(autouse=True)
def _preserve_handlers():
    """Save and restore _EVENT_HANDLERS around each test."""
    saved = dict(_EVENT_HANDLERS)
    _EVENT_HANDLERS.clear()
    yield
    _EVENT_HANDLERS.clear()
    _EVENT_HANDLERS.update(saved)


class TestRelayOutboxBatch:
    async def test_relay_returns_zero_when_no_rows(self):
        factory, _ = _make_session_factory(fetch_rows=[])

        count = await relay_outbox_batch(session_factory=factory, batch_size=100)

        assert count == 0

    async def test_relay_processes_known_event(self):
        handler = AsyncMock()
        register_event_handler("BrandCreated", handler)

        row = _make_row(event_id=1, event_type="BrandCreated", payload={"id": "123"})
        factory, _session = _make_session_factory(fetch_rows=[row])

        count = await relay_outbox_batch(session_factory=factory, batch_size=10)

        assert count == 1
        handler.assert_awaited_once()
        # The handler should receive the payload and correlation_id
        call_kwargs = handler.call_args
        assert call_kwargs[0][0] == {"id": "123"}

    async def test_relay_skips_unknown_event_type(self):
        row = _make_row(event_id=2, event_type="UnknownEvent")
        factory, _session = _make_session_factory(fetch_rows=[row])

        count = await relay_outbox_batch(session_factory=factory, batch_size=10)

        # Unknown events are still marked as processed
        assert count == 1

    async def test_relay_continues_on_handler_error(self):
        failing_handler = AsyncMock(side_effect=RuntimeError("handler failed"))
        register_event_handler("FailingEvent", failing_handler)

        row = _make_row(event_id=3, event_type="FailingEvent")
        factory, _session = _make_session_factory(fetch_rows=[row])

        # The handler raises, but relay catches the exception and continues
        count = await relay_outbox_batch(session_factory=factory, batch_size=10)

        # The event failed so processed count is 0 (it went to failed counter)
        assert count == 0
        failing_handler.assert_awaited_once()


class TestPruneProcessedMessages:
    async def test_prune_deletes_old_records(self):
        factory, session = _make_session_factory(rowcount=42)

        # Override execute to always return rowcount for the DELETE query
        result_mock = MagicMock()
        result_mock.rowcount = 42
        session.execute = AsyncMock(return_value=result_mock)

        deleted = await prune_processed_messages(session_factory=factory)

        assert deleted == 42
        session.execute.assert_awaited_once()
