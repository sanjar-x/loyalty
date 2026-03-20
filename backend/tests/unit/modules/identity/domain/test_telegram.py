# tests/unit/modules/identity/domain/test_telegram.py
"""Unit tests for Telegram domain objects."""

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.value_objects import (
    AuthProvider,
    IdentityType,
    PrimaryAuthMethod,
    TRUSTED_EMAIL_PROVIDERS,
    TelegramUserData,
)


class TestPrimaryAuthMethod:
    def test_telegram_value(self):
        assert PrimaryAuthMethod.TELEGRAM == "TELEGRAM"
        assert PrimaryAuthMethod.TELEGRAM.value == "TELEGRAM"

    def test_all_methods(self):
        assert set(PrimaryAuthMethod) == {PrimaryAuthMethod.LOCAL, PrimaryAuthMethod.OIDC, PrimaryAuthMethod.TELEGRAM}


class TestAuthProvider:
    def test_values(self):
        assert AuthProvider.TELEGRAM == "telegram"
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.APPLE == "apple"

    def test_trusted_email_providers(self):
        assert AuthProvider.GOOGLE in TRUSTED_EMAIL_PROVIDERS
        assert AuthProvider.APPLE in TRUSTED_EMAIL_PROVIDERS
        assert AuthProvider.TELEGRAM not in TRUSTED_EMAIL_PROVIDERS


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


from src.modules.identity.domain.entities import TelegramCredentials
from src.modules.identity.domain.value_objects import AccountType


class TestIdentityRegisterTelegram:
    def test_register_telegram_type(self):
        from src.modules.identity.domain.entities import Identity

        identity = Identity.register(IdentityType.TELEGRAM, AccountType.CUSTOMER)
        assert identity.type == IdentityType.TELEGRAM
        assert identity.account_type == AccountType.CUSTOMER
        assert identity.is_active is True


class TestTelegramCredentials:
    @pytest.fixture
    def credentials(self) -> TelegramCredentials:
        now = datetime.now(UTC)
        return TelegramCredentials(
            identity_id=uuid.uuid4(),
            telegram_id=123456789,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url="https://example.com/photo.jpg",
            allows_write_to_pm=True,
            created_at=now,
            updated_at=now,
        )

    def test_update_profile_detects_changes(self, credentials: TelegramCredentials):
        new_data = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="Jane",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=True,
            photo_url="https://example.com/photo.jpg",
            allows_write_to_pm=True,
            start_param=None,
        )
        assert credentials.update_profile(new_data) is True
        assert credentials.first_name == "Jane"
        assert credentials.is_premium is True

    def test_update_profile_no_changes(self, credentials: TelegramCredentials):
        same_data = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url="https://example.com/photo.jpg",
            allows_write_to_pm=True,
            start_param=None,
        )
        original_updated_at = credentials.updated_at
        assert credentials.update_profile(same_data) is False
        assert credentials.updated_at == original_updated_at

    def test_photo_url_not_erased_by_none(self, credentials: TelegramCredentials):
        data_no_photo = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url=None,
            allows_write_to_pm=True,
            start_param=None,
        )
        credentials.update_profile(data_no_photo)
        assert credentials.photo_url == "https://example.com/photo.jpg"

    def test_photo_url_updated_when_new_value(self, credentials: TelegramCredentials):
        data_new_photo = TelegramUserData(
            telegram_id=credentials.telegram_id,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            language_code="en",
            is_premium=False,
            photo_url="https://example.com/new_photo.jpg",
            allows_write_to_pm=True,
            start_param=None,
        )
        assert credentials.update_profile(data_new_photo) is True
        assert credentials.photo_url == "https://example.com/new_photo.jpg"


from src.modules.identity.domain.events import TelegramIdentityCreatedEvent
from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)


class TestTelegramIdentityCreatedEvent:
    def test_requires_identity_id(self):
        with pytest.raises(ValueError, match="identity_id is required"):
            TelegramIdentityCreatedEvent(aggregate_id="x")

    def test_sets_aggregate_id_from_identity_id(self):
        uid = uuid.uuid4()
        event = TelegramIdentityCreatedEvent(
            identity_id=uid, telegram_id=123,
        )
        assert event.aggregate_id == str(uid)
        assert event.aggregate_type == "Identity"
        assert event.event_type == "telegram_identity_created"

    def test_start_param_optional(self):
        event = TelegramIdentityCreatedEvent(
            identity_id=uuid.uuid4(), telegram_id=123, start_param="REF123",
        )
        assert event.start_param == "REF123"


class TestTelegramExceptions:
    def test_invalid_init_data_is_401(self):
        exc = InvalidInitDataError()
        assert exc.status_code == 401
        assert exc.error_code == "INVALID_INIT_DATA"

    def test_init_data_expired_has_details(self):
        exc = InitDataExpiredError(age_seconds=600, max_seconds=300)
        assert exc.status_code == 401
        assert exc.details == {"age_seconds": 600, "max_seconds": 300}

    def test_init_data_missing_user_is_401(self):
        exc = InitDataMissingUserError()
        assert exc.status_code == 401
        assert exc.error_code == "INIT_DATA_MISSING_USER"
