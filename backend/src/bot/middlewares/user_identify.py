"""Outer middleware that attaches basic Telegram user info to every update.

This middleware runs on **every** update (before filters) and makes the
Telegram user object available under a well-known key for downstream
handlers and middleware.  It does **not** hit the database -- that
responsibility belongs to feature-level handlers or DI providers.

For future use: this is the right place to add user-language detection
for i18n middleware chaining.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update


class UserIdentifyMiddleware(BaseMiddleware):
    """Extract Telegram user and locale hint from every update.

    Populates ``data["telegram_user"]`` and ``data["locale"]`` for
    downstream consumption.
    """

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")

        if user is not None:
            data["telegram_user"] = user
            # Best-effort locale from the Telegram client; downstream
            # middleware/handlers can override from DB preference.
            data["locale"] = user.language_code or "ru"
        else:
            data["telegram_user"] = None
            data["locale"] = "ru"

        return await handler(event, data)
