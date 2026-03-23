"""
Command handler: confirm a product media upload.

Verifies the raw file exists in S3, transitions the MediaAsset FSM from
PENDING_UPLOAD to PROCESSING, and emits a ProductMediaConfirmedEvent to the
Outbox so the AI processing service is notified via RabbitMQ.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import MediaAssetNotFoundError
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ConfirmProductMediaUploadCommand:
    """Input for confirming a product media upload.

    Attributes:
        product_id: UUID of the owning product (used for ownership validation).
        media_id: UUID of the MediaAsset to confirm.
        content_type: MIME type of the uploaded file (forwarded in the domain event).
    """

    product_id: uuid.UUID
    media_id: uuid.UUID
    content_type: str = ""


class ConfirmProductMediaUploadHandler:
    """Confirm that a product media file was uploaded and trigger AI processing."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._blob_storage = blob_storage
        self._uow = uow
        self._logger = logger.bind(handler="ConfirmProductMediaUploadHandler")

    async def handle(self, command: ConfirmProductMediaUploadCommand) -> None:
        """Execute the confirm-product-media command.

        Args:
            command: Confirmation parameters.

        Raises:
            MediaAssetNotFoundError: If the media asset does not exist or has no raw key.
            UnprocessableEntityError: If the raw file is not present in S3.
            InvalidMediaStateError: If the asset FSM is not in PENDING_UPLOAD.
        """
        # Two-phase approach: deliberate TOCTOU trade-off. The S3 existence
        # check runs outside the DB lock to avoid holding a connection during
        # external I/O. The domain FSM guard in Phase 2 protects against stale
        # reads (e.g. concurrent confirmations).

        # Phase 1: Read without lock and verify S3 existence (no row lock held)
        media = await self._media_repo.get(command.media_id)
        if media is None:
            raise MediaAssetNotFoundError(media_id=command.media_id)

        if media.product_id != command.product_id:
            raise MediaAssetNotFoundError(media_id=command.media_id, product_id=command.product_id)

        if media.raw_object_key is None:
            raise MediaAssetNotFoundError(media_id=command.media_id)

        exists = await self._blob_storage.object_exists(media.raw_object_key)
        if not exists:
            raise UnprocessableEntityError(
                "Raw file has not been uploaded yet. Please upload the file before confirming."
            )

        # Phase 2: Lock the row and perform FSM transition
        async with self._uow:
            media = await self._media_repo.get_for_update(command.media_id)
            if media is None:
                raise MediaAssetNotFoundError(media_id=command.media_id)

            # FSM transition PENDING_UPLOAD -> PROCESSING; emits
            # ProductMediaConfirmedEvent accumulated on the MediaAsset aggregate
            media.confirm_upload(content_type=command.content_type)

            await self._media_repo.update(media)

            # Register the aggregate so the UoW writes its domain events to the
            # Outbox atomically within this transaction
            self._uow.register_aggregate(media)

            await self._uow.commit()

        self._logger.info(
            "Media transitioned to PROCESSING, event written to Outbox",
            media_id=str(command.media_id),
            product_id=str(command.product_id),
        )
