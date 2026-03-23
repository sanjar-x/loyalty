"""Account management API endpoints for the Identity module.

Provides self-service endpoints for authenticated users to manage their
own account: deactivation (GDPR) and session listing.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

from src.modules.identity.application.commands.change_password import (
    ChangePasswordCommand,
    ChangePasswordHandler,
)
from src.modules.identity.application.commands.deactivate_identity import (
    DeactivateIdentityCommand,
    DeactivateIdentityHandler,
)
from src.modules.identity.application.queries.get_my_sessions import (
    GetMySessionsHandler,
    GetMySessionsQuery,
    SessionInfo,
)
from src.modules.identity.presentation.dependencies import Auth, RequirePermission
from src.modules.identity.presentation.schemas import (
    ChangePasswordRequest,
    MessageResponse,
)

identity_account_router = APIRouter(
    prefix="/profile",
    tags=["Account"],
    route_class=DishkaRoute,
)


@identity_account_router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete my account (GDPR)",
    dependencies=[Depends(RequirePermission("profile:delete"))],
)
async def delete_my_account(
    auth: Auth,
    handler: FromDishka[DeactivateIdentityHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    """Deactivate the authenticated user's account.

    Triggers identity deactivation, session revocation, and downstream
    GDPR PII anonymization via domain events.

    Args:
        auth: The authenticated context from the JWT.
        handler: The deactivate identity command handler.

    Returns:
        A message confirming account deactivation.
    """
    command = DeactivateIdentityCommand(
        identity_id=auth.identity_id,
        reason="user_request",
    )
    await handler.handle(command)
    return MessageResponse(message="Account deactivated. PII will be anonymized.")


@identity_account_router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="Change my password",
)
async def change_password(
    body: ChangePasswordRequest,
    auth: Auth,
    handler: FromDishka[ChangePasswordHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    """Change the authenticated user's password.

    Verifies the current password, sets the new one, and revokes all
    other sessions for security.

    Args:
        body: The password change request with current and new passwords.
        auth: The authenticated context from the JWT.
        handler: The change password command handler.

    Returns:
        A message confirming password change.
    """
    command = ChangePasswordCommand(
        identity_id=auth.identity_id,
        current_session_id=auth.session_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    await handler.handle(command)
    return MessageResponse(
        message="Password changed successfully. Other sessions have been revoked."
    )


@identity_account_router.get(
    "/me/sessions",
    response_model=list[SessionInfo],
    summary="List my active sessions",
)
async def get_my_sessions(
    auth: Auth,
    handler: FromDishka[GetMySessionsHandler] = ...,  # type: ignore[assignment]
) -> list[SessionInfo]:
    """List the authenticated user's active sessions.

    Returns all non-revoked sessions, marking the current one.

    Args:
        auth: The authenticated context from the JWT.
        handler: The get-my-sessions query handler.

    Returns:
        List of active session summaries.
    """
    query = GetMySessionsQuery(
        identity_id=auth.identity_id,
        current_session_id=auth.session_id,
    )
    return await handler.handle(query)
