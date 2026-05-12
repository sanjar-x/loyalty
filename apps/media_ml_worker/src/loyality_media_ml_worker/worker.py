"""TaskIQ entry point for the ``apps/media_ml_worker`` deployable artefact.

Subscribes to ``image_processing`` / ``image_maintenance`` / ``image.ml``
queues. The actual broker assembly lives in
``src.bootstrap.worker_media`` (backend) — this module is a thin re-export
so Railway can target a stable import path.

Eager-import torch / torchvision / timm on the main thread BEFORE the
broker imports image tasks. This sidesteps the
``torchvision::nms already has DispatchKey::Meta implementation``
RuntimeError that fired in prod (2026-05-12 incident): if ``transformers``
re-imports torchvision inside an asyncio worker thread, ``_meta_registrations.py``
attempts a second ``_register_fake`` which torch ≥ 2.4 rejects. Importing
those modules here ensures the registration happens exactly once in the
main interpreter, and subsequent worker-thread imports hit ``sys.modules``
cache.

Run command:

    taskiq worker loyality_media_ml_worker.worker:broker
"""

from __future__ import annotations

# 1. Eager-import the heavy ML stack on the main thread. Order matters:
#    torch first (registers core ops), then torchvision (extends with
#    NMS / RoI), then timm (pulls torchvision.models.feature_extraction).
import torch  # noqa: F401, E402
import torchvision  # noqa: F401, E402
import timm  # noqa: F401, E402
import kornia  # noqa: F401, E402

# 2. Now import the broker — ``src.bootstrap.worker_media`` registers
#    image tasks (incl. ``remove_background_task`` when
#    ``BG_REMOVAL_ENABLED=true``) on import.
from src.bootstrap.worker_media import broker  # noqa: E402

__all__ = ["broker"]
