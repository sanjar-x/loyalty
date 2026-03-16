# src/modules/identity/presentation/router_auth.py
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Request, status

from src.modules.identity.application.commands.login import LoginCommand, LoginHandler
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
from src.modules.identity.presentation.dependencies import get_auth_context
from src.modules.identity.presentation.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from src.shared.interfaces.auth import AuthContext

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
    command = RegisterCommand(email=body.email, password=body.password)
    result = await handler.handle(command)
    return RegisterResponse(identity_id=result.identity_id)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
async def login(
    body: LoginRequest,
    request: Request,
    handler: FromDishka[LoginHandler],
) -> TokenResponse:
    command = LoginCommand(
        email=body.email,
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
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    handler: FromDishka[RefreshTokenHandler],
) -> TokenResponse:
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
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[LogoutHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    await handler.handle(LogoutCommand(session_id=auth.session_id))
    return MessageResponse(message="Logged out successfully")


@auth_router.post(
    "/logout/all",
    response_model=MessageResponse,
    summary="Logout all sessions",
)
async def logout_all(
    auth: AuthContext = Depends(get_auth_context),
    handler: FromDishka[LogoutAllHandler] = ...,  # type: ignore[assignment]
) -> MessageResponse:
    await handler.handle(LogoutAllCommand(identity_id=auth.identity_id))
    return MessageResponse(message="All sessions logged out")
