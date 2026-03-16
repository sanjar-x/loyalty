# src/modules/user/presentation/schemas.py
import uuid

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None


class UpdateProfileRequest(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    profile_email: str | None = Field(None, max_length=320)
