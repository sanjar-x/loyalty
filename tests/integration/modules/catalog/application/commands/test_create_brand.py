from unittest.mock import AsyncMock, patch

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    LogoMetadata,
)
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.shared.interfaces.storage import IStorageFacade, PresignedUploadData


@pytest.mark.asyncio
async def test_create_brand_handler_without_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    handler = await app_container.get(CreateBrandHandler)
    command = CreateBrandCommand(name="TestBrand", slug="testbrand", logo=None)

    # Act
    result = await handler.handle(command)

    # Assert
    assert result.brand_id is not None
    assert result.presigned_upload_url is None

    # Verify in DB
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.slug == "testbrand"
    assert orm_brand.logo_status is None


@pytest.mark.asyncio
async def test_create_brand_handler_with_logo_calls_facade(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    handler = await app_container.get(CreateBrandHandler)
    facade = await app_container.get(IStorageFacade)

    command = CreateBrandCommand(
        name="TestBrandWithLogo",
        slug="testbrand-logo",
        logo=LogoMetadata(filename="logo.png", content_type="image/png"),
    )

    expected_upload_data = PresignedUploadData(
        url_data={"url": "https://s3/test", "fields": {}},
        object_key="catalog/testbrand-logo/logo.png",
    )

    with patch.object(
        facade,
        "request_direct_upload",
        new_callable=AsyncMock,
        return_value=expected_upload_data,
    ) as mock_upload:
        # Act
        result = await handler.handle(command)

        # Assert
        assert result.brand_id is not None
        assert result.presigned_upload_url == str(expected_upload_data.url_data)

        # Verify mock called
        mock_upload.assert_called_once_with(
            module="catalog",
            entity_id=result.brand_id,
            filename="logo.png",
            content_type="image/png",
        )

        # Verify in DB
        orm_brand = await db_session.get(OrmBrand, result.brand_id)
        assert orm_brand is not None
        assert orm_brand.logo_status == MediaProcessingStatus.PENDING_UPLOAD
