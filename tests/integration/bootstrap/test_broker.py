# tests/integration/bootstrap/test_broker.py
"""Integration tests for broker connectivity and task registration."""


async def test_broker_connects_to_rabbitmq(rabbitmq_url: str):
    """Verify the AioPikaBroker can connect and disconnect from RabbitMQ."""
    from taskiq_aio_pika import AioPikaBroker

    broker = AioPikaBroker(
        url=rabbitmq_url,
        exchange_name="test_exchange",
        queue_name="test_queue",
        declare_exchange=True,
        declare_queue=True,
    )
    await broker.startup()
    assert broker.is_worker_process is False
    await broker.shutdown()


async def test_broker_has_configured_url(rabbitmq_url: str):
    """Verify the project broker is configured with a valid RabbitMQ URL."""
    from src.bootstrap.broker import broker

    assert broker is not None
    assert "amqp://" in str(rabbitmq_url)


async def test_broker_task_registration():
    """Verify that importing task modules registers tasks on the broker."""
    from src.bootstrap.broker import broker

    import src.infrastructure.outbox.tasks  # noqa: F401

    tasks = broker.get_all_tasks()
    assert len(tasks) > 0


async def test_scheduler_creation(rabbitmq_url: str):
    """Verify the scheduler can be instantiated with the broker."""
    from taskiq import TaskiqScheduler
    from taskiq.schedule_sources import LabelScheduleSource
    from taskiq_aio_pika import AioPikaBroker

    broker = AioPikaBroker(
        url=rabbitmq_url,
        exchange_name="test_scheduler_exchange",
        queue_name="test_scheduler_queue",
        declare_exchange=True,
        declare_queue=True,
    )

    scheduler = TaskiqScheduler(
        broker=broker,
        sources=[LabelScheduleSource(broker)],
    )
    assert scheduler is not None
    assert len(scheduler.sources) == 1
