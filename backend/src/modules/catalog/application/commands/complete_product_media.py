"""
Command handlers: finalize or mark-failed a product media processing job.

Called by the internal AI-service webhook when it finishes (or fails) processing
a media asset. Both handlers acquire a row-level lock via ``get_for_update`` to
prevent concurrent state transitions.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import public_media_key
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


# ---------------------------------------------------------------------------
# Complete (success path)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompleteProductMediaCommand:
    """Input for marking a media asset as successfully processed.

    Attributes:
        media_id: UUID of the MediaAsset to finalize.
        object_key: S3 key of the processed (public) file.
        content_type: MIME type of the processed file.
        size_bytes: Size of the processed file in bytes.
        delete_raw: Whether to delete the raw upload file from S3 (default: True).
    """

    media_id: uuid.UUID
    object_key: str
    content_type: str = ""
    size_bytes: int = 0
    delete_raw: bool = True


class CompleteProductMediaHandler:
    """Finalize a successfully processed media asset."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        config: IStorageConfig,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._blob = blob_storage
        self._uow = uow
        self._config = config
        self._logger = logger.bind(handler="CompleteProductMediaHandler")

    async def handle(self, cmd: CompleteProductMediaCommand) -> None:
        """Execute the complete-product-media command.

        Args:
            cmd: Processing completion parameters.

        Raises:
            NotFoundError: If the media asset does not exist.
            InvalidMediaStateError: If the asset FSM is not in PROCESSING.
        """
        raw_object_key: str | None = None

        async with self._uow:
            media = await self._media_repo.get_for_update(cmd.media_id)
            if media is None:
                raise NotFoundError(f"Media {cmd.media_id} not found")

            # Stash raw key before the FSM transition overwrites it
            raw_object_key = media.raw_object_key

            # Build the publicly accessible URL from the processed object key
            public_url = f"{self._config.S3_PUBLIC_BASE_URL}/{cmd.object_key}"

            # FSM transition PROCESSING -> COMPLETED; emits ProductMediaProcessedEvent
            media.complete_processing(
                public_url=public_url,
                object_key=cmd.object_key,
            )

            await self._media_repo.update(media)

            # Register aggregate so its domain events are written to the Outbox
            self._uow.register_aggregate(media)

            await self._uow.commit()

        # Delete the raw upload file after the transaction is committed so that
        # a rollback does not leave us deleting a file we still need
        if cmd.delete_raw and raw_object_key:
            try:
                await self._blob.delete_object(raw_object_key)
            except Exception:  # noqa: BLE001
                self._logger.warning(
                    "Failed to delete raw upload after processing",
                    raw_object_key=raw_object_key,
                    media_id=str(cmd.media_id),
                )

        self._logger.info(
            "Media processing completed",
            media_id=str(cmd.media_id),
            object_key=cmd.object_key,
        )


# ---------------------------------------------------------------------------
# Fail (error path)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FailProductMediaCommand:
    """Input for marking a media asset as failed.

    Attributes:
        media_id: UUID of the MediaAsset that failed processing.
        reason: Optional human-readable failure reason (for logging only).
    """

    media_id: uuid.UUID
    reason: str = ""


class FailProductMediaHandler:
    """Mark a media asset as failed when the AI processing service reports an error."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._uow = uow
        self._logger = logger.bind(handler="FailProductMediaHandler")

    async def handle(self, cmd: FailProductMediaCommand) -> None:
        """Execute the fail-product-media command.

        Args:
            cmd: Failure parameters.

        Raises:
            NotFoundError: If the media asset does not exist.
            InvalidMediaStateError: If the asset FSM is not in PROCESSING.
        """
        async with self._uow:
            media = await self._media_repo.get_for_update(cmd.media_id)
            if media is None:
                raise NotFoundError(f"Media {cmd.media_id} not found")

            # FSM transition PROCESSING -> FAILED
            media.fail_processing()

            await self._media_repo.update(media)
            await self._uow.commit()

        self._logger.warning(
            "Media processing failed",
            media_id=str(cmd.media_id),
            reason=cmd.reason,
        )
