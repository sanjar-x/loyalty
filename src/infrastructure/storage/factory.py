# src\infrastructure\storage\factory.py
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from aiobotocore.client import AioBaseClient
from aiobotocore.config import AioConfig
from aiobotocore.session import AioSession, get_session

logger: Any = structlog.get_logger(__name__)


class S3ClientFactory:
    """
    Фабрика для создания одноразовых (ephemeral) клиентов S3.
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str,
        endpoint_url: str | None = None,
    ) -> None:
        self._access_key: str = access_key
        self._secret_key: str = secret_key
        self._region: str = region
        self._endpoint_url: str | None = endpoint_url
        self._session: AioSession = get_session()

    async def create_client(self) -> AsyncGenerator[AioBaseClient]:
        config = AioConfig(
            max_pool_connections=1,
            connect_timeout=5.0,
            read_timeout=60.0,
            retries={"max_attempts": 3, "mode": "standard"},
        )

        client_ctx = self._session.create_client(
            service_name="s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=config,
        )

        try:
            async with client_ctx as client:
                logger.debug("S3 клиент (ephemeral) успешно создан для текущего контекста.")
                yield client

        except Exception as e:
            logger.error("Ошибка при работе с одноразовым клиентом S3", exc_info=e)
            raise
        finally:
            logger.debug("S3 клиент и все TCP-соединения успешно уничтожены.")
