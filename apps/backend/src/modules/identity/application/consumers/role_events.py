"""Consumer for invalidating Redis permission cache on role changes.

Triggered by RoleAssignmentChangedEvent via the Outbox Relay. The
session_roles table is already updated synchronously by the command handlers
(AssignRoleHandler / RevokeRoleHandler). This consumer only handles cache
clearing -- the next request triggers a fresh CTE-based permission resolution.
"""

import uuid
from datetime import UTC, datetime

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.shared.interfaces.security import IPermissionResolver

logger = structlog.get_logger(__name__)

_ACTIVE_SESSIONS_SQL = text(
    "SELECT id FROM sessions "
    "WHERE identity_id = :identity_id AND is_revoked = false AND expires_at > :now"
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
    permission_resolver: FromDishka[IPermissionResolver],
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Invalidate cached permissions for all active sessions of an identity.

    Called asynchronously when a role assignment changes. Queries active
    session IDs and delegates cache invalidation to the PermissionResolver
    (single round-trip bulk delete).

    Args:
        identity_id: String UUID of the affected identity.
        permission_resolver: Permission resolver for cache invalidation.
        session_factory: Async SQLAlchemy session factory for querying sessions.

    Returns:
        A dict with "status" and "sessions_invalidated" count.
    """
    identity_uuid = uuid.UUID(identity_id)

    async with session_factory() as session:
        result = await session.execute(
            _ACTIVE_SESSIONS_SQL,
            {"identity_id": identity_uuid, "now": datetime.now(UTC)},
        )
        session_ids = [row[0] for row in result.all()]

    await permission_resolver.invalidate_many(session_ids)

    logger.info(
        "permissions_cache.invalidated",
        identity_id=str(identity_uuid),
        sessions_affected=len(session_ids),
    )

    return {"status": "success", "sessions_invalidated": len(session_ids)}
