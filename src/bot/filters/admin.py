"""Filter that restricts a handler (or entire router) to admin users."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from src.bootstrap.config import settings


class IsAdminFilter(BaseFilter):
    """Passes only if ``message.from_user.id`` is in ``BOT_ADMIN_IDS``."""

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False
        return message.from_user.id in settings.BOT_ADMIN_IDS
