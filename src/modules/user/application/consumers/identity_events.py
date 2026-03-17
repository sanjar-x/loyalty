# src/modules/user/application/consumers/identity_events.py
"""
Consumers for cross-module events from identity → user.

- IdentityRegisteredEvent → CreateUserHandler (creates User with Shared PK)
- IdentityDeactivatedEvent → AnonymizeUserHandler (GDPR: PII cleanup)
"""

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.uow import IUnitOfWork

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
    user_repo: FromDishka[IUserRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """Create User row with Shared PK when identity registers."""
    identity_uuid = uuid.UUID(identity_id)

    existing = await user_repo.get(identity_uuid)
    if existing:
        logger.info("user.already_exists", identity_id=identity_id)
        return {"status": "skipped", "reason": "already_exists"}

    user = User.create_from_identity(
        identity_id=identity_uuid,
        profile_email=email,
    )
    async with uow:
        await user_repo.add(user)
        uow.register_aggregate(user)
        await uow.commit()

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
    user_repo: FromDishka[IUserRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """GDPR: Anonymize user PII when identity is deactivated."""
    identity_uuid = uuid.UUID(identity_id)

    user = await user_repo.get(identity_uuid)
    if not user:
        logger.warning("user.not_found_for_anonymization", identity_id=identity_id)
        return {"status": "skipped", "reason": "user_not_found"}

    user.anonymize()
    async with uow:
        await user_repo.update(user)
        uow.register_aggregate(user)
        await uow.commit()

    logger.info("user.anonymized", identity_id=identity_id)
    return {"status": "success"}
