# tests/unit/modules/identity/application/consumers/test_role_events.py
"""Tests for role_events consumer (permission cache invalidation)."""

import uuid
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.identity.application.consumers.role_events import (
    invalidate_permissions_cache_on_role_change as _invalidate_task,
)


def _unwrap_dishka_task(task: Any) -> Callable[..., Any]:
    return cast(Callable[..., Any], getattr(task.original_func, "__dishka_orig_func__"))


invalidate_permissions_cache_on_role_change = _unwrap_dishka_task(_invalidate_task)

pytestmark = pytest.mark.asyncio


def _make_session_factory(session_ids=None):
    """
    Build a mock async session factory that returns the given session IDs
    when the active-sessions query is executed.
    """
    session_ids = session_ids or []

    rows = [(sid,) for sid in session_ids]
    result_mock = MagicMock()
    result_mock.all = MagicMock(return_value=rows)

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value = ctx

    return factory, session


class TestInvalidatePermissionsCacheOnRoleChange:
    async def test_invalidates_cache_for_all_active_sessions(self):
        identity_id = str(uuid.uuid4())
        sid1 = uuid.uuid4()
        sid2 = uuid.uuid4()

        factory, session = _make_session_factory(session_ids=[sid1, sid2])
        cache = AsyncMock()

        result = await invalidate_permissions_cache_on_role_change(
            identity_id=identity_id,
            cache=cache,
            session_factory=factory,
        )

        assert result["status"] == "success"
        assert result["sessions_invalidated"] == 2
        assert cache.delete.await_count == 2
        cache.delete.assert_any_await(f"perms:{sid1}")
        cache.delete.assert_any_await(f"perms:{sid2}")

    async def test_no_active_sessions(self):
        identity_id = str(uuid.uuid4())

        factory, session = _make_session_factory(session_ids=[])
        cache = AsyncMock()

        result = await invalidate_permissions_cache_on_role_change(
            identity_id=identity_id,
            cache=cache,
            session_factory=factory,
        )

        assert result["status"] == "success"
        assert result["sessions_invalidated"] == 0
        cache.delete.assert_not_awaited()
