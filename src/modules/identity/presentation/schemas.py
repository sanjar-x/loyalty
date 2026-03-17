# src/modules/identity/presentation/schemas.py
import uuid

from pydantic import EmailStr, Field

from src.shared.schemas import CamelModel

# --- Auth schemas ---


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(CamelModel):
    identity_id: uuid.UUID
    message: str = "Registration successful"


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(CamelModel):
    refresh_token: str


class LoginOIDCRequest(CamelModel):
    provider_token: str


# --- Admin schemas ---


class CreateRoleRequest(CamelModel):
    name: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)


class CreateRoleResponse(CamelModel):
    role_id: uuid.UUID
    message: str = "Role created"


class AssignRoleRequest(CamelModel):
    role_id: uuid.UUID


class MessageResponse(CamelModel):
    message: str
