# src/infrastructure/logging/dlq_middleware.py
"""
Dead Letter Queue (DLQ) Middleware для TaskIQ.

Перехватывает задачи, исчерпавшие все retry-попытки, и сохраняет
их в таблицу failed_tasks для последующего анализа и ручного повтора.
"""

from __future__ import annotations

import traceback

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from src.infrastructure.database.models.failed_task import FailedTask

logger = structlog.get_logger(__name__)


class DLQMiddleware(TaskiqMiddleware):
    """
    Middleware: сохраняет проваленные задачи в БД (Dead Letter Queue).

    Срабатывает только когда задача завершилась ошибкой и все
    retry-попытки исчерпаны.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self._session_factory = session_factory

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        if not result.is_err:
            return

        # Определяем retry-контекст из labels (SimpleRetryMiddleware convention)
        retry_count = int(message.labels.get("_retries", 0))
        max_retries = int(message.labels.get("max_retries", 0))

        # Если ещё есть retry-попытки — пропускаем
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
            "DLQ: задача исчерпала retry-попытки",
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
                "DLQ: не удалось сохранить проваленную задачу в БД",
                task_name=message.task_name,
                task_id=message.task_id,
            )
