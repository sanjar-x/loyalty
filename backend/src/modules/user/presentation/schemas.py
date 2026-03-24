"""Pydantic schemas for profile presentation layer.

Defines request and response models for the profile API endpoints.
All schemas use camelCase serialization via the shared ``CamelModel`` base.
"""

import uuid

from pydantic import Field, model_validator

from src.shared.schemas import CamelModel


class ProfileResponse(CamelModel):
    """Response schema for customer profile data.

    Attributes:
        id: The customer's unique identifier.
        profile_email: Optional display email address.
        first_name: Customer's first name.
        last_name: Customer's last name.
        phone: Optional phone number.
    """

    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


class UpdateProfileRequest(CamelModel):
    """Request schema for partial profile updates.

    At least one field must be provided. All fields are optional; only
    non-None values will be applied to the customer's profile.

    Attributes:
        first_name: New first name (max 100 chars), or None to skip.
        last_name: New last name (max 100 chars), or None to skip.
        phone: New phone number (max 20 chars), or None to skip.
        profile_email: New display email (max 320 chars), or None to skip.
    """

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    profile_email: str | None = Field(None, max_length=320)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateProfileRequest:
        """Validate that at least one field is provided for update."""
        if all(
            v is None
            for v in (self.first_name, self.last_name, self.phone, self.profile_email)
        ):
            raise ValueError("At least one field must be provided")
        return self
