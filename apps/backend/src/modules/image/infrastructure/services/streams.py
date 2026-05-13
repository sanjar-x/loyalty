"""Async stream helpers for the image module."""

from collections.abc import AsyncIterator


async def bytes_to_async_stream(data: bytes) -> AsyncIterator[bytes]:
    """Wrap raw bytes as a single-chunk async iterator.

    Used by the router and worker to feed the Pillow-produced WebP
    payload into ``IBlobStorage.upload_stream``.
    """
    yield data
