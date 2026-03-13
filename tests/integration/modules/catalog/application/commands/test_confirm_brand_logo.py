from unittest.mock import AsyncMock, patch

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.tasks import process_brand_logo_task
from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.shared.interfaces.storage import IStorageFacade


@pytest.mark.asyncio
async def test_confirm_brand_logo_upload_handler(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    handler = await app_container.get(ConfirmBrandLogoUploadHandler)
    facade = await app_container.get(IStorageFacade)
    repo = BrandRepository(db_session)

    # Create brand in DB
    brand = Brand.create(name="ConfirmTest", slug="confirm-test")
    brand.init_logo_upload()  # set PENDING_UPLOAD
    brand = await repo.add(brand)

    command = ConfirmBrandLogoUploadCommand(brand_id=brand.id, object_key="test-key")

    mock_metadata = {
        "object_key": "verified-test-key",
        "size": 1024,
        "content_type": "image/png",
    }

    with patch.object(
        facade,
        "verify_module_upload",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ) as mock_verify:
        with patch.object(
            process_brand_logo_task, "kiq", new_callable=AsyncMock
        ) as mock_kiq:
            # Act
            await handler.handle(command)

            # Assert
            # Verify Mock called
            mock_verify.assert_called_once_with(
                module="catalog", entity_id=brand.id, object_key="test-key"
            )

            # Verify TaskIQ task sent
            mock_kiq.assert_called_once_with(
                brand_id=brand.id, raw_object_key="verified-test-key"
            )

            # Check DB
            orm_brand = await db_session.get(OrmBrand, brand.id)
            assert orm_brand is not None
            assert orm_brand.logo_status == MediaProcessingStatus.PROCESSING
