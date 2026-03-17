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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.shared.interfaces.cache import ICacheService

logger = structlog.get_logger(__name__)

_ACTIVE_SESSIONS_SQL = text(
    "SELECT id FROM sessions WHERE identity_id = :identity_id AND is_revoked = false"
)


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
    cache: FromDishka[ICacheService],
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    identity_uuid = uuid.UUID(identity_id)

    async with session_factory() as session:
        result = await session.execute(_ACTIVE_SESSIONS_SQL, {"identity_id": identity_uuid})
        session_ids = [row[0] for row in result.all()]

    deleted_count = 0
    for sid in session_ids:
        cache_key = f"perms:{sid}"
        await cache.delete(cache_key)
        deleted_count += 1

    logger.info(
        "permissions_cache.invalidated",
        identity_id=str(identity_uuid),
        sessions_affected=deleted_count,
    )

    return {"status": "success", "sessions_invalidated": deleted_count}
