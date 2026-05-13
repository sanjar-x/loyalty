"""In-process media cleanup adapter (REC-026).

Implements :class:`IMediaCleanupPort` by delegating to the
``image`` module's :class:`DeleteStorageObjectHandler`. The handler
already encapsulates the "best-effort S3 delete + soft-delete DB row"
semantics, so this adapter is a thin shim that keeps the catalog layer
unaware of image module internals.

Replaces the legacy HTTP-based ``ImageBackendClient`` which made
server-to-server X-API-Key calls to the standalone ``image_backend``
microservice (deprecated in REC-026 after the image module was
consolidated into the main backend in PR #31).
"""

from __future__ import annotations

import uuid

import structlog

from src.modules.catalog.domain.interfaces import IMediaCleanupPort
from src.modules.image.application.commands.delete_storage_object import (
    DeleteStorageObjectHandler,
)

logger = structlog.get_logger(__name__)


class MediaCleanupAdapter(IMediaCleanupPort):
    """Best-effort in-process cleanup of storage objects.

    Cross-module DI: takes the image module's
    :class:`DeleteStorageObjectHandler` as a dependency. Allowed under
    the ``ALLOWED_CROSS_MODULE`` whitelist entry for
    ``catalog.infrastructure.adapters.media_cleanup_adapter`` —
    same anti-corruption-adapter pattern as ``cart.infrastructure.
    adapters.catalog_adapter``.
    """

    def __init__(self, handler: DeleteStorageObjectHandler) -> None:
        self._handler = handler

    async def delete(self, storage_object_id: uuid.UUID) -> None:
        try:
            await self._handler.handle(storage_object_id)
        except Exception:
            logger.warning(
                "media cleanup failed (best-effort)",
                storage_object_id=str(storage_object_id),
                exc_info=True,
            )
