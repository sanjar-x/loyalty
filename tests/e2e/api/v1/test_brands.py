from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.modules.catalog.application.tasks import process_brand_logo_task

# Достаточно указать один раз на весь файл
pytestmark = pytest.mark.asyncio


async def test_create_brand_e2e_success(async_client: AsyncClient):
    payload = {
        "name": "E2E Brand",
        "slug": "e2e-brand",
        "logo": {"filename": "test.png", "content_type": "image/png", "size": 1024},
    }

    # Делаем реальный запрос. FastAPI сам достанет IStorageFacade из Dishka
    # и сгенерирует настоящий URL для MinIO!
    response = await async_client.post("/api/v1/catalog/brands", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "brand_id" in data
    assert data["object_key"].startswith("catalog/e2e-brand/")
    assert "url" in data["upload_data"]  # Проверяем, что реальный URL сгенерирован


async def test_confirm_brand_logo_e2e_success(async_client: AsyncClient):
    # 1. Создаем бренд (реальный запрос)
    create_payload = {
        "name": "Brand Confirm",
        "slug": "brand-confirm",
        "logo": {"filename": "test.png", "content_type": "image/png", "size": 100},
    }
    create_res = await async_client.post("/api/v1/catalog/brands", json=create_payload)
    brand_data = create_res.json()
    brand_id = brand_data["brand_id"]
    object_key = brand_data["object_key"]

    # 2. Мокаем только фоновую задачу TaskIQ
    with patch.object(
        process_brand_logo_task, "kiq", new_callable=AsyncMock
    ) as mock_task:
        confirm_payload = {"object_key": object_key}
        response = await async_client.post(
            f"/api/v1/catalog/brands/{brand_id}/logo/confirm", json=confirm_payload
        )

    assert response.status_code == 202
    assert response.json() == {"message": "Запрос на обработку логотипа принят"}
    # Проверяем, что таска действительно вызвалась
    mock_task.assert_called_once()
