"""Common handlers: /start, /help, /cancel.

These form the bot's entry point and global escape hatch.
The main-menu keyboard is shown on /start so users always have
a clear set of actions available.
"""

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards.reply import main_menu_kb

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
        "Выберите действие в меню ниже 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    """Show available commands."""
    await message.answer(
        "<b>Доступные команды:</b>\n\n"
        "/start — Перезапустить бота\n"
        "/help — Список команд\n"
        "/cancel — Отменить текущее действие\n\n"
        "Или воспользуйтесь кнопками меню 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(StateFilter("*"), Command("cancel"))
@router.message(StateFilter("*"), F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel any active FSM dialog and return to the main menu."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=main_menu_kb())
        return

    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=main_menu_kb(),
    )
