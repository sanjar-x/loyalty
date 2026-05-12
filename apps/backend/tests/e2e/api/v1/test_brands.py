import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_create_brand_e2e_success(
    admin_client: AsyncClient,
    db_session: AsyncSession,
):
    payload = {
        "name": "E2E Brand",
        "slug": "e2e-brand",
        "logoUrl": "https://cdn.example.com/brands/e2e.webp",
    }

    response = await admin_client.post("/api/v1/catalog/brands", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
