import uuid
from unittest.mock import AsyncMock, patch

from dishka import AsyncContainer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.infrastructure.database.models.outbox import OutboxMessage
from src.shared.interfaces.storage import IStorageFacade


async def test_confirm_brand_logo_upload_handler(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request_container:
        handler = await request_container.get(ConfirmBrandLogoUploadHandler)
        facade = await request_container.get(IStorageFacade)
        repo = BrandRepository(db_session)

    # Create brand in DB
    file_id = uuid.uuid4()
    brand = Brand.create(name="ConfirmTest", slug="confirm-test")
    brand.init_logo_upload(file_id=file_id)  # set PENDING_UPLOAD
    brand = await repo.add(brand)

    command = ConfirmBrandLogoUploadCommand(brand_id=brand.id)

    mock_metadata = {
        "object_key": "verified-test-key",
        "size": 1024,
        "content_type": "image/png",
    }

    with patch.object(
        facade,
        "verify_upload",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ) as mock_verify:
        # Act
        await handler.handle(command)

        # Assert — верификация загрузки вызвана
        mock_verify.assert_called_once_with(file_id=brand.logo_file_id)

    # Assert — статус бренда обновлён в БД
    orm_brand = await db_session.get(OrmBrand, brand.id)
    assert orm_brand is not None
    assert orm_brand.logo_status == MediaProcessingStatus.PROCESSING

    # Assert — в Outbox появилось событие BrandLogoConfirmedEvent
    result = await db_session.execute(
        select(OutboxMessage).where(
            OutboxMessage.aggregate_type == "Brand",
            OutboxMessage.aggregate_id == str(brand.id),
            OutboxMessage.event_type == "BrandLogoConfirmedEvent",
        )
    )
    outbox_row = result.scalar_one_or_none()
    assert outbox_row is not None, "Outbox-событие не найдено в транзакции"
    assert outbox_row.payload["brand_id"] == str(brand.id)
    assert outbox_row.processed_at is None  # ещё не отправлено Relay
