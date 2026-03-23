import uuid
from datetime import UTC, datetime

from src.modules.user.domain.entities import Customer


class TestCustomer:
    def _make_customer(
        self,
        first_name: str = "John",
        last_name: str = "Doe",
        phone: str | None = "+1234567890",
        profile_email: str | None = "customer@example.com",
    ) -> Customer:
        now = datetime.now(UTC)
        return Customer(
            id=uuid.uuid4(),
            profile_email=profile_email,
            first_name=first_name,
            last_name=last_name,
            username=None,
            phone=phone,
            referral_code="ABCD1234",
            referred_by=None,
            created_at=now,
            updated_at=now,
        )

    def test_create_from_identity(self):
        identity_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            profile_email="customer@example.com",
            referral_code="REFCODE1",
        )
        assert customer.id == identity_id
        assert customer.profile_email == "customer@example.com"
        assert customer.first_name == ""
        assert customer.last_name == ""
        assert customer.referral_code == "REFCODE1"

    def test_update_profile(self):
        customer = self._make_customer()
        customer.update_profile(first_name="Jane", phone="+9876543210")
        assert customer.first_name == "Jane"
        assert customer.phone == "+9876543210"
        assert customer.last_name == "Doe"  # unchanged

    def test_update_profile_ignores_unknown_fields(self):
        customer = self._make_customer()
        customer.update_profile(unknown_field="value")
        # should not raise, unknown fields are silently ignored

    def test_anonymize_replaces_pii(self):
        customer = self._make_customer(
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            profile_email="customer@example.com",
        )
        customer.anonymize()
        assert customer.first_name == "[DELETED]"
        assert customer.last_name == "[DELETED]"
        assert customer.phone is None
        assert customer.profile_email is None
        assert customer.referral_code == "ABCD1234"  # preserved

    def test_anonymize_is_idempotent(self):
        customer = self._make_customer()
        customer.anonymize()
        customer.anonymize()  # should not raise
        assert customer.first_name == "[DELETED]"

    def test_create_from_identity_uses_shared_pk(self):
        identity_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            referral_code="REF12345",
        )
        assert customer.id == identity_id

    def test_update_profile_partial_fields(self):
        customer = self._make_customer(first_name="John", last_name="Doe")
        customer.update_profile(first_name="Jane")
        assert customer.first_name == "Jane"
        assert customer.last_name == "Doe"  # unchanged
