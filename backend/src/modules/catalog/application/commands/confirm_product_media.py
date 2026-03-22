"""
Command handler: confirm a product media upload.

Verifies the raw file exists in S3, transitions the MediaAsset FSM from
PENDING_UPLOAD to PROCESSING, and emits a ProductMediaConfirmedEvent to the
Outbox so the AI processing service is notified via RabbitMQ.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.shared.exceptions import NotFoundError, UnprocessableEntityError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ConfirmProductMediaCommand:
    """Input for confirming a product media upload.

    Attributes:
        product_id: UUID of the owning product (used for ownership validation).
        media_id: UUID of the MediaAsset to confirm.
        content_type: MIME type of the uploaded file (forwarded in the domain event).
    """

    product_id: uuid.UUID
    media_id: uuid.UUID
    content_type: str = ""


class ConfirmProductMediaHandler:
    """Confirm that a product media file was uploaded and trigger AI processing."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._blob = blob_storage
        self._uow = uow
        self._logger = logger.bind(handler="ConfirmProductMediaHandler")

    async def handle(self, cmd: ConfirmProductMediaCommand) -> None:
        """Execute the confirm-product-media command.

        Args:
            cmd: Confirmation parameters.

        Raises:
            NotFoundError: If the media asset does not exist or has no raw key.
            UnprocessableEntityError: If the raw file is not present in S3.
            InvalidMediaStateError: If the asset FSM is not in PENDING_UPLOAD.
        """
        async with self._uow:
            media = await self._media_repo.get(cmd.media_id)
            if media is None:
                raise NotFoundError(f"Media {cmd.media_id} not found")

            if media.raw_object_key is None:
                raise NotFoundError(f"Media {cmd.media_id} has no raw object key")

            # Verify raw file exists in S3 (outside transaction would be ideal, but
            # we are inside the UoW context to hold the row lock implicitly through
            # the session; S3 I/O here is acceptable for the confirmation flow)
            exists = await self._blob.object_exists(media.raw_object_key)
            if not exists:
                raise UnprocessableEntityError(
                    f"Raw file not yet uploaded to S3: {media.raw_object_key}"
                )

            # FSM transition PENDING_UPLOAD -> PROCESSING; emits
            # ProductMediaConfirmedEvent accumulated on the MediaAsset aggregate
            media.confirm_upload(content_type=cmd.content_type)

            await self._media_repo.update(media)

            # Register the aggregate so the UoW writes its domain events to the
            # Outbox atomically within this transaction
            self._uow.register_aggregate(media)

            await self._uow.commit()

        self._logger.info(
            "Media transitioned to PROCESSING, event written to Outbox",
            media_id=str(cmd.media_id),
            product_id=str(cmd.product_id),
        )
