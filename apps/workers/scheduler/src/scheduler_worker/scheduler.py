"""TaskIQ scheduler entry point for the ``apps/workers/scheduler`` deployable artefact.

Re-exports the canonical scheduler instance from
``src.bootstrap.scheduler`` so Railway can target a stable import path.

Run command:

    taskiq scheduler scheduler_worker.scheduler:scheduler
"""

from __future__ import annotations

from src.bootstrap.scheduler import scheduler

__all__ = ["scheduler"]
