# tests/unit/modules/identity/domain/test_exceptions.py
"""Tests for Identity domain exceptions — remediation changes."""

from src.modules.identity.domain.exceptions import IdentityAlreadyExistsError


class TestIdentityAlreadyExistsError:
    def test_no_args_constructor(self):
        error = IdentityAlreadyExistsError()
        assert error.message == "Email already registered"
        assert error.error_code == "IDENTITY_ALREADY_EXISTS"

    def test_no_pii_in_details(self):
        error = IdentityAlreadyExistsError()
        assert not hasattr(error, "details") or "email" not in getattr(
            error, "details", {}
        )

    def test_status_code_409(self):
        error = IdentityAlreadyExistsError()
        assert error.status_code == 409
