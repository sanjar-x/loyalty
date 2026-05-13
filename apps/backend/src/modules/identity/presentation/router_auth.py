"""Authentication API endpoints for the Identity module.

Provides public endpoints for registration, login, token refresh, and
logout operations. All endpoints use Dishka for dependency injection.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, status

from src.modules.identity.application.commands.login import LoginCommand, LoginHandler
from src.modules.identity.application.commands.login_telegram import (
    LoginTelegramCommand,
    LoginTelegramHandler,
)
from src.modules.identity.application.commands.logout import (
    LogoutCommand,
    LogoutHandler,
)
from src.modules.identity.application.commands.logout_all import (
    LogoutAllCommand,
    LogoutAllHandler,
)
from src.modules.identity.application.commands.refresh_token import (
    RefreshTokenCommand,
    RefreshTokenHandler,
)
from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.presentation.dependencies import Auth
from src.modules.identity.presentation.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TelegramTokenResponse,
    TokenResponse,
)
from src.shared.exceptions import UnauthorizedError

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    route_class=DishkaRoute,
)


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    summary="Register new identity",
)
async def register(
    body: RegisterRequest,
    handler: FromDishka[RegisterHandler],
) -> RegisterResponse:
    """Register a new identity with email and password.

    Args:
        body: The registration request payload.
        handler: The register command handler.

    Returns:
        The new identity's UUID and a confirmation message.
    """
    command = RegisterCommand(
        email=body.email, password=body.password, username=body.username
    )
    result = await handler.handle(command)
    return RegisterResponse(identity_id=result.identity_id)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email/username and password",
)
async def login(
    body: LoginRequest,
    request: Request,
    handler: FromDishka[LoginHandler],
) -> TokenResponse:
    """Authenticate with email or username and password, returning a token pair.

    Args:
        body: The login request payload.
        request: The FastAPI request (for extracting client IP and User-Agent).
        handler: The login command handler.

    Returns:
        An access/refresh token pair.
    """
    command = LoginCommand(
        login=body.login,
        password=body.password,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
    )
    result = await handler.handle(command)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )


@auth_router.post(
    "/telegram",
    response_model=TelegramTokenResponse,
    summary="Authenticate via Telegram Mini App",
)
async def login_telegram(
    request: Request,
    handler: FromDishka[LoginTelegramHandler],
) -> TelegramTokenResponse:
    """Authenticate using Telegram Mini App initData.

    The initData must be sent in the Authorization header:
        Authorization: tma <raw initData string>
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("tma "):
        raise UnauthorizedError(
            message="Expected Authorization: tma <initData>",
            error_code="INVALID_AUTH_SCHEME",
        )
    init_data_raw = auth_header[4:]

    command = LoginTelegramCommand(
        init_data_raw=init_data_raw,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
    )
    result = await handler.handle(command)

    return TelegramTokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        is_new_user=result.is_new_user,
    )


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    handler: FromDishka[RefreshTokenHandler],
) -> TokenResponse:
    """Rotate the refresh token and obtain a new access/refresh token pair.

    Args:
        body: The refresh token request payload.
        request: The FastAPI request (for extracting client IP and User-Agent).
        handler: The refresh token command handler.

    Returns:
        A new access/refresh token pair.
    """
    command = RefreshTokenCommand(
        refresh_token=body.refresh_token,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
    )
    result = await handler.handle(command)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )


@auth_router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current session",
)
async def logout(
    auth: Auth,
    handler: FromDishka[LogoutHandler],
) -> MessageResponse:
    """Revoke the current session.

    Args:
        auth: The authenticated context from the JWT.
        handler: The logout command handler.

    Returns:
        A confirmation message.
    """
    await handler.handle(LogoutCommand(session_id=auth.session_id))
    return MessageResponse(message="Logged out successfully")


@auth_router.post(
    "/logout/all",
    response_model=MessageResponse,
    summary="Logout all sessions",
)
async def logout_all(
    auth: Auth,
    handler: FromDishka[LogoutAllHandler],  # type: ignore[assignment]
) -> MessageResponse:
    """Revoke all sessions for the authenticated identity.

    Args:
        auth: The authenticated context from the JWT.
        handler: The logout-all command handler.

    Returns:
        A confirmation message.
    """
    await handler.handle(LogoutAllCommand(identity_id=auth.identity_id))
    return MessageResponse(message="All sessions logged out")
