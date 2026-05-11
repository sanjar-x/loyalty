"""TaskIQ message broker configuration.

Domain-split routing (Sprint 5 fix, 2026-05-12):

The original single-queue setup ("taskiq_background_jobs" bound with the
``#`` wildcard) caused both ``core-worker`` and ``media-worker`` to
compete-consume from the same queue. The lean core-worker would
sometimes pick up the heavy ``remove_background`` task, fail with
``task is not found`` (or worse — missing torch/transformers wheels),
and SSE clients saw ``status: failed``.

This module installs a two-queue topology on a RabbitMQ TOPIC exchange:

    queue ``taskiq_core_jobs``   bound with routing_key ``taskiq_background_jobs``
        — accepts every task whose ``@broker.task(queue_name=...)`` label
        is the broker's default queue label (i.e. tasks declared
        without an explicit ``queue_name``).

    queue ``taskiq_media_jobs``  bound with routing_key ``image.#``
        — accepts every image-domain task (``image.processing`` /
        ``image.maintenance`` / ``image.ml``). The ``#`` wildcard
        matches zero or more dot-separated words after the ``image.``
        prefix.

Per-process responsibilities:

* **backend / scheduler** — publish-only. They see BOTH queues in
  ``task_queues`` so :pyfunc:`DomainSplitBroker.kick` can resolve the
  per-task ``queue_name=`` label as the AMQP routing-key. They do NOT
  call :pyfunc:`DomainSplitBroker.listen`, so they consume nothing.
* **core-worker** — sets ``TASKIQ_PRIMARY_QUEUE=taskiq_core_jobs`` and
  consumes from that queue alone. It may still kick image tasks (e.g.
  from an outbox handler that triggers media work) and the label-based
  routing delivers the message to the media queue, not back to itself.
* **media-worker** — sets ``TASKIQ_PRIMARY_QUEUE=taskiq_media_jobs``
  and consumes from the media queue alone.

Why a subclass instead of the stock :class:`AioPikaBroker`:

* Upstream's ``kick()`` only honours the per-task ``queue_name=`` label
  when the broker has 2+ ``task_queues`` — otherwise it falls back to
  the lone queue's name, regardless of the label. To keep workers on a
  single-queue ``listen()`` (the cleanest way to scope a worker to its
  domain) AND keep publishers routing by label, we need both queues
  visible in ``task_queues`` at publish time but only one visible at
  consume time.
* The same ``kick()`` returns ``""`` as the routing-key when the label
  is absent and the broker has multiple queues — routing nothing to
  any queue, because neither ``taskiq_background_jobs`` (direct) nor
  ``image.#`` (topic) matches an empty string. The fallback in this
  subclass injects the primary queue's routing-key so unlabeled tasks
  still land on the core queue.
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


_CORE_QUEUE_NAME = "taskiq_core_jobs"
_MEDIA_QUEUE_NAME = "taskiq_media_jobs"
_CORE_ROUTING_KEY = "taskiq_background_jobs"
_MEDIA_ROUTING_KEY = "image.#"


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

    async def listen(self) -> AsyncGenerator[object, None]:
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
_MEDIA_QUEUE = Queue(
    name=_MEDIA_QUEUE_NAME,
    routing_key=_MEDIA_ROUTING_KEY,
    declare=True,
    durable=True,
)

broker: DomainSplitBroker = DomainSplitBroker(
    url=str(settings.RABBITMQ_PRIVATE_URL),
    exchange=_EXCHANGE,
    task_queues=[_CORE_QUEUE, _MEDIA_QUEUE],
    qos=10,
    primary_queue_name=settings.TASKIQ_PRIMARY_QUEUE,
).with_middlewares(LoggingTaskiqMiddleware())
