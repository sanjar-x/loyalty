"""TaskIQ broker — image-storage worker.

Subscribes to ``image_storage_jobs`` on the workspace-wide RabbitMQ
topic exchange ``taskiq_rpc_exchange``. The queue is bound to two
routing keys so that exactly the two storage task families published
by backend (``image_process_task`` and ``image_cleanup_orphans_task``)
land here and nothing else.

Wire-level contract (must stay in sync with backend):

* exchange ``taskiq_rpc_exchange`` — type TOPIC, durable
* queue    ``image_storage_jobs`` — durable, with bindings:
    - ``image.storage.process``         — published by backend's
      ``image_process_task``
    - ``image.storage.cleanup_orphans`` — published by scheduler's
      ``image_cleanup_orphans_task``

The rmbg worker subscribes to its own ``image_rmbg_jobs`` (binding
``image.rmbg.remove``). The two queues are siblings on the same
exchange; the topic-key bindings keep each worker's traffic isolated.

Why a plain :class:`AioPikaBroker` (not :class:`DomainSplitBroker`):

This worker is consume-only and never publishes, so the upstream
broker's stock behaviour is sufficient. The split-broker subclass
exists in backend for label-routed publishing.

Worker-owned: no import from backend.

``qos=5`` because storage ops are IO-bound (Pillow resize + S3) and
many can be in flight at once without saturating CPU. Compare with
the rmbg worker (``qos=1``) which serialises heavy torch inference.
"""

from __future__ import annotations

from taskiq_aio_pika import AioPikaBroker
from taskiq_aio_pika.exchange import Exchange
from taskiq_aio_pika.queue import Queue

from config import settings

_EXCHANGE = Exchange(name="taskiq_rpc_exchange", declare=True, durable=True)

# Two Queue objects sharing the same name produce a single RabbitMQ
# queue with two bindings. AMQP allows multiple bindings per queue;
# TaskIQ iterates this list at startup, declaring the queue (idempotent
# after the first declare) and adding each routing-key binding in turn.
_QUEUE_NAME = "image_storage_jobs"
_PROCESS_BINDING = Queue(
    name=_QUEUE_NAME,
    routing_key="image.storage.process",
    declare=True,
    durable=True,
)
_CLEANUP_BINDING = Queue(
    name=_QUEUE_NAME,
    routing_key="image.storage.cleanup_orphans",
    declare=True,
    durable=True,
)

broker: AioPikaBroker = AioPikaBroker(
    url=settings.RABBITMQ_PRIVATE_URL,
    exchange=_EXCHANGE,
    task_queues=[_PROCESS_BINDING, _CLEANUP_BINDING],
    qos=5,
)
