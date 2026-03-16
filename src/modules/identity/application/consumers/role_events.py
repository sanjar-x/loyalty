# src/modules/identity/application/consumers/role_events.py
"""
Consumer: Invalidate Redis permission cache when roles change.

Triggered by RoleAssignmentChangedEvent via Outbox Relay.
session_roles are already updated synchronously by AssignRoleHandler/RevokeRoleHandler.
This consumer only handles cache clearing — next request triggers fresh CTE.
"""
import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.infrastructure.cache.redis import RedisService
from src.modules.identity.infrastructure.models import SessionModel

logger = structlog.get_logger(__name__)


@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="identity.role_assignment_changed",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def invalidate_permissions_cache_on_role_change(
    identity_id: str,
    redis: FromDishka[RedisService],
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    identity_uuid = uuid.UUID(identity_id)

    async with session_factory() as session:
        # Find all active (non-revoked, non-expired) sessions for this identity
        stmt = select(SessionModel.id).where(
            SessionModel.identity_id == identity_uuid,
            SessionModel.is_revoked.is_(False),
        )
        result = await session.execute(stmt)
        session_ids = [row[0] for row in result.all()]

    # Delete permission cache keys
    deleted_count = 0
    for sid in session_ids:
        cache_key = f"perms:{sid}"
        await redis.delete(cache_key)
        deleted_count += 1

    logger.info(
        "permissions_cache.invalidated",
        identity_id=str(identity_uuid),
        sessions_affected=deleted_count,
    )

    return {"status": "success", "sessions_invalidated": deleted_count}
