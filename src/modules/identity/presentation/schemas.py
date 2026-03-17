"""Pydantic request/response schemas for the Identity module API.

All schemas use CamelModel (camelCase JSON serialization) and include
field-level validation constraints.
"""

import uuid

from pydantic import EmailStr, Field

from src.shared.schemas import CamelModel

# ---------------------------------------------------------------------------
# Authentication schemas
# ---------------------------------------------------------------------------


class RegisterRequest(CamelModel):
    """Request payload for identity registration.

    Attributes:
        email: A valid email address.
        password: Plaintext password (8-128 characters).
    """

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(CamelModel):
    """Response payload for successful registration.

    Attributes:
        identity_id: The newly created identity's UUID.
        message: Human-readable confirmation message.
    """

    identity_id: uuid.UUID
    message: str = "Registration successful"


class LoginRequest(CamelModel):
    """Request payload for email/password login.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password (max 128 characters).
    """

    email: EmailStr
    password: str = Field(..., max_length=128)


class TokenResponse(CamelModel):
    """Response payload containing an access/refresh token pair.

    Attributes:
        access_token: Short-lived JWT access token.
        refresh_token: Opaque refresh token for rotation.
        token_type: Token type (always "bearer").
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(CamelModel):
    """Request payload for token refresh.

    Attributes:
        refresh_token: The current opaque refresh token.
    """

    refresh_token: str


class LoginOIDCRequest(CamelModel):
    """Request payload for OIDC provider login.

    Attributes:
        provider_token: The token issued by the OIDC provider.
    """

    provider_token: str


# ---------------------------------------------------------------------------
# Admin schemas
# ---------------------------------------------------------------------------


class CreateRoleRequest(CamelModel):
    """Request payload for creating a custom role.

    Attributes:
        name: Unique role name (lowercase letters and underscores, 2-100 chars).
        description: Optional human-readable description (max 500 chars).
    """

    name: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)


class CreateRoleResponse(CamelModel):
    """Response payload for successful role creation.

    Attributes:
        role_id: The newly created role's UUID.
        message: Human-readable confirmation message.
    """

    role_id: uuid.UUID
    message: str = "Role created"


class AssignRoleRequest(CamelModel):
    """Request payload for assigning a role to an identity.

    Attributes:
        role_id: The UUID of the role to assign.
    """

    role_id: uuid.UUID


class MessageResponse(CamelModel):
    """Generic response payload with a human-readable message.

    Attributes:
        message: The response message.
    """

    message: str
