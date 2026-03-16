# src/modules/user/application/consumers/identity_events.py
"""
Consumers for cross-module events from identity → user.

- IdentityRegisteredEvent → CreateUserHandler (creates User with Shared PK)
- IdentityDeactivatedEvent → AnonymizeUserHandler (GDPR: PII cleanup)
"""
import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker

logger = structlog.get_logger(__name__)


@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="user.identity_registered",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def create_user_on_identity_registered(
    identity_id: str,
    email: str,
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Create User row with Shared PK when identity registers."""
    from src.modules.user.domain.entities import User
    from src.modules.user.infrastructure.repositories.user_repository import (
        UserRepository,
    )

    identity_uuid = uuid.UUID(identity_id)

    async with session_factory() as session:
        async with session.begin():
            repo = UserRepository(session)

            # Idempotency check: user may already exist (retry scenario)
            existing = await repo.get(identity_uuid)
            if existing:
                logger.info(
                    "user.already_exists",
                    identity_id=identity_id,
                )
                return {"status": "skipped", "reason": "already_exists"}

            user = User.create_from_identity(
                identity_id=identity_uuid,
                profile_email=email,
            )
            await repo.add(user)

    logger.info("user.created_from_event", identity_id=identity_id)
    return {"status": "success"}


@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="user.identity_deactivated",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def anonymize_user_on_identity_deactivated(
    identity_id: str,
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """GDPR: Anonymize user PII when identity is deactivated."""
    from src.modules.user.infrastructure.repositories.user_repository import (
        UserRepository,
    )

    identity_uuid = uuid.UUID(identity_id)

    async with session_factory() as session:
        async with session.begin():
            repo = UserRepository(session)
            user = await repo.get(identity_uuid)

            if not user:
                logger.warning(
                    "user.not_found_for_anonymization",
                    identity_id=identity_id,
                )
                return {"status": "skipped", "reason": "user_not_found"}

            user.anonymize()
            await repo.update(user)

    logger.info("user.anonymized", identity_id=identity_id)
    return {"status": "success"}
