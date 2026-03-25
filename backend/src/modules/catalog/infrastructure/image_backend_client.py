"""HTTP client for server-to-server calls to ImageBackend."""
from __future__ import annotations

import uuid

import httpx
import structlog

logger = structlog.get_logger()


class ImageBackendClient:
    """Best-effort DELETE calls to ImageBackend.

    Does NOT raise on failure — orphan cleanup on ImageBackend side
    handles files that fail to delete.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def delete(self, storage_object_id: uuid.UUID) -> None:
        """DELETE /api/v1/media/{storage_object_id}. Best-effort."""
        url = f"{self._base_url}/api/v1/media/{storage_object_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    url,
                    headers={"X-API-Key": self._api_key},
                )
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
