# src/modules/user/presentation/schemas.py
import uuid

from pydantic import Field, model_validator

from src.shared.schemas import CamelModel


class UserProfileResponse(CamelModel):
    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


class UpdateProfileRequest(CamelModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    profile_email: str | None = Field(None, max_length=320)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateProfileRequest:
        if all(
            v is None for v in (self.first_name, self.last_name, self.phone, self.profile_email)
        ):
            raise ValueError("At least one field must be provided")
        return self
