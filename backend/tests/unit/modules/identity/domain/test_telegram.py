# tests/unit/modules/identity/domain/test_telegram.py
"""Unit tests for Telegram domain objects."""

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.entities import Identity, LinkedAccount
from src.modules.identity.domain.events import (
    IdentityTokenVersionBumpedEvent,
    LinkedAccountCreatedEvent,
    LinkedAccountDeletedEvent,
)
from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)
from src.modules.identity.domain.value_objects import (
    TRUSTED_EMAIL_PROVIDERS,
    AccountType,
    AuthProvider,
    IdentityType,
    PrimaryAuthMethod,
    TelegramUserData,
)


class TestPrimaryAuthMethod:
    def test_telegram_value(self):
        assert PrimaryAuthMethod.TELEGRAM == "TELEGRAM"
        assert PrimaryAuthMethod.TELEGRAM.value == "TELEGRAM"

    def test_all_methods(self):
        assert set(PrimaryAuthMethod) == {
            PrimaryAuthMethod.LOCAL,
            PrimaryAuthMethod.OIDC,
            PrimaryAuthMethod.TELEGRAM,
        }


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
            sample_data.telegram_id = 999  # ty:ignore[invalid-assignment]

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


class TestIdentityRegisterTelegram:
    def test_register_telegram_type(self):
        identity = Identity.register(IdentityType.TELEGRAM, AccountType.CUSTOMER)
        assert identity.type == IdentityType.TELEGRAM
        assert identity.account_type == AccountType.CUSTOMER
        assert identity.is_active is True


class TestLinkedAccount:
    def test_update_metadata_returns_true_on_change(self):
        now = datetime.now(UTC)
        account = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            provider="telegram",
            provider_sub_id="123456",
            provider_email=None,
            email_verified=False,
            provider_metadata={"username": "old"},
            created_at=now,
            updated_at=now,
        )
        old_updated = account.updated_at
        changed = account.update_metadata({"username": "new"})
        assert changed is True
        assert account.provider_metadata == {"username": "new"}
        assert account.updated_at >= old_updated

    def test_update_metadata_returns_false_no_change(self):
        now = datetime.now(UTC)
        meta = {"username": "same"}
        account = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            provider="telegram",
            provider_sub_id="123456",
            provider_email=None,
            email_verified=False,
            provider_metadata=meta,
            created_at=now,
            updated_at=now,
        )
        old_updated = account.updated_at
        changed = account.update_metadata({"username": "same"})
        assert changed is False
        assert account.updated_at == old_updated


class TestLinkedAccountCreatedEvent:
    def test_creation(self):
        identity_id = uuid.uuid4()
        event = LinkedAccountCreatedEvent(
            identity_id=identity_id,
            provider="telegram",
            provider_sub_id="123456",
            provider_metadata={"username": "test"},
            start_param="ref123",
            is_new_identity=True,
            aggregate_id=str(identity_id),
        )
        assert event.provider == "telegram"
        assert event.is_new_identity is True
        assert event.event_type == "linked_account_created"

    def test_requires_identity_id(self):
        with pytest.raises(ValueError):
            LinkedAccountCreatedEvent(
                identity_id=None,
                provider="telegram",
                provider_sub_id="123",
                provider_metadata={},
                start_param=None,
                is_new_identity=True,
            )


class TestLinkedAccountDeletedEvent:
    def test_creation(self):
        identity_id = uuid.uuid4()
        event = LinkedAccountDeletedEvent(
            identity_id=identity_id,
            provider="telegram",
            provider_sub_id="123456",
            aggregate_id=str(identity_id),
        )
        assert event.event_type == "linked_account_removed"


class TestIdentityTokenVersionBumpedEvent:
    def test_creation(self):
        identity_id = uuid.uuid4()
        event = IdentityTokenVersionBumpedEvent(
            identity_id=identity_id,
            new_version=2,
            reason="password_change",
            aggregate_id=str(identity_id),
        )
        assert event.new_version == 2
        assert event.reason == "password_change"


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
