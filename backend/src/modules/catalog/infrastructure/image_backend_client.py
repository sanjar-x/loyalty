"""HTTP client for server-to-server calls to ImageBackend."""

from __future__ import annotations

import uuid

import httpx
import structlog

from src.modules.catalog.domain.interfaces import IImageBackendClient

logger = structlog.get_logger()


class ImageBackendClient(IImageBackendClient):
    """Best-effort DELETE calls to ImageBackend."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"X-API-Key": api_key},
        )

    async def delete(self, storage_object_id: uuid.UUID) -> None:
        """DELETE /api/v1/media/{storage_object_id}. Best-effort."""
        url = f"{self._base_url}/api/v1/media/{storage_object_id}"
        try:
            resp = await self._client.delete(url)
            if resp.status_code not in (200, 404):
                logger.warning(
                    "ImageBackend delete non-OK",
                    status=resp.status_code,
                    storage_object_id=str(storage_object_id),
                )
        except Exception:
            logger.warning(
                "ImageBackend delete failed (best-effort)",
                storage_object_id=str(storage_object_id),
                exc_info=True,
            )
