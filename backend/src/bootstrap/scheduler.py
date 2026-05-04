"""TaskIQ Scheduler (Beat) entry point.

The scheduler periodically dispatches scheduled tasks to the broker.

Launch command::

    taskiq scheduler src.bootstrap.scheduler:scheduler

IMPORTANT: Run exactly ONE scheduler instance.  Multiple instances will
cause duplicate task dispatches.

Schedule discovery follows the same module-registry convention used by
the worker process: each :class:`ModuleManifest` lists the dotted
paths whose ``@broker.task(schedule=...)`` registrations the scheduler
must see.
"""

import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from src.bootstrap.broker import broker
from src.bootstrap.container import create_container
from src.bootstrap.module_registry import import_task_modules
from src.bootstrap.modules import MODULES

logger = structlog.get_logger(__name__)

# Initialise the DI container (mirrors worker.py setup).
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# Import tasks so that their schedule labels are registered with the broker.
import src.infrastructure.outbox.tasks  # noqa: F401, E402

import_task_modules(MODULES)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
