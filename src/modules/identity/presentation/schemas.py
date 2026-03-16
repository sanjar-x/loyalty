# src/modules/identity/presentation/schemas.py
import uuid

from pydantic import BaseModel, EmailStr, Field

# --- Auth schemas ---


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    identity_id: uuid.UUID
    message: str = "Registration successful"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginOIDCRequest(BaseModel):
    provider_token: str


# --- Admin schemas ---


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)


class CreateRoleResponse(BaseModel):
    role_id: uuid.UUID
    message: str = "Role created"


class AssignRoleRequest(BaseModel):
    role_id: uuid.UUID


class MessageResponse(BaseModel):
    message: str
