"""TaskIQ broker — connects to the workspace-wide RabbitMQ."""

from __future__ import annotations

from taskiq_aio_pika import AioPikaBroker

from config import settings

broker: AioPikaBroker = AioPikaBroker(url=settings.RABBITMQ_PRIVATE_URL)
