"""TaskIQ broker — connects to the workspace-wide RabbitMQ.

Worker-owned: no import from backend. The broker URL is the only
piece of state we share with backend (config-level coordination —
both sides connect to the same RabbitMQ, both speak the same queue
names + task names).
"""

from __future__ import annotations

from taskiq_aio_pika import AioPikaBroker

from config import settings

broker: AioPikaBroker = AioPikaBroker(url=settings.RABBITMQ_PRIVATE_URL)
