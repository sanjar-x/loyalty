"""
Command handler: confirm brand logo upload.

Verifies the raw logo file exists in S3, transitions the Brand's logo
FSM to PROCESSING, and emits a domain event to trigger background
image processing. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import raw_logo_key
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    LogoFileNotUploadedError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ConfirmBrandLogoUploadCommand:
    """Input for confirming a logo upload.

    Attributes:
        brand_id: UUID of the brand whose logo upload is being confirmed.
    """

    brand_id: uuid.UUID


class ConfirmBrandLogoUploadHandler:
    """Confirm that a brand logo has been uploaded and trigger processing."""

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        blob_storage: IBlobStorage,
        logger: ILogger,
    ):
        self._brand_repo: IBrandRepository = brand_repo
        self._blob_storage: IBlobStorage = blob_storage
        self._uow: IUnitOfWork = uow
        self._logger: ILogger = logger.bind(handler="ConfirmBrandLogoUploadHandler")

    async def handle(self, command: ConfirmBrandLogoUploadCommand) -> None:
        """Execute the confirm-logo-upload command.

        Args:
            command: Logo confirmation parameters.

        Raises:
            BrandNotFoundError: If the brand does not exist.
            LogoFileNotUploadedError: If the raw logo file is not in S3.
            InvalidLogoStateError: If the logo FSM is not in PENDING_UPLOAD.
        """
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if not brand:
                raise BrandNotFoundError(brand_id=command.brand_id)

            object_key: str = raw_logo_key(brand.id)
            exists: bool = await self._blob_storage.object_exists(object_key)
            if not exists:
                raise LogoFileNotUploadedError(brand_id=brand.id)

            brand.confirm_logo_upload()
            await self._brand_repo.update(brand)

            self._uow.register_aggregate(brand)

            await self._uow.commit()

        self._logger.info(
            "Brand transitioned to PROCESSING, event written to Outbox",
            brand_id=str(brand.id),
        )
