"""Alert level enum + formatting helpers (HARD-2).

The formatter renders a Telegram-friendly plain-text message with an
emoji prefix per level. We deliberately avoid Telegram's MarkdownV2
because it requires escaping a long list of metacharacters in any
runtime-substituted body — every escape miss surfaces as ``Bad
Request: can't parse entities`` from the Bot API. Plain text keeps
the alert format robust at the cost of no syntax highlighting.
"""

from __future__ import annotations

from enum import StrEnum


class AlertLevel(StrEnum):
    """Severity discriminator for an outgoing alert."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


_PREFIX: dict[AlertLevel, str] = {
    AlertLevel.INFO: "ℹ️ INFO",
    AlertLevel.WARNING: "⚠️ WARNING",
    AlertLevel.CRITICAL: "🚨 CRITICAL",
}


def format_alert(level: AlertLevel, *, title: str, body: str) -> str:
    """Build the plain-text alert payload sent to Telegram.

    Args:
        level: Severity tag — controls the emoji prefix.
        title: One-line description of what fired.
        body: Free-form details (counts, IDs, timestamps).

    Returns:
        A multi-line string ready for ``sendMessage``.
    """
    return f"{_PREFIX[level]} — {title}\n\n{body}"
