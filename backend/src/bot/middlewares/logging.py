"""Outer middleware that logs every incoming Telegram update with timing."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Logs update_id, user, event type, and handler duration.

    Registered as an **outer** middleware on ``dp.update`` so it
    captures every update regardless of filter results.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        user = data.get("event_from_user")
        user_info = f"user_id={user.id}" if user else "anonymous"

        update_id = event.update_id if isinstance(event, Update) else None
        event_type = (
            event.event_type if isinstance(event, Update) else type(event).__name__
        )

        logger.info(
            "update_received",
            update_id=update_id,
            user=user_info,
            event_type=event_type,
        )

        try:
            result = await handler(event, data)
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "update_handled",
                update_id=update_id,
                duration_ms=round(duration_ms, 1),
            )
            return result
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "update_failed",
                update_id=update_id,
                duration_ms=round(duration_ms, 1),
                error=str(exc),
            )
            raise
