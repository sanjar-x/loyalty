import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_create_category_e2e_success(
    async_client: AsyncClient, db_session: AsyncSession
):
    payload = {"name": "Computers", "slug": "computers", "parent_id": None}
    response = await async_client.post("/api/v1/catalog/categories", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "id" in data


async def test_create_category_e2e_validation_error(
    async_client: AsyncClient, db_session: AsyncSession
):
    payload = {
        "name": "",  # invalid empty name
        "slug": "c",  # invalid too short slug
        "parent_id": None,
    }
    response = await async_client.post("/api/v1/catalog/categories", json=payload)

    # Assert
    assert response.status_code == 422
