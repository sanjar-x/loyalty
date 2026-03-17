# src/infrastructure/outbox/tasks.py
"""
TaskIQ-задачи для Outbox Relay и Pruning.

Relay: периодический поллинг outbox_messages (каждую минуту через Beat).
Pruning: ежесуточная очистка обработанных записей старше 7 дней (03:00 UTC).
"""

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.infrastructure.outbox.relay import (
    prune_processed_messages,
    register_event_handler,
    relay_outbox_batch,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Регистрация обработчиков событий (event_type → TaskIQ dispatch)
# ---------------------------------------------------------------------------


def _build_labels(correlation_id: str | None) -> dict[str, str]:
    """Формирует labels для сквозной трассировки HTTP → Outbox → TaskIQ."""
    if correlation_id:
        return {"correlation_id": correlation_id}
    return {}


async def _handle_brand_created(payload: dict, correlation_id: str | None = None) -> None:
    """Регистрирует StorageFile в модуле Storage через consumer."""
    from src.modules.storage.application.consumers.brand_events import (
        handle_brand_created_event,
    )

    await (
        handle_brand_created_event.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            brand_id=payload["brand_id"],
            object_key=payload["object_key"],
            content_type=payload["content_type"],
        )  # ty:ignore[no-matching-overload]
    )


async def _handle_brand_logo_confirmed(payload: dict, correlation_id: str | None = None) -> None:
    """Отправляет задачу обработки логотипа бренда в TaskIQ."""
    from src.modules.catalog.application.tasks import process_brand_logo_task

    brand_id = uuid.UUID(payload["brand_id"])
    await (
        process_brand_logo_task.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(brand_id=brand_id)  # ty:ignore[no-matching-overload]
    )


async def _handle_brand_logo_processed(payload: dict, correlation_id: str | None = None) -> None:
    """Регистрирует обработанный файл в модуле Storage."""
    from src.modules.storage.application.consumers.brand_events import (
        handle_brand_logo_processed_event,
    )

    await (
        handle_brand_logo_processed_event.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            brand_id=payload["brand_id"],
            object_key=payload["object_key"],
            content_type=payload["content_type"],
            size_bytes=payload["size_bytes"],
        )  # ty:ignore[no-matching-overload]
    )


# Регистрируем маппинг: event_type → handler
register_event_handler("BrandCreatedEvent", _handle_brand_created)
register_event_handler("BrandLogoConfirmedEvent", _handle_brand_logo_confirmed)
register_event_handler("BrandLogoProcessedEvent", _handle_brand_logo_processed)


# ---------------------------------------------------------------------------
# IAM Event Handlers
# ---------------------------------------------------------------------------


async def _handle_identity_registered(payload: dict, correlation_id: str | None = None) -> None:
    """Dispatches CreateUserConsumer to create User row (Shared PK)."""
    from src.modules.user.application.consumers.identity_events import (
        create_user_on_identity_registered,
    )

    await (
        create_user_on_identity_registered.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
            email=payload["email"],
        )  # ty:ignore[no-matching-overload]
    )


async def _handle_identity_deactivated(payload: dict, correlation_id: str | None = None) -> None:
    """Dispatches AnonymizeUserConsumer to anonymize PII (GDPR)."""
    from src.modules.user.application.consumers.identity_events import (
        anonymize_user_on_identity_deactivated,
    )

    await (
        anonymize_user_on_identity_deactivated.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
        )  # ty:ignore[no-matching-overload]
    )


async def _handle_role_assignment_changed(payload: dict, correlation_id: str | None = None) -> None:
    """Dispatches cache invalidation for affected identity's sessions."""
    from src.modules.identity.application.consumers.role_events import (
        invalidate_permissions_cache_on_role_change,
    )

    await (
        invalidate_permissions_cache_on_role_change.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            identity_id=payload["identity_id"],
        )  # ty:ignore[no-matching-overload]
    )


# Register IAM event mappings
register_event_handler("IdentityRegisteredEvent", _handle_identity_registered)
register_event_handler("IdentityDeactivatedEvent", _handle_identity_deactivated)
register_event_handler("RoleAssignmentChangedEvent", _handle_role_assignment_changed)


# ---------------------------------------------------------------------------
# TaskIQ: Outbox Relay (периодический поллинг)
# ---------------------------------------------------------------------------


@broker.task(
    queue="outbox_relay",
    exchange="taskiq_rpc_exchange",
    routing_key="infrastructure.outbox.relay",
    max_retries=0,
    retry_on_error=False,
    timeout=55,  # 55 секунд: меньше интервала cron (1 мин)
    schedule=[{"cron": "* * * * *", "schedule_id": "outbox_relay_every_minute"}],
)
@inject
async def outbox_relay_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """
    Периодическая задача: забирает батч из Outbox и публикует в брокер.
    Запускается через TaskIQ Scheduler (Beat) каждую минуту.
    """
    try:
        processed = await relay_outbox_batch(
            session_factory=session_factory,
            batch_size=100,
        )
        return {"status": "success", "processed": processed}
    except Exception:
        logger.exception("Outbox Relay: критическая ошибка в цикле поллинга")
        return {"status": "error", "processed": 0}


# ---------------------------------------------------------------------------
# TaskIQ: Outbox Pruning (ежесуточная очистка)
# ---------------------------------------------------------------------------


@broker.task(
    queue="outbox_pruning",
    exchange="taskiq_rpc_exchange",
    routing_key="infrastructure.outbox.pruning",
    max_retries=1,
    retry_on_error=True,
    timeout=120,  # 2 минуты: DELETE может быть тяжёлым
    schedule=[{"cron": "0 3 * * *", "schedule_id": "outbox_pruning_daily_3am"}],
)
@inject
async def outbox_pruning_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """
    Ежесуточная задача: удаляет обработанные Outbox-записи старше 7 дней.
    Запускается через TaskIQ Scheduler (Beat) ежесуточно в 03:00 UTC.
    """
    deleted = await prune_processed_messages(session_factory=session_factory)
    return {"status": "success", "deleted": deleted}
