# tests/unit/modules/user/presentation/test_schemas.py
"""Tests for User presentation schema validations."""

import pytest
from pydantic import ValidationError

from src.modules.user.presentation.schemas import UpdateProfileRequest


class TestUpdateProfileRequest:
    def test_at_least_one_field_required(self):
        with pytest.raises(ValidationError, match="At least one field"):
            UpdateProfileRequest()

    def test_accepts_first_name_only(self):
        m = UpdateProfileRequest(first_name="John")
        assert m.first_name == "John"
        assert m.last_name is None

    def test_accepts_phone_only(self):
        m = UpdateProfileRequest(phone="+1234567890")
        assert m.phone == "+1234567890"

    def test_accepts_profile_email_only(self):
        m = UpdateProfileRequest(profile_email="user@example.com")
        assert m.profile_email == "user@example.com"

    def test_accepts_all_fields(self):
        m = UpdateProfileRequest(
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            profile_email="john@example.com",
        )
        assert m.first_name == "John"
        assert m.last_name == "Doe"

    def test_first_name_max_length_100(self):
        with pytest.raises(ValidationError, match="first_name"):
            UpdateProfileRequest(first_name="x" * 101)

    def test_last_name_max_length_100(self):
        with pytest.raises(ValidationError, match="last_name"):
            UpdateProfileRequest(last_name="x" * 101)

    def test_phone_max_length_20(self):
        with pytest.raises(ValidationError, match="phone"):
            UpdateProfileRequest(phone="1" * 21)

    def test_profile_email_max_length_320(self):
        with pytest.raises(ValidationError, match="profile_email"):
            UpdateProfileRequest(profile_email="a" * 321)
