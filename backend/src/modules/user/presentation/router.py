"""FastAPI router for User profile endpoints.

Exposes REST API endpoints for reading and updating the authenticated
user's profile. All endpoints require appropriate permissions enforced
via the Identity module's authentication dependencies.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    get_auth_context,
)
from src.modules.identity.presentation.schemas import MessageResponse
from src.modules.user.application.commands.update_profile import (
    UpdateProfileCommand,
    UpdateProfileHandler,
)
from src.modules.user.application.queries.get_my_profile import (
    GetMyProfileHandler,
    GetMyProfileQuery,
)
from src.modules.user.presentation.schemas import (
    UpdateProfileRequest,
    UserProfileResponse,
)
from src.shared.interfaces.auth import AuthContext

user_router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    route_class=DishkaRoute,
)


@user_router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get my profile",
    dependencies=[Depends(RequirePermission("profile:read"))],
)
async def get_my_profile(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[GetMyProfileHandler] = ...,  # type: ignore[assignment]
) -> UserProfileResponse:
    """Retrieve the authenticated user's profile.

    Returns the full profile data for the currently authenticated user,
    identified by the auth context's identity ID.

    Args:
        auth: The authenticated user's context with identity information.
        handler: Injected query handler for profile retrieval.

    Returns:
        The user's profile data including name, email, and phone.
    """
    profile = await handler.handle(GetMyProfileQuery(user_id=auth.identity_id))
    return UserProfileResponse(
        id=profile.id,
        profile_email=profile.profile_email,
        first_name=profile.first_name,
        last_name=profile.last_name,
        phone=profile.phone,
    )


@user_router.patch(
    "/me",
    response_model=MessageResponse,
    summary="Update my profile",
    dependencies=[Depends(RequirePermission("profile:update"))],
)
async def update_profile(
    body: UpdateProfileRequest,
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[UpdateProfileHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    """Update the authenticated user's profile fields.

    Applies a partial update to the user's profile. Only fields included
    in the request body (non-None) will be modified.

    Args:
        body: The request body containing fields to update.
        auth: The authenticated user's context with identity information.
        handler: Injected command handler for profile updates.

    Returns:
        A confirmation message indicating the profile was updated.
    """
    command = UpdateProfileCommand(
        user_id=auth.identity_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        profile_email=body.profile_email,
    )
    await handler.handle(command)
    return MessageResponse(message="Profile updated")
