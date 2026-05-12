"""TaskIQ entry point for the ``apps/workers/image/storage`` deployable artefact.

Subscribes to ``image.processing`` + ``image.maintenance`` queues — the
non-ML half of the image module's background work (Pillow resize and
S3 cleanup). The broker assembly in ``src.bootstrap.worker_image_storage``
imports ONLY the storage task submodule
(``src.modules.image.infrastructure.tasks.storage``); the rmbg task is
not registered on this broker, so this worker never subscribes to the
``image.ml`` queue. That queue is drained exclusively by
``apps/workers/image/rmbg``, the only artefact carrying the torch +
transformers stack.

Run command (from this app's directory):

    cd apps/workers/image/storage && python -m taskiq worker main:broker
"""

from __future__ import annotations

from src.bootstrap.worker_image_storage import broker

__all__ = ["broker"]
