"""Shared bot utilities (message splitting, chat actions, etc.)."""

from aiogram.types import Message

MAX_MESSAGE_LENGTH = 4096


def split_long_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split *text* into chunks that fit a single Telegram message.

    Tries to break on newlines first, then spaces, and falls back to
    a hard cut only when neither is available.
    """
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length

        parts.append(text[:split_at])
        text = text[split_at:].lstrip()

    return parts


async def send_long_message(
    message: Message,
    text: str,
    **kwargs: object,
) -> None:
    """Send a potentially long message, splitting if necessary.

    Only the **last** chunk receives ``reply_markup`` (if provided in
    *kwargs*) so the keyboard sticks to the final piece.
    """
    parts = split_long_text(text)
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            # intermediate chunks — strip reply_markup
            kw = {k: v for k, v in kwargs.items() if k != "reply_markup"}
            await message.answer(part, **kw)
        else:
            await message.answer(part, **kwargs)
