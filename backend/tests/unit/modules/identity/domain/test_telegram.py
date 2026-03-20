# tests/unit/modules/identity/domain/test_telegram.py
"""Unit tests for Telegram domain objects."""

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.value_objects import IdentityType, TelegramUserData


class TestIdentityTypeTelegram:
    def test_telegram_type_exists(self):
        assert IdentityType.TELEGRAM == "TELEGRAM"

    def test_telegram_type_is_string(self):
        assert isinstance(IdentityType.TELEGRAM, str)


class TestTelegramUserData:
    @pytest.fixture
    def sample_data(self) -> TelegramUserData:
        return TelegramUserData(
            telegram_id=123456789,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=True,
            photo_url="https://t.me/i/userpic/320/photo.jpg",
            allows_write_to_pm=True,
            start_param="ref_ABC123",
        )

    def test_immutable(self, sample_data: TelegramUserData):
        with pytest.raises(FrozenInstanceError):
            sample_data.telegram_id = 999  # type: ignore[misc]

    def test_all_fields_accessible(self, sample_data: TelegramUserData):
        assert sample_data.telegram_id == 123456789
        assert sample_data.first_name == "John"
        assert sample_data.last_name == "Doe"
        assert sample_data.username == "johndoe"
        assert sample_data.language_code == "en"
        assert sample_data.is_premium is True
        assert sample_data.photo_url == "https://t.me/i/userpic/320/photo.jpg"
        assert sample_data.allows_write_to_pm is True
        assert sample_data.start_param == "ref_ABC123"

    def test_optional_fields_none(self):
        data = TelegramUserData(
            telegram_id=1,
            first_name="A",
            last_name=None,
            username=None,
            language_code=None,
            is_premium=False,
            photo_url=None,
            allows_write_to_pm=False,
            start_param=None,
        )
        assert data.last_name is None
        assert data.start_param is None
