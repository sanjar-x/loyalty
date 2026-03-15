from unittest.mock import AsyncMock, patch

from dishka import AsyncContainer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    LogoMetadata,
)
from src.modules.catalog.application.constants import raw_logo_key
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.infrastructure.database.models.outbox import OutboxMessage
from src.shared.interfaces.blob_storage import IBlobStorage


async def test_create_brand_handler_without_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request_container:
        handler = await request_container.get(CreateBrandHandler)
        command = CreateBrandCommand(name="TestBrand", slug="testbrand", logo=None)

        # Act
        result = await handler.handle(command)

    # Assert
    assert result.brand_id is not None
    assert result.presigned_upload_url is None
    assert result.object_key is None

    # Verify in DB
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.slug == "testbrand"
    assert orm_brand.logo_status is None


async def test_create_brand_handler_with_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request_container:
        handler = await request_container.get(CreateBrandHandler)
        blob_storage = await request_container.get(IBlobStorage)

    command = CreateBrandCommand(
        name="TestBrandWithLogo",
        slug="testbrand-logo",
        logo=LogoMetadata(filename="logo.png", content_type="image/png"),
    )

    presigned_url = "https://s3.example.com/presigned-put-url"

    with patch.object(
        blob_storage,
        "generate_presigned_put_url",
        new_callable=AsyncMock,
        return_value=presigned_url,
    ) as mock_put_url:
        # Act
        result = await handler.handle(command)

        # Assert — presigned URL сгенерирован через IBlobStorage (stateless)
        assert result.brand_id is not None
        assert result.presigned_upload_url == presigned_url
        assert result.object_key == raw_logo_key(result.brand_id)

        # Verify IBlobStorage вызван с детерминированным ключом
        mock_put_url.assert_called_once_with(
            object_name=raw_logo_key(result.brand_id),
            content_type="image/png",
        )

    # Verify in DB
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.logo_status == MediaProcessingStatus.PENDING_UPLOAD

    # Verify Outbox — BrandCreatedEvent записан
    outbox_result = await db_session.execute(
        select(OutboxMessage).where(
            OutboxMessage.aggregate_type == "Brand",
            OutboxMessage.aggregate_id == str(result.brand_id),
            OutboxMessage.event_type == "BrandCreatedEvent",
        )
    )
    outbox_row = outbox_result.scalar_one_or_none()
    assert outbox_row is not None, "BrandCreatedEvent не найден в Outbox"
    assert outbox_row.payload["object_key"] == raw_logo_key(result.brand_id)
    assert outbox_row.payload["content_type"] == "image/png"
