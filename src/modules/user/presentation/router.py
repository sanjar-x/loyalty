# src/modules/user/presentation/router.py
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

from src.modules.identity.application.commands.deactivate_identity import (
    DeactivateIdentityCommand,
    DeactivateIdentityHandler,
)
from src.modules.identity.application.queries.get_my_sessions import (
    GetMySessionsHandler,
    GetMySessionsQuery,
    SessionInfo,
)
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
    prefix="/users",
    tags=["User Profile"],
    route_class=DishkaRoute,
)


@user_router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get my profile",
    dependencies=[Depends(RequirePermission("users:read"))],
)
async def get_my_profile(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[GetMyProfileHandler] = ...,  # type: ignore[assignment]
) -> UserProfileResponse:
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
    dependencies=[Depends(RequirePermission("users:update"))],
)
async def update_profile(
    body: UpdateProfileRequest,
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[UpdateProfileHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    command = UpdateProfileCommand(
        user_id=auth.identity_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        profile_email=body.profile_email,
    )
    await handler.handle(command)
    return MessageResponse(message="Profile updated")


@user_router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete my account (GDPR)",
    dependencies=[Depends(RequirePermission("users:delete"))],
)
async def delete_my_account(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[DeactivateIdentityHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    command = DeactivateIdentityCommand(
        identity_id=auth.identity_id,
        reason="user_request",
    )
    await handler.handle(command)
    return MessageResponse(message="Account deactivated. PII will be anonymized.")


@user_router.get(
    "/me/sessions",
    response_model=list[SessionInfo],
    summary="List my active sessions",
)
async def get_my_sessions(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[GetMySessionsHandler] = ...,  # type: ignore[assignment]
) -> list[SessionInfo]:
    query = GetMySessionsQuery(
        identity_id=auth.identity_id,
        current_session_id=auth.session_id,
    )
    return await handler.handle(query)
