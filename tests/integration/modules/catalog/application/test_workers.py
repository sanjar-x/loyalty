import uuid
from unittest.mock import AsyncMock, patch

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


async def test_process_brand_logo_task(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request_container:
        blob_storage = await request_container.get(IBlobStorage)
        facade = await request_container.get(IStorageFacade)
        processor = await request_container.get(BrandLogoProcessor)
        repo = BrandRepository(db_session)

    file_id = uuid.uuid4()
    brand = Brand.create(
        name="Worker Brand",
        slug="worker-brand",
        logo_file_id=file_id,
        logo_status=MediaProcessingStatus.PROCESSING,
    )
    brand = await repo.add(brand)

    # Upload dummy raw file
    raw_key = f"raw_uploads/catalog/{brand.id}/dummy.png"

    async def dummy_stream():
        yield b"dummy image content"

    await blob_storage.upload_stream(
        object_name=raw_key, data_stream=dummy_stream(), content_type="image/png"
    )

    # Mock Storage Facade verify and update
    with patch.object(
        facade,
        "verify_upload",
        new_callable=AsyncMock,
        return_value={"object_key": raw_key},
    ):
        with patch.object(
            facade, "update_object_metadata", new_callable=AsyncMock
        ) as mock_update:
            # Act
            result = await process_brand_logo_task(
                brand_id=brand.id, processor=processor
            )

            # Assert
            assert result == {"status": "success", "brand_id": str(brand.id)}
            assert mock_update.called

    # Check DB
    orm_brand = await db_session.get(OrmBrand, brand.id)
    assert orm_brand is not None
    assert orm_brand.logo_status == MediaProcessingStatus.COMPLETED
    assert orm_brand.logo_file_id == file_id
    assert orm_brand.logo_url == f"http://127.0.0.1:9000/test-bucket/public/brands/{brand.id}/logo.webp"
