# src/infrastructure/logging/taskiq_middleware.py
"""
TaskIQ Middleware для привязки trace-контекста к фоновым задачам.

Решает проблему: фоновые задачи (TaskIQ) выполняются вне HTTP-запроса,
AccessLoggerMiddleware не вызывается → structlog contextvars пуст.

Данный middleware:
1. Извлекает correlation_id из labels задачи (если передан из Relay)
2. Генерирует task_trace_id если correlation_id отсутствует
3. Привязывает контекст в structlog.contextvars для всех дочерних логов
4. Очищает контекст после выполнения задачи
"""

from __future__ import annotations

import uuid

import structlog
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult


class LoggingTaskiqMiddleware(TaskiqMiddleware):
    """Middleware: привязка trace-контекста к каждой выполняемой задаче."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        correlation_id = message.labels.get("correlation_id", "task-" + uuid.uuid4().hex[:12])

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            task_id=message.task_id,
            task_name=message.task_name,
        )
        return message

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        structlog.contextvars.clear_contextvars()
