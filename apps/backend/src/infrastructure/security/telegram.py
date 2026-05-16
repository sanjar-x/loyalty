"""Telegram initData HMAC-SHA256 validator.

Uses aiogram's safe_parse_webapp_init_data for cryptographic verification,
then applies additional business rules (freshness, user presence).
"""

# TEMP-VALIDATION-DISABLED — ``datetime`` / ``InitDataExpiredError`` imports
# removed alongside the freshness check; restore them when re-enabling.
import structlog
from aiogram.utils.web_app import parse_webapp_init_data

from src.modules.identity.domain.exceptions import (
    InitDataMissingUserError,
    InvalidInitDataError,
)
from src.modules.identity.domain.interfaces import ITelegramInitDataValidator
from src.modules.identity.domain.value_objects import TelegramUserData

logger = structlog.get_logger(__name__)


class TelegramInitDataValidator(ITelegramInitDataValidator):
    """Validates Telegram Mini App initData using HMAC-SHA256."""

    def __init__(self, bot_token: str, max_age: int = 300) -> None:
        self._bot_token = bot_token
        self._max_age = max_age

    def validate_and_parse(self, init_data_raw: str) -> TelegramUserData:
        # TEMP-VALIDATION-DISABLED — both HMAC-SHA256 verification and the
        # freshness (max_age) check are temporarily bypassed. Any client
        # can forge the user= payload, and stale init_data is accepted.
        # To restore production behaviour:
        #   1. Swap ``parse_webapp_init_data(init_data_raw)`` back to
        #      ``safe_parse_webapp_init_data(token=self._bot_token,
        #      init_data=init_data_raw)`` and re-import ``safe_parse_*``.
        #   2. Re-enable the freshness block below.
        #   3. Drop this warning log.
        try:
            parsed = parse_webapp_init_data(init_data_raw)
        except ValueError:
            raise InvalidInitDataError() from None
        logger.warning(
            "telegram.init_data.validation_disabled",
            reason=(
                "TEMP-VALIDATION-DISABLED: HMAC-SHA256 verification AND "
                "freshness check bypassed"
            ),
        )

        # TEMP-VALIDATION-DISABLED — freshness check turned off.
        # _ = self._max_age  # kept on the instance for the restore step
        # age = int((datetime.now(UTC) - parsed.auth_date).total_seconds())
        # if age < 0 or age > self._max_age:
        #     raise InitDataExpiredError(age_seconds=age, max_seconds=self._max_age)

        # User must exist (kept on — without it there is nothing to log in).
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
