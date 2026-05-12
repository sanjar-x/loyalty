"""TaskIQ entry point for the ``apps/workers/core`` deployable artefact.

The workspace member ``loyality`` (apps/backend) hosts the actual broker
assembly under ``src.bootstrap.worker_core``. That module performs
side-effectful task registration on import (DishkaMiddleware → DLQ →
``import_task_modules`` walk over MODULES), so a plain
``from src.bootstrap.worker_core import broker`` is enough — TaskIQ
discovers everything registered by the time it reads ``broker``.

Run command (Railway / local):

    taskiq worker loyality_worker_core.worker:broker
"""

from __future__ import annotations

from src.bootstrap.worker_core import broker

__all__ = ["broker"]
