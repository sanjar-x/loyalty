"""Aiogram-backed ``ITelegramNotifier`` adapter (T-2 / D3.1).

Wraps ``Bot.send_message`` with the error-classification semantics
documented on :class:`ITelegramNotifier`:

* User blocked the bot or chat not found (``TelegramForbiddenError`` /
  ``TelegramBadRequest`` with ``chat not found`` text) → log + swallow.
  TaskIQ MUST NOT retry these — they are permanent.
* Rate limit (``TelegramRetryAfter``) → re-raise so TaskIQ honours
  the broker-side backoff.
* Network / 5xx → re-raise so TaskIQ retries up to ``max_retries``.
"""

from __future__ import annotations

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.modules.order.application.ports import ITelegramNotifier

logger = structlog.get_logger(__name__)


class AiogramTelegramNotifier(ITelegramNotifier):
    """Adapter that pushes HTML messages via the project's aiogram Bot."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_html(self, *, chat_id: int, html: str) -> None:
        try:
            await self._bot.send_message(
                chat_id=chat_id,
                text=html,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except TelegramForbiddenError:
            # 403 — user blocked the bot, account deleted, channel
            # ejected. Permanent failure for this chat — DO NOT retry.
            logger.warning(
                "telegram_notifier.skip_forbidden",
                chat_id=chat_id,
            )
            return
        except TelegramBadRequest as exc:
            # ``chat not found``, ``user is deactivated``, etc. —
            # also permanent. Aiogram does not split these into a
            # narrower exception class so we string-match on the
            # human description (the API guarantees it stays in
            # English).
            message = str(exc).lower()
            if any(
                keyword in message
                for keyword in (
                    "chat not found",
                    "user is deactivated",
                    "bot was blocked",
                    "user is bot",
                )
            ):
                logger.warning(
                    "telegram_notifier.skip_bad_request",
                    chat_id=chat_id,
                    reason=str(exc),
                )
                return
            raise
