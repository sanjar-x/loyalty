# src/infrastructure/database/models/failed_task.py
"""
Dead Letter Queue (DLQ): запись о задаче, исчерпавшей все retry-попытки.

Позволяет инспектировать и вручную повторять проваленные задачи.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class FailedTask(Base):
    __tablename__ = "failed_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Первичный ключ",
    )
    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Имя задачи TaskIQ",
    )
    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ID сообщения TaskIQ",
    )
    args: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Аргументы задачи",
    )
    labels: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Labels задачи (correlation_id и др.)",
    )
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст ошибки",
    )
    retry_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Количество выполненных retry-попыток",
    )
    failed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время окончательного провала",
    )
