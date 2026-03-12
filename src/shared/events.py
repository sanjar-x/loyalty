from datetime import UTC, datetime
from typing import Any, Dict
from uuid import UUID, uuid7

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Событие, происходящее внутри домена. Обычно обрабатывается in-memory."""

    event_id: UUID = Field(default_factory=uuid7)
    occurred_on: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationEvent(BaseModel):
    """Событие для межмодульной коммуникации и публикации в RabbitMQ."""

    event_id: UUID = Field(default_factory=uuid7)
    occurred_on: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str
    payload: Dict[str, Any]
