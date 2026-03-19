import pytest

from src.modules.identity.domain.value_objects import (
    AccountType,
    IdentityType,
    InvitationStatus,
    PermissionCode,
)


class TestIdentityType:
    def test_local_value(self):
        assert IdentityType.LOCAL == "LOCAL"

    def test_oidc_value(self):
        assert IdentityType.OIDC == "OIDC"

    def test_is_string_enum(self):
        assert isinstance(IdentityType.LOCAL, str)


class TestPermissionCode:
    def test_valid_code(self):
        code = PermissionCode("brands:create")
        assert code.resource == "brands"
        assert code.action == "create"
        assert str(code) == "brands:create"

    def test_invalid_format_no_colon(self):
        with pytest.raises(ValueError, match="resource:action"):
            PermissionCode("invalid")

    def test_invalid_format_empty_resource(self):
        with pytest.raises(ValueError, match="resource:action"):
            PermissionCode(":create")

    def test_invalid_format_empty_action(self):
        with pytest.raises(ValueError, match="resource:action"):
            PermissionCode("brands:")

    def test_equality(self):
        assert PermissionCode("brands:create") == PermissionCode("brands:create")

    def test_hash(self):
        codes = {PermissionCode("brands:create"), PermissionCode("brands:create")}
        assert len(codes) == 1


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
