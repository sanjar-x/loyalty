"""Common handlers: /start, /help, /cancel.

These form the bot's entry point and global escape hatch.
"""

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

router = Router(name="common")

# Only handle private messages
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Greet the user and reset any active FSM dialog."""
    await state.clear()
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}! 👋\n\n"
        "Добро пожаловать в наш бот.\n"
        "Используйте /help для списка команд.",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands."""
    await message.answer(
        "<b>Доступные команды:</b>\n\n"
        "/start — Перезапустить бота\n"
        "/help — Список команд\n"
        "/cancel — Отменить текущее действие",
    )


@router.message(StateFilter("*"), Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel any active FSM dialog."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=ReplyKeyboardRemove(),
    )
