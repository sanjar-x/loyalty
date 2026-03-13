import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category_e2e_success(async_client: AsyncClient):
    payload = {"name": "Computers", "slug": "computers", "parent_id": None}
    response = await async_client.post("/api/v1/catalog/categories", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Computers"
    assert data["slug"] == "computers"
    assert data["level"] == 0


@pytest.mark.asyncio
async def test_create_category_e2e_validation_error(async_client: AsyncClient):
    payload = {
        "name": "",  # invalid empty name
        "slug": "c",  # invalid too short slug
        "parent_id": None,
    }
    response = await async_client.post("/api/v1/catalog/categories", json=payload)

    # Assert
    assert response.status_code == 422
