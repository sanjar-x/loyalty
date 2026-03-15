# src/bootstrap/scheduler.py
"""
Точка входа TaskIQ Scheduler (Beat).

Scheduler периодически отправляет запланированные задачи в брокер.
Запуск: taskiq scheduler src.bootstrap.scheduler:scheduler

ВАЖНО: Запускать только ОДИН экземпляр Scheduler!
Несколько экземпляров приведут к дублированию задач.

Задачи, которые планируются через Beat:
  - outbox_relay_task   — каждую минуту (поллинг Outbox-таблицы)
  - outbox_pruning_task — ежесуточно в 03:00 UTC (очистка старых записей)
"""

import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from src.bootstrap.broker import broker
from src.bootstrap.container import create_container

logger = structlog.get_logger(__name__)

# Инициализируем DI-контейнер (аналогично worker.py)
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# Импортируем задачи для регистрации schedule-лейблов
import src.infrastructure.outbox.tasks  # noqa: E402, F401

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
