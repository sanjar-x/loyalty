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
  here. The broker declares only the core queue; routing to media
  queues happens through the topic exchange and bindings declared by
  the respective workers. Publishers do not need media queues in
  ``task_queues``: ``AioPikaBroker.kick`` resolves the routing key
  from the per-task ``queue_name=`` label and publishes to the
  exchange — the bindings owned by the workers route to the right
  queue.
* **core-worker** — sets ``TASKIQ_PRIMARY_QUEUE=core_jobs`` and
  consumes from that queue alone. It may still kick image tasks (e.g.
  from an outbox handler that triggers media work) and the label-based
  routing delivers the message to the appropriate media queue, never
  back to itself.

Why ``DomainSplitBroker`` instead of stock :class:`AioPikaBroker`:

* Upstream's ``kick()`` returns ``""`` as the routing key when no
  ``queue_name`` label is set and the broker has 2+ queues. The
  fallback in this subclass injects the primary queue's routing key
  so unlabeled tasks still land on the core queue.

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

# Media-domain queues are declared by their workers (apps/workers/image/*),
# not here, so each worker owns its routing-key binding and the two
# image workers never compete-consume from a shared queue. See module
# docstring for the deploy note about the orphaned ``taskiq_media_jobs``.
broker: DomainSplitBroker = DomainSplitBroker(
    url=str(settings.RABBITMQ_PRIVATE_URL),
    exchange=_EXCHANGE,
    task_queues=[_CORE_QUEUE],
    qos=10,
    primary_queue_name=settings.TASKIQ_PRIMARY_QUEUE,
).with_middlewares(LoggingTaskiqMiddleware())
