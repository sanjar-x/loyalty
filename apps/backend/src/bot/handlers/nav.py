"""Inline navigation handlers (back / home / noop).

Handles the shared NavCallback so that every screen in the bot
can include a consistent navigation row without duplicating logic.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.callbacks.base import NavAction, NavCallback

router = Router(name="nav")


@router.callback_query(NavCallback.filter(F.action == NavAction.HOME))
async def on_home(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to the main menu."""
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Вы в главном меню 👇",
    )
    await callback.answer()


@router.callback_query(NavCallback.filter(F.action == NavAction.CANCEL))
async def on_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the current action via inline button."""
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()


@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery) -> None:
    """Swallow noop callbacks (used for informational buttons like page counters)."""
    await callback.answer()
