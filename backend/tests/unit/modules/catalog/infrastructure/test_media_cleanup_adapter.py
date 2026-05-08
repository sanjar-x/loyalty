"""Unit tests for :class:`MediaCleanupAdapter` (REC-026)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.modules.catalog.infrastructure.adapters.media_cleanup_adapter import (
    MediaCleanupAdapter,
)
from src.modules.image.application.commands.delete_storage_object import (
    DeleteStorageObjectHandler,
)

pytestmark = pytest.mark.unit


class TestMediaCleanupAdapter:
    @pytest.mark.asyncio
    async def test_delegates_to_image_handler(self):
        handler = AsyncMock(spec=DeleteStorageObjectHandler)
        sid = uuid.uuid4()

        adapter = MediaCleanupAdapter(handler=handler)
        await adapter.delete(sid)

        handler.handle.assert_awaited_once_with(sid)

    @pytest.mark.asyncio
    async def test_swallows_handler_exceptions(self):
        # Best-effort contract — image module's failure must not propagate
        # into the catalog command handler. Catalog already committed its
        # business write; orphan storage gets cleaned by the orphan-prune
        # cron in the image module.
        handler = AsyncMock(spec=DeleteStorageObjectHandler)
        handler.handle.side_effect = RuntimeError("boom")
        sid = uuid.uuid4()

        adapter = MediaCleanupAdapter(handler=handler)
        await adapter.delete(sid)  # must NOT raise

        handler.handle.assert_awaited_once_with(sid)
