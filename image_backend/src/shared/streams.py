"""Shared async stream utilities."""

from collections.abc import AsyncIterator


async def bytes_to_async_stream(data: bytes) -> AsyncIterator[bytes]:
    """Wrap raw bytes as a single-chunk async iterator."""
    yield data
