# tests/e2e/api/v1/test_users.py
"""E2E tests for /profile/* endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_get_my_profile_returns_401_without_token(
    async_client: AsyncClient, db_session: AsyncSession
):
    response = await async_client.get("/api/v1/profile/me")
    assert response.status_code == 401
