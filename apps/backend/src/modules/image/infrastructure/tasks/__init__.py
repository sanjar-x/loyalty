"""Image-domain task declarations — **stubs**, bodies live in workers.

Why this file exists
====================

Backend's HTTP handlers dispatch image work via TaskIQ — they need a
``.kicker()`` handle to publish messages onto RabbitMQ. ``.kicker()`` is
a method on :class:`AsyncTaskiqDecoratedTask`, not on the bare broker;
so the publisher side needs an ``@broker.task`` declaration even though
it never runs the body. The actual implementations live in the
dedicated worker artefacts:

* ``apps/workers/image/storage/tasks.py``  → ``image_process_task``,
  ``image_cleanup_orphans_task``
* ``apps/workers/image/rmbg/tasks.py``     → ``image_remove_background_task``

How TaskIQ routes correctly
===========================

Both backend (publisher) and worker (consumer) register tasks with the
same ``task_name``. RabbitMQ routes the message by routing-key
(``image.storage.process`` / ``image.storage.cleanup_orphans`` /
``image.rmbg.remove``) to the worker-owned queue. The worker process
consumes from that queue and executes its own task body — backend's
stub body never runs.

Why ``NotImplementedError`` and not ``pass``
=============================================

Defence in depth: if a misconfiguration ever causes backend's
``core-worker`` to subscribe to a media queue, the stub will fail
loudly into the DLQ instead of silently dropping the task. The
``worker_core.py`` bootstrap filters ``image`` out of ``MODULES``
specifically to prevent that subscription — this is the second line of
defence.

Why declared on backend's shared broker singleton
==================================================

Module-level ``@broker.task`` decorators run at import time. Backend's
web service (uvicorn) imports this module via ``router_admin.py`` and
registers the stubs on its broker instance — used only for kick().
Backend's web does NOT run a TaskIQ worker loop, so it never consumes.
Each worker process has its own broker singleton (own Python
interpreter) and registers its OWN task body on import; the two
registrations don't interfere.
"""

from __future__ import annotations

from src.bootstrap.broker import broker


@broker.task(
    task_name="image_process",
    queue_name="image.storage.process",
    retry_on_error=True,
    max_retries=2,
    timeout=300,
)
async def image_process_task(storage_object_id: str) -> None:
    """Stub — consumer body lives in ``apps/workers/image/storage/tasks.py``.

    Routing: RabbitMQ exchange ``taskiq_rpc_exchange`` topic key
    ``image.storage.process`` → queue ``image_storage_jobs`` →
    consumed by ``image-storage-worker``.
    """
    raise NotImplementedError(
        "image_process_task is a publisher stub. The body runs in "
        "apps/workers/image/storage/tasks.py — only that worker should "
        "consume from the image.storage.process routing key. If you hit "
        "this, your worker bootstrap is subscribing to the wrong queue."
    )


@broker.task(
    task_name="image_cleanup_orphans",
    queue_name="image.storage.cleanup_orphans",
    timeout=600,
    schedule=[{"cron": "0 */6 * * *"}],
)
async def image_cleanup_orphans_task() -> None:
    """Stub — body in ``apps/workers/image/storage/tasks.py``.

    Six-hourly cron, published by ``apps/workers/scheduler`` and
    consumed by ``image-storage-worker``.
    """
    raise NotImplementedError(
        "image_cleanup_orphans_task is a publisher stub. Body in "
        "apps/workers/image/storage/tasks.py."
    )


@broker.task(
    task_name="image_remove_background",
    queue_name="image.rmbg.remove",
    retry_on_error=True,
    max_retries=2,
    timeout=240,
)
async def image_remove_background_task(derived_storage_object_id: str) -> None:
    """Stub — body in ``apps/workers/image/rmbg/tasks.py``.

    Routing key ``image.rmbg.remove`` → queue ``image_rmbg_jobs`` →
    consumed by ``image-rmbg-worker`` which alone carries the torch +
    Bria RMBG-2.0 stack.
    """
    raise NotImplementedError(
        "image_remove_background_task is a publisher stub. Body in "
        "apps/workers/image/rmbg/tasks.py."
    )


__all__ = [
    "image_cleanup_orphans_task",
    "image_process_task",
    "image_remove_background_task",
]
