"""Telegram initData HMAC-SHA256 validator.

Uses aiogram's safe_parse_webapp_init_data for cryptographic verification,
then applies additional business rules (freshness, user presence).
"""

from datetime import UTC, datetime

from aiogram.utils.web_app import safe_parse_webapp_init_data

from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)
from src.modules.identity.domain.interfaces import ITelegramInitDataValidator
from src.modules.identity.domain.value_objects import TelegramUserData


class TelegramInitDataValidator(ITelegramInitDataValidator):
    """Validates Telegram Mini App initData using HMAC-SHA256."""

    def __init__(self, bot_token: str, max_age: int = 300) -> None:
        self._bot_token = bot_token
        self._max_age = max_age

    def validate_and_parse(self, init_data_raw: str) -> TelegramUserData:
        # 1. HMAC-SHA256 validation via aiogram
        try:
            parsed = safe_parse_webapp_init_data(
                token=self._bot_token, init_data=init_data_raw,
            )
        except ValueError:
            raise InvalidInitDataError()

        # 2. Freshness check (aiogram does NOT do this)
        age = int((datetime.now(UTC) - parsed.auth_date).total_seconds())
        if age < 0:
            raise InitDataExpiredError(age_seconds=age, max_seconds=self._max_age)
        if age > self._max_age:
            raise InitDataExpiredError(age_seconds=age, max_seconds=self._max_age)

        # 3. User must exist
        if parsed.user is None:
            raise InitDataMissingUserError()

        user = parsed.user
        return TelegramUserData(
            telegram_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=user.is_premium or False,
            photo_url=user.photo_url,
            allows_write_to_pm=user.allows_write_to_pm or False,
            start_param=parsed.start_param,
        )
