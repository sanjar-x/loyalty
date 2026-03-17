import pytest
from dishka import AsyncContainer
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.interfaces.blob_storage import IBlobStorage

pytestmark = pytest.mark.asyncio


async def test_create_brand_e2e_success(
    admin_client: AsyncClient,
    db_session: AsyncSession,
):
    payload = {
        "name": "E2E Brand",
        "slug": "e2e-brand",
        "logo": {
            "filename": "test.png",
            "contentType": "image/png",
            "size": 1024,
        },
    }

    response = await admin_client.post("/api/v1/catalog/brands", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "brandId" in data
    assert data["objectKey"].startswith("raw_uploads/catalog/brands/")
    assert data["presignedUploadUrl"] is not None


async def test_confirm_brand_logo_e2e_success(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    app_container: AsyncContainer,
):
    # 1. Create brand
    create_payload = {
        "name": "Brand Confirm",
        "slug": "brand-confirm",
        "logo": {"filename": "test.png", "contentType": "image/png", "size": 100},
    }
    create_res = await admin_client.post("/api/v1/catalog/brands", json=create_payload)
    brand_data = create_res.json()
    brand_id = brand_data["brandId"]
    object_key = brand_data["objectKey"]

    # 2. Simulate client-side upload: seed InMemoryBlobStorage with the raw file
    blob_storage = await app_container.get(IBlobStorage)

    async def _dummy_stream():
        yield b"fake-png-content"

    await blob_storage.upload_stream(
        object_name=object_key, data_stream=_dummy_stream(), content_type="image/png"
    )

    # 3. Confirm upload
    response = await admin_client.post(f"/api/v1/catalog/brands/{brand_id}/logo/confirm", json={})

    assert response.status_code == 202
    assert response.json() == {"message": "Запрос на обработку логотипа принят"}
