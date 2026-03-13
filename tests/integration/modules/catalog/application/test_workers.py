import uuid
from unittest.mock import AsyncMock, patch

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.services.media_processor import BrandLogoProcessor
from src.modules.catalog.application.tasks import process_brand_logo_task
from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.storage import IStorageFacade


@pytest.mark.asyncio
async def test_process_brand_logo_task(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    blob_storage = await app_container.get(IBlobStorage)
    facade = await app_container.get(IStorageFacade)
    processor = await app_container.get(BrandLogoProcessor)
    repo = BrandRepository(db_session)

    brand = Brand.create(name="Worker Brand", slug="worker-brand")
    brand.init_logo_upload()
    brand.confirm_logo_upload()  # processing
    brand = await repo.add(brand)

    # Upload dummy raw file to MinIO testcontainer directly
    raw_key = f"catalog/raw/{brand.id}/dummy.png"

    async def dummy_stream():
        yield b"dummy image content"

    await blob_storage.upload_stream(
        object_name=raw_key, data_stream=dummy_stream(), content_type="image/png"
    )

    mock_file_id = uuid.uuid4()

    # Mock Storage Facade so we don't have to deal with nested UoW issues in test
    with patch.object(
        facade,
        "register_processed_media",
        new_callable=AsyncMock,
        return_value=mock_file_id,
    ):
        # Act
        result = await process_brand_logo_task(
            brand_id=brand.id, raw_object_key=raw_key, processor=processor
        )

    # Assert
    assert result == {"status": "success"}

    # Check DB
    orm_brand = await db_session.get(OrmBrand, brand.id)
    assert orm_brand is not None
    assert orm_brand.logo_status == MediaProcessingStatus.COMPLETED
    assert orm_brand.logo_file_id == mock_file_id
    assert orm_brand.logo_url == f"public/brands/{brand.id}/logo.webp"
