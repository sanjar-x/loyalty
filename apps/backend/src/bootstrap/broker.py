"""TaskIQ message broker configuration.

Topology (RabbitMQ TOPIC exchange ``taskiq_rpc_exchange``):

    queue ``core_jobs``           — declared here, bound with
        routing_key ``core``. Consumed by ``core-worker``. Accepts
        every task whose ``@broker.task(queue_name=...)`` label is the
        broker's default queue label (i.e. tasks declared without an
        explicit ``queue_name``).

    queue ``image_rmbg_jobs``     — declared by the rmbg worker
        (``apps/workers/image/rmbg/broker.py``), bound with
        routing_key ``image.rmbg.remove``. Consumed by the rmbg
        worker only.

    queue ``image_storage_jobs``  — declared by the storage worker
        (``apps/workers/image/storage/broker.py``), bound with TWO
        routing keys (``image.storage.process`` and
        ``image.storage.cleanup_orphans``). Consumed by the storage
        worker only.

Naming convention:

* **routing keys** — dotted hierarchy ``<domain>.<sub-domain>.<action>``
  (``image.storage.process``, ``image.rmbg.remove``). Bound to per-
  worker queues so each worker's traffic stays isolated. The flat
  ``core`` key is the catch-all for non-image tasks routed by the
  ``DomainSplitBroker`` fallback below.
* **queue names** — ``<role>_jobs`` (snake_case, AMQP-friendly). No
  ``taskiq_`` prefix: this is a TaskIQ broker by construction, so the
  prefix is noise.
* **task names** — domain-prefixed snake_case verbs (``image_process``,
  ``image_remove_background``, ``image_cleanup_orphans``). Domain
  prefix prevents collision across workers sharing the broker.

Each worker owns its own queue with a tight routing-key binding so the
two image workers never compete-consume from one shared queue — a bug
in the prior single-``taskiq_media_jobs`` topology where TaskIQ's
receiver silently ACK'd unknown tasks (see ``receiver.py:133-138``),
losing roughly half of every image task type to whichever worker did
not register it.

Per-process responsibilities:

* **web / scheduler / core-worker** — publish via the broker defined
  here. The broker lists every queue in ``task_queues`` (core PLUS all
  three image queues) — declarations are idempotent with the workers'
  own declarations. The image entries are present ONLY so upstream's
  ``kick()`` honours the per-task ``queue_name=`` label as the AMQP
  routing key; ``DomainSplitBroker.listen`` filters back to the primary
  queue at consume time so backend never accidentally consumes media
  work.
* **core-worker** — sets ``TASKIQ_PRIMARY_QUEUE=core_jobs`` and
  consumes from that queue alone. It may still kick image tasks (e.g.
  from an outbox handler that triggers media work) and the label-based
  routing delivers the message to the appropriate media queue, never
  back to itself.

Why ``DomainSplitBroker`` instead of stock :class:`AioPikaBroker`:

* Upstream's ``kick()`` short-circuits when ``task_queues`` has
  exactly ONE queue, forcing every publish to use that queue's routing
  key regardless of the per-task label. That is precisely why this
  broker lists the image queues even though backend never consumes
  them — without them, every image task would be misrouted to the
  core queue and dropped.
* Upstream's ``listen()`` consumes from every queue in ``task_queues``.
  This subclass overrides ``listen()`` to filter back to a single
  primary queue per process, so the core-worker reads core_jobs alone
  while still keeping every queue visible at publish time.
* Upstream's ``kick()`` returns ``""`` as the routing key when no
  ``queue_name`` label is set; the subclass injects the primary
  queue's routing key as a fallback so unlabeled tasks (the majority
  of core jobs) still land on the core queue.

Deploy note: queues from the prior naming scheme (``taskiq_core_jobs``,
``taskiq_media_jobs``, ``taskiq_storage_jobs``, ``taskiq_rmbg_jobs``)
linger in RabbitMQ after rollout. They have no consumers under the new
scheme, so any message bound to their old bindings accumulates forever.
Delete them via the RabbitMQ management UI after the new workers are
running.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from taskiq.message import BrokerMessage
from taskiq_aio_pika import AioPikaBroker
from taskiq_aio_pika.broker import parse_val
from taskiq_aio_pika.exchange import Exchange
from taskiq_aio_pika.queue import Queue

from src.bootstrap.config import settings
from src.infrastructure.logging.taskiq_middleware import LoggingTaskiqMiddleware

logger = structlog.get_logger(__name__)


_CORE_QUEUE_NAME = "core_jobs"
_CORE_ROUTING_KEY = "core"

# Image-worker queues are owned by the workers (they declare and consume).
# Backend lists them in ``task_queues`` ONLY so the upstream broker's
# ``kick()`` honours the per-task ``queue_name=`` label as the AMQP
# routing key. Without 2+ entries here, ``AioPikaBroker.kick()`` short-
# circuits to ``task_queues[0].routing_key`` (``core``) for EVERY task
# regardless of label — every image task would land on the core queue
# and starve the image workers. See receiver / broker source at
# ``taskiq_aio_pika/broker.py:375``. Declarations are idempotent (workers
# declare with identical name + routing_key + durable), so listing them
# here adds no resource cost.
_IMAGE_STORAGE_PROCESS_KEY = "image.storage.process"
_IMAGE_STORAGE_CLEANUP_KEY = "image.storage.cleanup_orphans"
_IMAGE_RMBG_REMOVE_KEY = "image.rmbg.remove"


class DomainSplitBroker(AioPikaBroker):
    """AioPikaBroker variant that decouples publish-routing from
    consume-scope, allowing each worker process to listen to exactly
    one queue while every publisher sees all queues for label-based
    routing. See module docstring for the rationale.
    """

    def __init__(
        self,
        *args: object,
        primary_queue_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._primary_queue_name = primary_queue_name
        # Cache the fallback routing-key for tasks published without an
        # explicit ``queue_name=`` label (the majority of core tasks).
        self._fallback_routing_key: str | None = next(
            (
                queue.routing_key or queue.name
                for queue in self._task_queues
                if queue.name == primary_queue_name
            ),
            None,
        )

    async def kick(self, message: BrokerMessage) -> None:
        """Publish a task, injecting the primary queue's routing-key as
        a fallback when the task did not declare a ``queue_name=`` label.
        """
        label = parse_val(str, message.labels.get(self._label_for_routing))
        if not label and self._fallback_routing_key is not None:
            message.labels[self._label_for_routing] = self._fallback_routing_key
        await super().kick(message)

    async def listen(self) -> AsyncGenerator[object]:
        """Consume only from the primary queue, hiding the other queues
        from the upstream listener that would otherwise merge them.
        """
        all_queues = self._task_queues
        self._task_queues = [
            queue for queue in all_queues if queue.name == self._primary_queue_name
        ]
        if not self._task_queues:
            raise RuntimeError(
                f"DomainSplitBroker: primary_queue_name={self._primary_queue_name!r} "
                f"not found in task_queues={[q.name for q in all_queues]!r}"
            )
        try:
            async for message in super().listen():
                yield message
        finally:
            self._task_queues = all_queues


_EXCHANGE = Exchange(name="taskiq_rpc_exchange", declare=True, durable=True)
_CORE_QUEUE = Queue(
    name=_CORE_QUEUE_NAME,
    routing_key=_CORE_ROUTING_KEY,
    declare=True,
    durable=True,
)
# Image worker queues are owned (consumed) by their workers, but backend
# lists them here for one reason only: ``AioPikaBroker.kick()`` short-
# circuits to ``task_queues[0]``'s routing key whenever the broker has
# exactly ONE queue, ignoring every per-task ``queue_name=`` label.
# Without these entries every image task would be published with
# routing key ``core`` and starve the image workers. Declarations are
# idempotent (workers declare with identical name + routing_key +
# durable). ``DomainSplitBroker.listen`` filters back to the primary
# queue at consume time so backend itself never receives image work.
_IMAGE_STORAGE_PROCESS_QUEUE = Queue(
    name="image_storage_jobs",
    routing_key=_IMAGE_STORAGE_PROCESS_KEY,
    declare=True,
    durable=True,
)
_IMAGE_STORAGE_CLEANUP_QUEUE = Queue(
    name="image_storage_jobs",
    routing_key=_IMAGE_STORAGE_CLEANUP_KEY,
    declare=True,
    durable=True,
)
_IMAGE_RMBG_QUEUE = Queue(
    name="image_rmbg_jobs",
    routing_key=_IMAGE_RMBG_REMOVE_KEY,
    declare=True,
    durable=True,
)

broker: DomainSplitBroker = DomainSplitBroker(
    url=str(settings.RABBITMQ_PRIVATE_URL),
    exchange=_EXCHANGE,
    task_queues=[
        _CORE_QUEUE,
        _IMAGE_STORAGE_PROCESS_QUEUE,
        _IMAGE_STORAGE_CLEANUP_QUEUE,
        _IMAGE_RMBG_QUEUE,
    ],
    qos=10,
    primary_queue_name=settings.TASKIQ_PRIMARY_QUEUE,
).with_middlewares(LoggingTaskiqMiddleware())
