"""TaskIQ entry point for the ``apps/workers/image/rmbg`` deployable artefact.

Subscribes to the ``image.ml`` queue (Bria RMBG-2.0 background removal).
The broker assembly in ``src.bootstrap.worker_image_rmbg`` imports ONLY
the rmbg task submodule (``src.modules.image.infrastructure.tasks.rmbg``);
the storage tasks are not registered on this broker, so we never accept
``image.processing`` / ``image.maintenance`` jobs even on the same
RabbitMQ instance. The lean ``apps/workers/image/storage`` worker owns
those queues.

Eager-import torch / torchvision / timm on the main thread BEFORE the
broker imports rmbg tasks. This sidesteps the
``torchvision::nms already has DispatchKey::Meta implementation``
RuntimeError that fired in prod (2026-05-12 incident): if
``transformers`` re-imports torchvision inside an asyncio worker
thread, ``_meta_registrations.py`` attempts a second
``_register_fake`` which torch ≥ 2.4 rejects. Importing those modules
here ensures the registration happens exactly once in the main
interpreter, and subsequent worker-thread imports hit ``sys.modules``
cache.

Run command (from this app's directory):

    cd apps/workers/image/rmbg && python -m taskiq worker main:broker
"""

from __future__ import annotations

# 1. Eager-import the heavy ML stack on the main thread. Order matters:
#    torch first (registers core ops), then torchvision (extends with
#    NMS / RoI), then timm (pulls torchvision.models.feature_extraction).
import torch  # noqa: F401, E402
import torchvision  # noqa: F401, E402
import timm  # noqa: F401, E402
import kornia  # noqa: F401, E402

# 2. Now import the broker — ``src.bootstrap.worker_image_rmbg`` registers
#    ``remove_background_task`` (when ``BG_REMOVAL_ENABLED=true``) on
#    import.
from src.bootstrap.worker_image_rmbg import broker  # noqa: E402

__all__ = ["broker"]
