# tests/integration/modules/identity/application/commands/test_login.py
"""Integration tests for LoginHandler."""

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.commands.login import (
    LoginCommand,
    LoginHandler,
)
from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.domain.exceptions import InvalidCredentialsError


async def test_login_returns_tokens_for_valid_credentials(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Register first
    async with app_container() as request:
        reg_handler = await request.get(RegisterHandler)
        await reg_handler.handle(
            RegisterCommand(email="login@example.com", password="S3cure!Pass")
        )

    # Login
    async with app_container() as request:
        login_handler = await request.get(LoginHandler)
        result = await login_handler.handle(
            LoginCommand(
                login="login@example.com",
                password="S3cure!Pass",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
            )
        )

    assert result.access_token is not None
    assert result.refresh_token is not None


async def test_login_raises_invalid_credentials_for_wrong_password(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        reg_handler = await request.get(RegisterHandler)
        await reg_handler.handle(
            RegisterCommand(email="wrongpw@example.com", password="S3cure!Pass")
        )

    with pytest.raises(InvalidCredentialsError):
        async with app_container() as request:
            handler = await request.get(LoginHandler)
            await handler.handle(
                LoginCommand(
                    login="wrongpw@example.com",
                    password="WrongPassword!",
                    ip_address="127.0.0.1",
                    user_agent="TestAgent/1.0",
                )
            )
