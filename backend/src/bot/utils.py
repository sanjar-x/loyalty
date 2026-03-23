"""Shared bot utilities (message splitting, chat actions, etc.)."""

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
