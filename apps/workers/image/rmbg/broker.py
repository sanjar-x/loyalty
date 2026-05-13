"""TaskIQ broker — image-rmbg (background-removal) worker.

Subscribes to the **media** queue on the workspace-wide RabbitMQ topic
exchange. Mirrors backend's broker topology (see
``apps/backend/src/bootstrap/broker.py``) so the worker binds to the
same exchange/queue/routing-key tuple that backend publishes to.

Wire-level contract (must stay in sync with backend):

* exchange ``taskiq_rpc_exchange`` — type TOPIC, durable
* queue    ``taskiq_media_jobs``   — durable, bound with routing key
  ``image.#`` (this worker only receives ``image.ml`` messages
  published by backend's ``remove_background_task``, the
  ``taskiq_storage_worker`` competes for ``image.processing`` /
  ``image.maintenance`` on the same queue but the task name on the
  payload routes execution to the right consumer)

Why a plain :class:`AioPikaBroker` (not :class:`DomainSplitBroker`):

This worker is consume-only and listens to a single queue, so the
upstream broker's stock behaviour is sufficient. The split-broker
subclass exists to let backend's web service publish to multiple
queues by label and to let backend's core-worker consume from one
queue while seeing all of them — neither concern applies here.

Worker-owned: no import from backend. ``qos=1`` because rmbg inference
is heavy (torch + Bria RMBG-2.0) — we want one message per worker
process in-flight at a time so a slow message doesn't queue up behind
faster ones.
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
    qos=1,
)
