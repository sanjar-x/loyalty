import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Достаточно указать один раз на весь файл
pytestmark = pytest.mark.asyncio


async def test_create_brand_e2e_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    payload = {
        "name": "E2E Brand",
        "slug": "e2e-brand",
        "logo": {
            "filename": "test.png",
            "content_type": "image/png",
            "size": 1024,
        },
    }

    # IBlobStorage.generate_presigned_put_url — stateless, работает напрямую с S3
    response = await async_client.post("/api/v1/catalog/brands", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "brand_id" in data
    assert data["object_key"].startswith("raw_uploads/catalog/brands/")
    assert data["presigned_upload_url"] is not None


async def test_confirm_brand_logo_e2e_success(
    async_client: AsyncClient, db_session: AsyncSession
):
    # 1. Создаем бренд (реальный запрос)
    create_payload = {
        "name": "Brand Confirm",
        "slug": "brand-confirm",
        "logo": {"filename": "test.png", "content_type": "image/png", "size": 100},
    }
    create_res = await async_client.post("/api/v1/catalog/brands", json=create_payload)
    brand_data = create_res.json()
    brand_id = brand_data["brand_id"]

    # 2. Подтверждаем загрузку — событие записывается в Outbox атомарно
    confirm_payload = {}
    response = await async_client.post(
        f"/api/v1/catalog/brands/{brand_id}/logo/confirm", json=confirm_payload
    )

    assert response.status_code == 202
    assert response.json() == {"message": "Запрос на обработку логотипа принят"}
