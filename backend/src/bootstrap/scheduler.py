"""TaskIQ Scheduler (Beat) entry point.

The scheduler periodically dispatches scheduled tasks to the broker.

Launch command::

    taskiq scheduler src.bootstrap.scheduler:scheduler

IMPORTANT: Run exactly ONE scheduler instance.  Multiple instances will
cause duplicate task dispatches.

Tasks dispatched via Beat:
- ``outbox_relay_task``               -- every minute (polls the Outbox table).
- ``outbox_pruning_task``             -- daily at 03:00 UTC (prunes stale records).
- ``outbox_lag_check`` (HARD-2)       -- every minute (alerts on PENDING > 50 OR oldest > 5min).
- ``failed_tasks_growth_check`` (HARD-2) -- every minute (alerts on new DLQ rows).
"""

import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from src.bootstrap.broker import broker
from src.bootstrap.container import create_container

logger = structlog.get_logger(__name__)

# Initialise the DI container (mirrors worker.py setup).
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# Import tasks so that their schedule labels are registered with the broker.
# Framework-level outbox tasks + HARD-2 alert monitors + every module's
# declared ``task_modules`` (REFACT-001 PR-5).
import src.infrastructure.outbox.tasks  # noqa: E402
import src.shared.infrastructure.alerts.monitors.failed_tasks_monitor  # noqa: E402
import src.shared.infrastructure.alerts.monitors.outbox_monitor  # noqa: E402, F401
from src.bootstrap.module_registry import import_task_modules  # noqa: E402
from src.bootstrap.modules import MODULES  # noqa: E402

import_task_modules(MODULES)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
