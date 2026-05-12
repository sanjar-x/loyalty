"""TaskIQ entry point for the ``apps/workers/core`` deployable artefact.

The workspace member ``backend`` (apps/backend) hosts the actual broker
assembly under ``src.bootstrap.worker_core``. That module performs
side-effectful task registration on import (DishkaMiddleware → DLQ →
``import_task_modules`` walk over MODULES), so a plain
``from src.bootstrap.worker_core import broker`` is enough — TaskIQ
discovers everything registered by the time it reads ``broker``.

Run command (Railway / local — invoke from this app's directory so
``main`` resolves on cwd):

    cd apps/workers/core && taskiq worker main:broker
"""

from __future__ import annotations

from src.bootstrap.worker_core import broker

__all__ = ["broker"]
