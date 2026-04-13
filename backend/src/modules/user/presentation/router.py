"""FastAPI router for customer profile endpoints.

Exposes REST API endpoints for reading and updating the authenticated
customer's profile. All endpoints require appropriate permissions enforced
via the Identity module's authentication dependencies.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

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
) -> ProfileResponse:
    """Retrieve the authenticated customer's profile.

    Auto-provisions a minimal Customer record if the async event pipeline
    has not yet created one (race condition on first login).
    """
    try:
        profile = await handler.handle(GetMyProfileQuery(customer_id=auth.identity_id))
    except CustomerNotFoundError:
        await create_handler.handle(
            CreateCustomerCommand(identity_id=auth.identity_id)
        )
        profile = await handler.handle(GetMyProfileQuery(customer_id=auth.identity_id))
    return ProfileResponse(
        id=profile.id,
        profile_email=profile.profile_email,
        first_name=profile.first_name,
        last_name=profile.last_name,
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
) -> MessageResponse:
    """Update the authenticated customer's profile fields.

    Auto-provisions a minimal Customer record if the async event pipeline
    has not yet created one (race condition on first login).
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
        await create_handler.handle(
            CreateCustomerCommand(identity_id=auth.identity_id)
        )
        await handler.handle(command)
    return MessageResponse(message="Profile updated")
