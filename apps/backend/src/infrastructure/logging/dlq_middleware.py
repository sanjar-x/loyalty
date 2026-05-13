"""Dead Letter Queue (DLQ) middleware for TaskIQ.

Intercepts tasks that have exhausted all retry attempts and persists
them to the ``failed_tasks`` table for later inspection and manual replay.
"""

from __future__ import annotations

import traceback

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from src.infrastructure.database.models.failed_task import FailedTask

logger = structlog.get_logger(__name__)


class DLQMiddleware(TaskiqMiddleware):
    """Middleware that saves permanently failed tasks to the database.

    Activates only when a task finishes with an error and all retry
    attempts have been exhausted.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize the DLQ middleware with a database session factory.

        Args:
            session_factory: An async session factory for creating DB sessions.
        """
        super().__init__()
        self._session_factory = session_factory

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        """Persist a failed task to the DLQ table after retries are exhausted.

        Args:
            message: The TaskIQ message that was executed.
            result: The execution result containing error information.
        """
        if not result.is_err:
            return

        # Determine retry context from labels (SimpleRetryMiddleware convention)
        retry_count = int(message.labels.get("_retries", 0))
        max_retries = int(message.labels.get("max_retries", 0))

        # Skip if there are remaining retry attempts
        if retry_count < max_retries:
            return

        error_text = (
            "".join(
                traceback.format_exception(
                    type(result.error), result.error, result.error.__traceback__
                )
            )
            if result.error
            else "Unknown error"
        )

        logger.error(
            "DLQ: task exhausted all retry attempts",
            task_name=message.task_name,
            task_id=message.task_id,
            retry_count=retry_count,
        )

        try:
            async with self._session_factory() as session, session.begin():
                failed = FailedTask(
                    task_name=message.task_name,
                    task_id=message.task_id,
                    args={"args": list(message.args), "kwargs": message.kwargs},
                    labels=dict(message.labels),
                    error_message=error_text,
                    retry_count=retry_count,
                )
                session.add(failed)
        except Exception:
            logger.exception(
                "DLQ: failed to persist failed task to database",
                task_name=message.task_name,
                task_id=message.task_id,
            )
