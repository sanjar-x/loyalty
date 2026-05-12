# tests/unit/infrastructure/logging/test_dlq_middleware.py
"""Tests for DLQ (Dead Letter Queue) Middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from _pytest.mark.structures import MarkDecorator
from taskiq import TaskiqMessage, TaskiqResult

from src.infrastructure.logging.dlq_middleware import DLQMiddleware

pytestmark: MarkDecorator = pytest.mark.asyncio


def _make_message(
    task_id: str = "test-task-id",
    task_name: str = "test_task",
    retries: str = "0",
    max_retries: str = "3",
) -> TaskiqMessage:
    return TaskiqMessage(
        task_id=task_id,
        task_name=task_name,
        labels={"_retries": retries, "max_retries": max_retries},
        args=[],
        kwargs={},
    )


def _make_result(
    is_err: bool = False,
    error: Exception | None = None,
) -> TaskiqResult:
    return TaskiqResult(
        is_err=is_err,
        return_value=None,
        execution_time=1.0,
        error=error,
    )


def _make_middleware():
    """Create DLQMiddleware with a mocked session factory."""
    session = AsyncMock()
    # session.add is synchronous in SQLAlchemy, so use MagicMock
    session.add = MagicMock()

    begin_ctx = AsyncMock()
    begin_ctx.__aenter__ = AsyncMock()
    begin_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=begin_ctx)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value: AsyncMock = ctx

    middleware = DLQMiddleware(session_factory=factory)
    return middleware, session, factory


class TestDLQMiddlewarePostExecute:
    async def test_post_execute_skips_successful_task(self):
        middleware, session, _ = _make_middleware()
        message: TaskiqMessage = _make_message()
        result = _make_result(is_err=False)

        await middleware.post_execute(message, result)

        session.add.assert_not_called()

    async def test_post_execute_skips_retriable_task(self):
        middleware, session, _ = _make_middleware()
        message: TaskiqMessage = _make_message(retries="1", max_retries="3")
        result = _make_result(is_err=True, error=ValueError("retry me"))

        await middleware.post_execute(message, result)

        # retry_count (1) < max_retries (3), so no DB write
        session.add.assert_not_called()

    async def test_post_execute_saves_failed_task(self):
        middleware, session, _ = _make_middleware()
        message: TaskiqMessage = _make_message(retries="3", max_retries="3")
        error = ValueError("final failure")
        result = _make_result(is_err=True, error=error)

        await middleware.post_execute(message, result)

        # retry_count (3) >= max_retries (3), so the task should be saved
        session.add.assert_called_once()
        failed_task = session.add.call_args[0][0]
        assert failed_task.task_name == "test_task"
        assert failed_task.task_id == "test-task-id"
        assert failed_task.retry_count == 3
        assert "final failure" in failed_task.error_message

    async def test_post_execute_handles_db_error(self):
        middleware, session, _factory = _make_middleware()
        message = _make_message(retries="3", max_retries="3")
        result = _make_result(is_err=True, error=ValueError("test error"))

        # Make session.add raise an exception
        session.add.side_effect = RuntimeError("DB connection lost")

        # Should not crash — the exception is caught and logged
        with patch("src.infrastructure.logging.dlq_middleware.logger") as mock_logger:
            await middleware.post_execute(message, result)
            mock_logger.exception.assert_called_once()
