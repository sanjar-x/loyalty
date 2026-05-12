"""Dead Letter Queue (DLQ) ORM model for permanently failed tasks.

Stores tasks that have exhausted all retry attempts so they can be
inspected and manually retried by operators.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class FailedTask(Base):
    """ORM model representing a task that exhausted all retry attempts.

    Attributes:
        id: Primary key (UUID).
        task_name: The TaskIQ task name.
        task_id: The TaskIQ message ID.
        args: Serialized task arguments.
        labels: Task labels (correlation_id, etc.).
        error_message: Full error traceback text.
        retry_count: Number of retry attempts executed.
        failed_at: Timestamp of the final failure.
    """

    __tablename__ = "failed_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary key",
    )
    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="TaskIQ task name",
    )
    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="TaskIQ message ID",
    )
    args: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Task arguments",
    )
    labels: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Task labels (correlation_id, etc.)",
    )
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Error message text",
    )
    retry_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Number of retry attempts executed",
    )
    failed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of the final failure",
    )
