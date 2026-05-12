"""Public staff invitation router.

Provides unauthenticated endpoints for validating and accepting staff
invitations. These endpoints are used by the invitation acceptance flow
where the invitee does not yet have an account.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request

from src.modules.identity.application.commands.accept_staff_invitation import (
    AcceptStaffInvitationCommand,
    AcceptStaffInvitationHandler,
)
from src.modules.identity.application.queries.validate_invitation import (
    ValidateInvitationHandler,
    ValidateInvitationQuery,
)
from src.modules.identity.presentation.schemas import (
    AcceptInvitationRequest,
    InvitationInfoResponse,
    TokenResponse,
)

invitation_router = APIRouter(
    prefix="/invitations",
    tags=["Invitations"],
    route_class=DishkaRoute,
)


@invitation_router.get(
    "/{token}/validate",
    response_model=InvitationInfoResponse,
    summary="Validate an invitation token",
)
async def validate_invitation(
    token: str,
    handler: FromDishka[ValidateInvitationHandler],
) -> InvitationInfoResponse:
    """Validate a staff invitation token and return invitation details.

    This is a public endpoint (no authentication required). It checks that the
    token corresponds to a valid, pending, non-expired invitation.

    Args:
        token: The raw invitation token from the URL.
        handler: The validate-invitation query handler.

    Returns:
        Invitation info including email, roles, and expiry.
    """
    result = await handler.handle(ValidateInvitationQuery(raw_token=token))
    return InvitationInfoResponse(
        email=result.email,
        roles=result.roles,
        expires_at=result.expires_at,
    )


@invitation_router.post(
    "/{token}/accept",
    response_model=TokenResponse,
    summary="Accept a staff invitation",
)
async def accept_invitation(
    token: str,
    body: AcceptInvitationRequest,
    request: Request,
    handler: FromDishka[AcceptStaffInvitationHandler],
) -> TokenResponse:
    """Accept a staff invitation and create a new staff account.

    This is a public endpoint (no authentication required). It creates a new
    staff identity, assigns pre-defined roles, and returns authentication tokens.

    Args:
        token: The raw invitation token from the URL.
        body: The acceptance request with password and optional name fields.
        request: The incoming HTTP request (for IP and User-Agent).
        handler: The accept-staff-invitation command handler.

    Returns:
        Access and refresh tokens for the newly created staff account.
    """
    result = await handler.handle(
        AcceptStaffInvitationCommand(
            raw_token=token,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
    )
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )
