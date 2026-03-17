"""TaskIQ middleware for binding trace context to background tasks.

Background tasks (TaskIQ) execute outside of HTTP requests, so the
``AccessLoggerMiddleware`` never fires and structlog's contextvars are
empty. This middleware:

1. Extracts ``correlation_id`` from the task labels (if forwarded by the relay).
2. Generates a ``task_trace_id`` when no correlation_id is present.
3. Binds the context into ``structlog.contextvars`` for all downstream logs.
4. Clears the context after task execution completes.
"""

from __future__ import annotations

import uuid

import structlog
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult


class LoggingTaskiqMiddleware(TaskiqMiddleware):
    """Middleware that binds trace context to every executed task."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Bind correlation and task identifiers before task execution.

        Args:
            message: The incoming TaskIQ message.

        Returns:
            The unmodified message, after context has been bound.
        """
        correlation_id = message.labels.get("correlation_id", "task-" + uuid.uuid4().hex[:12])

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            task_id=message.task_id,
            task_name=message.task_name,
        )
        return message

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        """Clear structlog contextvars after task execution.

        Args:
            message: The executed TaskIQ message.
            result: The task execution result.
        """
        structlog.contextvars.clear_contextvars()
