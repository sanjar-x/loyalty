import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_create_category_e2e_success(admin_client: AsyncClient, db_session: AsyncSession):
    payload = {"name": "Computers", "slug": "computers", "parentId": None}
    response = await admin_client.post("/api/v1/catalog/categories", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data


async def test_create_category_e2e_validation_error(
    admin_client: AsyncClient, db_session: AsyncSession
):
    payload = {
        "name": "",  # invalid empty name
        "slug": "c",  # invalid too short slug
        "parentId": None,
    }
    response = await admin_client.post("/api/v1/catalog/categories", json=payload)

    assert response.status_code == 422
