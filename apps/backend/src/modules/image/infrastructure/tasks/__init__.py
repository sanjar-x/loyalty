"""Image module TaskIQ task registry.

Tasks are split across two submodules so each deploy artefact can
import only what it owns:

* :mod:`.storage` — ``process_image_task`` + ``cleanup_orphans_task``
  (Pillow resize + S3 cleanup), consumed by ``apps/workers/image/storage``.
* :mod:`.rmbg` — ``remove_background_task`` (Bria RMBG-2.0 ML inference),
  consumed by ``apps/workers/image/rmbg``.

The package-level ``__init__`` re-exports both names so callers that
historically wrote ``from src.modules.image.infrastructure.tasks import
process_image_task`` (presentation routers, etc.) keep working.

IMPORTANT: importing this ``__init__`` pulls in BOTH submodules, which
in turn registers the rmbg task on the broker (provided
``BG_REMOVAL_ENABLED=true``). Workers that should NOT subscribe to the
``image.ml`` queue MUST import the specific submodule directly
(``import src.modules.image.infrastructure.tasks.storage``) rather than
the package, so the rmbg task is never registered on their broker.
"""

from src.modules.image.infrastructure.tasks.rmbg import remove_background_task
from src.modules.image.infrastructure.tasks.storage import (
    cleanup_orphans_task,
    process_image_task,
)

__all__ = [
    "cleanup_orphans_task",
    "process_image_task",
    "remove_background_task",
]
