import io
import uuid

from PIL import Image

from src.modules.catalog.application.constants import public_logo_key, raw_logo_key
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

MAX_LOGO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB


class BrandLogoProcessor:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        settings: IStorageConfig,
        logger: ILogger,
    ):
        self._brand_repo = brand_repo
        self._blob_storage = blob_storage
        self._uow = uow
        self._settings = settings
        self._log = logger.bind(service="BrandLogoProcessor")

    async def process(self, brand_id: uuid.UUID) -> None:
        log = self._log.bind(brand_id=str(brand_id))
        log.info("brand_logo_processing_started")

        raw_key = raw_logo_key(brand_id)
        pub_key = public_logo_key(brand_id)

        try:
            raw_data = await self._download_raw(raw_key, log)
            processed_data = self._convert_to_webp(raw_data, log)
            await self._upload_processed(pub_key, processed_data, log)

            logo_url = f"{self._settings.S3_PUBLIC_BASE_URL}/{pub_key}"
            await self._finalize_brand(
                brand_id, logo_url, pub_key, len(processed_data), log
            )

            await self._blob_storage.delete_file(raw_key)
            log.info("brand_logo_processing_completed")

        except Exception:
            log.exception("brand_logo_processing_failed")
            await self._mark_failed(brand_id, log)
            raise

    async def _download_raw(self, key: str, log: ILogger) -> bytes:
        buf = io.BytesIO()
        total = 0

        async for chunk in self._blob_storage.download_stream(key):
            total += len(chunk)
            if total > MAX_LOGO_SIZE_BYTES:
                raise ValueError(
                    f"Logo file exceeds size limit: {total} > {MAX_LOGO_SIZE_BYTES}"
                )
            buf.write(chunk)

        log.info("raw_logo_downloaded", size_bytes=total)
        return buf.getvalue()

    @staticmethod
    def _convert_to_webp(raw_data: bytes, log: ILogger) -> bytes:
        output = io.BytesIO()

        with Image.open(io.BytesIO(raw_data)) as img:
            img.convert("RGBA").save(
                output, format="WEBP", lossless=True, method=6, quality=100
            )

        result = output.getvalue()
        log.info(
            "logo_converted_to_webp",
            raw_size=len(raw_data),
            processed_size=len(result),
        )
        return result

    async def _upload_processed(self, key: str, data: bytes, log: ILogger) -> None:
        async def chunked_stream():
            for offset in range(0, len(data), UPLOAD_CHUNK_SIZE):
                yield data[offset : offset + UPLOAD_CHUNK_SIZE]

        await self._blob_storage.upload_stream(
            object_name=key,
            data_stream=chunked_stream(),
            content_type="image/webp",
        )
        log.info("processed_logo_uploaded", key=key)

    async def _finalize_brand(
        self,
        brand_id: uuid.UUID,
        logo_url: str,
        object_key: str,
        size_bytes: int,
        log: ILogger,
    ) -> None:
        async with self._uow:
            brand = await self._brand_repo.get_for_update(brand_id)
            if not brand:
                log.warning("brand_not_found_at_finalization")
                return

            brand.complete_logo_processing(
                url=logo_url,
                object_key=object_key,
                content_type="image/webp",
                size_bytes=size_bytes,
            )
            await self._brand_repo.update(brand)
            self._uow.register_aggregate(brand)
            await self._uow.commit()
            log.info("brand_status_completed")

    async def _mark_failed(self, brand_id: uuid.UUID, log: ILogger) -> None:
        try:
            async with self._uow:
                brand = await self._brand_repo.get_for_update(brand_id)
                if not brand:
                    return
                brand.fail_logo_processing()
                await self._brand_repo.update(brand)
                await self._uow.commit()
                log.warning("brand_status_failed")
        except Exception:
            log.exception("failed_to_mark_brand_as_failed")
