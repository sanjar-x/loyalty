"""TaskIQ Scheduler (Beat) entry point.

Launch command::

    taskiq scheduler src.bootstrap.scheduler:scheduler

IMPORTANT: Run exactly ONE scheduler instance.
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
import src.modules.storage.presentation.tasks  # noqa: E402, F401

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
