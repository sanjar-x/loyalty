# src/modules/storage/infrastructure/service.py
from collections.abc import AsyncIterator
from typing import Any

import structlog
from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError

from src.shared.exceptions import NotFoundError, ServiceUnavailableError
from src.shared.interfaces.blob_storage import IBlobStorage

logger = structlog.get_logger(__name__)


class S3StorageService(IBlobStorage):
    def __init__(self, s3_client: AioBaseClient, bucket_name: str):
        self._client: AioBaseClient = s3_client
        self._bucket = bucket_name

    def _handle_client_error(self, e: ClientError, object_name: str) -> None:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey", "NotFound"):
            raise NotFoundError(
                message=f"Объект '{object_name}' не найден в хранилище.",
                details={"bucket": self._bucket, "key": object_name},
            )
        logger.error(
            "s3_client_error",
            object_name=object_name,
            error_code=error_code,
            error=str(e),
        )
        raise ServiceUnavailableError(
            message="Ошибка взаимодействия с сервисом хранения данных.",
            details={"error_code": error_code},
        )

    async def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=object_name)
            stream = response["Body"]

            while True:
                chunk = await stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        except ClientError as e:
            self._handle_client_error(e, object_name)

    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        try:
            return await self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_name},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error("s3_presigned_url_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Не удалось сгенерировать ссылку на файл.",
                details={"key": object_name},
            )

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        upload_id = None
        parts = []
        part_number = 1
        buffer = b""
        min_part_size = 5 * 1024 * 1024  # 5 MB - минимум для AWS S3 Multipart

        try:
            # Инициализация Multipart Upload
            mpu = await self._client.create_multipart_upload(
                Bucket=self._bucket, Key=object_name, ContentType=content_type
            )
            upload_id = mpu["UploadId"]

            # Чтение потока и отправка чанками
            async for chunk in data_stream:
                buffer += chunk
                while len(buffer) >= min_part_size:
                    part_data = buffer[:min_part_size]
                    buffer = buffer[min_part_size:]

                    upload_result = await self._client.upload_part(
                        Bucket=self._bucket,
                        Key=object_name,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=part_data,
                    )
                    parts.append({"PartNumber": part_number, "ETag": upload_result["ETag"]})
                    part_number += 1

            # Отправка остатков (хвоста), даже если он меньше 5MB
            if buffer or part_number == 1:
                upload_result = await self._client.upload_part(
                    Bucket=self._bucket,
                    Key=object_name,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=buffer,
                )
                parts.append({"PartNumber": part_number, "ETag": upload_result["ETag"]})

            # Завершение сборки файла на стороне S3
            await self._client.complete_multipart_upload(
                Bucket=self._bucket,
                Key=object_name,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            logger.debug(
                "s3_multipart_upload_completed",
                object_name=object_name,
                total_parts=len(parts),
            )
            return object_name

        except Exception as e:
            # В случае ошибки - обязательно очищаем "мусорные" куски с сервера S3
            logger.error("s3_upload_stream_error", object_name=object_name, error=str(e))
            if upload_id:
                try:
                    await self._client.abort_multipart_upload(
                        Bucket=self._bucket, Key=object_name, UploadId=upload_id
                    )
                except Exception as abort_err:
                    logger.error(
                        "s3_abort_multipart_error",
                        object_name=object_name,
                        upload_id=upload_id,
                        error=str(abort_err),
                    )

            raise ServiceUnavailableError(
                message="Ошибка при загрузке файла в хранилище.",
                details={"key": object_name, "error": str(e)},
            )

    async def get_presigned_upload_url(self, object_name: str, expiration: int = 3600) -> dict:
        try:
            return await self._client.generate_presigned_post(
                Bucket=self._bucket, Key=object_name, ExpiresIn=expiration
            )
        except ClientError as e:
            logger.error("s3_presigned_upload_url_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Не удалось сгенерировать ссылку для загрузки файла.",
                details={"key": object_name},
            )

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        try:
            return await self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": object_name,
                    "ContentType": content_type,
                },
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error("s3_presigned_put_url_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Не удалось сгенерировать прямую ссылку для загрузки файла.",
                details={"key": object_name},
            )

    async def object_exists(self, object_name: str) -> bool:
        try:
            await self._client.head_object(Bucket=self._bucket, Key=object_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False

            logger.error("s3_object_exists_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(message="Ошибка при проверке существования файла.")

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]:
        try:
            response = await self._client.head_object(Bucket=self._bucket, Key=object_name)
            return {
                "content_length": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "etag": response.get("ETag", "").strip('"'),
                "last_modified": response.get("LastModified"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError as e:
            self._handle_client_error(e, object_name)
            return {}

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Prefix": prefix,
            "MaxKeys": limit,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        try:
            response = await self._client.list_objects_v2(**kwargs)

            objects = []
            for s3_item in response.get("Contents", []):
                objects.append(
                    {
                        "key": s3_item["Key"],
                        "size": s3_item["Size"],
                        "last_modified": s3_item["LastModified"],
                        "etag": s3_item.get("ETag", "").strip('"'),
                    }
                )

            return {
                "objects": objects,
                "next_continuation_token": response.get("NextContinuationToken"),
                "is_truncated": response.get("IsTruncated", False),
                "key_count": response.get("KeyCount", 0),
            }
        except ClientError as e:
            logger.error("s3_list_objects_error", prefix=prefix, error=str(e))
            raise ServiceUnavailableError(
                message="Ошибка при получении списка файлов из хранилища."
            )

    async def delete_object(self, object_name: str) -> None:
        try:
            await self._client.delete_object(Bucket=self._bucket, Key=object_name)
        except ClientError as e:
            logger.error("s3_delete_object_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Не удалось удалить файл.", details={"key": object_name}
            )

    async def delete_objects(self, object_names: list[str]) -> list[str]:
        failed_keys = []
        chunk_size = 1000

        try:
            for i in range(0, len(object_names), chunk_size):
                chunk = object_names[i : i + chunk_size]
                delete_request = {
                    "Objects": [{"Key": key} for key in chunk],
                    "Quiet": True,
                }

                response = await self._client.delete_objects(
                    Bucket=self._bucket, Delete=delete_request
                )

                if "Errors" in response:
                    failed_keys.extend([error["Key"] for error in response["Errors"]])

            return failed_keys
        except ClientError as e:
            logger.error("s3_batch_delete_error", count=len(object_names), error=str(e))
            raise ServiceUnavailableError(message="Ошибка при пакетном удалении файлов.")

    async def copy_object(self, source_name: str, dest_name: str) -> None:
        try:
            copy_source = {"Bucket": self._bucket, "Key": source_name}
            await self._client.copy_object(
                Bucket=self._bucket, CopySource=copy_source, Key=dest_name
            )
        except ClientError as e:
            self._handle_client_error(e, source_name)
