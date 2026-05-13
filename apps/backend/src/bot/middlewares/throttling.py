"""Message-level middleware that silently drops updates from users
who send messages faster than the configured rate.

Uses an in-memory TTLCache — simple and sufficient for single-process
long-polling.  For multi-process webhook deployments, replace with
Redis-based throttling.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    """Anti-flood: one message per ``throttle_rate`` seconds per chat."""

    def __init__(self, throttle_rate: float = 0.5) -> None:
        self._cache: TTLCache[int, None] = TTLCache(maxsize=10_000, ttl=throttle_rate)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if user.id in self._cache:
            return None  # silently drop

        self._cache[user.id] = None
        return await handler(event, data)
