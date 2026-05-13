"""TaskIQ broker — image-storage worker.

Subscribes to the **media** queue on the workspace-wide RabbitMQ topic
exchange. Mirrors backend's broker topology (see
``apps/backend/src/bootstrap/broker.py``) so the worker binds to the
same exchange/queue/routing-key tuple that backend publishes to.

Wire-level contract (must stay in sync with backend):

* exchange ``taskiq_rpc_exchange`` — type TOPIC, durable
* queue    ``taskiq_media_jobs``   — durable, bound with routing key
  ``image.#`` (matches ``image.processing`` published by backend's
  ``process_image_task`` and ``image.maintenance`` published by the
  scheduler's ``cleanup_orphans_task``)

Why a plain :class:`AioPikaBroker` (not :class:`DomainSplitBroker`):

Backend uses ``DomainSplitBroker`` because it both publishes (to
multiple queues, label-routed) and lets ``core-worker`` consume (from
exactly one). This worker is consume-only and listens to exactly one
queue, so the upstream broker's stock behaviour is fine.

Worker-owned: no import from backend. The broker URL and queue names
are the only state we share with backend (config-level coordination).
"""

from __future__ import annotations

from taskiq_aio_pika import AioPikaBroker
from taskiq_aio_pika.exchange import Exchange
from taskiq_aio_pika.queue import Queue

from config import settings

_EXCHANGE = Exchange(name="taskiq_rpc_exchange", declare=True, durable=True)
_MEDIA_QUEUE = Queue(
    name="taskiq_media_jobs",
    routing_key="image.#",
    declare=True,
    durable=True,
)

broker: AioPikaBroker = AioPikaBroker(
    url=settings.RABBITMQ_PRIVATE_URL,
    exchange=_EXCHANGE,
    task_queues=[_MEDIA_QUEUE],
    qos=5,
)
