
from src.modules.identity.domain.value_objects import (
    AccountType,
    IdentityType,
    InvitationStatus,
)


class TestIdentityType:
    def test_local_value(self):
        assert IdentityType.LOCAL == "LOCAL"

    def test_oidc_value(self):
        assert IdentityType.OIDC == "OIDC"

    def test_is_string_enum(self):
        assert isinstance(IdentityType.LOCAL, str)


class TestAccountType:
    def test_customer_value(self):
        assert AccountType.CUSTOMER.value == "CUSTOMER"

    def test_staff_value(self):
        assert AccountType.STAFF.value == "STAFF"

    def test_is_string_enum(self):
        assert isinstance(AccountType.CUSTOMER, str)


class TestInvitationStatus:
    def test_all_statuses_exist(self):
        assert InvitationStatus.PENDING.value == "PENDING"
        assert InvitationStatus.ACCEPTED.value == "ACCEPTED"
        assert InvitationStatus.EXPIRED.value == "EXPIRED"
        assert InvitationStatus.REVOKED.value == "REVOKED"
