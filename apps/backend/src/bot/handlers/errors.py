"""Global error handler and fallback for unrecognised messages."""

import contextlib

import structlog
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import ErrorEvent, Message

from src.bot.keyboards.reply import main_menu_kb

logger = structlog.get_logger(__name__)

router = Router(name="errors")


@router.error()
async def global_error_handler(event: ErrorEvent) -> bool:
    """Catch all unhandled exceptions and notify the user."""
    logger.exception(
        "unhandled_error",
        update_id=event.update.update_id,
        error=str(event.exception),
    )

    # Try to inform the user
    update = event.update
    if update.message:
        with contextlib.suppress(Exception):
            await update.message.answer(
                "😔 Что-то пошло не так. Мы уже разбираемся!\n"
                "Попробуйте ещё раз или напишите /start",
                reply_markup=main_menu_kb(),
            )
    elif update.callback_query:
        with contextlib.suppress(Exception):
            await update.callback_query.answer(
                "😔 Произошла ошибка. Попробуйте позже.",
                show_alert=True,
            )

    return True  # error handled


@router.message(StateFilter(None))
async def fallback_handler(message: Message) -> None:
    """Handle messages that don't match any other handler.

    Registered on the error router (last in priority) so it only
    fires when no feature handler matched.
    """
    if message.text and message.text.startswith("/"):
        await message.answer(
            "🤔 Неизвестная команда.\nСписок доступных команд: /help",
        )
    else:
        await message.answer(
            "Не совсем понял вас. Воспользуйтесь меню 👇",
            reply_markup=main_menu_kb(),
        )
