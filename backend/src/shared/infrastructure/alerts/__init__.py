"""Ops alerting via Telegram (HARD-2).

Cross-cutting infrastructure for surfacing operational signals
(outbox lag, DLQ growth, deploy notifications) to a Telegram channel
configured via ``TG_ALERTS_CHANNEL``. The alerter reuses the existing
``BOT_TOKEN`` so no extra credentials are required at the Railway
service level.

Usage::

    from src.shared.infrastructure.alerts import (
        AlertLevel,
        TelegramAlerter,
        format_alert,
    )

    alerter = TelegramAlerter()
    await alerter.send(
        format_alert(AlertLevel.CRITICAL, title="DLQ growth", body="..."),
    )

The two scheduled monitors (``outbox_monitor`` / ``failed_tasks_monitor``)
use this kernel directly; they live under ``alerts.monitors``.
"""

from src.shared.infrastructure.alerts.alert_levels import AlertLevel, format_alert
from src.shared.infrastructure.alerts.telegram_alerter import TelegramAlerter

__all__ = [
    "AlertLevel",
    "TelegramAlerter",
    "format_alert",
]
