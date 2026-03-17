# src/modules/identity/presentation/router_account.py
"""Account management endpoints owned by the identity module."""

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
from src.shared.interfaces.auth import AuthContext

identity_account_router = APIRouter(
    prefix="/users",
    tags=["Account Management"],
    route_class=DishkaRoute,
)


@identity_account_router.delete(
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


@identity_account_router.get(
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
