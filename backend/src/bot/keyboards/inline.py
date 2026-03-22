"""Inline keyboard builders for common patterns.

Inline keyboards are attached to a specific message and are ideal for
contextual actions, pagination, and confirmations.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.callbacks.base import (
    ConfirmAction,
    ConfirmCallback,
    NavAction,
    NavCallback,
    PageCallback,
)

# -- Navigation row ------------------------------------------------------------


def nav_row(
    *,
    show_back: bool = True,
    show_home: bool = True,
    back_ctx: str = "",
) -> list[InlineKeyboardButton]:
    """Build a reusable navigation button row (back / home)."""
    buttons: list[InlineKeyboardButton] = []
    if show_back:
        buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=NavCallback(action=NavAction.BACK, ctx=back_ctx).pack(),
            )
        )
    if show_home:
        buttons.append(
            InlineKeyboardButton(
                text="🏠 Главная",
                callback_data=NavCallback(action=NavAction.HOME).pack(),
            )
        )
    return buttons


def add_nav_row(
    builder: InlineKeyboardBuilder,
    *,
    show_back: bool = True,
    show_home: bool = True,
    back_ctx: str = "",
) -> None:
    """Append a navigation row to an existing builder."""
    row = nav_row(show_back=show_back, show_home=show_home, back_ctx=back_ctx)
    if row:
        builder.row(*row)


# -- Pagination row ------------------------------------------------------------


def add_pagination_row(
    builder: InlineKeyboardBuilder,
    *,
    entity: str,
    page: int,
    total_pages: int,
    page_size: int = 10,
) -> None:
    """Append ◀ page/total ▶ navigation to an existing builder."""
    buttons: list[InlineKeyboardButton] = []

    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=PageCallback(entity=entity, page=page - 1, size=page_size).pack(),
            )
        )

    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=PageCallback(entity=entity, page=page + 1, size=page_size).pack(),
            )
        )

    builder.row(*buttons)


# -- Confirmation prompt -------------------------------------------------------


def confirm_kb(tag: str = "") -> InlineKeyboardMarkup:
    """Two-button confirm / cancel prompt for destructive actions."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить",
        callback_data=ConfirmCallback(action=ConfirmAction.YES, tag=tag),
    )
    builder.button(
        text="❌ Отмена",
        callback_data=ConfirmCallback(action=ConfirmAction.NO, tag=tag),
    )
    builder.adjust(2)
    return builder.as_markup()
