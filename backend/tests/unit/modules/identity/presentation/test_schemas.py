# tests/unit/modules/identity/presentation/test_schemas.py
"""Tests for Identity presentation schema validations."""

import pytest
from pydantic import ValidationError

from src.modules.identity.presentation.schemas import (
    CreateRoleRequest,
    LoginRequest,
    RegisterRequest,
)


class TestLoginRequest:
    def test_valid_login(self):
        m = LoginRequest(email="user@example.com", password="secret123")
        assert m.password == "secret123"

    def test_password_max_length_128(self):
        with pytest.raises(ValidationError, match="password"):
            LoginRequest(email="user@example.com", password="x" * 129)

    def test_password_at_max_length_accepted(self):
        m = LoginRequest(email="user@example.com", password="x" * 128)
        assert len(m.password) == 128


class TestRegisterRequest:
    def test_valid_registration(self):
        m = RegisterRequest(email="new@example.com", password="S3cure!Pass")
        assert m.email == "new@example.com"

    def test_password_min_length_8(self):
        with pytest.raises(ValidationError, match="password"):
            RegisterRequest(email="new@example.com", password="short")

    def test_password_max_length_128(self):
        with pytest.raises(ValidationError, match="password"):
            RegisterRequest(email="new@example.com", password="x" * 129)

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError, match="email"):
            RegisterRequest(email="not-an-email", password="S3cure!Pass")


class TestCreateRoleRequest:
    def test_valid_role(self):
        m = CreateRoleRequest(name="admin_user")
        assert m.name == "admin_user"

    def test_name_min_length_2(self):
        with pytest.raises(ValidationError, match="name"):
            CreateRoleRequest(name="a")

    def test_name_max_length_100(self):
        with pytest.raises(ValidationError, match="name"):
            CreateRoleRequest(name="a" * 101)

    @pytest.mark.parametrize("name", ["Admin", "has-dash", "has space", "123"])
    def test_name_pattern_rejects_invalid(self, name: str):
        with pytest.raises(ValidationError, match="name"):
            CreateRoleRequest(name=name)

    def test_name_pattern_accepts_lowercase_underscore(self):
        m = CreateRoleRequest(name="catalog_manager")
        assert m.name == "catalog_manager"
