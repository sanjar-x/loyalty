"""Unit tests for TelegramInitDataValidator."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.security.telegram import TelegramInitDataValidator
from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)
from src.modules.identity.domain.value_objects import TelegramUserData

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


class TestTelegramInitDataValidator:
    @pytest.fixture
    def validator(self) -> TelegramInitDataValidator:
        return TelegramInitDataValidator(bot_token=BOT_TOKEN, max_age=300)

    def _mock_parsed(self, **overrides) -> MagicMock:
        user = MagicMock()
        user.id = 123456789
        user.first_name = "John"
        user.last_name = "Doe"
        user.username = "johndoe"
        user.language_code = "en"
        user.is_premium = True
        user.photo_url = "https://t.me/photo.jpg"
        user.allows_write_to_pm = True

        parsed = MagicMock()
        parsed.user = user
        parsed.auth_date = overrides.get("auth_date", datetime.now(UTC))
        parsed.start_param = overrides.get("start_param", "REF123")

        if "user" in overrides:
            parsed.user = overrides["user"]

        return parsed

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_valid_init_data_returns_telegram_user_data(self, mock_parse, validator):
        mock_parse.return_value = self._mock_parsed()
        result = validator.validate_and_parse("valid_init_data")
        assert isinstance(result, TelegramUserData)
        assert result.telegram_id == 123456789
        assert result.first_name == "John"
        assert result.is_premium is True
        assert result.start_param == "REF123"

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_invalid_signature_raises(self, mock_parse, validator):
        mock_parse.side_effect = ValueError("Invalid init data signature")
        with pytest.raises(InvalidInitDataError):
            validator.validate_and_parse("bad_data")

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_expired_auth_date_raises(self, mock_parse, validator):
        old_date = datetime.now(UTC) - timedelta(seconds=600)
        mock_parse.return_value = self._mock_parsed(auth_date=old_date)
        with pytest.raises(InitDataExpiredError) as exc_info:
            validator.validate_and_parse("old_data")
        assert exc_info.value.details["max_seconds"] == 300

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_future_auth_date_raises(self, mock_parse, validator):
        future_date = datetime.now(UTC) + timedelta(seconds=60)
        mock_parse.return_value = self._mock_parsed(auth_date=future_date)
        with pytest.raises(InitDataExpiredError):
            validator.validate_and_parse("future_data")

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_missing_user_raises(self, mock_parse, validator):
        mock_parse.return_value = self._mock_parsed(user=None)
        with pytest.raises(InitDataMissingUserError):
            validator.validate_and_parse("no_user_data")

    @patch("src.infrastructure.security.telegram.safe_parse_webapp_init_data")
    def test_optional_fields_default_to_false(self, mock_parse, validator):
        user = MagicMock()
        user.id = 1
        user.first_name = "A"
        user.last_name = None
        user.username = None
        user.language_code = None
        user.is_premium = None
        user.photo_url = None
        user.allows_write_to_pm = None
        mock_parse.return_value = self._mock_parsed(user=user)
        mock_parse.return_value.user = user
        result = validator.validate_and_parse("data")
        assert result.is_premium is False
        assert result.allows_write_to_pm is False
