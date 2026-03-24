"""TaskIQ consumers for cross-module Identity events.

Handles events published by the Identity bounded context that require
a reaction in the User module. Routes by account_type to create Customer
or StaffMember profiles.
"""

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.exc import IntegrityError

from src.bootstrap.broker import broker
from src.modules.user.domain.entities import Customer, StaffMember
from src.modules.user.domain.interfaces import (
    ICustomerRepository,
    IStaffMemberRepository,
)
from src.modules.user.domain.services import generate_referral_code
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
async def create_profile_on_identity_registered(
    identity_id: str,
    email: str,
    customer_repo: FromDishka[ICustomerRepository],
    staff_repo: FromDishka[IStaffMemberRepository],
    uow: FromDishka[IUnitOfWork],
    account_type: str = "CUSTOMER",
    invited_by: str | None = None,
    first_name: str = "",
    last_name: str = "",
    username: str | None = None,
) -> dict:
    """Create a profile when an identity registers. Routes by account_type.

    Args:
        identity_id: String UUID of the new identity.
        email: Email from the registration event.
        customer_repo: Injected Customer repository.
        staff_repo: Injected StaffMember repository.
        uow: Injected Unit of Work.
        account_type: CUSTOMER or STAFF.
        invited_by: Identity ID of inviter (for STAFF).
        first_name: First name (for STAFF).
        last_name: Last name (for STAFF).

    Returns:
        Status dict.
    """
    identity_uuid = uuid.UUID(identity_id)

    if account_type == "STAFF":
        return await _create_staff_member(
            identity_uuid,
            email,
            staff_repo,
            uow,
            invited_by=invited_by,
            first_name=first_name,
            last_name=last_name,
        )

    return await _create_customer(
        identity_uuid, email, customer_repo, uow, username=username
    )


async def _create_customer(
    identity_id: uuid.UUID,
    email: str,
    customer_repo: ICustomerRepository,
    uow: IUnitOfWork,
    username: str | None = None,
) -> dict:
    """Create a Customer profile with auto-generated referral code."""
    existing = await customer_repo.get(identity_id)
    if existing:
        logger.info("customer.already_exists", identity_id=str(identity_id))
        return {"status": "skipped", "reason": "already_exists"}

    referral_code = generate_referral_code()
    customer = Customer.create_from_identity(
        identity_id=identity_id,
        profile_email=email,
        referral_code=referral_code,
        username=username,
    )
    async with uow:
        await customer_repo.add(customer)
        uow.register_aggregate(customer)
        await uow.commit()

    logger.info("customer.created_from_event", identity_id=str(identity_id))
    return {"status": "success", "type": "customer"}


async def _create_staff_member(
    identity_id: uuid.UUID,
    email: str,
    staff_repo: IStaffMemberRepository,
    uow: IUnitOfWork,
    invited_by: str | None = None,
    first_name: str = "",
    last_name: str = "",
) -> dict:
    """Create a StaffMember profile."""
    existing = await staff_repo.get(identity_id)
    if existing:
        logger.info("staff_member.already_exists", identity_id=str(identity_id))
        return {"status": "skipped", "reason": "already_exists"}

    invited_by_uuid = uuid.UUID(invited_by) if invited_by else identity_id
    staff = StaffMember.create_from_invitation(
        identity_id=identity_id,
        profile_email=email,
        invited_by=invited_by_uuid,
        first_name=first_name,
        last_name=last_name,
    )
    async with uow:
        await staff_repo.add(staff)
        uow.register_aggregate(staff)
        await uow.commit()

    logger.info("staff_member.created_from_event", identity_id=str(identity_id))
    return {"status": "success", "type": "staff"}


@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="user.identity_deactivated",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def anonymize_customer_on_identity_deactivated(
    identity_id: str,
    customer_repo: FromDishka[ICustomerRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """Anonymize customer PII when an identity is deactivated.

    Staff members are not anonymized (GDPR legitimate interest for
    employment records).

    Args:
        identity_id: String UUID of the deactivated identity.
        customer_repo: Injected Customer repository.
        uow: Injected Unit of Work.

    Returns:
        Status dict.
    """
    identity_uuid = uuid.UUID(identity_id)

    customer = await customer_repo.get(identity_uuid)
    if customer:
        customer.anonymize()
        async with uow:
            await customer_repo.update(customer)
            uow.register_aggregate(customer)
            await uow.commit()
        logger.info("customer.anonymized", identity_id=identity_id)
        return {"status": "success", "type": "customer"}

    logger.warning("customer.not_found_for_anonymization", identity_id=identity_id)
    return {"status": "skipped", "reason": "not_found"}


@broker.task(
    queue_name="user.linked_account_created",
    retry_on_error=True,
    timeout=30,
)
@inject
async def on_linked_account_created(
    identity_id: str,
    provider: str,
    customer_repo: FromDishka[ICustomerRepository],
    uow: FromDishka[IUnitOfWork],
    provider_metadata: dict | None = None,
    start_param: str | None = None,
    is_new_identity: bool = True,
    provider_sub_id: str = "",
) -> dict:
    """Handle LinkedAccountCreatedEvent -- create or enrich Customer."""
    identity_uuid = uuid.UUID(identity_id)
    provider_metadata = provider_metadata or {}

    if is_new_identity:
        existing = await customer_repo.get(identity_uuid)
        if existing:
            logger.info("customer.already_exists", identity_id=identity_id)
            return {"status": "skipped", "reason": "already_exists"}

        referred_by: uuid.UUID | None = None
        if start_param:
            referrer = await customer_repo.get_by_referral_code(start_param)
            referred_by = referrer.id if referrer else None

        customer = Customer.create_from_identity(
            identity_id=identity_uuid,
            first_name=provider_metadata.get("first_name", ""),
            last_name=provider_metadata.get("last_name", ""),
            username=provider_metadata.get("username"),
            referral_code=generate_referral_code(),
            referred_by=referred_by,
        )

        try:
            async with uow:
                await customer_repo.add(customer)
                uow.register_aggregate(customer)
                await uow.commit()
        except IntegrityError:
            logger.warning(
                "customer.username_conflict",
                identity_id=identity_id,
                username=provider_metadata.get("username"),
            )
            customer = Customer.create_from_identity(
                identity_id=identity_uuid,
                first_name=provider_metadata.get("first_name", ""),
                last_name=provider_metadata.get("last_name", ""),
                username=None,
                referral_code=generate_referral_code(),
                referred_by=referred_by,
            )
            async with uow:
                await customer_repo.add(customer)
                uow.register_aggregate(customer)
                await uow.commit()

        logger.info(
            "customer.created_from_provider",
            identity_id=identity_id,
            provider=provider,
            referred_by=str(referred_by) if referred_by else None,
        )
        return {"status": "success", "type": "customer"}
    else:
        customer = await customer_repo.get(identity_uuid)
        if customer and not customer.username:
            username = provider_metadata.get("username")
            if username:
                async with uow:
                    customer.update_profile(username=username)
                    await customer_repo.update(customer)
                    await uow.commit()
                logger.info(
                    "customer.username_enriched",
                    identity_id=identity_id,
                    provider=provider,
                )
        return {"status": "success", "type": "enriched"}
