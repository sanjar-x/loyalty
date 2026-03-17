"""TaskIQ consumers for cross-module Identity events.

Handles events published by the Identity bounded context that require
a reaction in the User module:

- IdentityRegisteredEvent: Creates a User with a shared primary key.
- IdentityDeactivatedEvent: Anonymizes user PII for GDPR compliance.
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
    """Create a User record when an identity registers.

    Listens for IdentityRegisteredEvent via the message broker and creates
    a new User aggregate with a shared primary key. The operation is
    idempotent: if the user already exists, creation is skipped.

    Args:
        identity_id: String representation of the Identity UUID.
        email: The email address from the registration event.
        user_repo: Injected User repository.
        uow: Injected Unit of Work for transactional consistency.

    Returns:
        A status dict indicating ``"success"`` or ``"skipped"``.
    """
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
    """Anonymize user PII when an identity is deactivated.

    Listens for IdentityDeactivatedEvent via the message broker and
    performs GDPR-compliant anonymization of all personal data. The
    operation is idempotent: if the user is not found, it is skipped.

    Args:
        identity_id: String representation of the Identity UUID.
        user_repo: Injected User repository.
        uow: Injected Unit of Work for transactional consistency.

    Returns:
        A status dict indicating ``"success"`` or ``"skipped"``.
    """
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
