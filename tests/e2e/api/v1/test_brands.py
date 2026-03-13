from unittest.mock import AsyncMock, patch

import pytest
from dishka import AsyncContainer
from httpx import AsyncClient

from src.modules.catalog.presentation.tasks import process_brand_logo_task
from src.shared.interfaces.storage import IStorageFacade, PresignedUploadData


@pytest.mark.asyncio
async def test_create_brand_e2e_success(
    async_client: AsyncClient, app_container: AsyncContainer
):
    facade = await app_container.get(IStorageFacade)

    expected_upload_data = PresignedUploadData(
        url_data={"url": "http://minio:9000/test", "fields": {}},
        object_key="catalog/test-e2e-brand/test.png",
    )

    with patch.object(
        facade,
        "request_direct_upload",
        new_callable=AsyncMock,
        return_value=expected_upload_data,
    ):
        payload = {
            "name": "E2E Brand",
            "slug": "e2e-brand",
            "logo": {"filename": "test.png", "content_type": "image/png", "size": 1024},
        }
        response = await async_client.post("/api/v1/catalog/brands", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "brand_id" in data
    assert data["object_key"] == "catalog/test-e2e-brand/test.png"


@pytest.mark.asyncio
async def test_confirm_brand_logo_e2e_success(
    async_client: AsyncClient, app_container: AsyncContainer
):
    facade = await app_container.get(IStorageFacade)

    # Needs a brand in the DB. Best to just call create API first!
    expected_upload_data = PresignedUploadData(
        url_data={"url": "http://minio/test", "fields": {}},
        object_key="catalog/e2e-brand-confirm/test.png",
    )

    with patch.object(
        facade,
        "request_direct_upload",
        new_callable=AsyncMock,
        return_value=expected_upload_data,
    ):
        payload = {
            "name": "Brand Confirm",
            "slug": "brand-confirm",
            "logo": {"filename": "test.png", "content_type": "image/png", "size": 100},
        }
        create_res = await async_client.post("/api/v1/catalog/brands", json=payload)
        brand_id = create_res.json()["brand_id"]

    mock_metadata = {
        "object_key": "catalog/e2e-brand-confirm/test.png",
        "size": 100,
        "content_type": "image/png",
    }

    with patch.object(
        facade,
        "verify_module_upload",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        with patch.object(process_brand_logo_task, "kiq", new_callable=AsyncMock):
            confirm_payload = {"object_key": "catalog/e2e-brand-confirm/test.png"}
            response = await async_client.post(
                f"/api/v1/catalog/brands/{brand_id}/logo/confirm", json=confirm_payload
            )

    assert response.status_code == 202
    assert response.json() == {"message": "Запрос на обработку логотипа принят"}
