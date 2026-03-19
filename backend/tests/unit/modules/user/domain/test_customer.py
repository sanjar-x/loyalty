import uuid

from src.modules.user.domain.entities import Customer


class TestCustomerCreate:
    def test_create_from_identity(self):
        identity_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            profile_email="test@example.com",
            referral_code="ABC12345",
        )
        assert customer.id == identity_id
        assert customer.profile_email == "test@example.com"
        assert customer.referral_code == "ABC12345"
        assert customer.referred_by is None
        assert customer.first_name == ""
        assert customer.last_name == ""

    def test_create_with_referrer(self):
        referrer_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            referral_code="XYZ99999",
            referred_by=referrer_id,
        )
        assert customer.referred_by == referrer_id


class TestCustomerUpdate:
    def test_update_profile_partial(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(), referral_code="AAA11111"
        )
        old_updated = customer.updated_at
        customer.update_profile(first_name="John")
        assert customer.first_name == "John"
        assert customer.last_name == ""
        assert customer.updated_at >= old_updated


class TestCustomerAnonymize:
    def test_anonymize_clears_pii_keeps_referral(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            profile_email="test@example.com",
            referral_code="KEEP1234",
        )
        customer.update_profile(first_name="John", last_name="Doe", phone="+123")
        customer.anonymize()
        assert customer.first_name == "[DELETED]"
        assert customer.last_name == "[DELETED]"
        assert customer.phone is None
        assert customer.profile_email is None
        assert customer.referral_code == "KEEP1234"
