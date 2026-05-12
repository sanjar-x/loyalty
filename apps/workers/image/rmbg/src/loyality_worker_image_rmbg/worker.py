"""TaskIQ entry point for the ``apps/workers/image/rmbg`` deployable artefact.

Subscribes to the ``image.ml`` queue (Bria RMBG-2.0 background removal).
For now the broker assembly in ``src.bootstrap.worker_media`` registers
the full image task set (storage + ML); the lean
``apps/workers/image/storage`` worker subscribes to its own queues and
ignores the ML task. A follow-up will split ``worker_media`` so this
artefact loads ONLY the rmbg task.

Eager-import torch / torchvision / timm on the main thread BEFORE the
broker imports image tasks. This sidesteps the
``torchvision::nms already has DispatchKey::Meta implementation``
RuntimeError that fired in prod (2026-05-12 incident): if ``transformers``
re-imports torchvision inside an asyncio worker thread,
``_meta_registrations.py`` attempts a second ``_register_fake`` which
torch ≥ 2.4 rejects. Importing those modules here ensures the
registration happens exactly once in the main interpreter, and subsequent
worker-thread imports hit ``sys.modules`` cache.

Run command:

    taskiq worker loyality_worker_image_rmbg.worker:broker
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
