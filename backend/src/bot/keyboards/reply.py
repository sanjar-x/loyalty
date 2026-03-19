"""Reply (bottom) keyboards used across the bot.

Reply keyboards persist beneath the input field and are ideal for
the main menu and frequently-used global actions.  Always use
``resize_keyboard=True`` to avoid occupying half the screen.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Build the persistent main-menu keyboard.

    Layout::

        [ Каталог ]  [ Мои заказы ]
        [ Баланс  ]  [ Профиль    ]
        [       Помощь             ]
    """
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛒 Каталог")
    builder.button(text="📦 Мои заказы")
    builder.button(text="💰 Баланс")
    builder.button(text="👤 Профиль")
    builder.button(text="❓ Помощь")
    builder.adjust(2, 2, 1)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    """Single-button keyboard shown during FSM dialogs."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def phone_request_kb() -> ReplyKeyboardMarkup:
    """Keyboard for requesting the user's phone number."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Отправить номер", request_contact=True)
    builder.button(text="⏩ Пропустить")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
