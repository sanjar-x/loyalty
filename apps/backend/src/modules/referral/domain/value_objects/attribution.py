"""Attribution-context value objects.

Records *how* a referral was attributed (Telegram deep-link, web, manual
admin override, …) and what request-level context surrounded the
signup. The fraud evaluator reads these fields to compute its
heuristic score.
"""

from __future__ import annotations

from enum import StrEnum

import attrs


class ReferralChannel(StrEnum):
    """Channel through which a referral attribution was captured."""

    TG_START_PARAM = "tg_start_param"
    TG_SHARE = "tg_share"
    TG_STORY = "tg_story"
    WEB_LINK = "web_link"
    MANUAL_ADMIN = "manual_admin"


@attrs.frozen
class AttributionContext:
    """Frozen snapshot of the attribution-time request context.

    Persisted on the :class:`Referral` aggregate so the fraud evaluator
    can reason about same-IP / same-device / fast-signup signals
    without relying on transient session data.
    """

    channel: ReferralChannel
    chat_instance: str | None = None
    auth_date: str | None = None
    signup_ip: str | None = None
    signup_user_agent: str | None = None
