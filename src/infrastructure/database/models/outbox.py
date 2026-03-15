# src/infrastructure/database/models/outbox.py
import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OutboxMessage(Base):
    """
    Transactional Outbox: запись доменного события для гарантированной
    доставки в брокер сообщений (RabbitMQ).

    Записывается атомарно в одной транзакции с бизнес-данными.
    Relay-воркер читает необработанные записи и публикует их в брокер.
    """

    __tablename__ = "outbox_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="PK (UUIDv4, т.к. uuid7 опционален)",
    )

    aggregate_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Тип агрегата-источника (Brand, Order, ...)",
    )

    aggregate_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ID агрегата-источника",
    )

    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название доменного события (BrandLogoConfirmedEvent, ...)",
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Сериализованное тело события (.model_dump(mode='json'))",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Момент записи события в Outbox",
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=None,
        comment="Момент успешной публикации в брокер (NULL = не обработано)",
    )

    __table_args__ = (
        # Критический индекс для Relay-воркера:
        # WHERE processed_at IS NULL ORDER BY created_at ASC
        Index(
            "ix_outbox_processed_created",
            "processed_at",
            "created_at",
        ),
    )
