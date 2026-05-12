import uuid

from src.modules.user.domain.entities import Customer


class TestCustomerCreate:
    def test_create_from_identity(self):
        identity_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            profile_email="test@example.com",
        )
        assert customer.id == identity_id
        assert customer.profile_email == "test@example.com"
        assert customer.first_name == ""
        assert customer.last_name == ""

    def test_create_with_profile_data(self):
        identity_id = uuid.uuid4()
        customer = Customer.create_from_identity(
            identity_id=identity_id,
            first_name="Алексей",
            last_name="Иванов",
        )
        assert customer.first_name == "Алексей"
        assert customer.last_name == "Иванов"


class TestCustomerUpdate:
    def test_update_profile_partial(self):
        customer = Customer.create_from_identity(identity_id=uuid.uuid4())
        old_updated = customer.updated_at
        customer.update_profile(first_name="John")
        assert customer.first_name == "John"
        assert customer.last_name == ""
        assert customer.updated_at >= old_updated


class TestCustomerAnonymize:
    def test_anonymize_clears_pii(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            profile_email="test@example.com",
        )
        customer.update_profile(first_name="John", last_name="Doe", phone="+123")
        customer.anonymize()
        assert customer.first_name == "[DELETED]"
        assert customer.last_name == "[DELETED]"
        assert customer.phone is None
        assert customer.profile_email is None


class TestCustomerUsername:
    def test_create_with_username(self):
        customer = Customer.create_from_identity(
            identity_id=uuid.uuid4(),
            username="johndoe",
        )
        assert customer.username == "johndoe"

    def test_create_without_username(self):
        customer = Customer.create_from_identity(identity_id=uuid.uuid4())
        assert customer.username is None

    def test_update_profile_username(self):
        customer = Customer.create_from_identity(identity_id=uuid.uuid4())
        customer.update_profile(username="newname")
        assert customer.username == "newname"
