"""Factory for creating ephemeral S3 clients via aiobotocore.

Produces short-lived S3 client instances scoped to a single async
context manager usage. TCP connections are torn down automatically
when the context exits.
"""

from collections.abc import AsyncGenerator

import structlog
from aiobotocore.client import AioBaseClient
from aiobotocore.config import AioConfig
from aiobotocore.session import AioSession, get_session

logger: structlog.BoundLogger = structlog.get_logger(__name__)


class S3ClientFactory:
    """Factory for creating ephemeral (single-use) S3 clients."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str,
        endpoint_url: str | None = None,
    ) -> None:
        """Initialize the factory with AWS credentials and region.

        Args:
            access_key: AWS access key ID.
            secret_key: AWS secret access key.
            region: AWS region name.
            endpoint_url: Optional custom endpoint URL (e.g., for MinIO).
        """
        self._access_key: str = access_key
        self._secret_key: str = secret_key
        self._region: str = region
        self._endpoint_url: str | None = endpoint_url
        self._session: AioSession = get_session()

    async def create_client(self) -> AsyncGenerator[AioBaseClient]:
        """Create and yield an ephemeral S3 client.

        The client and its TCP connections are automatically destroyed
        when the async generator is closed.

        Yields:
            AioBaseClient: A configured S3 client instance.

        Raises:
            Exception: Re-raises any error that occurs during S3 operations.
        """
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
                logger.debug("Ephemeral S3 client created for current context.")
                yield client

        except Exception as e:
            logger.error("Error during ephemeral S3 client operation", exc_info=e)
            raise
        finally:
            logger.debug("Ephemeral S3 client and TCP connections destroyed.")
