# tests/e2e/api/v1/test_auth.py
"""E2E tests for /auth/* endpoints."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_register_returns_201_with_identity_id(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"reg-{uuid.uuid4().hex[:8]}@test.com"
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cure!Pass"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "identityId" in data


async def test_register_returns_409_when_email_exists(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"dupe-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cure!Pass"},
    )
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cure!Pass"},
    )
    assert response.status_code == 409


async def test_login_returns_200_with_tokens(async_client: AsyncClient, db_session: AsyncSession):
    email = f"login-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cure!Pass"},
    )
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "S3cure!Pass"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data


async def test_login_returns_401_for_wrong_password(
    async_client: AsyncClient, db_session: AsyncSession
):
    email = f"bad-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "S3cure!Pass"},
    )
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
