"""FastAPI router for customer profile endpoints.

Exposes REST API endpoints for reading and updating the authenticated
customer's profile. All endpoints require appropriate permissions enforced
via the Identity module's authentication dependencies.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.presentation.dependencies import Auth, RequirePermission
from src.modules.identity.presentation.schemas import MessageResponse
from src.modules.user.application.commands.create_customer import (
    CreateCustomerCommand,
    CreateCustomerHandler,
)
from src.modules.user.application.commands.update_profile import (
    UpdateProfileCommand,
    UpdateProfileHandler,
)
from src.modules.user.application.queries.get_my_profile import (
    GetMyProfileHandler,
    GetMyProfileQuery,
)
from src.modules.user.domain.exceptions import CustomerNotFoundError
from src.modules.user.presentation.schemas import (
    ProfileResponse,
    UpdateProfileRequest,
)

profile_router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    route_class=DishkaRoute,
)

_LINKED_ACCOUNT_METADATA_SQL = text(
    "SELECT provider_metadata FROM linked_accounts "
    "WHERE identity_id = :identity_id "
    "ORDER BY created_at DESC LIMIT 1"
)


async def _fetch_provider_metadata(
    session: AsyncSession, identity_id: uuid.UUID
) -> dict:
    """Fetch provider_metadata from linked_accounts for auto-provisioning.

    Returns the most recent linked account's metadata (Telegram/OIDC)
    so that first_name, last_name, and username can be populated
    on the auto-created Customer record.
    """
    result = await session.execute(
        _LINKED_ACCOUNT_METADATA_SQL, {"identity_id": identity_id}
    )
    row = result.mappings().first()
    if row and row["provider_metadata"]:
        return dict(row["provider_metadata"])
    return {}


@profile_router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Get my profile",
    dependencies=[Depends(RequirePermission("profile:read"))],
)
async def get_my_profile(
    auth: Auth,
    handler: FromDishka[GetMyProfileHandler],
    create_handler: FromDishka[CreateCustomerHandler],
    session: FromDishka[AsyncSession],
) -> ProfileResponse:
    """Retrieve the authenticated customer's profile.

    Auto-provisions a Customer record with linked-account metadata
    if the async event pipeline has not yet created one.
    """
    try:
        profile = await handler.handle(GetMyProfileQuery(customer_id=auth.identity_id))
    except CustomerNotFoundError:
        metadata = await _fetch_provider_metadata(session, auth.identity_id)
        await create_handler.handle(
            CreateCustomerCommand(
                identity_id=auth.identity_id,
                first_name=metadata.get("first_name", ""),
                last_name=metadata.get("last_name", ""),
                username=metadata.get("username"),
                photo_url=metadata.get("photo_url"),
            )
        )
        profile = await handler.handle(GetMyProfileQuery(customer_id=auth.identity_id))
    return ProfileResponse(
        id=profile.id,
        profile_email=profile.profile_email,
        first_name=profile.first_name,
        last_name=profile.last_name,
        username=profile.username,
        photo_url=profile.photo_url,
        phone=profile.phone,
    )


@profile_router.patch(
    "/me",
    response_model=MessageResponse,
    summary="Update my profile",
    dependencies=[Depends(RequirePermission("profile:update"))],
)
async def update_profile(
    body: UpdateProfileRequest,
    auth: Auth,
    handler: FromDishka[UpdateProfileHandler],
    create_handler: FromDishka[CreateCustomerHandler],
    session: FromDishka[AsyncSession],
) -> MessageResponse:
    """Update the authenticated customer's profile fields.

    Auto-provisions a Customer record with linked-account metadata
    if the async event pipeline has not yet created one.
    """
    command = UpdateProfileCommand(
        customer_id=auth.identity_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        profile_email=body.profile_email,
    )
    try:
        await handler.handle(command)
    except CustomerNotFoundError:
        metadata = await _fetch_provider_metadata(session, auth.identity_id)
        await create_handler.handle(
            CreateCustomerCommand(
                identity_id=auth.identity_id,
                first_name=metadata.get("first_name", ""),
                last_name=metadata.get("last_name", ""),
                username=metadata.get("username"),
                photo_url=metadata.get("photo_url"),
            )
        )
        await handler.handle(command)
    return MessageResponse(message="Profile updated")
