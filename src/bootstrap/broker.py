# src/bootstrap/taskiq.py
import structlog
from taskiq_aio_pika import AioPikaBroker

from src.bootstrap.config import settings
from src.infrastructure.logging.taskiq_middleware import LoggingTaskiqMiddleware

logger = structlog.get_logger(__name__)


broker: AioPikaBroker = AioPikaBroker(
    url=str(settings.RABBITMQ_URL),
    exchange_name="taskiq_rpc_exchange",
    queue_name="taskiq_background_jobs",
    qos=10,
    declare_exchange=True,
    declare_queue=True,
).with_middlewares(LoggingTaskiqMiddleware())
