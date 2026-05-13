"""TaskIQ broker — image-rmbg (background-removal) worker.

Subscribes to ``image_rmbg_jobs`` on the workspace-wide RabbitMQ topic
exchange ``taskiq_rpc_exchange``. The queue is bound to the single
routing key ``image.rmbg.remove`` so the worker receives ONLY the
background-removal task published by backend's
``image_remove_background_task``.

Wire-level contract (must stay in sync with backend):

* exchange ``taskiq_rpc_exchange`` — type TOPIC, durable
* queue    ``image_rmbg_jobs``     — durable, bound with routing key
  ``image.rmbg.remove``

The storage worker subscribes to its own ``image_storage_jobs``
(bindings ``image.storage.process`` + ``image.storage.cleanup_orphans``).
The two queues are siblings on the same exchange; the topic-key
bindings keep each worker's traffic isolated.

Why a plain :class:`AioPikaBroker` (not :class:`DomainSplitBroker`):

This worker is consume-only and never publishes, so the upstream
broker's stock behaviour is sufficient. The split-broker subclass
exists in backend for label-routed publishing.

Worker-owned: no import from backend.

``qos=1`` because rmbg inference is heavy (torch + Bria RMBG-2.0) and
holds the GIL for ~6-30 seconds per image. One in-flight message per
process avoids head-of-line blocking on the broker side.
"""

from __future__ import annotations

from taskiq_aio_pika import AioPikaBroker
from taskiq_aio_pika.exchange import Exchange
from taskiq_aio_pika.queue import Queue

from config import settings

_EXCHANGE = Exchange(name="taskiq_rpc_exchange", declare=True, durable=True)
_RMBG_QUEUE = Queue(
    name="image_rmbg_jobs",
    routing_key="image.rmbg.remove",
    declare=True,
    durable=True,
)

broker: AioPikaBroker = AioPikaBroker(
    url=settings.RABBITMQ_PRIVATE_URL,
    exchange=_EXCHANGE,
    task_queues=[_RMBG_QUEUE],
    qos=1,
)
