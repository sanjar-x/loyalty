"""Typed CallbackData factories for common bot interactions.

Using typed factories instead of raw ``f"action:{id}"`` strings ensures
compile-time safety, automatic (de)serialisation, and short prefixes
that stay within Telegram's 64-byte callback_data limit.
"""

from enum import IntEnum

from aiogram.filters.callback_data import CallbackData

# -- Navigation ----------------------------------------------------------------


class NavAction(IntEnum):
    """Navigation targets used by the global nav keyboard row."""

    BACK = 0
    HOME = 1
    CANCEL = 2


class NavCallback(CallbackData, prefix="nav"):
    """Navigate between screens (back / home / cancel)."""

    action: NavAction
    ctx: str = ""  # optional origin context for smarter "back"


# -- Pagination ----------------------------------------------------------------


class PageCallback(CallbackData, prefix="pg"):
    """Generic pagination for any entity list."""

    entity: str  # e.g. "products", "orders"
    page: int
    size: int = 10


# -- Confirmation --------------------------------------------------------------


class ConfirmAction(IntEnum):
    """Confirm / reject a destructive or important action."""

    YES = 1
    NO = 0


class ConfirmCallback(CallbackData, prefix="cfm"):
    """Generic confirm / reject prompt."""

    action: ConfirmAction
    tag: str = ""  # identifies *what* is being confirmed
