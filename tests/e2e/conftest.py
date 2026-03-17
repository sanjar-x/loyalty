# tests/e2e/conftest.py
import uuid
from collections.abc import AsyncIterable
from types import AsyncGeneratorType
from unittest.mock import patch

import pytest
from dishka import AsyncContainer
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.web import create_app

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
async def fastapi_app(app_container: AsyncContainer) -> AsyncGeneratorType:
    with patch("src.bootstrap.web.create_container", return_value=app_container):
        app = create_app()
        yield app


@pytest.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncIterable[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_client(
    async_client: AsyncClient, db_session: AsyncSession
) -> AsyncGeneratorType:
    """Register a user, login, and return a client with Authorization header."""
    email = f"e2e-{uuid.uuid4().hex[:8]}@test.com"
    password = "S3cure!TestPass"

    # Register
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    # Login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    tokens = login_resp.json()
    access_token = tokens["access_token"]

    # Return client with auth header set
    async_client.headers["Authorization"] = f"Bearer {access_token}"
    yield async_client
    # Clean up header after test
    async_client.headers.pop("Authorization", None)
