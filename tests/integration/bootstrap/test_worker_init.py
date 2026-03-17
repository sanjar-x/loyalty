# tests/integration/bootstrap/test_worker_init.py
"""Integration tests for worker module initialization and DI setup."""


async def test_worker_container_creation():
    """Verify the DI container can be created as worker.py does."""
    from src.bootstrap.container import create_container

    container = create_container()
    assert container is not None
    await container.close()


async def test_dishka_middleware_attaches_to_broker():
    """Verify setup_dishka() successfully attaches ContainerMiddleware to the broker."""
    from dishka.integrations.taskiq import setup_dishka
    from taskiq_aio_pika import AioPikaBroker

    from src.bootstrap.container import create_container

    container = create_container()
    broker = AioPikaBroker(
        url="amqp://admin:password@127.0.0.1:5672/",
        exchange_name="test_dishka_exchange",
        queue_name="test_dishka_queue",
    )

    setup_dishka(container=container, broker=broker)

    # Dishka adds a ContainerMiddleware
    has_container_mw = any("Container" in type(mw).__name__ for mw in broker.middlewares)
    assert has_container_mw is True

    await container.close()


async def test_dlq_middleware_creation():
    """Verify DLQ middleware can be created with a valid engine."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import AsyncAdaptedQueuePool

    from src.bootstrap.config import settings
    from src.infrastructure.logging.dlq_middleware import DLQMiddleware

    engine = create_async_engine(
        url=settings.database_url,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=1,
        max_overflow=0,
    )
    session_factory = async_sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )

    middleware = DLQMiddleware(session_factory=session_factory)
    assert middleware is not None

    await engine.dispose()


async def test_outbox_tasks_register_schedule_labels():
    """Verify outbox tasks declare schedule labels for the scheduler."""
    import src.infrastructure.outbox.tasks  # noqa: F401

    from src.bootstrap.broker import broker

    tasks = broker.get_all_tasks()
    tasks_with_schedule = [
        name
        for name, task in tasks.items()
        if hasattr(task, "labels") and task.labels.get("schedule")
    ]
    # outbox_relay_task and outbox_pruning_task both have schedule labels
    assert len(tasks_with_schedule) >= 2
